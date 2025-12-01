#!/usr/bin/env python3
"""
Data Collection GUI for OpenVLA Fine-tuning
Records demonstrations with scene camera, gripper camera, joint states, and instructions
"""

import sys
import cv2
import numpy as np
import json
import os
from datetime import datetime
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QTextEdit, 
                             QComboBox, QSpinBox, QGroupBox, QFileDialog,
                             QMessageBox, QProgressBar)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QFont
from robot_controller import RobotController
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

class DataCollectionGUI(QMainWindow):
    def __init__(self, ros_node):
        super().__init__()
        self.setWindowTitle("OpenVLA Data Collection")
        self.setGeometry(100, 100, 1400, 900)
        
        # ROS2 node for camera subscriptions
        self.ros_node = ros_node
        self.bridge = CvBridge()
        
        # Initialize robot
        self.robot = RobotController()
        self.robot_connected = False
        
        # Camera setup
        self.scene_rgb = None  # Orbbec RGB
        self.scene_depth = None  # Orbbec depth
        self.gripper_camera = None  # USB camera
        
        # Recording state
        self.is_recording = False
        self.current_episode = []
        self.dataset_path = Path.home() / "vla_dataset"
        self.dataset_path.mkdir(exist_ok=True)
        
        # Episode counter
        self.episode_count = len(list(self.dataset_path.glob("episode_*")))
        
        # Setup UI
        self.setup_ui()
        
        # Connect to hardware
        self.connect_hardware()
        
        # Start camera update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frames)
        self.timer.start(33)  # ~30 FPS
        
    def setup_ui(self):
        """Create the GUI layout"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("🎥 OpenVLA Data Collection")
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # Camera displays
        camera_layout = QHBoxLayout()
        
        # Scene camera (RGB-D)
        scene_group = QGroupBox("Scene Camera (RGB-D)")
        scene_layout = QVBoxLayout()
        self.scene_rgb_label = QLabel()
        self.scene_rgb_label.setMinimumSize(640, 480)
        self.scene_rgb_label.setStyleSheet("border: 2px solid #666; background: black;")
        self.scene_rgb_label.setAlignment(Qt.AlignCenter)
        scene_layout.addWidget(self.scene_rgb_label)
        
        self.scene_depth_label = QLabel()
        self.scene_depth_label.setMinimumSize(320, 240)
        self.scene_depth_label.setStyleSheet("border: 2px solid #666; background: black;")
        self.scene_depth_label.setAlignment(Qt.AlignCenter)
        scene_layout.addWidget(self.scene_depth_label)
        scene_group.setLayout(scene_layout)
        camera_layout.addWidget(scene_group)
        
        # Gripper camera
        gripper_group = QGroupBox("Gripper Camera")
        gripper_layout = QVBoxLayout()
        self.gripper_label = QLabel()
        self.gripper_label.setMinimumSize(640, 480)
        self.gripper_label.setStyleSheet("border: 2px solid #666; background: black;")
        self.gripper_label.setAlignment(Qt.AlignCenter)
        gripper_layout.addWidget(self.gripper_label)
        gripper_group.setLayout(gripper_layout)
        camera_layout.addWidget(gripper_group)
        
        main_layout.addLayout(camera_layout)
        
        # Control panel
        control_group = QGroupBox("Recording Controls")
        control_layout = QVBoxLayout()
        
        # Instruction input
        instruction_layout = QHBoxLayout()
        instruction_layout.addWidget(QLabel("Instruction:"))
        self.instruction_input = QTextEdit()
        self.instruction_input.setMaximumHeight(60)
        self.instruction_input.setPlaceholderText("e.g., 'pick up the red cup', 'move to home position', 'reach forward'")
        instruction_layout.addWidget(self.instruction_input)
        control_layout.addLayout(instruction_layout)
        
        # Quick instruction templates
        template_layout = QHBoxLayout()
        template_layout.addWidget(QLabel("Quick Templates:"))
        templates = ["go to home", "reach forward", "pick up object", "move left", "move right", "stop"]
        for template in templates:
            btn = QPushButton(template)
            btn.clicked.connect(lambda checked, t=template: self.instruction_input.setText(t))
            template_layout.addWidget(btn)
        control_layout.addLayout(template_layout)
        
        # Recording buttons
        button_layout = QHBoxLayout()
        
        self.record_button = QPushButton("🔴 Start Recording")
        self.record_button.setStyleSheet("background: #4CAF50; color: white; font-size: 16px; padding: 10px;")
        self.record_button.clicked.connect(self.toggle_recording)
        button_layout.addWidget(self.record_button)
        
        self.save_button = QPushButton("💾 Save Episode")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_episode)
        button_layout.addWidget(self.save_button)
        
        self.discard_button = QPushButton("🗑️ Discard")
        self.discard_button.setEnabled(False)
        self.discard_button.clicked.connect(self.discard_episode)
        button_layout.addWidget(self.discard_button)
        
        control_layout.addLayout(button_layout)
        
        # Statistics
        stats_layout = QHBoxLayout()
        self.episode_label = QLabel(f"Episodes collected: {self.episode_count}")
        self.episode_label.setFont(QFont("Arial", 12))
        stats_layout.addWidget(self.episode_label)
        
        self.frame_label = QLabel("Frames in current episode: 0")
        self.frame_label.setFont(QFont("Arial", 12))
        stats_layout.addWidget(self.frame_label)
        control_layout.addLayout(stats_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        control_layout.addWidget(self.progress_bar)
        
        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group)
        
        # Robot status
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Status: Initializing...")
        self.status_label.setFont(QFont("Arial", 10))
        status_layout.addWidget(self.status_label)
        
        self.joint_label = QLabel("Joints: --")
        self.joint_label.setFont(QFont("Monospace", 9))
        status_layout.addWidget(self.joint_label)
        main_layout.addLayout(status_layout)
        
    def connect_hardware(self):
        """Connect to robot and cameras"""
        # Connect robot
        if self.robot.connect():
            self.robot_connected = True
            self.status_label.setText("✓ Robot connected")
            self.status_label.setStyleSheet("color: green;")
        else:
            self.status_label.setText("✗ Robot connection failed")
            self.status_label.setStyleSheet("color: red;")
            
        # Subscribe to Orbbec camera topics (scene camera with depth)
        # Assuming standard Orbbec topic names - adjust if different
        self.ros_node.create_subscription(
            Image,
            '/camera/color/image_raw',  # Orbbec RGB topic
            self.scene_rgb_callback,
            10
        )
        self.ros_node.create_subscription(
            Image,
            '/camera/depth/image_raw',  # Orbbec depth topic
            self.scene_depth_callback,
            10
        )
        print("✓ Subscribed to Orbbec camera topics")
            
        # Initialize USB camera (gripper)
        try:
            self.gripper_camera = cv2.VideoCapture(0)
            self.gripper_camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.gripper_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            print("✓ Gripper camera initialized")
        except Exception as e:
            print(f"✗ Gripper camera initialization failed: {e}")
            
    def scene_rgb_callback(self, msg):
        """Callback for Orbbec RGB images"""
        try:
            self.scene_rgb = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            print(f"Error converting RGB image: {e}")
            
    def scene_depth_callback(self, msg):
        """Callback for Orbbec depth images"""
        try:
            self.scene_depth = self.bridge.imgmsg_to_cv2(msg, desired_encoding='16UC1')
        except Exception as e:
            print(f"Error converting depth image: {e}")
            
    def update_frames(self):
        """Update camera displays and record if active"""
        # Spin ROS node to process callbacks
        rclpy.spin_once(self.ros_node, timeout_sec=0)
        
        # Display Orbbec RGB
        if self.scene_rgb is not None:
            self.display_image(self.scene_rgb, self.scene_rgb_label)
            
        # Display Orbbec depth
        if self.scene_depth is not None:
            depth_colormap = cv2.applyColorMap(
                cv2.convertScaleAbs(self.scene_depth, alpha=0.03), 
                cv2.COLORMAP_JET
            )
            self.display_image(depth_colormap, self.scene_depth_label, size=(320, 240))
                
        # Get gripper camera frame
        gripper_rgb = None
        if self.gripper_camera and self.gripper_camera.isOpened():
            ret, frame = self.gripper_camera.read()
            if ret:
                gripper_rgb = frame
                self.display_image(gripper_rgb, self.gripper_label)
                
        # Get robot joint positions
        joint_positions = None
        if self.robot_connected:
            joint_positions = self.robot.get_joint_positions_degrees()
            if joint_positions:
                joint_str = ", ".join([f"J{i+1}:{j:.1f}°" for i, j in enumerate(joint_positions)])
                self.joint_label.setText(f"Joints: {joint_str}")
                
        # Record frame if recording
        if self.is_recording:
            if self.scene_rgb is not None and gripper_rgb is not None and joint_positions is not None:
                frame_data = {
                    'scene_rgb': self.scene_rgb.copy(),
                    'scene_depth': self.scene_depth.copy() if self.scene_depth is not None else None,
                    'gripper_rgb': gripper_rgb.copy(),
                    'joint_positions': joint_positions.copy(),
                    'timestamp': datetime.now().isoformat()
                }
                self.current_episode.append(frame_data)
                self.frame_label.setText(f"Frames in current episode: {len(self.current_episode)}")
                
    def display_image(self, img, label, size=None):
        """Display image in QLabel"""
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w, ch = img_rgb.shape
        bytes_per_line = ch * w
        qt_img = QImage(img_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        if size:
            pixmap = QPixmap.fromImage(qt_img).scaled(size[0], size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)
        else:
            pixmap = QPixmap.fromImage(qt_img).scaled(label.width(), label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        label.setPixmap(pixmap)
        
    def toggle_recording(self):
        """Start or stop recording"""
        instruction = self.instruction_input.toPlainText().strip()
        
        if not self.is_recording:
            if not instruction:
                QMessageBox.warning(self, "No Instruction", "Please enter an instruction before recording!")
                return
                
            # Start recording
            self.is_recording = True
            self.current_episode = []
            self.current_instruction = instruction
            self.record_button.setText("⏹️ Stop Recording")
            self.record_button.setStyleSheet("background: #f44336; color: white; font-size: 16px; padding: 10px;")
            self.instruction_input.setEnabled(False)
            self.status_label.setText("🔴 RECORDING...")
            self.status_label.setStyleSheet("color: red;")
        else:
            # Stop recording
            self.is_recording = False
            self.record_button.setText("🔴 Start Recording")
            self.record_button.setStyleSheet("background: #4CAF50; color: white; font-size: 16px; padding: 10px;")
            self.instruction_input.setEnabled(True)
            self.save_button.setEnabled(True)
            self.discard_button.setEnabled(True)
            self.status_label.setText(f"✓ Recording stopped. {len(self.current_episode)} frames captured.")
            self.status_label.setStyleSheet("color: blue;")
            
    def save_episode(self):
        """Save the recorded episode to disk"""
        if not self.current_episode:
            return
            
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Create episode directory
        episode_dir = self.dataset_path / f"episode_{self.episode_count:04d}"
        episode_dir.mkdir(exist_ok=True)
        
        # Save metadata
        metadata = {
            'instruction': self.current_instruction,
            'num_frames': len(self.current_episode),
            'timestamp': datetime.now().isoformat()
        }
        
        with open(episode_dir / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
            
        # Save frames
        for i, frame in enumerate(self.current_episode):
            # Save images
            cv2.imwrite(str(episode_dir / f'scene_rgb_{i:04d}.png'), frame['scene_rgb'])
            if frame['scene_depth'] is not None:
                np.save(episode_dir / f'scene_depth_{i:04d}.npy', frame['scene_depth'])
            cv2.imwrite(str(episode_dir / f'gripper_rgb_{i:04d}.png'), frame['gripper_rgb'])
            
            # Save joint positions
            with open(episode_dir / f'joints_{i:04d}.json', 'w') as f:
                json.dump({'joints': frame['joint_positions']}, f)
                
            self.progress_bar.setValue(int((i + 1) / len(self.current_episode) * 100))
            QApplication.processEvents()
            
        self.episode_count += 1
        self.episode_label.setText(f"Episodes collected: {self.episode_count}")
        
        self.progress_bar.setVisible(False)
        self.save_button.setEnabled(False)
        self.discard_button.setEnabled(False)
        self.current_episode = []
        self.frame_label.setText("Frames in current episode: 0")
        self.status_label.setText(f"✓ Episode saved to {episode_dir}")
        self.status_label.setStyleSheet("color: green;")
        
        QMessageBox.information(self, "Success", f"Episode saved!\nTotal episodes: {self.episode_count}")
        
    def discard_episode(self):
        """Discard the current episode"""
        reply = QMessageBox.question(self, "Discard Episode", 
                                     f"Discard {len(self.current_episode)} frames?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.current_episode = []
            self.frame_label.setText("Frames in current episode: 0")
            self.save_button.setEnabled(False)
            self.discard_button.setEnabled(False)
            self.status_label.setText("Episode discarded")
            self.status_label.setStyleSheet("color: orange;")
            
    def closeEvent(self, event):
        """Cleanup on close"""
        if self.robot_connected:
            self.robot.disconnect()
        if self.gripper_camera:
            self.gripper_camera.release()
        event.accept()

def main():
    # Initialize ROS2
    rclpy.init()
    
    # Create a minimal ROS2 node for camera subscriptions
    ros_node = rclpy.create_node('data_collection_node')
    
    # Create Qt application and GUI
    app = QApplication(sys.argv)
    gui = DataCollectionGUI(ros_node)
    gui.show()
    
    # Run Qt event loop
    result = app.exec_()
    
    # Cleanup
    ros_node.destroy_node()
    rclpy.shutdown()
    
    sys.exit(result)

if __name__ == '__main__':
    main()
