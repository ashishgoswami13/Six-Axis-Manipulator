#!/usr/bin/env python3

# Copyright 2025 Kikobot LeRobot Integration
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Kikobot Integration Examples

This file contains example code snippets showing how to use the Kikobot
LeRobot integration for various tasks.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def example_1_basic_connection():
    """Example 1: Basic robot connection and disconnection"""
    print("\n" + "="*60)
    print("Example 1: Basic Robot Connection")
    print("="*60 + "\n")
    
    from robots.kikobot import KikobotFollower, KikobotFollowerConfig
    
    # Create configuration
    config = KikobotFollowerConfig(
        port="/dev/ttyACM0",
        use_degrees=True,
    )
    
    # Create robot instance
    robot = KikobotFollower(config)
    
    # Connect (without calibration)
    robot.connect(calibrate=False)
    
    # Check connection
    print(f"Robot connected: {robot.is_connected}")
    print(f"Robot calibrated: {robot.is_calibrated}")
    
    # Disconnect
    robot.disconnect()
    
    print("\n✓ Example 1 complete\n")


def example_2_read_positions():
    """Example 2: Read current motor positions"""
    print("\n" + "="*60)
    print("Example 2: Reading Motor Positions")
    print("="*60 + "\n")
    
    from robots.kikobot import KikobotLeader, KikobotLeaderConfig
    
    # Create and connect leader arm
    config = KikobotLeaderConfig(port="/dev/ttyACM1")
    robot = KikobotLeader(config)
    robot.connect(calibrate=False)
    
    # Read positions
    observation = robot.get_observation()
    
    print("Current joint positions:")
    for key, value in observation.items():
        if key.endswith('.pos'):
            joint_name = key.replace('.pos', '')
            print(f"  {joint_name:15s}: {value:7.2f}°")
    
    robot.disconnect()
    
    print("\n✓ Example 2 complete\n")


def example_3_teleoperation():
    """Example 3: Simple leader-follower teleoperation"""
    print("\n" + "="*60)
    print("Example 3: Leader-Follower Teleoperation")
    print("="*60 + "\n")
    
    import time
    from robots.kikobot import (
        KikobotLeader, KikobotLeaderConfig,
        KikobotFollower, KikobotFollowerConfig
    )
    
    # Create robots
    leader = KikobotLeader(KikobotLeaderConfig(port="/dev/ttyACM1"))
    follower = KikobotFollower(KikobotFollowerConfig(port="/dev/ttyACM0"))
    
    # Connect both
    leader.connect(calibrate=False)
    follower.connect(calibrate=False)
    
    print("Running teleoperation for 5 seconds...")
    print("Move the leader arm manually!\n")
    
    start_time = time.time()
    iterations = 0
    
    try:
        while time.time() - start_time < 5.0:
            # Read leader
            leader_obs = leader.get_observation()
            
            # Extract positions
            action = {k: v for k, v in leader_obs.items() if k.endswith('.pos')}
            
            # Send to follower
            follower.send_action(action)
            
            iterations += 1
            time.sleep(0.02)  # 50 Hz
    
    finally:
        leader.disconnect()
        follower.disconnect()
    
    print(f"\n✓ Completed {iterations} iterations")
    print("✓ Example 3 complete\n")


def example_4_dataset_info():
    """Example 4: Inspect a recorded dataset"""
    print("\n" + "="*60)
    print("Example 4: Dataset Inspection")
    print("="*60 + "\n")
    
    try:
        from lerobot.common.datasets.lerobot_dataset import LeRobotDataset
    except ImportError:
        print("LeRobot not installed. Skipping this example.")
        return
    
    # Replace with your dataset repo_id
    repo_id = "username/kikobot_demos"
    
    try:
        # Load dataset
        dataset = LeRobotDataset(repo_id=repo_id, root="./data")
        
        print(f"Dataset: {repo_id}")
        print(f"  Total episodes: {len(dataset.episode_data_index)}")
        print(f"  Total frames: {len(dataset)}")
        print(f"  FPS: {dataset.fps}")
        
        # Get first episode
        if len(dataset) > 0:
            print("\nFirst frame features:")
            frame = dataset[0]
            
            print("\n  Observations:")
            for key in frame['observation'].keys():
                print(f"    - {key}")
            
            print("\n  Actions:")
            for key in frame['action'].keys():
                print(f"    - {key}")
        
        print("\n✓ Example 4 complete\n")
    
    except Exception as e:
        print(f"Could not load dataset: {e}")
        print("Record a dataset first using record_dataset.py")


def example_5_custom_configuration():
    """Example 5: Custom robot configuration"""
    print("\n" + "="*60)
    print("Example 5: Custom Configuration")
    print("="*60 + "\n")
    
    from robots.kikobot import KikobotFollowerConfig, KikobotFollower
    
    # Create custom configuration
    config = KikobotFollowerConfig(
        port="/dev/ttyACM0",
        use_degrees=True,
        max_relative_target=20.0,  # More conservative safety limit
        p_coefficient=12,          # Even smoother motion
        i_coefficient=0,
        d_coefficient=32,
        max_torque_limit=800,      # Reduce max torque to 80%
        gripper_max_torque=400,    # Reduce gripper torque to 40%
        default_speed=1000,        # Slower default speed
    )
    
    print("Custom configuration:")
    print(f"  Port: {config.port}")
    print(f"  Use degrees: {config.use_degrees}")
    print(f"  Max relative target: {config.max_relative_target}°")
    print(f"  P coefficient: {config.p_coefficient}")
    print(f"  Max torque: {config.max_torque_limit}")
    print(f"  Gripper torque: {config.gripper_max_torque}")
    print(f"  Default speed: {config.default_speed}")
    
    # Create robot with custom config
    robot = KikobotFollower(config)
    print(f"\n✓ Robot created with custom configuration")
    
    print("\n✓ Example 5 complete\n")


def example_6_calibration():
    """Example 6: Running calibration (interactive)"""
    print("\n" + "="*60)
    print("Example 6: Motor Calibration")
    print("="*60 + "\n")
    
    from robots.kikobot import KikobotFollower, KikobotFollowerConfig
    
    print("This example will run the calibration procedure.")
    print("Make sure the follower arm is connected and ready.")
    
    response = input("\nContinue with calibration? (y/n): ")
    if response.lower() != 'y':
        print("Skipping calibration.")
        return
    
    config = KikobotFollowerConfig(port="/dev/ttyACM0")
    robot = KikobotFollower(config)
    
    # Connect with calibration enabled
    robot.connect(calibrate=True)
    
    print("\n✓ Calibration complete!")
    print(f"   Calibration file: {robot.calibration_fpath}")
    
    robot.disconnect()
    
    print("\n✓ Example 6 complete\n")


def main():
    """Run all examples"""
    print("\n" + "="*60)
    print("Kikobot LeRobot Integration - Examples")
    print("="*60)
    print("\nAvailable examples:")
    print("  1. Basic robot connection")
    print("  2. Reading motor positions")
    print("  3. Leader-follower teleoperation")
    print("  4. Dataset inspection")
    print("  5. Custom configuration")
    print("  6. Motor calibration (interactive)")
    print("\nNote: Examples 2, 3, and 6 require hardware to be connected.")
    print("\nSelect an example (1-6) or 'all' to run compatible examples:")
    
    choice = input("\nChoice: ").strip().lower()
    
    examples = {
        '1': example_1_basic_connection,
        '2': example_2_read_positions,
        '3': example_3_teleoperation,
        '4': example_4_dataset_info,
        '5': example_5_custom_configuration,
        '6': example_6_calibration,
    }
    
    if choice == 'all':
        # Run examples that don't require hardware
        example_5_custom_configuration()
        example_4_dataset_info()
    elif choice in examples:
        examples[choice]()
    else:
        print(f"Invalid choice: {choice}")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
