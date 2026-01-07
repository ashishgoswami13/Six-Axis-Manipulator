#!/usr/bin/env python3
"""
Servo Control GUI for 7-Axis Manipulator
Interactive GUI for controlling ST3215 servo motors
"""

import sys
import serial
import struct
import time
import os
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QSlider, QPushButton, 
                             QSpinBox, QGroupBox, QGridLayout, QTabWidget,
                             QLineEdit, QMessageBox, QComboBox, QTextEdit,
                             QInputDialog, QListWidget, QFileDialog)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette

# Try to load custom servo configuration
try:
    from servo_limits_config import SERVO_CONFIG
    print("✓ Loaded custom servo limits from servo_limits_config.py")
except ImportError:
    print("⚠ Using default servo limits (edit servo_limits_config.py to customize)")
    SERVO_CONFIG = None

# Coordinate transform - robot is mounted with 90° clockwise rotation
J1_OFFSET = 90.0

def degrees_to_steps(deg):
    """Convert degrees to servo steps (matches C++ implementation)"""
    steps = 2048.0 + (deg / 360.0) * 4096.0
    while steps < 0:
        steps += 4096.0
    while steps >= 4096.0:
        steps -= 4096.0
    return int(steps + 0.5)

def steps_to_degrees(steps):
    """Convert servo steps to degrees (centered around 0°)"""
    angle = (steps / 4096.0) * 360.0
    if angle >= 360.0:
        angle -= 360.0
    if angle > 180.0:
        angle -= 360.0
    return angle

# SMS/STS Protocol Commands
INST_PING = 1
INST_READ = 2
INST_WRITE = 3
INST_REG_WRITE = 4
INST_ACTION = 5
INST_SYNC_WRITE = 131
INST_SYNC_READ = 132

# Memory addresses
SMS_STS_PRESENT_POSITION_L = 56
SMS_STS_PRESENT_SPEED_L = 58
SMS_STS_PRESENT_LOAD_L = 60
SMS_STS_PRESENT_VOLTAGE = 62
SMS_STS_PRESENT_TEMPERATURE = 63
SMS_STS_MOVING = 66
SMS_STS_PRESENT_CURRENT_L = 69
SMS_STS_GOAL_POSITION_L = 42
SMS_STS_GOAL_SPEED_L = 46
SMS_STS_GOAL_ACC = 41
# Note: ST3215 uses same register for acceleration and deceleration
# We'll use the deceleration value when stopping motion

class ServoProtocol:
    """Handles low-level communication with SMS/STS servos"""
    
    def __init__(self, port='/dev/ttyACM0', baudrate=1000000):
        self.ser = None
        self.port = port
        self.baudrate = baudrate
        
    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=0.1)
            time.sleep(0.1)
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
    
    def calculate_checksum(self, data):
        """Calculate checksum for SMS/STS protocol"""
        return (~sum(data)) & 0xFF
    
    def write_packet(self, servo_id, instruction, params):
        """Send a packet to servo"""
        if not self.ser or not self.ser.is_open:
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
        if not self.ser or not self.ser.is_open:
            return None
            
        try:
            # Look for header
            while self.ser.in_waiting > 0:
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
    
    def write_position(self, servo_id, position, speed=2400, acc=50, dec=50):
        """Write goal position, speed, acceleration and deceleration"""
        # First enable torque
        self.write_packet(servo_id, INST_WRITE, [40, 1])  # Enable torque at address 40
        time.sleep(0.01)
        
        # ST3215 uses ACC register for both acceleration and deceleration
        # We use the average of both for smooth motion, or acc for starting
        combined_acc = int((acc + dec) / 2) if acc != dec else acc
        
        # Write acceleration first
        self.write_packet(servo_id, INST_WRITE, [SMS_STS_GOAL_ACC, combined_acc])
        time.sleep(0.01)
        
        # Write position with speed - direct WRITE for immediate execution
        params = [
            SMS_STS_GOAL_POSITION_L,
            position & 0xFF,
            (position >> 8) & 0xFF,
            0,  # Time low byte
            0,  # Time high byte  
            speed & 0xFF,
            (speed >> 8) & 0xFF
        ]
        result = self.write_packet(servo_id, INST_WRITE, params)
        return result
    
    def action(self, servo_id=254):
        """Trigger action (execute REG_WRITE commands)"""
        return self.write_packet(servo_id, INST_ACTION, [])
    
    def enable_torque(self, servo_id, enable=True):
        """Enable or disable servo torque"""
        return self.write_packet(servo_id, INST_WRITE, [40, 1 if enable else 0])
    
    def read_position(self, servo_id):
        """Read current position"""
        if self.write_packet(servo_id, INST_READ, [SMS_STS_PRESENT_POSITION_L, 2]):
            time.sleep(0.01)
            response = self.read_packet()
            if response and len(response['params']) >= 2:
                return response['params'][0] | (response['params'][1] << 8)
        return None
    
    def read_feedback(self, servo_id):
        """Read all feedback data"""
        if self.write_packet(servo_id, INST_READ, [SMS_STS_PRESENT_POSITION_L, 14]):
            time.sleep(0.01)
            response = self.read_packet()
            if response and len(response['params']) >= 14:
                params = response['params']
                return {
                    'position': params[0] | (params[1] << 8),
                    'speed': params[2] | (params[3] << 8),
                    'load': params[4] | (params[5] << 8),
                    'voltage': params[6],
                    'temperature': params[7],
                    'moving': params[10],
                    'current': params[13] | (params[14] << 8) if len(params) > 14 else 0
                }
        return None


class ServoControlWidget(QWidget):
    """Widget for controlling a single servo"""
    
    def __init__(self, servo_id, joint_name, protocol, min_pos=0, max_pos=4095):
        super().__init__()
        self.servo_id = servo_id
        self.joint_name = joint_name
        self.protocol = protocol
        self.min_pos = min_pos
        self.max_pos = max_pos
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Header with limits
        header = QLabel(f"{self.joint_name} (ID: {self.servo_id})")
        header.setFont(QFont('Arial', 10, QFont.Bold))
        layout.addWidget(header)
        
        limits_label = QLabel(f"Limits: {self.min_pos} - {self.max_pos}")
        limits_label.setStyleSheet("color: gray; font-size: 9px;")
        layout.addWidget(limits_label)
        
        # Position slider
        slider_layout = QHBoxLayout()
        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setMinimum(self.min_pos)
        self.position_slider.setMaximum(self.max_pos)
        self.position_slider.setValue((self.min_pos + self.max_pos) // 2)
        self.position_slider.valueChanged.connect(self.on_slider_change)
        
        self.position_spinbox = QSpinBox()
        self.position_spinbox.setMinimum(self.min_pos)
        self.position_spinbox.setMaximum(self.max_pos)
        self.position_spinbox.setValue((self.min_pos + self.max_pos) // 2)
        self.position_spinbox.valueChanged.connect(self.on_spinbox_change)
        
        slider_layout.addWidget(self.position_slider, 4)
        slider_layout.addWidget(self.position_spinbox, 1)
        layout.addLayout(slider_layout)
        
        # Current position display
        self.current_pos_label = QLabel("Current: ---")
        self.current_pos_label.setStyleSheet("color: blue;")
        layout.addWidget(self.current_pos_label)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.move_btn = QPushButton("Move")
        self.move_btn.clicked.connect(self.move_to_position)
        
        self.center_btn = QPushButton("Center")
        self.center_btn.clicked.connect(self.move_to_center)
        
        self.read_btn = QPushButton("Read")
        self.read_btn.clicked.connect(self.read_position)
        
        button_layout.addWidget(self.move_btn)
        button_layout.addWidget(self.center_btn)
        button_layout.addWidget(self.read_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def on_slider_change(self, value):
        self.position_spinbox.blockSignals(True)
        self.position_spinbox.setValue(value)
        self.position_spinbox.blockSignals(False)
    
    def on_spinbox_change(self, value):
        self.position_slider.blockSignals(True)
        self.position_slider.setValue(value)
        self.position_slider.blockSignals(False)
    
    def move_to_position(self):
        position = self.position_slider.value()
        if self.protocol.write_position(self.servo_id, position):
            self.protocol.action(self.servo_id)
    
    def move_to_center(self):
        center = (self.min_pos + self.max_pos) // 2
        self.position_slider.setValue(center)
        self.move_to_position()
    
    def read_position(self):
        pos = self.protocol.read_position(self.servo_id)
        if pos is not None:
            self.current_pos_label.setText(f"Current: {pos}")
            self.current_pos_label.setStyleSheet("color: green;")
        else:
            self.current_pos_label.setText("Current: Error")
            self.current_pos_label.setStyleSheet("color: red;")
    
    def get_position(self):
        return self.position_slider.value()
    
    def set_position(self, position):
        self.position_slider.setValue(position)


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        # Load servo configuration from config file or use defaults
        # Configuration matches HomeAll.cpp joint limits
        if SERVO_CONFIG:
            self.servo_config = SERVO_CONFIG
        else:
            # Default configuration from HomeAll.cpp - tested and safe
            joint_limits = [
                (1, "Joint 1 (Base)", -165, 165),
                (2, "Joint 2 (Shoulder)", -125, 125),
                (3, "Joint 3 (Elbow)", -140, 140),
                (4, "Joint 4 (Wrist 1)", -140, 140),
                (5, "Joint 5 (Wrist 2)", -140, 140),
                (6, "Joint 6 (Wrist 3)", -175, 175),
                (7, "Joint 7 (Gripper)", -180, 180)
            ]
            
            # Convert to (id, name, min_steps, max_steps, home_steps)
            self.servo_config = []
            for i, (servo_id, name, min_deg, max_deg) in enumerate(joint_limits):
                # Home position is 0° for all joints
                home_deg = 0.0
                # Apply J1 offset (robot coordinate alignment)
                if i == 0:
                    home_deg += J1_OFFSET
                
                # Clamp home to limits
                home_deg = max(min_deg, min(max_deg, home_deg))
                
                # Convert to steps
                min_steps = degrees_to_steps(min_deg)
                max_steps = degrees_to_steps(max_deg)
                home_steps = degrees_to_steps(home_deg)
                
                self.servo_config.append((servo_id, name, min_steps, max_steps, home_steps))
        
        self.protocol = ServoProtocol()
        self.servo_widgets = []
        
        # Extract home positions from config
        self.home_positions = [config[4] for config in self.servo_config]
        
        # Multiple saved positions
        self.saved_positions = {}  # Dict of {name: [pos1, pos2, ...]}
        self.load_saved_positions()
        
        # Real-time monitoring
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.update_realtime_positions)
        self.realtime_monitoring = False
        
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("7-Axis Manipulator Control")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Connection panel
        conn_group = QGroupBox("Connection")
        conn_layout = QHBoxLayout()
        
        self.port_combo = QComboBox()
        self.port_combo.addItems(['/dev/ttyACM0', '/dev/ttyACM1', '/dev/ttyUSB0', '/dev/ttyUSB1'])
        self.port_combo.setEditable(True)
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)
        
        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        
        conn_layout.addWidget(QLabel("Port:"))
        conn_layout.addWidget(self.port_combo)
        conn_layout.addWidget(self.connect_btn)
        conn_layout.addWidget(self.status_label)
        conn_layout.addStretch()
        
        conn_group.setLayout(conn_layout)
        main_layout.addWidget(conn_group)
        
        # Tab widget
        tabs = QTabWidget()
        
        # Individual control tab
        individual_tab = QWidget()
        individual_layout = QGridLayout()
        
        for i, (servo_id, joint_name, min_pos, max_pos, home_pos) in enumerate(self.servo_config):
            widget = ServoControlWidget(servo_id, joint_name, self.protocol, min_pos, max_pos)
            widget.set_position(home_pos)  # Set to home initially
            self.servo_widgets.append(widget)
            row = i // 2
            col = i % 2
            individual_layout.addWidget(widget, row, col)
        
        individual_tab.setLayout(individual_layout)
        tabs.addTab(individual_tab, "Individual Control")
        
        # Global control tab
        global_tab = QWidget()
        global_layout = QVBoxLayout()
        
        # Speed and acceleration
        params_group = QGroupBox("Global Parameters")
        params_layout = QGridLayout()
        
        params_layout.addWidget(QLabel("Speed (0-2400):"), 0, 0)
        self.speed_spinbox = QSpinBox()
        self.speed_spinbox.setMinimum(0)
        self.speed_spinbox.setMaximum(2400)
        self.speed_spinbox.setValue(2400)
        params_layout.addWidget(self.speed_spinbox, 0, 1)
        
        params_layout.addWidget(QLabel("Acceleration (0-254):"), 1, 0)
        self.acc_spinbox = QSpinBox()
        self.acc_spinbox.setMinimum(0)
        self.acc_spinbox.setMaximum(254)
        self.acc_spinbox.setValue(50)
        params_layout.addWidget(self.acc_spinbox, 1, 1)
        
        params_layout.addWidget(QLabel("Deceleration (0-254):"), 2, 0)
        self.dec_spinbox = QSpinBox()
        self.dec_spinbox.setMinimum(0)
        self.dec_spinbox.setMaximum(254)
        self.dec_spinbox.setValue(50)
        params_layout.addWidget(self.dec_spinbox, 2, 1)
        
        params_group.setLayout(params_layout)
        global_layout.addWidget(params_group)
        
        # Home position settings
        home_group = QGroupBox("Home Position Configuration")
        home_layout = QVBoxLayout()
        
        home_grid = QGridLayout()
        self.home_spinboxes = []
        
        for i, (servo_id, joint_name, min_pos, max_pos, home_pos) in enumerate(self.servo_config):
            home_grid.addWidget(QLabel(joint_name), i, 0)
            spinbox = QSpinBox()
            spinbox.setMinimum(min_pos)
            spinbox.setMaximum(max_pos)
            spinbox.setValue(home_pos)
            self.home_spinboxes.append(spinbox)
            home_grid.addWidget(spinbox, i, 1)
            
            # Add limit label
            limit_label = QLabel(f"({min_pos}-{max_pos})")
            limit_label.setStyleSheet("color: gray; font-size: 9px;")
            home_grid.addWidget(limit_label, i, 2)
        
        home_layout.addLayout(home_grid)
        
        home_btn_layout = QHBoxLayout()
        
        save_home_btn = QPushButton("Save Home Position")
        save_home_btn.clicked.connect(self.save_home_position)
        
        load_home_btn = QPushButton("Load from Current")
        load_home_btn.clicked.connect(self.load_current_as_home)
        
        export_config_btn = QPushButton("Export Config File")
        export_config_btn.clicked.connect(self.export_config)
        export_config_btn.setStyleSheet("background-color: #2196F3; color: white;")
        
        home_btn_layout.addWidget(save_home_btn)
        home_btn_layout.addWidget(load_home_btn)
        home_btn_layout.addWidget(export_config_btn)
        home_layout.addLayout(home_btn_layout)
        
        home_group.setLayout(home_layout)
        global_layout.addWidget(home_group)
        
        # Global actions
        actions_group = QGroupBox("Global Actions")
        actions_layout = QVBoxLayout()
        
        btn_row1 = QHBoxLayout()
        home_all_btn = QPushButton("Home All Servos")
        home_all_btn.clicked.connect(self.home_all_servos)
        home_all_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        
        read_all_btn = QPushButton("Read All Positions")
        read_all_btn.clicked.connect(self.read_all_positions)
        
        btn_row1.addWidget(home_all_btn)
        btn_row1.addWidget(read_all_btn)
        actions_layout.addLayout(btn_row1)
        
        btn_row2 = QHBoxLayout()
        ping_all_btn = QPushButton("Test All Connections")
        ping_all_btn.clicked.connect(self.ping_all_servos)
        
        move_all_btn = QPushButton("Move All to Current UI")
        move_all_btn.clicked.connect(self.move_all_to_ui_positions)
        
        btn_row2.addWidget(ping_all_btn)
        btn_row2.addWidget(move_all_btn)
        actions_layout.addLayout(btn_row2)
        
        actions_group.setLayout(actions_layout)
        global_layout.addWidget(actions_group)
        
        global_layout.addStretch()
        global_tab.setLayout(global_layout)
        tabs.addTab(global_tab, "Global Control")
        
        # Monitoring tab
        monitor_tab = QWidget()
        monitor_layout = QVBoxLayout()
        
        self.monitor_text = QTextEdit()
        self.monitor_text.setReadOnly(True)
        self.monitor_text.setFont(QFont('Courier', 9))
        monitor_layout.addWidget(self.monitor_text)
        
        monitor_btn_layout = QHBoxLayout()
        
        refresh_monitor_btn = QPushButton("Refresh Status")
        refresh_monitor_btn.clicked.connect(self.refresh_monitor)
        
        clear_monitor_btn = QPushButton("Clear")
        clear_monitor_btn.clicked.connect(self.monitor_text.clear)
        
        self.auto_refresh_btn = QPushButton("Auto-Refresh: OFF")
        self.auto_refresh_btn.setCheckable(True)
        self.auto_refresh_btn.clicked.connect(self.toggle_auto_refresh)
        
        monitor_btn_layout.addWidget(refresh_monitor_btn)
        monitor_btn_layout.addWidget(clear_monitor_btn)
        monitor_btn_layout.addWidget(self.auto_refresh_btn)
        monitor_btn_layout.addStretch()
        
        monitor_layout.addLayout(monitor_btn_layout)
        monitor_tab.setLayout(monitor_layout)
        tabs.addTab(monitor_tab, "Monitor")
        
        # Real-time Position Monitor tab
        realtime_tab = QWidget()
        realtime_layout = QVBoxLayout()
        
        info_label = QLabel("Real-Time Position Monitor\n\nMove the arm manually and watch positions update in real-time.")
        info_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        realtime_layout.addWidget(info_label)
        
        # Position display area
        self.realtime_text = QTextEdit()
        self.realtime_text.setReadOnly(True)
        self.realtime_text.setFont(QFont('Courier', 10))
        self.realtime_text.setStyleSheet("background-color: #f5f5f5;")
        realtime_layout.addWidget(self.realtime_text)
        
        # Control buttons
        realtime_btn_layout = QHBoxLayout()
        
        self.start_monitor_btn = QPushButton("▶ Start Real-Time Monitoring")
        self.start_monitor_btn.clicked.connect(self.toggle_realtime_monitor)
        self.start_monitor_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        
        copy_positions_btn = QPushButton("📋 Copy Current Positions")
        copy_positions_btn.clicked.connect(self.copy_realtime_positions)
        
        save_as_preset_btn = QPushButton("💾 Save as Preset")
        save_as_preset_btn.clicked.connect(self.save_current_as_preset)
        
        realtime_btn_layout.addWidget(self.start_monitor_btn)
        realtime_btn_layout.addWidget(copy_positions_btn)
        realtime_btn_layout.addWidget(save_as_preset_btn)
        
        realtime_layout.addLayout(realtime_btn_layout)
        
        # Torque control - second row
        torque_layout = QHBoxLayout()
        
        self.torque_btn = QPushButton("🔓 Disable All Torque (Free Move)")
        self.torque_btn.clicked.connect(self.toggle_torque)
        self.torque_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; padding: 10px;")
        torque_layout.addWidget(self.torque_btn)
        
        self.torque_enabled = True
        
        torque_layout.addStretch()
        realtime_layout.addLayout(torque_layout)
        
        # Update interval
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Update Interval (ms):"))
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setMinimum(100)
        self.interval_spinbox.setMaximum(2000)
        self.interval_spinbox.setValue(500)
        interval_layout.addWidget(self.interval_spinbox)
        interval_layout.addStretch()
        realtime_layout.addLayout(interval_layout)
        
        realtime_tab.setLayout(realtime_layout)
        tabs.addTab(realtime_tab, "Real-Time Monitor")
        
        # Saved Positions tab
        positions_tab = QWidget()
        positions_layout = QVBoxLayout()
        
        positions_layout.addWidget(QLabel("Saved Positions Manager"))
        
        # List of saved positions
        self.positions_list = QListWidget()
        self.positions_list.itemClicked.connect(self.on_position_selected)
        positions_layout.addWidget(self.positions_list)
        
        # Buttons
        pos_btn_layout = QHBoxLayout()
        
        save_current_btn = QPushButton("💾 Save Current Position")
        save_current_btn.clicked.connect(self.save_current_position_dialog)
        
        load_pos_btn = QPushButton("📥 Load Selected")
        load_pos_btn.clicked.connect(self.load_selected_position)
        
        goto_pos_btn = QPushButton("➡️ Go to Selected")
        goto_pos_btn.clicked.connect(self.goto_selected_position)
        
        delete_pos_btn = QPushButton("🗑️ Delete Selected")
        delete_pos_btn.clicked.connect(self.delete_selected_position)
        
        pos_btn_layout.addWidget(save_current_btn)
        pos_btn_layout.addWidget(load_pos_btn)
        pos_btn_layout.addWidget(goto_pos_btn)
        pos_btn_layout.addWidget(delete_pos_btn)
        
        positions_layout.addLayout(pos_btn_layout)
        
        # Import/Export buttons
        io_btn_layout = QHBoxLayout()
        
        import_btn = QPushButton("📂 Import from File")
        import_btn.clicked.connect(self.import_positions)
        
        export_btn = QPushButton("💾 Export to File")
        export_btn.clicked.connect(self.export_positions)
        
        io_btn_layout.addWidget(import_btn)
        io_btn_layout.addWidget(export_btn)
        io_btn_layout.addStretch()
        
        positions_layout.addLayout(io_btn_layout)
        
        # Position details
        self.position_details = QTextEdit()
        self.position_details.setReadOnly(True)
        self.position_details.setMaximumHeight(150)
        positions_layout.addWidget(QLabel("Position Details:"))
        positions_layout.addWidget(self.position_details)
        
        positions_tab.setLayout(positions_layout)
        tabs.addTab(positions_tab, "Saved Positions")
        
        main_layout.addWidget(tabs)
        
        # Update saved positions list
        self.update_positions_list()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_monitor)
        
    def toggle_connection(self):
        if self.protocol.ser and self.protocol.ser.is_open:
            self.protocol.disconnect()
            self.connect_btn.setText("Connect")
            self.status_label.setText("Disconnected")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.protocol.port = self.port_combo.currentText()
            if self.protocol.connect():
                self.connect_btn.setText("Disconnect")
                self.status_label.setText("Connected")
                self.status_label.setStyleSheet("color: green; font-weight: bold;")
                QMessageBox.information(self, "Success", "Connected to servos!")
            else:
                QMessageBox.critical(self, "Error", f"Failed to connect to {self.protocol.port}")
    
    def home_all_servos(self):
        """Home all servos to 0° (matches HomeAll.cpp behavior)"""
        if not self.protocol.ser or not self.protocol.ser.is_open:
            QMessageBox.warning(self, "Warning", "Not connected!")
            return
        
        speed = min(self.speed_spinbox.value(), 1000)  # Cap at 1000 like C++ code
        acc = self.acc_spinbox.value()
        dec = self.dec_spinbox.value()
        
        output = "Homing all servos to 0° (with J1 offset):\n\n"
        
        # Move servos to home (0°) with coordinate transform
        for i, widget in enumerate(self.servo_widgets):
            # Get joint limits in degrees (convert from steps)
            servo_id, joint_name, min_steps, max_steps, _ = self.servo_config[i]
            
            # Target is 0° for all joints
            target_deg = 0.0
            
            # Apply J1 offset for coordinate alignment
            if i == 0:  # Joint 1 (Base)
                target_deg += J1_OFFSET
            
            # Convert to steps
            target_steps = degrees_to_steps(target_deg)
            
            # Clamp to joint limits
            target_steps = max(min_steps, min(max_steps, target_steps))
            
            # Update UI and move servo
            widget.set_position(target_steps)
            self.protocol.write_position(widget.servo_id, target_steps, speed, acc, dec)
            
            output += f"{joint_name}: {target_deg:.1f}° → {target_steps} steps\n"
            time.sleep(0.1)  # 100ms delay like C++ code
        
        QMessageBox.information(self, "Homing", output)
    
    def read_all_positions(self):
        if not self.protocol.ser or not self.protocol.ser.is_open:
            QMessageBox.warning(self, "Warning", "Not connected!")
            return
        
        for widget in self.servo_widgets:
            widget.read_position()
            time.sleep(0.05)
    
    def ping_all_servos(self):
        if not self.protocol.ser or not self.protocol.ser.is_open:
            QMessageBox.warning(self, "Warning", "Not connected!")
            return
        
        results = []
        for servo_id, joint_name, _, _, _ in self.servo_config:
            status = "✓ Connected" if self.protocol.ping(servo_id) else "✗ No response"
            results.append(f"{joint_name} (ID {servo_id}): {status}")
            time.sleep(0.05)
        
        QMessageBox.information(self, "Connection Test", "\n".join(results))
    
    def move_all_to_ui_positions(self):
        if not self.protocol.ser or not self.protocol.ser.is_open:
            QMessageBox.warning(self, "Warning", "Not connected!")
            return
        
        speed = self.speed_spinbox.value()
        acc = self.acc_spinbox.value()
        dec = self.dec_spinbox.value()
        
        for widget in self.servo_widgets:
            position = widget.get_position()
            self.protocol.write_position(widget.servo_id, position, speed, acc, dec)
            time.sleep(0.05)  # Small delay between commands
        
        QMessageBox.information(self, "Success", "All servos moving!")
    
    def save_home_position(self):
        for i, spinbox in enumerate(self.home_spinboxes):
            self.home_positions[i] = spinbox.value()
        QMessageBox.information(self, "Success", "Home positions saved in memory!\n\nTo save permanently, click 'Export Config File'")
    
    def export_config(self):
        """Export current configuration to servo_limits_config.py"""
        config_content = '"""\n'
        config_content += 'Servo Limits Configuration\n'
        config_content += 'Generated by Servo Control GUI\n'
        config_content += '"""\n\n'
        config_content += 'SERVO_CONFIG = [\n'
        
        for i, (servo_id, joint_name, min_pos, max_pos, _) in enumerate(self.servo_config):
            home_pos = self.home_positions[i]
            config_content += f'    ({servo_id}, "{joint_name}", {min_pos}, {max_pos}, {home_pos}),\n'
        
        config_content += ']\n'
        
        try:
            with open('servo_limits_config.py', 'w') as f:
                f.write(config_content)
            QMessageBox.information(self, "Success", 
                                   "Configuration exported to servo_limits_config.py!\n\n"
                                   "Restart the GUI to load the new configuration.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export config:\n{e}")
    
    def load_current_as_home(self):
        if not self.protocol.ser or not self.protocol.ser.is_open:
            QMessageBox.warning(self, "Warning", "Not connected!")
            return
        
        for i, (servo_id, _, _, _, _) in enumerate(self.servo_config):
            pos = self.protocol.read_position(servo_id)
            if pos is not None:
                self.home_spinboxes[i].setValue(pos)
                self.home_positions[i] = pos
            time.sleep(0.05)
        
        QMessageBox.information(self, "Success", "Loaded current positions as home!")
    
    def refresh_monitor(self):
        if not self.protocol.ser or not self.protocol.ser.is_open:
            return
        
        output = "=" * 80 + "\n"
        output += f"Servo Status Report - {time.strftime('%H:%M:%S')}\n"
        output += "=" * 80 + "\n\n"
        output += f"{'Joint':<20} {'ID':<4} {'Pos':<6} {'Temp':<6} {'Volt':<7} {'Moving':<8}\n"
        output += "-" * 80 + "\n"
        
        for servo_id, joint_name, _, _, _ in self.servo_config:
            feedback = self.protocol.read_feedback(servo_id)
            if feedback:
                output += f"{joint_name:<20} {servo_id:<4} {feedback['position']:<6} "
                output += f"{feedback['temperature']:<6} {feedback['voltage']/10.0:<7.1f} "
                output += f"{'Yes' if feedback['moving'] else 'No':<8}\n"
            else:
                output += f"{joint_name:<20} {servo_id:<4} [ERROR - No response]\n"
            time.sleep(0.05)
        
        output += "-" * 80 + "\n"
        
        self.monitor_text.setText(output)
    
    def toggle_auto_refresh(self):
        if self.auto_refresh_btn.isChecked():
            self.refresh_timer.start(1000)  # Refresh every 1 second
            self.auto_refresh_btn.setText("Auto-Refresh: ON")
            self.auto_refresh_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        else:
            self.refresh_timer.stop()
            self.auto_refresh_btn.setText("Auto-Refresh: OFF")
            self.auto_refresh_btn.setStyleSheet("")
    
    def toggle_realtime_monitor(self):
        """Start/stop real-time position monitoring"""
        if not self.protocol.ser or not self.protocol.ser.is_open:
            QMessageBox.warning(self, "Warning", "Not connected!")
            return
        
        if self.realtime_monitoring:
            self.monitor_timer.stop()
            self.realtime_monitoring = False
            self.start_monitor_btn.setText("▶ Start Real-Time Monitoring")
            self.start_monitor_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        else:
            interval = self.interval_spinbox.value()
            self.monitor_timer.start(interval)
            self.realtime_monitoring = True
            self.start_monitor_btn.setText("⏸ Stop Monitoring")
            self.start_monitor_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 10px;")
            self.update_realtime_positions()  # Immediate update
    
    def update_realtime_positions(self):
        """Update real-time position display"""
        if not self.protocol.ser or not self.protocol.ser.is_open:
            self.monitor_timer.stop()
            self.realtime_monitoring = False
            return
        
        output = "=" * 80 + "\n"
        output += f"Real-Time Positions - {time.strftime('%H:%M:%S')}\n"
        output += "=" * 80 + "\n\n"
        output += f"{'Joint':<22} {'ID':<4} {'Steps':<6} {'Degrees':<10}\n"
        output += "-" * 80 + "\n"
        
        positions = []
        for servo_id, joint_name, _, _, _ in self.servo_config:
            pos = self.protocol.read_position(servo_id)
            if pos is not None:
                deg = steps_to_degrees(pos)
                output += f"{joint_name:<22} {servo_id:<4} {pos:<6} {deg:>8.2f}°\n"
                positions.append(pos)
            else:
                output += f"{joint_name:<22} {servo_id:<4} [ERROR]\n"
                positions.append(0)
            time.sleep(0.02)
        
        output += "-" * 80 + "\n\n"
        output += "Copy-paste format:\n"
        output += f"positions = {positions}\n"
        
        self.realtime_text.setText(output)
        self.current_realtime_positions = positions
    
    def copy_realtime_positions(self):
        """Copy current positions to clipboard"""
        if hasattr(self, 'current_realtime_positions'):
            clipboard = QApplication.clipboard()
            clipboard.setText(str(self.current_realtime_positions))
            QMessageBox.information(self, "Copied", "Positions copied to clipboard!")
        else:
            QMessageBox.warning(self, "Warning", "No positions to copy. Start monitoring first!")
    
    def save_current_as_preset(self):
        """Save current real-time positions as a preset"""
        if not hasattr(self, 'current_realtime_positions'):
            QMessageBox.warning(self, "Warning", "No positions to save. Start monitoring first!")
            return
        
        name, ok = QInputDialog.getText(self, "Save Preset", "Enter preset name:")
        if ok and name:
            self.saved_positions[name] = self.current_realtime_positions.copy()
            self.save_saved_positions()
            self.update_positions_list()
            QMessageBox.information(self, "Success", f"Preset '{name}' saved!")
    
    def load_saved_positions(self):
        """Load saved positions from JSON file"""
        try:
            if os.path.exists('saved_positions.json'):
                with open('saved_positions.json', 'r') as f:
                    self.saved_positions = json.load(f)
        except Exception as e:
            print(f"Error loading saved positions: {e}")
            self.saved_positions = {}
    
    def save_saved_positions(self):
        """Save positions to JSON file"""
        try:
            with open('saved_positions.json', 'w') as f:
                json.dump(self.saved_positions, f, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save positions:\n{e}")
    
    def update_positions_list(self):
        """Update the list widget with saved positions"""
        self.positions_list.clear()
        for name in sorted(self.saved_positions.keys()):
            self.positions_list.addItem(name)
    
    def on_position_selected(self, item):
        """Show details of selected position"""
        name = item.text()
        if name in self.saved_positions:
            positions = self.saved_positions[name]
            details = f"Position: {name}\n\n"
            for i, (servo_id, joint_name, _, _, _) in enumerate(self.servo_config):
                if i < len(positions):
                    pos = positions[i]
                    deg = steps_to_degrees(pos)
                    details += f"{joint_name}: {pos} steps ({deg:.2f}°)\n"
            self.position_details.setText(details)
    
    def save_current_position_dialog(self):
        """Save current UI positions"""
        if not self.protocol.ser or not self.protocol.ser.is_open:
            QMessageBox.warning(self, "Warning", "Not connected!")
            return
        
        name, ok = QInputDialog.getText(self, "Save Position", "Enter position name:")
        if ok and name:
            positions = []
            for widget in self.servo_widgets:
                pos = self.protocol.read_position(widget.servo_id)
                if pos is not None:
                    positions.append(pos)
                else:
                    QMessageBox.warning(self, "Warning", f"Could not read {widget.joint_name}")
                    return
                time.sleep(0.05)
            
            self.saved_positions[name] = positions
            self.save_saved_positions()
            self.update_positions_list()
            QMessageBox.information(self, "Success", f"Position '{name}' saved!")
    
    def load_selected_position(self):
        """Load selected position to UI sliders"""
        item = self.positions_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Warning", "No position selected!")
            return
        
        name = item.text()
        if name in self.saved_positions:
            positions = self.saved_positions[name]
            for i, widget in enumerate(self.servo_widgets):
                if i < len(positions):
                    widget.set_position(positions[i])
            QMessageBox.information(self, "Success", f"Position '{name}' loaded to UI!")
    
    def goto_selected_position(self):
        """Move servos to selected position"""
        item = self.positions_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Warning", "No position selected!")
            return
        
        if not self.protocol.ser or not self.protocol.ser.is_open:
            QMessageBox.warning(self, "Warning", "Not connected!")
            return
        
        name = item.text()
        if name in self.saved_positions:
            positions = self.saved_positions[name]
            speed = self.speed_spinbox.value()
            acc = self.acc_spinbox.value()
            dec = self.dec_spinbox.value()
            
            for i, widget in enumerate(self.servo_widgets):
                if i < len(positions):
                    pos = positions[i]
                    widget.set_position(pos)
                    self.protocol.write_position(widget.servo_id, pos, speed, acc, dec)
                    time.sleep(0.1)
            
            QMessageBox.information(self, "Success", f"Moving to position '{name}'!")
    
    def delete_selected_position(self):
        """Delete selected saved position"""
        item = self.positions_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Warning", "No position selected!")
            return
        
        name = item.text()
        reply = QMessageBox.question(self, "Confirm Delete", 
                                     f"Delete position '{name}'?",
                                     QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            del self.saved_positions[name]
            self.save_saved_positions()
            self.update_positions_list()
            self.position_details.clear()
            QMessageBox.information(self, "Success", f"Position '{name}' deleted!")
    
    def import_positions(self):
        """Import positions from JSON file"""
        filename, _ = QFileDialog.getOpenFileName(self, "Import Positions", "", "JSON Files (*.json)")
        if filename:
            try:
                with open(filename, 'r') as f:
                    imported = json.load(f)
                self.saved_positions.update(imported)
                self.save_saved_positions()
                self.update_positions_list()
                QMessageBox.information(self, "Success", f"Imported {len(imported)} positions!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to import:\n{e}")
    
    def export_positions(self):
        """Export positions to JSON file"""
        filename, _ = QFileDialog.getSaveFileName(self, "Export Positions", "positions.json", "JSON Files (*.json)")
        if filename:
            try:
                with open(filename, 'w') as f:
                    json.dump(self.saved_positions, f, indent=2)
                QMessageBox.information(self, "Success", f"Exported {len(self.saved_positions)} positions!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export:\n{e}")
    
    def toggle_torque(self):
        """Enable or disable torque on all servos"""
        if not self.protocol.ser or not self.protocol.ser.is_open:
            QMessageBox.warning(self, "Warning", "Not connected!")
            return
        
        if self.torque_enabled:
            # Disable torque - allow free movement
            reply = QMessageBox.question(self, "Disable Torque", 
                                        "This will disable torque on all servos.\n"
                                        "You can move the arm manually.\n\n"
                                        "Continue?",
                                        QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                for servo_id, _, _, _, _ in self.servo_config:
                    self.protocol.enable_torque(servo_id, False)
                    time.sleep(0.02)
                
                self.torque_enabled = False
                self.torque_btn.setText("🔒 Enable All Torque (Lock Position)")
                self.torque_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
                QMessageBox.information(self, "Torque Disabled", 
                                       "All servos unlocked!\n\n"
                                       "You can now move the arm manually.\n"
                                       "Use 'Start Real-Time Monitoring' to see positions.")
        else:
            # Enable torque - lock positions
            for servo_id, _, _, _, _ in self.servo_config:
                self.protocol.enable_torque(servo_id, True)
                time.sleep(0.02)
            
            self.torque_enabled = True
            self.torque_btn.setText("🔓 Disable All Torque (Free Move)")
            self.torque_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; padding: 10px;")
            QMessageBox.information(self, "Torque Enabled", "All servos locked at current positions!")
    
    def closeEvent(self, event):
        if self.realtime_monitoring:
            self.monitor_timer.stop()
        if self.protocol.ser and self.protocol.ser.is_open:
            self.protocol.disconnect()
        event.accept()


def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
