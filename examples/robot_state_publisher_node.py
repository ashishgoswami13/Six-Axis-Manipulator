#!/usr/bin/env python3
"""
Robot State Publisher - Publishes real robot joint states to RViz
Reads actual servo positions and publishes to /joint_states for RViz visualization
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Header
import time
from robot_controller import RobotController

class RobotStatePublisher(Node):
    def __init__(self):
        super().__init__('real_robot_joint_publisher')
        
        # Publisher for joint states
        self.joint_state_pub = self.create_publisher(JointState, 'joint_states', 10)
        
        # Connect to robot
        self.get_logger().info("Connecting to robot...")
        self.robot = RobotController()
        if not self.robot.connect():
            self.get_logger().error("Failed to connect to robot!")
            return
        
        self.get_logger().info("✓ Robot connected, publishing joint states...")
        
        # Joint names must match URDF exactly (with spaces as in URDF)
        self.joint_names = [
            'Revolute 1',  # Base
            'Revolute 2',  # Shoulder
            'Revolute 3',  # Elbow
            'Revolute 4',  # Wrist 1
            'Revolute 5',  # Wrist 2
            'Revolute 6',  # Wrist 3
            # Note: Gripper (Joint 7) not in URDF, skip it
        ]
        
        # Joint angle corrections and offsets
        # Some joints need sign flip, some need 180° offset
        self.joint_signs = [
            -1.0,  # Revolute 1: inverted
            -1.0,  # Revolute 2: inverted
            1.0,   # Revolute 3: normal (but may need offset)
            1.0,  # Revolute 4: FLIPPED
            -1.0,   # Revolute 5: normal (but may need offset)
            -1.0,   # Revolute 6: normal (but may need offset)
        ]
        
        # 180 degree offsets for joints that are in opposite reference frame
        self.joint_offsets = [
            0.0,    # J1: no offset
            180.0,    # J2: no offset
            180.0,  # J3: add 180° (raw -177.8° becomes 2.2°)
            180.0,    # J4: no offset
            -180.0,  # J5: add 180° (raw -177.4° becomes 2.6°)
            0.0,    # J6: no offset
        ]
        
        # Timer to publish at 20 Hz
        self.timer = self.create_timer(0.05, self.publish_joint_states)
        
    def publish_joint_states(self):
        """Read robot positions and publish to joint_states topic"""
        # Read current joint positions from robot
        positions_deg = self.robot.get_joint_positions_degrees()
        
        if positions_deg is None:
            self.get_logger().warn("Failed to read joint positions")
            return
        
        # Apply offset and sign correction, then convert to radians
        import math
        positions_rad = [
            math.radians((deg + offset) * sign)
            for deg, offset, sign in zip(positions_deg[:6], self.joint_offsets, self.joint_signs)
        ]
        
        # Debug output every 2 seconds (40 cycles at 20Hz)
        if not hasattr(self, '_debug_counter'):
            self._debug_counter = 0
        self._debug_counter += 1
        if self._debug_counter % 40 == 0:
            corrected_deg = [(deg + offset) * sign for deg, offset, sign in zip(positions_deg[:6], self.joint_offsets, self.joint_signs)]
            self.get_logger().info(f"Raw deg: {[f'{d:.1f}' for d in positions_deg[:6]]}")
            self.get_logger().info(f"Corrected: {[f'{d:.1f}' for d in corrected_deg]}")
        
        # Create JointState message
        msg = JointState()
        msg.header = Header()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = self.joint_names
        msg.position = positions_rad
        msg.velocity = []
        msg.effort = []
        
        # Publish
        self.joint_state_pub.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = RobotStatePublisher()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node.robot:
            node.robot.disconnect()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
