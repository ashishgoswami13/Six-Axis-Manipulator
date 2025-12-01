#!/usr/bin/env python3
"""
Action Space Transformer
Converts OpenVLA action predictions (Bridge dataset frame) to KikoBot C1 joint commands

Bridge Frame (OpenVLA output):
    - 7D vector: [x, y, z, roll, pitch, yaw, gripper]
    - Position deltas in meters
    - Orientation deltas in radians
    - Coordinate frame:
        X: forward from robot base
        Y: right from robot perspective
        Z: up (against gravity)

KikoBot C1 Frame:
    - 7 joint angles in degrees
    - Joint space control (no direct Cartesian control)
    - Need inverse kinematics or mapping strategy
"""

import numpy as np
from typing import Tuple, List
import math

class ActionTransformer:
    """
    Transforms VLA actions (end-effector deltas) to robot joint commands
    
    Strategy Options:
    1. Direct Mapping: Map Cartesian deltas to joint deltas (simple, approximate)
    2. Inverse Kinematics: Compute exact joint angles (complex, accurate)
    3. Learned Mapping: Train a neural network (advanced)
    
    We'll start with Strategy 1 (Direct Mapping) for Phase 2
    """
    
    def __init__(self, control_mode='velocity'):
        """
        Args:
            control_mode: 'velocity' (incremental) or 'position' (absolute)
        """
        self.control_mode = control_mode
        
        # Link lengths from URDF (meters)
        self.link_lengths = [
            0.1378,  # Base to shoulder (50.856mm + 86.888mm)
            0.147,   # Shoulder to elbow (146.99mm)
            0.147,   # Elbow to wrist (147.013mm)
            0.081,   # Wrist to end effector (18.543mm + 63.005mm)
        ]
        
        # Joint limits from URDF (degrees)
        self.joint_limits = [
            (-165.0, 165.0),   # Joint 1 (Base): ±165°
            (-100.0, 150.0),   # Joint 2 (Shoulder): -100° to +150°
            (-140.0, 140.0),   # Joint 3 (Elbow): ±140°
            (-140.0, 140.0),   # Joint 4 (Wrist 1): ±140°
            (-140.0, 140.0),   # Joint 5 (Wrist 2): ±140°
            (-175.0, 175.0),   # Joint 6 (Wrist 3): ±175°
            (-180.0, 180.0),   # Joint 7 (Gripper): ±180°
        ]
        
        # Scaling factors: how much each Cartesian delta affects each joint
        # These are INITIAL GUESSES - will be calibrated in Phase 3
        self.position_to_joint_scale = {
            'x': [0.0, 30.0, 15.0, 5.0, 0.0, 0.0, 0.0],   # X affects shoulder, elbow mostly
            'y': [50.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],    # Y affects base rotation
            'z': [0.0, 20.0, 25.0, 10.0, 0.0, 0.0, 0.0],  # Z affects shoulder, elbow, wrist
        }
        
        # Orientation to joint mapping (roll, pitch, yaw → wrist joints)
        self.orientation_to_joint_scale = {
            'roll': [0.0, 0.0, 0.0, 0.0, 50.0, 0.0, 0.0],   # Roll → Joint 5
            'pitch': [0.0, 0.0, 0.0, 30.0, 0.0, 0.0, 0.0],  # Pitch → Joint 4
            'yaw': [0.0, 0.0, 0.0, 0.0, 0.0, 40.0, 0.0],    # Yaw → Joint 6
        }
        
        # Gripper mapping
        self.gripper_open_angle = 45.0   # degrees for open
        self.gripper_close_angle = -45.0  # degrees for closed
        
        # Safety limits
        self.max_joint_delta = 5.0  # Maximum degrees change per step (reduced for smoother motion)
        self.min_action_threshold = 0.001  # Minimum action magnitude to trigger movement
        
        # Smoothing factor (0-1): lower = smoother but slower response
        self.action_damping = 0.3  # Reduce action magnitude to 30% for gentler movements
        
    def is_within_limits(self, joint_angles: List[float]) -> Tuple[bool, str]:
        """
        Check if joint angles are within safe limits
        
        Args:
            joint_angles: List of 7 joint angles in degrees
            
        Returns:
            (is_safe, message)
        """
        for i, angle in enumerate(joint_angles):
            min_limit, max_limit = self.joint_limits[i]
            if angle < min_limit or angle > max_limit:
                return False, f"Joint {i+1} at {angle:.1f}° exceeds limits [{min_limit:.1f}°, {max_limit:.1f}°]"
        return True, "Within limits"
    
    def transform_action(self, action_vla: np.ndarray, current_joints: List[float]) -> Tuple[List[float], dict]:
        """
        Transform VLA action (Cartesian delta) to joint angles
        
        Args:
            action_vla: 7D numpy array [x, y, z, roll, pitch, yaw, gripper]
                       Position in meters, orientation in radians, gripper in [-1, 1]
            current_joints: Current joint positions in degrees [7 values]
        
        Returns:
            (target_joints, info_dict)
            target_joints: Target joint positions in degrees [7 values]
            info_dict: Additional information about the transformation
        """
        
        # Extract components
        dx, dy, dz = action_vla[0], action_vla[1], action_vla[2]
        droll, dpitch, dyaw = action_vla[3], action_vla[4], action_vla[5]
        gripper_state = action_vla[6]
        
        # Convert orientation from radians to degrees
        droll_deg = np.rad2deg(droll)
        dpitch_deg = np.rad2deg(dpitch)
        dyaw_deg = np.rad2deg(dyaw)
        
        # Initialize joint deltas
        joint_deltas = np.zeros(7)
        
        # Map position deltas to joint deltas
        # This is a simplified Jacobian-like mapping
        for i in range(7):
            joint_deltas[i] += dx * self.position_to_joint_scale['x'][i]
            joint_deltas[i] += dy * self.position_to_joint_scale['y'][i]
            joint_deltas[i] += dz * self.position_to_joint_scale['z'][i]
        
        # Map orientation deltas to wrist joint deltas
        for i in range(7):
            joint_deltas[i] += droll_deg * self.orientation_to_joint_scale['roll'][i]
            joint_deltas[i] += dpitch_deg * self.orientation_to_joint_scale['pitch'][i]
            joint_deltas[i] += dyaw_deg * self.orientation_to_joint_scale['yaw'][i]
        
        # Apply action damping for smoother motion
        joint_deltas = joint_deltas * self.action_damping
        
        # Map gripper state to joint 7
        # OpenVLA typically outputs: -1 = closed, +1 = open
        # Only change gripper if there's a clear command
        if gripper_state > 0.7:  # Strong open signal
            joint_deltas[6] = self.gripper_open_angle - current_joints[6]
        elif gripper_state < -0.7:  # Strong close signal
            joint_deltas[6] = self.gripper_close_angle - current_joints[6]
        else:
            # Weak signal or neutral - maintain current position
            joint_deltas[6] = 0.0
        
        # Apply safety limits: clamp joint deltas
        joint_deltas = np.clip(joint_deltas, -self.max_joint_delta, self.max_joint_delta)
        
        # Compute target joints
        target_joints = [current_joints[i] + joint_deltas[i] for i in range(7)]
        
        # Additional safety: clamp to joint limits
        for i in range(7):
            min_limit, max_limit = self.joint_limits[i]
            target_joints[i] = max(min_limit, min(max_limit, target_joints[i]))
        
        # Info for debugging/visualization
        info = {
            'action_cartesian': {
                'position': [dx, dy, dz],
                'orientation': [droll_deg, dpitch_deg, dyaw_deg],
                'gripper': gripper_state
            },
            'joint_deltas': joint_deltas.tolist(),
            'current_joints': current_joints,
            'target_joints': target_joints,
            'action_magnitude': np.linalg.norm([dx, dy, dz])
        }
        
        return target_joints, info
    
    def calibrate_position_scale(self, axis: str, joint_idx: int, scale: float):
        """
        Calibrate scaling factor for a specific axis and joint
        Use this during Phase 3 calibration
        
        Args:
            axis: 'x', 'y', or 'z'
            joint_idx: Joint index (0-6)
            scale: New scaling factor
        """
        if axis in self.position_to_joint_scale:
            self.position_to_joint_scale[axis][joint_idx] = scale
            print(f"✓ Updated {axis} → Joint {joint_idx+1} scale to {scale}")
        else:
            print(f"✗ Unknown axis: {axis}")
    
    def calibrate_orientation_scale(self, orientation: str, joint_idx: int, scale: float):
        """
        Calibrate scaling factor for orientation to joint mapping
        
        Args:
            orientation: 'roll', 'pitch', or 'yaw'
            joint_idx: Joint index (0-6)
            scale: New scaling factor
        """
        if orientation in self.orientation_to_joint_scale:
            self.orientation_to_joint_scale[orientation][joint_idx] = scale
            print(f"✓ Updated {orientation} → Joint {joint_idx+1} scale to {scale}")
        else:
            print(f"✗ Unknown orientation: {orientation}")
    
    def save_calibration(self, filename='action_calibration.json'):
        """Save calibration parameters to file"""
        import json
        calibration = {
            'position_to_joint_scale': self.position_to_joint_scale,
            'orientation_to_joint_scale': self.orientation_to_joint_scale,
            'gripper_open_angle': self.gripper_open_angle,
            'gripper_close_angle': self.gripper_close_angle,
            'max_joint_delta': self.max_joint_delta
        }
        with open(filename, 'w') as f:
            json.dump(calibration, f, indent=2)
        print(f"✓ Saved calibration to {filename}")
    
    def load_calibration(self, filename='action_calibration.json'):
        """Load calibration parameters from file"""
        import json
        try:
            with open(filename, 'r') as f:
                calibration = json.load(f)
            self.position_to_joint_scale = calibration['position_to_joint_scale']
            self.orientation_to_joint_scale = calibration['orientation_to_joint_scale']
            self.gripper_open_angle = calibration['gripper_open_angle']
            self.gripper_close_angle = calibration['gripper_close_angle']
            self.max_joint_delta = calibration['max_joint_delta']
            print(f"✓ Loaded calibration from {filename}")
            return True
        except FileNotFoundError:
            print(f"⚠ Calibration file not found: {filename}")
            return False
        except Exception as e:
            print(f"✗ Error loading calibration: {e}")
            return False


class InverseKinematicsSolver:
    """
    Placeholder for proper inverse kinematics
    This is more advanced - can be implemented in Phase 4
    """
    
    def __init__(self, link_lengths):
        self.link_lengths = link_lengths
    
    def solve_ik(self, target_position, target_orientation):
        """
        Solve inverse kinematics to find joint angles
        
        Args:
            target_position: [x, y, z] in meters
            target_orientation: [roll, pitch, yaw] in radians
        
        Returns:
            joint_angles: [7 values] in degrees, or None if no solution
        """
        # TODO: Implement proper IK solver
        # Options:
        # 1. Analytical solution (if robot is simple enough)
        # 2. Numerical optimization (scipy.optimize)
        # 3. Use existing robotics library (PyBullet, KDL, etc.)
        raise NotImplementedError("IK solver not implemented yet - using direct mapping for now")


if __name__ == "__main__":
    # Test the action transformer
    print("Testing Action Transformer...")
    
    transformer = ActionTransformer()
    
    # Simulate current joint positions (all at 0 degrees)
    current_joints = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    
    # Test cases
    test_actions = [
        {
            'name': 'Move forward',
            'action': np.array([0.05, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])  # 5cm forward
        },
        {
            'name': 'Move left',
            'action': np.array([0.0, -0.05, 0.0, 0.0, 0.0, 0.0, 0.0])  # 5cm left
        },
        {
            'name': 'Move up',
            'action': np.array([0.0, 0.0, 0.05, 0.0, 0.0, 0.0, 0.0])  # 5cm up
        },
        {
            'name': 'Close gripper',
            'action': np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0])  # Close
        },
        {
            'name': 'Combined motion',
            'action': np.array([0.03, 0.02, 0.01, 0.0, 0.1, 0.0, 1.0])  # Complex
        },
    ]
    
    print("\n" + "="*70)
    for test in test_actions:
        print(f"\nTest: {test['name']}")
        print(f"VLA Action: {test['action']}")
        
        target_joints, info = transformer.transform_action(test['action'], current_joints)
        
        print(f"Joint Deltas: {[f'{d:+.1f}°' for d in info['joint_deltas']]}")
        print(f"Target Joints: {[f'{j:.1f}°' for j in target_joints]}")
        print(f"Action Magnitude: {info['action_magnitude']:.4f} m")
    
    print("\n" + "="*70)
    print("\n✓ Action transformer test complete")
    print("\nNote: These are UNCALIBRATED mappings!")
    print("In Phase 3, we'll calibrate these scaling factors by testing actual robot movement.")
