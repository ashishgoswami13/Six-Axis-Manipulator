#!/usr/bin/env python3
"""
Automated Data Collection for OpenVLA
Moves robot to random positions, then records homing movement.
This creates proper training data with varied starting positions.
"""

import serial
import struct
import numpy as np
import cv2
import time
import json
from pathlib import Path
from datetime import datetime
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image as ROSImage
from cv_bridge import CvBridge

# Import home positions
from servo_limits_config import ACTUAL_HOME_STEPS, JOINT_LIMITS_DEG, degrees_to_steps, steps_to_degrees

# SMS/STS Protocol Commands
INST_PING = 1
INST_READ = 2
INST_WRITE = 3
INST_SYNC_WRITE = 131

class AutomatedDataCollector(Node):
    def __init__(self):
        super().__init__('automated_data_collector')
        
        # Robot connection using direct serial
        self.DEVICENAME = '/dev/ttyACM0'
        self.BAUDRATE = 1000000
        
        try:
            self.serial_port = serial.Serial(
                port=self.DEVICENAME,
                baudrate=self.BAUDRATE,
                timeout=1
            )
            self.get_logger().info("✓ Connected to robot")
        except Exception as e:
            raise Exception(f"Failed to connect to robot: {e}")
        
        # Servo configuration
        self.servo_ids = [1, 2, 3, 4, 5, 6, 7]
        self.home_steps = ACTUAL_HOME_STEPS
        
        # Joint limits (in steps)
        self.joint_limits = []
        for i, (servo_id, name, min_deg, max_deg) in enumerate(JOINT_LIMITS_DEG):
            min_steps = degrees_to_steps(min_deg)
            max_steps = degrees_to_steps(max_deg)
            self.joint_limits.append((min_steps, max_steps))
        
        self.get_logger().info(f"✓ Home position: {self.home_steps}")
        self.get_logger().info(f"✓ Joint limits loaded")
        
        # Camera
        self.bridge = CvBridge()
        self.latest_scene_image = None
        
        self.scene_sub = self.create_subscription(
            ROSImage, '/camera/color/image_raw',
            self.scene_callback, 10
        )
        
        # Dataset directory
        self.dataset_dir = Path.home() / "vla_dataset"
        self.dataset_dir.mkdir(exist_ok=True)
        
        # Enable torque
        for servo_id in self.servo_ids:
            self.write_byte(servo_id, 40, 1)  # Address 40 = torque enable
        self.get_logger().info("✓ Torque enabled")
        
        # Statistics
        self.episodes_collected = 0
        self.start_time = time.time()
    
    def calculate_checksum(self, data):
        """Calculate checksum for SMS/STS protocol"""
        return (~sum(data)) & 0xFF
    
    def write_byte(self, servo_id, address, value):
        """Write single byte to servo"""
        data = [servo_id, 4, INST_WRITE, address, value & 0xFF]
        checksum = self.calculate_checksum(data)
        packet = bytes([0xFF, 0xFF] + data + [checksum])
        self.serial_port.write(packet)
        time.sleep(0.001)
    
    def write_word(self, servo_id, address, value):
        """Write 2 bytes (word) to servo"""
        data = [servo_id, 5, INST_WRITE, address, value & 0xFF, (value >> 8) & 0xFF]
        checksum = self.calculate_checksum(data)
        packet = bytes([0xFF, 0xFF] + data + [checksum])
        self.serial_port.write(packet)
        time.sleep(0.001)
    
    def read_word(self, servo_id, address):
        """Read 2 bytes (word) from servo"""
        data = [servo_id, 4, INST_READ, address, 2]
        checksum = self.calculate_checksum(data)
        packet = bytes([0xFF, 0xFF] + data + [checksum])
        
        self.serial_port.flushInput()
        self.serial_port.write(packet)
        time.sleep(0.005)
        
        if self.serial_port.in_waiting >= 8:
            response = self.serial_port.read(8)
            if len(response) == 8 and response[0] == 0xFF and response[1] == 0xFF:
                value = response[5] + (response[6] << 8)
                return value
        return None
    
    def scene_callback(self, msg):
        """Store latest camera image"""
        try:
            self.latest_scene_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f"Camera error: {e}")
    
    def get_current_positions(self):
        """Read current joint positions"""
        positions = []
        for servo_id in self.servo_ids:
            pos = self.read_word(servo_id, 56)  # Address 56 = current position
            if pos is not None:
                positions.append(pos)
            else:
                positions.append(2048)  # Default center if read fails
        return positions
    
    def move_to_position(self, target_steps, speed=30, wait=True):
        """Move robot to target position (slow and safe)"""
        # Set speed for all servos - SLOW for safety
        for servo_id in self.servo_ids:
            self.write_byte(servo_id, 46, speed)  # Address 46 = speed
            self.write_byte(servo_id, 41, 20)  # Address 41 = acceleration
        
        # Send target positions
        for servo_id, target in zip(self.servo_ids, target_steps):
            self.write_word(servo_id, 42, target)  # Address 42 = target position
        
        if wait:
            # Wait for movement to complete
            time.sleep(0.5)
            max_wait = 100  # 10 seconds max
            for _ in range(max_wait):
                current = self.get_current_positions()
                distances = [abs(c - t) for c, t in zip(current, target_steps)]
                if max(distances) < 15:  # Close enough
                    break
                time.sleep(0.1)
    
    def generate_random_position(self):
        """Generate safe random position within joint limits"""
        random_pos = []
        for i, (min_steps, max_steps) in enumerate(self.joint_limits):
            # Use narrower range for safety (50% of full range - extra conservative)
            mid = (min_steps + max_steps) / 2
            range_size = (max_steps - min_steps) * 0.5  # More conservative than 0.7
            
            random_val = mid + np.random.uniform(-range_size/2, range_size/2)
            random_pos.append(int(random_val))
        
        return random_pos
    
    def degrees_to_steps_func(self, deg):
        """Use imported function"""
        return degrees_to_steps(deg)
    
    def steps_to_degrees_func(self, steps):
        """Use imported function"""
        return steps_to_degrees(steps)
    
    def record_homing_trajectory(self, episode_num):
        """Record robot moving from current position to home"""
        episode_dir = self.dataset_dir / f"episode_{episode_num:04d}"
        episode_dir.mkdir(exist_ok=True)
        
        trajectory = {
            'episode_id': episode_num,
            'task': 'go to home',
            'timestamp': datetime.now().isoformat(),
            'frames': []
        }
        
        self.get_logger().info(f"Recording episode {episode_num}...")
        
        # Get starting position
        start_pos = self.get_current_positions()
        start_deg = [steps_to_degrees(s) for s in start_pos]
        
        self.get_logger().info(f"  Start: {[f'{d:.1f}°' for d in start_deg]}")
        
        # Move to home while recording
        # Use very slow speed for better data collection at 30Hz
        speed = 10  # Even slower = more frames captured during movement
        
        for servo_id in self.servo_ids:
            self.write_byte(servo_id, 46, speed)
            self.write_byte(servo_id, 41, 5)  # very slow acceleration
        
        # Send home command
        for servo_id, target in zip(self.servo_ids, self.home_steps):
            self.write_word(servo_id, 42, target)
        
        # Wait a moment for camera to be ready
        time.sleep(0.1)
        
        # Record frames while moving - ONLY during movement
        frame_count = 0
        recording_start = time.time()
        
        # Track movement
        prev_pos = self.get_current_positions()
        still_count = 0
        
        while True:
            # Process ROS callbacks to get latest image
            rclpy.spin_once(self, timeout_sec=0.01)
            
            # Get current state
            current_pos = self.get_current_positions()
            current_deg = [steps_to_degrees(s) for s in current_pos]
            
            # Check if reached home
            distances = [abs(c - h) for c, h in zip(current_pos, self.home_steps)]
            max_dist = max(distances)
            
            if max_dist < 15:  # Reached home
                break
            
            # Check if robot is actually moving
            movement = max([abs(c - p) for c, p in zip(current_pos, prev_pos)])
            
            if movement < 2:  # Robot not moving much
                still_count += 1
                if still_count > 10:  # Been still for too long, probably stuck
                    self.get_logger().warn(f"Robot stopped moving (distance: {max_dist} steps)")
                    break
            else:
                still_count = 0  # Reset if moving
            
            # ONLY save frame if robot is moving AND we have image
            if self.latest_scene_image is not None and movement >= 2:
                # Save image
                img_path = episode_dir / f"frame_{frame_count:04d}.jpg"
                cv2.imwrite(str(img_path), self.latest_scene_image)
                
                # Save joint state
                trajectory['frames'].append({
                    'frame_id': frame_count,
                    'timestamp': time.time() - recording_start,
                    'joint_positions': current_deg,
                    'joint_positions_steps': current_pos,
                    'image_path': f"frame_{frame_count:04d}.jpg"
                })
                
                frame_count += 1
                prev_pos = current_pos
            
            time.sleep(0.033)  # 30Hz sampling rate
            
            # Safety timeout
            if time.time() - recording_start > 60:
                self.get_logger().warn("Recording timeout!")
                break
        
        # Get final position
        final_pos = self.get_current_positions()
        final_deg = [steps_to_degrees(s) for s in final_pos]
        
        # Save final frame
        if self.latest_scene_image is not None:
            img_path = episode_dir / f"frame_{frame_count:04d}.jpg"
            cv2.imwrite(str(img_path), self.latest_scene_image)
            
            trajectory['frames'].append({
                'frame_id': frame_count,
                'timestamp': time.time() - recording_start,
                'joint_positions': final_deg,
                'joint_positions_steps': final_pos,
                'image_path': f"frame_{frame_count:04d}.jpg"
            })
            frame_count += 1
        
        # Save metadata
        metadata_path = episode_dir / "trajectory.json"
        with open(metadata_path, 'w') as f:
            json.dump(trajectory, f, indent=2)
        
        self.get_logger().info(f"  ✓ Recorded {frame_count} frames")
        self.get_logger().info(f"  ✓ End: {[f'{d:.1f}°' for d in final_deg]}")
        
        return frame_count + 1
    
    def collect_episodes(self, num_episodes=100):
        """Main data collection loop"""
        self.get_logger().info("\n" + "="*70)
        self.get_logger().info(f"Starting Automated Data Collection")
        self.get_logger().info("="*70)
        self.get_logger().info(f"Target: {num_episodes} episodes")
        self.get_logger().info(f"Strategy: Random position → Home")
        self.get_logger().info(f"Dataset: {self.dataset_dir}")
        self.get_logger().info("="*70 + "\n")
        
        # First, move to home
        self.get_logger().info("Moving to home position (slow for safety)...")
        self.move_to_position(self.home_steps, speed=30, wait=True)  # Slow speed
        time.sleep(2)  # Extra stabilization time
        
        for episode in range(num_episodes):
            try:
                self.get_logger().info(f"\n{'='*70}")
                self.get_logger().info(f"Episode {episode + 1}/{num_episodes}")
                self.get_logger().info(f"{'='*70}")
                
                # Generate random starting position
                random_pos = self.generate_random_position()
                random_deg = [steps_to_degrees(s) for s in random_pos]
                
                self.get_logger().info(f"Moving to random position: {[f'{d:.1f}°' for d in random_deg]}")
                self.move_to_position(random_pos, speed=30, wait=True)  # Slow speed for safety
                
                # Wait for robot to stabilize
                time.sleep(0.5)
                
                # Record homing movement
                num_frames = self.record_homing_trajectory(episode + 1)
                
                self.episodes_collected += 1
                
                # Statistics
                elapsed = time.time() - self.start_time
                episodes_per_min = (self.episodes_collected / elapsed) * 60
                remaining = num_episodes - self.episodes_collected
                eta_min = remaining / episodes_per_min if episodes_per_min > 0 else 0
                
                self.get_logger().info(f"\nProgress: {self.episodes_collected}/{num_episodes} episodes")
                self.get_logger().info(f"Rate: {episodes_per_min:.1f} episodes/min")
                self.get_logger().info(f"ETA: {eta_min:.1f} minutes")
                
                # Brief pause between episodes
                time.sleep(0.5)
                
            except KeyboardInterrupt:
                self.get_logger().info("\n\nInterrupted by user!")
                break
            except Exception as e:
                self.get_logger().error(f"Error in episode {episode + 1}: {e}")
                import traceback
                traceback.print_exc()
                # Try to recover
                time.sleep(2)
                continue
        
        self.get_logger().info("\n" + "="*70)
        self.get_logger().info(f"Data Collection Complete!")
        self.get_logger().info("="*70)
        self.get_logger().info(f"Episodes collected: {self.episodes_collected}")
        self.get_logger().info(f"Total time: {(time.time() - self.start_time)/60:.1f} minutes")
        self.get_logger().info(f"Dataset location: {self.dataset_dir}")
        self.get_logger().info("="*70 + "\n")
    
    def cleanup(self):
        """Disable torque and close connection"""
        self.get_logger().info("Cleaning up...")
        for servo_id in self.servo_ids:
            self.write_byte(servo_id, 40, 0)  # Disable torque
        self.serial_port.close()
        self.get_logger().info("✓ Connection closed")

def main():
    print("\n" + "="*70)
    print("Automated OpenVLA Data Collection")
    print("="*70)
    print("This will automatically collect training data by:")
    print("  1. Moving robot to random positions")
    print("  2. Recording movement back to HOME")
    print("  3. Repeating 100+ times")
    print("\nThis creates proper varied training data for OpenVLA!")
    print("="*70 + "\n")
    
    # Get number of episodes
    try:
        num_episodes = int(input("How many episodes to collect? [100]: ") or "100")
    except:
        num_episodes = 100
    
    print(f"\nWill collect {num_episodes} episodes")
    print("Press Ctrl+C at any time to stop\n")
    input("Press ENTER to start...")
    
    rclpy.init()
    
    collector = None
    try:
        collector = AutomatedDataCollector()
        # Wait for camera
        time.sleep(2)
        collector.collect_episodes(num_episodes)
    except KeyboardInterrupt:
        print("\n\nStopped by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if collector:
            collector.cleanup()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == "__main__":
    main()
