#!/usr/bin/env python3
"""
Simple Robot Calibration Helper
================================

Quick and easy calibration workflow for beginners.
This script guides you through a simplified calibration process.
"""

import numpy as np
from robot_controller import RobotController
import time
import json

# Pre-defined calibration positions (safe and easy to measure)
CALIBRATION_POSITIONS = [
    # Format: [joint1, joint2, joint3, joint4, joint5, joint6, gripper]
    # Positions in degrees
    
    # Position 1: Home position
    {
        'name': 'Home - Center',
        'joints_deg': [0, 0, 0, -90, 0, 0, 0],
        'description': 'Arm straight down, gripper vertical'
    },
    
    # Position 2: Forward reach
    {
        'name': 'Forward Reach',
        'joints_deg': [0, 45, -90, 45, 0, 0, 0],
        'description': 'Arm extended forward at mid height'
    },
    
    # Position 3: High reach
    {
        'name': 'High Forward',
        'joints_deg': [0, -30, -60, 0, 0, 0, 0],
        'description': 'Arm reaching high and forward'
    },
    
    # Position 4: Low reach
    {
        'name': 'Low Forward',
        'joints_deg': [0, 75, -90, 15, 0, 0, 0],
        'description': 'Arm reaching low forward'
    },
    
    # Position 5: Left side
    {
        'name': 'Left Side',
        'joints_deg': [60, 45, -90, 45, 0, 0, 0],
        'description': 'Arm extended to left side'
    },
    
    # Position 6: Right side
    {
        'name': 'Right Side',
        'joints_deg': [-60, 45, -90, 45, 0, 0, 0],
        'description': 'Arm extended to right side'
    },
    
    # Position 7: Maximum reach
    {
        'name': 'Maximum Reach',
        'joints_deg': [0, 0, 0, 0, 0, 0, 0],
        'description': 'Arm fully extended horizontally'
    },
    
    # Position 8: Compact
    {
        'name': 'Compact',
        'joints_deg': [0, 90, -135, 45, 0, 0, 0],
        'description': 'Arm folded close to base'
    },
]


def print_banner(text):
    """Print a nice banner"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")


def measure_position():
    """Interactive position measurement"""
    print("Measure the end-effector position relative to robot base:")
    print("  X-axis: Forward (positive) / Backward (negative)")
    print("  Y-axis: Left (positive) / Right (negative)")  
    print("  Z-axis: Up (positive) / Down (negative)")
    print()
    
    while True:
        try:
            x = float(input("  X position (mm): "))
            y = float(input("  Y position (mm): "))
            z = float(input("  Z position (mm): "))
            
            print(f"\nYou entered: [{x:.1f}, {y:.1f}, {z:.1f}] mm")
            confirm = input("Is this correct? (y/n): ").lower()
            
            if confirm == 'y':
                return [x, y, z]
            else:
                print("\nLet's try again...")
                
        except ValueError:
            print("✗ Invalid input. Please enter numbers only.")
            continue


def calculate_fk_simple(joints_deg):
    """
    Simple FK calculation using nominal parameters
    Returns predicted position [x, y, z] in mm
    """
    # Convert to radians
    joints_rad = np.array(joints_deg[:4]) * np.pi / 180.0
    
    # Link lengths (nominal from Step1_FK.cpp)
    L1 = 137.8  # Base height
    L2 = 147.0  # Shoulder to elbow
    L3 = 147.0  # Elbow to wrist
    L4 = 81.0   # Wrist to end-effector
    
    # Extract joint angles
    theta1, theta2, theta3, theta4 = joints_rad
    
    # Calculate reach and height in vertical plane
    reach = L2 * np.cos(theta2) + L3 * np.cos(theta2 + theta3) + L4 * np.cos(theta2 + theta3 + theta4)
    height = L2 * np.sin(theta2) + L3 * np.sin(theta2 + theta3) + L4 * np.sin(theta2 + theta3 + theta4)
    
    # Apply base rotation
    x = reach * np.cos(theta1)
    y = reach * np.sin(theta1)
    z = L1 + height
    
    return [x, y, z]


def main():
    print_banner("SIMPLE ROBOT CALIBRATION HELPER")
    
    print("This tool will guide you through calibrating your robot.")
    print("You'll move the robot to predefined positions and measure where it actually is.")
    print()
    print(f"We'll collect {len(CALIBRATION_POSITIONS)} calibration points.")
    print()
    
    input("Press Enter to connect to robot...")
    
    # Connect to robot
    robot = RobotController()
    if not robot.connect():
        print("\n✗ Failed to connect to robot. Check connection and try again.")
        return
    
    print("\n✓ Connected to robot!")
    print("\nSafety check: Make sure robot has clear workspace.")
    input("Press Enter when ready to start calibration...")
    
    # Collect calibration data
    calibration_data = []
    
    for i, position in enumerate(CALIBRATION_POSITIONS):
        print_banner(f"Position {i+1}/{len(CALIBRATION_POSITIONS)}: {position['name']}")
        
        print(f"Description: {position['description']}")
        print(f"Joint angles: {position['joints_deg']}")
        print()
        
        print("Moving robot to position...")
        if not robot.set_joint_positions_degrees(position['joints_deg'], speed=800):
            print("✗ Failed to move robot. Skipping this position.")
            continue
        
        # Wait for movement
        time.sleep(3)
        
        print("\n✓ Robot in position!")
        print()
        
        # Ask user if they want to measure this position
        measure = input("Measure this position? (y/n/skip all remaining): ").lower()
        
        if measure == 'skip all remaining':
            print("Skipping remaining positions...")
            break
        elif measure == 'n':
            print("Skipping this position...")
            continue
        
        # Measure actual position
        actual_pos = measure_position()
        
        # Calculate predicted position
        predicted_pos = calculate_fk_simple(position['joints_deg'])
        
        # Calculate error
        error = np.linalg.norm(np.array(actual_pos) - np.array(predicted_pos))
        
        print("\n" + "-"*70)
        print(f"Predicted position: [{predicted_pos[0]:.1f}, {predicted_pos[1]:.1f}, {predicted_pos[2]:.1f}] mm")
        print(f"Actual position:    [{actual_pos[0]:.1f}, {actual_pos[1]:.1f}, {actual_pos[2]:.1f}] mm")
        print(f"Error:              {error:.1f} mm")
        print("-"*70)
        
        # Save data point
        data_point = {
            'position_name': position['name'],
            'joint_angles_deg': position['joints_deg'],
            'predicted_position': predicted_pos,
            'actual_position': actual_pos,
            'error': float(error)
        }
        calibration_data.append(data_point)
        
        print(f"\n✓ Calibration point {len(calibration_data)} saved!")
        
        # Option to continue or stop
        if i < len(CALIBRATION_POSITIONS) - 1:
            cont = input("\nContinue to next position? (y/n): ").lower()
            if cont != 'y':
                break
    
    # Summary
    print_banner("CALIBRATION COMPLETE")
    
    if len(calibration_data) == 0:
        print("✗ No calibration data collected.")
        robot.disconnect()
        return
    
    print(f"✓ Collected {len(calibration_data)} calibration points")
    print()
    
    # Calculate statistics
    errors = [d['error'] for d in calibration_data]
    mean_error = np.mean(errors)
    max_error = np.max(errors)
    min_error = np.min(errors)
    
    print("Error Statistics (before calibration):")
    print(f"  Mean error:   {mean_error:.1f} mm")
    print(f"  Max error:    {max_error:.1f} mm")
    print(f"  Min error:    {min_error:.1f} mm")
    print()
    
    # Save calibration data
    filename = 'calibration_data.json'
    with open(filename, 'w') as f:
        json.dump({
            'calibration_points': calibration_data,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'statistics': {
                'mean_error': float(mean_error),
                'max_error': float(max_error),
                'min_error': float(min_error),
                'num_points': len(calibration_data)
            }
        }, f, indent=2)
    
    print(f"✓ Calibration data saved to {filename}")
    print()
    print("Next steps:")
    print("  1. Run: python3 robot_calibration.py")
    print("  2. Choose option 7 to load this calibration data")
    print("  3. Choose option 3 to optimize parameters")
    print("  4. Test with circle drawing (option 4)")
    print()
    
    # Return to home
    print("Returning robot to home position...")
    robot.move_to_home()
    time.sleep(3)
    
    robot.disconnect()
    print("\n✓ Calibration session complete!")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✗ Calibration interrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
