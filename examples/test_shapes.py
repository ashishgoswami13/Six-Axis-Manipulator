#!/usr/bin/env python3
"""
Calibration Test - Draw Shapes
===============================

Test your robot calibration by drawing geometric shapes.
This validates that your inverse kinematics is accurate.
"""

import numpy as np
from robot_controller import RobotController
from robot_calibration import RobotCalibration, RobotKinematics
import time
import json


def draw_circle(robot, kinematics, center, radius, n_points=36, speed=1000, z_safe=200):
    """
    Draw a circle to test calibration accuracy
    
    Args:
        robot: RobotController instance
        kinematics: RobotKinematics instance (calibrated)
        center: [x, y, z] center position in mm
        radius: radius in mm
        n_points: number of points around circle
        speed: movement speed
        z_safe: safe height for travel moves
    """
    print("\n" + "="*70)
    print(f"Drawing Circle: center={center}, radius={radius}mm")
    print("="*70)
    
    # Generate circle points
    angles = np.linspace(0, 2*np.pi, n_points, endpoint=True)
    
    actual_points = []
    errors = []
    
    for i, angle in enumerate(angles):
        # Calculate target point on circle
        x = center[0] + radius * np.cos(angle)
        y = center[1] + radius * np.sin(angle)
        z = center[2]
        target = np.array([x, y, z])
        
        # Calculate IK
        joint_angles = kinematics.inverse_kinematics(target)
        if joint_angles is None:
            print(f"✗ IK failed at angle {angle*180/np.pi:.0f}°")
            continue
        
        # Verify FK (where will robot actually go?)
        actual_pos, _ = kinematics.forward_kinematics(joint_angles)
        error = np.linalg.norm(actual_pos - target)
        
        # Convert to degrees and move
        degrees = [rad * 180.0 / np.pi for rad in joint_angles]
        
        # Move robot
        if robot.set_joint_positions_degrees(degrees[:7], speed=speed):
            time.sleep(0.05)  # Small delay
            actual_points.append(actual_pos)
            errors.append(error)
            
            if i % 9 == 0:  # Print every 10th point
                print(f"  Point {i+1}/{n_points}: target=[{x:.1f}, {y:.1f}, {z:.1f}], "
                      f"error={error:.2f}mm")
    
    # Analyze circle quality
    if len(actual_points) > 0:
        analyze_circle(actual_points, center, radius, errors)
    
    return actual_points, errors


def analyze_circle(points, expected_center, expected_radius, errors):
    """Analyze how well the drawn circle matches expected"""
    points = np.array(points)
    
    # Fit circle to points in XY plane
    center_xy = np.mean(points[:, :2], axis=0)
    radii = np.linalg.norm(points[:, :2] - center_xy, axis=1)
    
    mean_radius = np.mean(radii)
    std_radius = np.std(radii)
    min_radius = np.min(radii)
    max_radius = np.max(radii)
    
    # Z variation
    z_mean = np.mean(points[:, 2])
    z_std = np.std(points[:, 2])
    
    # Position errors
    mean_error = np.mean(errors)
    max_error = np.max(errors)
    
    print("\n" + "="*70)
    print("CIRCLE QUALITY ANALYSIS")
    print("="*70)
    
    print(f"\nCenter Analysis:")
    print(f"  Expected: [{expected_center[0]:.1f}, {expected_center[1]:.1f}]")
    print(f"  Actual:   [{center_xy[0]:.1f}, {center_xy[1]:.1f}]")
    center_error = np.linalg.norm(center_xy - expected_center[:2])
    print(f"  Error:    {center_error:.2f} mm")
    
    print(f"\nRadius Analysis:")
    print(f"  Expected:     {expected_radius:.1f} mm")
    print(f"  Mean:         {mean_radius:.1f} mm")
    print(f"  Std Dev:      {std_radius:.2f} mm")
    print(f"  Range:        [{min_radius:.1f}, {max_radius:.1f}] mm")
    print(f"  Circularity:  {(1 - std_radius/mean_radius)*100:.1f}%")
    
    print(f"\nHeight Analysis:")
    print(f"  Expected:     {expected_center[2]:.1f} mm")
    print(f"  Mean:         {z_mean:.1f} mm")
    print(f"  Std Dev:      {z_std:.2f} mm")
    
    print(f"\nPosition Accuracy:")
    print(f"  Mean error:   {mean_error:.2f} mm")
    print(f"  Max error:    {max_error:.2f} mm")
    
    # Overall grade
    circularity = (1 - std_radius/mean_radius) * 100
    if circularity > 98 and mean_error < 2:
        grade = "EXCELLENT ✓✓✓"
    elif circularity > 95 and mean_error < 3:
        grade = "VERY GOOD ✓✓"
    elif circularity > 90 and mean_error < 5:
        grade = "GOOD ✓"
    elif circularity > 85 and mean_error < 10:
        grade = "FAIR"
    else:
        grade = "POOR - NEEDS RECALIBRATION"
    
    print(f"\nOverall Grade: {grade}")
    print("="*70)


def draw_line(robot, kinematics, start, end, n_points=20, speed=1000):
    """Draw a straight line"""
    print("\n" + "="*70)
    print(f"Drawing Line: {start} → {end}")
    print("="*70)
    
    actual_points = []
    errors = []
    
    # Generate line points
    for i in range(n_points):
        t = i / (n_points - 1)
        target = np.array(start) * (1 - t) + np.array(end) * t
        
        # Calculate IK
        joint_angles = kinematics.inverse_kinematics(target)
        if joint_angles is None:
            print(f"✗ IK failed at t={t:.2f}")
            continue
        
        # Verify FK
        actual_pos, _ = kinematics.forward_kinematics(joint_angles)
        error = np.linalg.norm(actual_pos - target)
        
        # Convert to degrees and move
        degrees = [rad * 180.0 / np.pi for rad in joint_angles]
        
        if robot.set_joint_positions_degrees(degrees[:7], speed=speed):
            time.sleep(0.05)
            actual_points.append(actual_pos)
            errors.append(error)
            
            if i % 5 == 0:
                print(f"  Point {i+1}/{n_points}: error={error:.2f}mm")
    
    # Analyze line quality
    if len(actual_points) > 0:
        analyze_line(actual_points, start, end, errors)
    
    return actual_points, errors


def analyze_line(points, expected_start, expected_end, errors):
    """Analyze how straight the line is"""
    points = np.array(points)
    expected_start = np.array(expected_start)
    expected_end = np.array(expected_end)
    
    # Fit line using least squares
    direction = expected_end - expected_start
    direction = direction / np.linalg.norm(direction)
    
    # Calculate perpendicular distance from ideal line
    deviations = []
    for point in points:
        # Vector from start to point
        v = point - expected_start
        # Project onto line direction
        projection_length = np.dot(v, direction)
        projection = expected_start + projection_length * direction
        # Perpendicular distance
        deviation = np.linalg.norm(point - projection)
        deviations.append(deviation)
    
    mean_deviation = np.mean(deviations)
    max_deviation = np.max(deviations)
    
    # Length analysis
    expected_length = np.linalg.norm(expected_end - expected_start)
    actual_length = np.linalg.norm(points[-1] - points[0])
    
    print("\n" + "="*70)
    print("LINE QUALITY ANALYSIS")
    print("="*70)
    
    print(f"\nStraightness:")
    print(f"  Mean deviation:  {mean_deviation:.2f} mm")
    print(f"  Max deviation:   {max_deviation:.2f} mm")
    print(f"  Straightness:    {(1 - mean_deviation/expected_length)*100:.1f}%")
    
    print(f"\nLength:")
    print(f"  Expected:        {expected_length:.1f} mm")
    print(f"  Actual:          {actual_length:.1f} mm")
    print(f"  Error:           {abs(actual_length - expected_length):.2f} mm")
    
    print(f"\nPosition Accuracy:")
    print(f"  Mean error:      {np.mean(errors):.2f} mm")
    print(f"  Max error:       {np.max(errors):.2f} mm")
    
    # Overall grade
    if mean_deviation < 1 and abs(actual_length - expected_length) < 2:
        grade = "EXCELLENT ✓✓✓"
    elif mean_deviation < 2 and abs(actual_length - expected_length) < 5:
        grade = "VERY GOOD ✓✓"
    elif mean_deviation < 3 and abs(actual_length - expected_length) < 8:
        grade = "GOOD ✓"
    elif mean_deviation < 5:
        grade = "FAIR"
    else:
        grade = "POOR - NEEDS RECALIBRATION"
    
    print(f"\nOverall Grade: {grade}")
    print("="*70)


def draw_square(robot, kinematics, center, side_length, speed=1000):
    """Draw a square"""
    print("\n" + "="*70)
    print(f"Drawing Square: center={center}, side={side_length}mm")
    print("="*70)
    
    half = side_length / 2
    x, y, z = center
    
    # Define corners
    corners = [
        [x - half, y - half, z],  # Bottom-left
        [x + half, y - half, z],  # Bottom-right
        [x + half, y + half, z],  # Top-right
        [x - half, y + half, z],  # Top-left
        [x - half, y - half, z],  # Back to start
    ]
    
    all_points = []
    
    # Draw each side
    for i in range(4):
        print(f"\nDrawing side {i+1}/4...")
        points, _ = draw_line(robot, kinematics, corners[i], corners[i+1], 
                            n_points=15, speed=speed)
        all_points.extend(points)
        time.sleep(0.5)
    
    return all_points


def main():
    """Test calibration with various shapes"""
    print("="*70)
    print("  CALIBRATION TEST - SHAPE DRAWING")
    print("="*70)
    
    # Connect to robot
    robot = RobotController()
    if not robot.connect():
        print("✗ Failed to connect to robot")
        return
    
    # Load calibration
    print("\nLoading calibration...")
    try:
        with open('calibration.json', 'r') as f:
            cal_data = json.load(f)
        kinematics = RobotKinematics(cal_data['dh_parameters'])
        print("✓ Loaded calibrated parameters")
    except FileNotFoundError:
        print("! No calibration file found, using nominal parameters")
        kinematics = RobotKinematics()
    
    calibration = RobotCalibration(robot)
    calibration.kinematics = kinematics
    
    # Menu
    while True:
        print("\n" + "="*70)
        print("TEST MENU")
        print("="*70)
        print("1. Draw circle")
        print("2. Draw line")
        print("3. Draw square")
        print("4. Draw figure-8")
        print("5. Return to home")
        print("6. Exit")
        print()
        
        choice = input("Choose test: ").strip()
        
        try:
            if choice == '1':
                print("\nCircle parameters:")
                x = float(input("  Center X [200]: ") or "200")
                y = float(input("  Center Y [0]: ") or "0")
                z = float(input("  Center Z [150]: ") or "150")
                r = float(input("  Radius [50]: ") or "50")
                draw_circle(robot, kinematics, [x, y, z], r)
            
            elif choice == '2':
                print("\nLine parameters:")
                x1 = float(input("  Start X [150]: ") or "150")
                y1 = float(input("  Start Y [-50]: ") or "-50")
                z1 = float(input("  Start Z [150]: ") or "150")
                x2 = float(input("  End X [250]: ") or "250")
                y2 = float(input("  End Y [50]: ") or "50")
                z2 = float(input("  End Z [150]: ") or "150")
                draw_line(robot, kinematics, [x1, y1, z1], [x2, y2, z2])
            
            elif choice == '3':
                print("\nSquare parameters:")
                x = float(input("  Center X [200]: ") or "200")
                y = float(input("  Center Y [0]: ") or "0")
                z = float(input("  Center Z [150]: ") or "150")
                s = float(input("  Side length [80]: ") or "80")
                draw_square(robot, kinematics, [x, y, z], s)
            
            elif choice == '4':
                print("\nFigure-8 not yet implemented")
            
            elif choice == '5':
                print("\nReturning to home position...")
                robot.move_to_home()
                time.sleep(3)
                print("✓ At home position")
            
            elif choice == '6':
                break
        
        except Exception as e:
            print(f"\n✗ Error: {e}")
            import traceback
            traceback.print_exc()
    
    # Return to home before exit
    print("\nReturning to home position...")
    robot.move_to_home()
    time.sleep(3)
    
    robot.disconnect()
    print("\n✓ Test complete!")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✗ Test interrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
