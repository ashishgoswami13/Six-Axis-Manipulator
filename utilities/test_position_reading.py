#!/usr/bin/env python3
"""
Test robot position reading reliability
"""

from robot_controller import RobotController
import time

def test_position_reading():
    robot = RobotController()
    
    if not robot.connect():
        print("❌ Failed to connect to robot")
        return
    
    print("\nTesting position reading reliability (20 attempts)...")
    print(f"{'Attempt':<10} {'Success':<10} {'Joint 1':<12} {'Joint 2':<12} {'Joint 3':<12}")
    print("-" * 70)
    
    success_count = 0
    for i in range(20):
        positions = robot.get_joint_positions_degrees()
        if positions:
            success_count += 1
            print(f"{i+1:<10} ✓{'':<9} {positions[0]:>10.1f}° {positions[1]:>10.1f}° {positions[2]:>10.1f}°")
        else:
            print(f"{i+1:<10} ✗{'':<9} {'FAILED':<12} {'FAILED':<12} {'FAILED':<12}")
        time.sleep(0.1)
    
    print(f"\nSuccess rate: {success_count}/20 ({success_count/20*100:.0f}%)")
    
    robot.disconnect()

if __name__ == "__main__":
    test_position_reading()
