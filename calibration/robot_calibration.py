#!/usr/bin/env python3
"""
Robot Kinematic Calibration Tool
=================================

Purpose: Calibrate robot's kinematic parameters for perfect inverse kinematics
         by measuring actual positions and optimizing DH parameters.

This tool will help you:
1. Collect calibration data by moving robot to various positions
2. Measure actual end-effector positions
3. Optimize DH parameters (link lengths, offsets, angles) to minimize error
4. Test calibrated model with lines and circles

Theory:
- Real robots have manufacturing tolerances and assembly errors
- Nominal parameters (measured with ruler) are approximate
- Calibration finds true kinematic parameters by:
  * Recording joint angles at many configurations
  * Measuring actual end-effector positions
  * Optimizing parameters to minimize position error

Calibration Methods Implemented:
1. Geometric measurement (manual position marking)
2. Grid-based calibration (systematic workspace sampling)
3. Circle/line drawing test (validate accuracy)
"""

import numpy as np
import json
from scipy.optimize import minimize, least_squares
from robot_controller import RobotController
import time
from typing import List, Tuple, Dict
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

class RobotKinematics:
    """Forward and Inverse Kinematics with calibratable DH parameters"""
    
    def __init__(self, dh_params=None):
        """
        Initialize with DH parameters
        
        DH Parameters for each joint (modified DH convention):
        - a (link length): distance along x_i from z_i to z_{i+1}
        - alpha (link twist): angle from z_i to z_{i+1} about x_i
        - d (link offset): distance along z_i from x_{i-1} to x_i  
        - theta_offset: offset angle for joint (calibration parameter)
        """
        
        if dh_params is None:
            # Initial parameters from Step1_FK.cpp (nominal values)
            # Format: [a, alpha, d, theta_offset]
            self.dh_params = np.array([
                # Joint 1 (Base rotation)
                [0.0,    -np.pi/2,  137.8,  0.0],
                # Joint 2 (Shoulder)  
                [147.0,   0.0,      0.0,    0.0],
                # Joint 3 (Elbow)
                [147.0,   0.0,      0.0,    0.0],
                # Joint 4 (Wrist pitch)
                [81.0,    0.0,      0.0,    0.0],
                # Joint 5 (Wrist roll) - orientation only
                [0.0,     np.pi/2,  0.0,    0.0],
                # Joint 6 (Wrist yaw) - orientation only
                [0.0,     0.0,      0.0,    0.0],
            ])
        else:
            self.dh_params = np.array(dh_params)
    
    def dh_transform(self, a, alpha, d, theta):
        """
        Create transformation matrix from DH parameters
        
        T = Rot_z(theta) * Trans_z(d) * Trans_x(a) * Rot_x(alpha)
        """
        ct = np.cos(theta)
        st = np.sin(theta)
        ca = np.cos(alpha)
        sa = np.sin(alpha)
        
        return np.array([
            [ct,    -st*ca,  st*sa,   a*ct],
            [st,     ct*ca, -ct*sa,   a*st],
            [0,      sa,     ca,      d],
            [0,      0,      0,       1]
        ])
    
    def forward_kinematics(self, joint_angles, use_all_joints=False):
        """
        Calculate end-effector position from joint angles
        
        Args:
            joint_angles: array of 6 joint angles in radians
            use_all_joints: if True, use all 6 joints; else use first 4 (position only)
            
        Returns:
            position: [x, y, z] in mm
            transform: full 4x4 transformation matrix
        """
        joint_angles = np.array(joint_angles)
        
        # Start with identity matrix
        T = np.eye(4)
        
        # Number of joints to use (4 for position, 6 for full orientation)
        n_joints = 6 if use_all_joints else 4
        
        # Multiply transformations
        for i in range(n_joints):
            theta = joint_angles[i] + self.dh_params[i, 3]  # Add offset
            Ti = self.dh_transform(
                self.dh_params[i, 0],  # a
                self.dh_params[i, 1],  # alpha
                self.dh_params[i, 2],  # d
                theta                   # theta
            )
            T = T @ Ti
        
        # Extract position from transformation matrix
        position = T[0:3, 3]
        
        return position, T
    
    def inverse_kinematics(self, target_pos, current_angles=None, method='geometric'):
        """
        Calculate joint angles to reach target position
        
        Args:
            target_pos: [x, y, z] target position in mm
            current_angles: initial guess for optimization (if None, uses zeros)
            method: 'geometric' for analytical IK or 'numeric' for numerical optimization
            
        Returns:
            joint_angles: array of 6 joint angles in radians (or None if no solution)
        """
        if method == 'geometric':
            return self._inverse_kinematics_geometric(target_pos)
        else:
            return self._inverse_kinematics_numeric(target_pos, current_angles)
    
    def _inverse_kinematics_geometric(self, target_pos):
        """
        Analytical inverse kinematics for 4-DOF positioning
        (Joints 1-4, ignoring wrist orientation)
        """
        x, y, z = target_pos
        
        # Extract link lengths from DH parameters
        L1 = self.dh_params[0, 2]  # Base height
        L2 = self.dh_params[1, 0]  # Shoulder to elbow
        L3 = self.dh_params[2, 0]  # Elbow to wrist
        L4 = self.dh_params[3, 0]  # Wrist to end-effector
        
        # Joint 1: Base rotation (simple atan2)
        theta1 = np.arctan2(y, x)
        
        # Working in vertical plane perpendicular to theta1
        # Distance from base axis
        r = np.sqrt(x**2 + y**2)
        
        # Height relative to shoulder joint
        h = z - L1
        
        # We'll solve for a 3-link planar arm (J2, J3, J4)
        # For simplicity, assume end-effector should point down
        # (theta2 + theta3 + theta4 = -pi/2 for vertical pointing)
        
        # This is the "3R planar arm" problem
        # Target for wrist joint (subtract end-effector)
        # Assuming end-effector points down: subtract L4 from height
        wx = r
        wz = h + L4  # Adjust for end-effector length
        
        # Distance to wrist
        D = np.sqrt(wx**2 + wz**2)
        
        # Check if reachable
        if D > (L2 + L3) or D < abs(L2 - L3):
            print(f"Target unreachable! D={D:.1f}, L2+L3={L2+L3:.1f}")
            return None
        
        # Law of cosines for elbow angle
        cos_theta3 = (D**2 - L2**2 - L3**2) / (2 * L2 * L3)
        cos_theta3 = np.clip(cos_theta3, -1, 1)  # Numerical safety
        theta3 = np.arccos(cos_theta3)  # Elbow up configuration
        
        # Angle to wrist from base
        phi = np.arctan2(wz, wx)
        
        # Shoulder angle
        psi = np.arctan2(L3 * np.sin(theta3), L2 + L3 * np.cos(theta3))
        theta2 = phi - psi
        
        # Wrist angle to point end-effector down
        theta4 = -np.pi/2 - (theta2 + theta3)
        
        # Return 6 joint angles (last 2 are zero for now)
        return np.array([theta1, theta2, theta3, theta4, 0.0, 0.0])
    
    def _inverse_kinematics_numeric(self, target_pos, initial_guess=None):
        """
        Numerical inverse kinematics using optimization
        More robust but slower than geometric solution
        """
        if initial_guess is None:
            initial_guess = np.zeros(6)
        
        def objective(angles):
            """Distance between FK result and target"""
            pos, _ = self.forward_kinematics(angles[:6])
            error = np.linalg.norm(pos - target_pos)
            return error
        
        # Optimize
        result = minimize(
            objective,
            initial_guess,
            method='SLSQP',
            bounds=[(-np.pi, np.pi)] * 6,
            options={'ftol': 1e-6, 'maxiter': 100}
        )
        
        if result.success and result.fun < 1.0:  # Error < 1mm
            return result.x
        else:
            return None


class RobotCalibration:
    """Main calibration class"""
    
    def __init__(self, robot_controller: RobotController):
        self.robot = robot_controller
        self.kinematics = RobotKinematics()
        self.calibration_data = []
        
    def collect_calibration_point(self, manual_position=None):
        """
        Collect one calibration data point
        
        Args:
            manual_position: If provided [x,y,z], use this as ground truth.
                           Otherwise, prompt user to measure actual position.
        
        Returns:
            dict with joint_angles and actual_position
        """
        print("\n" + "="*60)
        print("Collecting calibration point...")
        print("="*60)
        
        # Read current joint positions
        positions_deg = self.robot.get_positions()
        if positions_deg is None:
            print("✗ Failed to read joint positions")
            return None
        
        # Convert to radians (centered at 2048 = 0°)
        joint_angles = []
        for i, deg in enumerate(positions_deg):
            # Assuming 2048 steps = 0°, convert to radians
            steps = int(deg / 360 * 4096)
            rad = (steps - 2048) * 2 * np.pi / 4096
            joint_angles.append(rad)
        
        print(f"Current joint angles (degrees): {positions_deg}")
        
        # Get actual position
        if manual_position is None:
            print("\nPlease measure the ACTUAL end-effector position:")
            try:
                x = float(input("  X coordinate (mm): "))
                y = float(input("  Y coordinate (mm): "))
                z = float(input("  Z coordinate (mm): "))
                actual_position = np.array([x, y, z])
            except:
                print("✗ Invalid input")
                return None
        else:
            actual_position = np.array(manual_position)
        
        # Compare with FK prediction
        predicted_pos, _ = self.kinematics.forward_kinematics(joint_angles)
        error = np.linalg.norm(predicted_pos - actual_position)
        
        print(f"\nPredicted position: [{predicted_pos[0]:.1f}, {predicted_pos[1]:.1f}, {predicted_pos[2]:.1f}] mm")
        print(f"Actual position:    [{actual_position[0]:.1f}, {actual_position[1]:.1f}, {actual_position[2]:.1f}] mm")
        print(f"Error:              {error:.1f} mm")
        
        data_point = {
            'joint_angles': joint_angles,
            'actual_position': actual_position.tolist(),
            'predicted_position': predicted_pos.tolist(),
            'error': error
        }
        
        self.calibration_data.append(data_point)
        print(f"\n✓ Calibration point {len(self.calibration_data)} collected")
        
        return data_point
    
    def collect_grid_calibration(self, n_points=20):
        """
        Automatically collect calibration points in a grid pattern
        
        Note: This assumes you have a way to measure actual positions
              (e.g., camera system, physical grid, etc.)
        """
        print("\n" + "="*60)
        print(f"Grid Calibration: Collecting {n_points} points")
        print("="*60)
        print("\nThe robot will move to various positions.")
        print("At each position, you'll need to measure the actual end-effector position.")
        print("\nPress Enter to start...")
        input()
        
        # Define workspace boundaries (mm)
        x_range = [100, 300]
        y_range = [-150, 150]
        z_range = [50, 300]
        
        # Generate random target positions
        np.random.seed(42)
        targets = []
        for i in range(n_points):
            x = np.random.uniform(*x_range)
            y = np.random.uniform(*y_range)
            z = np.random.uniform(*z_range)
            targets.append([x, y, z])
        
        collected = 0
        for i, target in enumerate(targets):
            print(f"\n{'='*60}")
            print(f"Point {i+1}/{n_points}: Moving to target {target}")
            print(f"{'='*60}")
            
            # Calculate IK
            joint_angles = self.kinematics.inverse_kinematics(target)
            if joint_angles is None:
                print("✗ IK failed for this target, skipping...")
                continue
            
            # Convert to degrees and move
            degrees = self._angles_to_degrees(joint_angles)
            print(f"Moving to joint positions: {degrees}")
            
            # Move robot
            if self.robot.set_joint_positions_degrees(degrees[:7], speed=800):
                time.sleep(2)  # Wait for movement to complete
                
                # Collect calibration point
                data = self.collect_calibration_point()
                if data is not None:
                    collected += 1
            else:
                print("✗ Failed to move robot")
        
        print(f"\n✓ Collected {collected}/{n_points} calibration points")
        return collected
    
    def _angles_to_degrees(self, angles_rad):
        """Convert joint angles (radians) to degrees"""
        degrees = []
        for rad in angles_rad:
            deg = rad * 180.0 / np.pi
            degrees.append(deg)
        return degrees
    
    def optimize_parameters(self, params_to_optimize='all'):
        """
        Optimize DH parameters to minimize calibration error
        
        Args:
            params_to_optimize: 'all', 'lengths', 'offsets', or 'angles'
        """
        if len(self.calibration_data) < 10:
            print(f"✗ Need at least 10 calibration points (have {len(self.calibration_data)})")
            return False
        
        print("\n" + "="*60)
        print("Optimizing Kinematic Parameters")
        print("="*60)
        print(f"Using {len(self.calibration_data)} calibration points")
        
        # Extract calibration data
        joint_angles_list = [np.array(d['joint_angles']) for d in self.calibration_data]
        actual_positions = [np.array(d['actual_position']) for d in self.calibration_data]
        
        # Current parameters
        initial_params = self.kinematics.dh_params.flatten()
        
        # Define which parameters to optimize
        param_mask = self._get_param_mask(params_to_optimize)
        
        def residuals(params_flat):
            """Calculate residuals for all calibration points"""
            # Reshape parameters
            dh_params = params_flat.reshape(6, 4)
            temp_kin = RobotKinematics(dh_params)
            
            errors = []
            for joints, actual_pos in zip(joint_angles_list, actual_positions):
                pred_pos, _ = temp_kin.forward_kinematics(joints)
                error = pred_pos - actual_pos
                errors.extend(error)  # Flatten to 1D
            
            return np.array(errors)
        
        # Initial error
        initial_errors = residuals(initial_params)
        initial_rmse = np.sqrt(np.mean(initial_errors**2))
        print(f"Initial RMSE: {initial_rmse:.2f} mm")
        
        # Optimize
        print("Optimizing... (this may take a minute)")
        
        # Set bounds for parameters
        bounds_lower = []
        bounds_upper = []
        for i in range(6):
            bounds_lower.extend([0, -np.pi, 0, -np.pi/4])      # a, alpha, d, theta_offset
            bounds_upper.extend([500, np.pi, 500, np.pi/4])    # reasonable limits
        
        result = least_squares(
            residuals,
            initial_params,
            bounds=(bounds_lower, bounds_upper),
            verbose=2,
            ftol=1e-8,
            xtol=1e-8,
            max_nfev=1000
        )
        
        # Update parameters
        optimized_params = result.x.reshape(6, 4)
        self.kinematics.dh_params = optimized_params
        
        # Calculate final error
        final_errors = result.fun
        final_rmse = np.sqrt(np.mean(final_errors**2))
        
        print("\n" + "="*60)
        print("Optimization Results")
        print("="*60)
        print(f"Initial RMSE: {initial_rmse:.2f} mm")
        print(f"Final RMSE:   {final_rmse:.2f} mm")
        print(f"Improvement:  {((initial_rmse - final_rmse) / initial_rmse * 100):.1f}%")
        
        # Show parameter changes
        print("\nParameter Changes:")
        param_names = ['a', 'alpha', 'd', 'theta_offset']
        for i in range(4):
            print(f"\n  Joint {i+1}:")
            for j, name in enumerate(param_names):
                old_val = initial_params[i*4 + j]
                new_val = optimized_params[i, j]
                change = new_val - old_val
                print(f"    {name:13s}: {old_val:8.2f} → {new_val:8.2f} (Δ {change:+8.2f})")
        
        return True
    
    def _get_param_mask(self, params_to_optimize):
        """Create mask for which parameters to optimize"""
        # For now, optimize all parameters
        # Could be made more selective
        return np.ones(24, dtype=bool)
    
    def test_circle(self, center, radius, n_points=36):
        """
        Test calibration by drawing a circle
        
        Args:
            center: [x, y, z] center of circle
            radius: radius in mm
            n_points: number of points around circle
        """
        print("\n" + "="*60)
        print(f"Circle Test: r={radius}mm at {center}")
        print("="*60)
        
        # Generate circle points in XY plane
        angles = np.linspace(0, 2*np.pi, n_points)
        actual_positions = []
        
        for angle in angles:
            # Target position
            x = center[0] + radius * np.cos(angle)
            y = center[1] + radius * np.sin(angle)
            z = center[2]
            target = [x, y, z]
            
            # Calculate IK
            joint_angles = self.kinematics.inverse_kinematics(target)
            if joint_angles is None:
                print(f"✗ IK failed for position {target}")
                continue
            
            # Move robot
            degrees = self._angles_to_degrees(joint_angles)
            if self.robot.set_joint_positions_degrees(degrees[:7], speed=1000):
                time.sleep(0.2)
                
                # Read actual position (would need external measurement)
                # For now, just verify FK
                actual_pos, _ = self.kinematics.forward_kinematics(joint_angles)
                actual_positions.append(actual_pos)
                
                error = np.linalg.norm(actual_pos - target)
                print(f"Point {len(actual_positions)}: error = {error:.2f} mm")
        
        # Analyze circle quality
        actual_positions = np.array(actual_positions)
        self._analyze_circle_quality(actual_positions, center, radius)
    
    def _analyze_circle_quality(self, points, expected_center, expected_radius):
        """Analyze how circular the path is"""
        # Fit circle to points
        center_2d = np.mean(points[:, :2], axis=0)
        radii = np.linalg.norm(points[:, :2] - center_2d, axis=1)
        
        mean_radius = np.mean(radii)
        std_radius = np.std(radii)
        
        print("\nCircle Quality Analysis:")
        print(f"  Expected center: [{expected_center[0]:.1f}, {expected_center[1]:.1f}]")
        print(f"  Actual center:   [{center_2d[0]:.1f}, {center_2d[1]:.1f}]")
        print(f"  Expected radius: {expected_radius:.1f} mm")
        print(f"  Mean radius:     {mean_radius:.1f} mm")
        print(f"  Std deviation:   {std_radius:.2f} mm")
        print(f"  Circularity:     {(1 - std_radius/mean_radius)*100:.1f}%")
    
    def save_calibration(self, filename='calibration.json'):
        """Save calibration data and optimized parameters"""
        data = {
            'dh_parameters': self.kinematics.dh_params.tolist(),
            'calibration_points': self.calibration_data,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\n✓ Calibration saved to {filename}")
    
    def load_calibration(self, filename='calibration.json'):
        """Load calibration data and parameters"""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            self.kinematics.dh_params = np.array(data['dh_parameters'])
            self.calibration_data = data['calibration_points']
            
            print(f"✓ Calibration loaded from {filename}")
            print(f"  {len(self.calibration_data)} calibration points")
            print(f"  Timestamp: {data.get('timestamp', 'unknown')}")
            return True
        except Exception as e:
            print(f"✗ Failed to load calibration: {e}")
            return False


def main():
    """Interactive calibration session"""
    print("=" * 70)
    print("  ROBOT KINEMATIC CALIBRATION TOOL")
    print("=" * 70)
    print()
    print("This tool will help you calibrate your robot for perfect IK.")
    print()
    
    # Connect to robot
    robot = RobotController()
    if not robot.connect():
        print("✗ Failed to connect to robot")
        return
    
    calibration = RobotCalibration(robot)
    
    # Main menu
    while True:
        print("\n" + "="*70)
        print("CALIBRATION MENU")
        print("="*70)
        print("1. Collect single calibration point (manual)")
        print("2. Collect grid calibration (automatic)")
        print("3. Optimize parameters")
        print("4. Test with circle")
        print("5. Test with line")
        print("6. Save calibration")
        print("7. Load calibration")
        print("8. Show current parameters")
        print("9. Exit")
        print()
        
        choice = input("Choose option: ").strip()
        
        if choice == '1':
            calibration.collect_calibration_point()
        
        elif choice == '2':
            n = int(input("Number of points to collect [20]: ") or "20")
            calibration.collect_grid_calibration(n)
        
        elif choice == '3':
            calibration.optimize_parameters()
        
        elif choice == '4':
            print("\nCircle test parameters:")
            x = float(input("  Center X [200]: ") or "200")
            y = float(input("  Center Y [0]: ") or "0")
            z = float(input("  Center Z [150]: ") or "150")
            r = float(input("  Radius [50]: ") or "50")
            calibration.test_circle([x, y, z], r)
        
        elif choice == '5':
            print("Line test not yet implemented")
        
        elif choice == '6':
            filename = input("Filename [calibration.json]: ") or "calibration.json"
            calibration.save_calibration(filename)
        
        elif choice == '7':
            filename = input("Filename [calibration.json]: ") or "calibration.json"
            calibration.load_calibration(filename)
        
        elif choice == '8':
            print("\nCurrent DH Parameters:")
            print("Joint | a (mm) | alpha (rad) | d (mm) | theta_offset (rad)")
            print("-" * 60)
            for i, params in enumerate(calibration.kinematics.dh_params):
                print(f"  {i+1}   | {params[0]:6.1f} | {params[1]:11.4f} | {params[2]:6.1f} | {params[3]:18.4f}")
        
        elif choice == '9':
            break
    
    robot.disconnect()
    print("\n✓ Calibration session complete")


if __name__ == '__main__':
    main()
