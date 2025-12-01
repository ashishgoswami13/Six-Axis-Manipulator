#!/usr/bin/env python3
"""
Robot Controller Interface
Low-level interface to control KikoBot C1 via Waveshare servo adapter
Wraps the servo protocol for easy position/velocity control
"""

import serial
import struct
import time
import numpy as np
from servo_limits_config import SERVO_CONFIG, degrees_to_steps, steps_to_degrees

# SMS/STS Protocol Commands
INST_PING = 1
INST_READ = 2
INST_WRITE = 3
INST_SYNC_WRITE = 131

# Memory addresses
SMS_STS_GOAL_POSITION_L = 42
SMS_STS_GOAL_SPEED_L = 46
SMS_STS_GOAL_ACC = 41
SMS_STS_PRESENT_POSITION_L = 56
SMS_STS_TORQUE_ENABLE = 40

class RobotController:
    """
    High-level interface for KikoBot C1 control
    Handles servo communication, safety checks, and coordinate transformations
    """
    
    def __init__(self, port='/dev/ttyACM0', baudrate=1000000):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.connected = False
        
        # Servo configuration (ID, name, min_steps, max_steps, home_steps)
        self.servo_config = SERVO_CONFIG
        self.num_servos = len(SERVO_CONFIG)
        
        # Current joint positions (in steps)
        self.current_positions = [config[4] for config in SERVO_CONFIG]  # home positions
        
        # Default motion parameters
        self.default_speed = 1500  # steps/sec
        self.default_acc = 50      # acceleration
        
        # Safety limits
        self.max_position_change = 500  # Maximum steps change per command (safety)
        self.min_move_threshold = 10   # Minimum steps to trigger movement
        
    def connect(self):
        """Connect to servo adapter"""
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=0.1)
            time.sleep(0.1)
            self.connected = True
            print(f"✓ Connected to robot on {self.port}")
            
            # Ping all servos
            online = []
            for servo_id, name, _, _, _ in self.servo_config:
                if self.ping(servo_id):
                    online.append(servo_id)
            
            print(f"✓ Found {len(online)}/{self.num_servos} servos online: {online}")
            return True
            
        except Exception as e:
            print(f"✗ Connection error: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect from servo adapter"""
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.connected = False
        print("✓ Disconnected from robot")
    
    def calculate_checksum(self, data):
        """Calculate checksum for SMS/STS protocol"""
        return (~sum(data)) & 0xFF
    
    def write_packet(self, servo_id, instruction, params):
        """Send a packet to servo"""
        if not self.connected:
            return False
            
        length = len(params) + 2
        packet = [0xFF, 0xFF, servo_id, length, instruction] + params
        checksum = self.calculate_checksum(packet[2:])
        packet.append(checksum)
        
        try:
            self.ser.write(bytes(packet))
            return True
        except Exception as e:
            print(f"Write error: {e}")
            return False
    
    def read_packet(self):
        """Read response packet from servo"""
        if not self.connected:
            return None
            
        try:
            # Look for header
            timeout = time.time() + 0.1
            while time.time() < timeout:
                if self.ser.in_waiting > 0:
                    if self.ser.read(1)[0] == 0xFF:
                        if self.ser.read(1)[0] == 0xFF:
                            # Got header, read rest
                            servo_id = self.ser.read(1)[0]
                            length = self.ser.read(1)[0]
                            error = self.ser.read(1)[0]
                            
                            params = []
                            for _ in range(length - 2):
                                params.append(self.ser.read(1)[0])
                            
                            checksum = self.ser.read(1)[0]
                            return {'id': servo_id, 'error': error, 'params': params}
            return None
        except Exception as e:
            print(f"Read error: {e}")
            return None
    
    def ping(self, servo_id):
        """Ping a servo to check connection"""
        if self.write_packet(servo_id, INST_PING, []):
            time.sleep(0.01)
            response = self.read_packet()
            return response is not None
        return False
    
    def write_position(self, servo_id, position, speed=None, acc=None):
        """
        Write goal position to a single servo
        
        Args:
            servo_id: Servo ID (1-7)
            position: Target position in steps (0-4095)
            speed: Movement speed in steps/sec (default: self.default_speed)
            acc: Acceleration (default: self.default_acc)
        """
        if speed is None:
            speed = self.default_speed
        if acc is None:
            acc = self.default_acc
        
        # Clamp position to valid range
        position = int(max(0, min(4095, position)))
        speed = int(max(0, min(2400, speed)))
        acc = int(max(0, min(254, acc)))
        
        # Build parameter list: [acc, position_low, position_high, 0, 0, speed_low, speed_high]
        params = [
            acc,
            position & 0xFF,
            (position >> 8) & 0xFF,
            0,  # Time (not used)
            0,
            speed & 0xFF,
            (speed >> 8) & 0xFF
        ]
        
        return self.write_packet(servo_id, INST_WRITE, [SMS_STS_GOAL_ACC] + params)
    
    def read_position(self, servo_id):
        """
        Read current position from a servo
        
        Returns:
            Current position in steps, or None if read failed
        """
        if self.write_packet(servo_id, INST_READ, [SMS_STS_PRESENT_POSITION_L, 2]):
            time.sleep(0.01)
            response = self.read_packet()
            if response and len(response['params']) >= 2:
                position = response['params'][0] | (response['params'][1] << 8)
                return position
        return None
    
    def get_joint_positions_degrees(self):
        """
        Read all joint positions in degrees
        
        Returns:
            List of 7 joint angles in degrees, or None if read failed
        """
        positions = []
        for servo_id, _, _, _, _ in self.servo_config:
            pos_steps = self.read_position(servo_id)
            if pos_steps is not None:
                pos_deg = steps_to_degrees(pos_steps)
                positions.append(pos_deg)
            else:
                return None
        return positions
    
    def set_joint_positions_degrees(self, joint_angles_deg, speed=None, acc=None):
        """
        Set all joint positions from degrees
        
        Args:
            joint_angles_deg: List of 7 joint angles in degrees
            speed: Movement speed (default: self.default_speed)
            acc: Acceleration (default: self.default_acc)
        
        Returns:
            True if command sent successfully
        """
        if len(joint_angles_deg) != self.num_servos:
            print(f"Error: Expected {self.num_servos} joint angles, got {len(joint_angles_deg)}")
            return False
        
        # Convert to steps and apply safety checks
        target_steps = []
        for i, (servo_id, name, min_steps, max_steps, home_steps) in enumerate(self.servo_config):
            # Convert to steps
            steps = degrees_to_steps(joint_angles_deg[i])
            
            # Safety check: clamp to limits
            if steps < min_steps or steps > max_steps:
                print(f"⚠ Warning: {name} target {steps} steps outside limits [{min_steps}, {max_steps}]")
                steps = max(min_steps, min(max_steps, steps))
            
            # Safety check: limit change rate
            change = abs(steps - self.current_positions[i])
            if change > self.max_position_change:
                print(f"⚠ Warning: {name} change too large ({change} steps), clamping to {self.max_position_change}")
                if steps > self.current_positions[i]:
                    steps = self.current_positions[i] + self.max_position_change
                else:
                    steps = self.current_positions[i] - self.max_position_change
            
            target_steps.append(steps)
        
        # Send commands to all servos
        success = True
        for i, (servo_id, _, _, _, _) in enumerate(self.servo_config):
            if not self.write_position(servo_id, target_steps[i], speed, acc):
                success = False
        
        # Update current positions if successful
        if success:
            self.current_positions = target_steps
        
        return success
    
    def move_to_home(self):
        """Move all servos to home position"""
        home_angles = [steps_to_degrees(config[4]) for config in self.servo_config]
        print("Moving to home position...")
        return self.set_joint_positions_degrees(home_angles, speed=1000, acc=30)
    
    def emergency_stop(self):
        """Emergency stop - stop all servos immediately"""
        print("🛑 EMERGENCY STOP")
        for servo_id, _, _, _, _ in self.servo_config:
            # Write current position as goal (stops motion)
            pos = self.read_position(servo_id)
            if pos is not None:
                self.write_position(servo_id, pos, speed=0, acc=200)
    
    def is_safe_position(self, joint_angles_deg):
        """
        Check if a set of joint angles is within safe limits
        
        Args:
            joint_angles_deg: List of 7 joint angles in degrees
        
        Returns:
            (is_safe, error_message)
        """
        if len(joint_angles_deg) != self.num_servos:
            return False, f"Expected {self.num_servos} joints, got {len(joint_angles_deg)}"
        
        for i, (servo_id, name, min_steps, max_steps, _) in enumerate(self.servo_config):
            steps = degrees_to_steps(joint_angles_deg[i])
            
            if steps < min_steps or steps > max_steps:
                min_deg = steps_to_degrees(min_steps)
                max_deg = steps_to_degrees(max_steps)
                return False, f"{name}: {joint_angles_deg[i]:.1f}° outside safe range [{min_deg:.1f}°, {max_deg:.1f}°]"
        
        return True, "Safe"
    
    def get_end_effector_state(self):
        """
        Get approximate end effector state (for monitoring only)
        This is a simplified forward kinematics - not accurate for control
        
        Returns:
            Dictionary with estimated position and gripper state
        """
        positions = self.get_joint_positions_degrees()
        if positions is None:
            return None
        
        # Very rough approximation - replace with proper forward kinematics
        # This is just for visualization/monitoring
        base_angle = np.deg2rad(positions[0])
        shoulder_angle = np.deg2rad(positions[1])
        elbow_angle = np.deg2rad(positions[2])
        
        # Simple planar approximation (ignoring wrist joints for now)
        link1 = 0.15  # approximate link lengths in meters
        link2 = 0.15
        
        x = link1 * np.cos(shoulder_angle) + link2 * np.cos(shoulder_angle + elbow_angle)
        y = link1 * np.sin(shoulder_angle) + link2 * np.sin(shoulder_angle + elbow_angle)
        
        # Rotate by base
        x_world = x * np.cos(base_angle)
        y_world = x * np.sin(base_angle)
        z_world = y
        
        return {
            'position': [x_world, y_world, z_world],
            'gripper': positions[6]  # gripper angle
        }


if __name__ == "__main__":
    # Test the robot controller
    print("Testing Robot Controller...")
    
    robot = RobotController()
    
    if robot.connect():
        print("\n✓ Robot connected successfully")
        
        # Read current positions
        positions = robot.get_joint_positions_degrees()
        if positions:
            print("\nCurrent joint positions:")
            for i, (_, name, _, _, _) in enumerate(robot.servo_config):
                print(f"  {name}: {positions[i]:.1f}°")
        
        # Test safety check
        test_angles = [0, 0, 0, 0, 0, 0, 0]
        is_safe, msg = robot.is_safe_position(test_angles)
        print(f"\nSafety check for {test_angles}: {msg}")
        
        # Move to home (commented out for safety - uncomment to test)
        # response = input("\nMove to home position? (y/n): ")
        # if response.lower() == 'y':
        #     robot.move_to_home()
        #     time.sleep(2)
        
        robot.disconnect()
    else:
        print("✗ Failed to connect to robot")
