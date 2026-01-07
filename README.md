# Six Axis Manipulator Robot

A complete control system for a 6-DOF robotic arm using Feetech SCS servos.

## 🚀 Quick Start

### 1. Installation
```bash
pip install -r requirements.txt
```

### 2. Calibrate Your Robot
```bash
python3 interactive_calibration.py
```

Follow the interactive prompts to:
- Set zero positions for all 6 joints
- Measure link lengths
- Test forward kinematics
- Save calibration data

**See [docs/MANUAL_CALIBRATION_GUIDE.md](docs/MANUAL_CALIBRATION_GUIDE.md) for detailed instructions.**

### 3. Control Your Robot
```python
from robot_controller import RobotController

robot = RobotController()

# Move to position (in degrees)
robot.set_joint_angles([0, 45, -90, 45, 0, 0])

# Read current position
positions = robot.read_all_positions()
print(positions)
```

---

## 📁 Project Structure

```
├── README.md                       # This file
├── requirements.txt                # Python dependencies
│
├── interactive_calibration.py      # 🎯 Main calibration tool
├── robot_controller.py             # Core robot control library
├── servo_limits_config.py          # Servo configuration
├── saved_positions.json            # Saved robot positions
│
├── docs/                           # 📚 Documentation
│   └── MANUAL_CALIBRATION_GUIDE.md # Complete calibration guide
│
├── calibration/                    # 🎛️ Calibration tools
│   ├── robot_calibration.py        # Advanced calibration with optimization
│   ├── simple_calibration.py       # Simple calibration workflow
│   └── visualize_calibration.py    # Calibration visualization
│
├── utilities/                      # 🔧 Utility scripts
│   ├── check_servos.py             # Test servo communication
│   ├── scan_and_change_servo_ids.py# Servo ID management
│   ├── test_position_reading.py    # Position reading tests
│   └── servo_control_gui.py        # GUI for manual control
│
├── examples/                       # 📝 Example programs
│   ├── leader_follower.py          # Leader-follower teleoperation
│   ├── test_shapes.py              # Draw shapes (circles, lines)
│   └── robot_state_publisher_node.py # ROS integration
│
├── lerobot_integration/            # 🤖 LeRobot dataset integration
│   └── ...
│
└── external/                       # 📦 External libraries & references
    └── SCServo_Linux_220329/       # Feetech servo library (C++)
```

---

## 🎯 Core Components

### `robot_controller.py`
Main library for robot control:
- Servo communication (read/write positions)
- Joint angle control
- Position reading and conversion
- Safe movement commands

### `interactive_calibration.py`
Interactive calibration tool:
- Manual joint-by-joint calibration
- Zero position establishment
- Servo-to-angle mapping
- Forward kinematics testing
- **Start here for a new robot!**

### `servo_limits_config.py`
Configuration file:
- Joint limits (degrees and servo steps)
- Servo ID mappings
- Conversion functions (degrees ↔ steps)

---

## 🛠️ Common Tasks

### Check Servo Connection
```bash
python3 utilities/check_servos.py
```

### Manual Control with GUI
```bash
python3 utilities/servo_control_gui.py
```

### Test Shape Drawing
```bash
python3 examples/test_shapes.py
```

### Leader-Follower Mode
```bash
python3 examples/leader_follower.py
```

---

## 📖 Documentation

- **[Manual Calibration Guide](docs/MANUAL_CALIBRATION_GUIDE.md)** - Complete calibration walkthrough
- **[LeRobot Integration](lerobot_integration/README.md)** - Dataset collection for learning

---

## 🔧 Hardware Setup

### Requirements
- 6-DOF robotic arm with Feetech SCS servos
- USB-to-serial adapter (for servo communication)
- Linux system (tested on Ubuntu)

### Servo Configuration
- **Protocol**: Feetech SCS serial protocol
- **Baud rate**: 1000000
- **Servo IDs**: 1-6 (base to end effector)
- **Servo range**: 0-4095 steps (0-360°)

### Wiring
- All servos daisy-chained on single serial bus
- Each servo must have unique ID (1-6)
- Use `utilities/scan_and_change_servo_ids.py` to configure IDs

---

## 🎓 Kinematics

### Forward Kinematics
**Base frame**: (0, 0, 0) - fixed reference  
**Input**: Joint angles [θ₁, θ₂, θ₃, θ₄, θ₅, θ₆]  
**Output**: End effector position [x, y, z]

Uses DH (Denavit-Hartenberg) parameters for transformation chain:
```
Base → J1 → J2 → J3 → J4 → J5 → J6 → End Effector
```

### Calibration Approach
1. Manually move each joint to zero position
2. Record servo values at reference positions
3. Measure physical link lengths
4. Calculate DH parameters
5. Test FK accuracy

---

## 🐛 Troubleshooting

### Servos not responding
```bash
# Check connections
python3 utilities/check_servos.py

# Scan for servo IDs
python3 utilities/scan_and_change_servo_ids.py
```

### Permission denied on serial port
```bash
sudo usermod -a -G dialout $USER
# Log out and back in
```

### Position reading errors
- Check power supply (servos need adequate current)
- Verify baud rate (1000000)
- Check serial cable quality

---

## 📝 License

This project is for educational and research purposes.

---

## 🤝 Contributing

This is a personal robot project. Feel free to fork and adapt for your own robot!

---# Six Axis Manipulator Robot

A complete control system for a 6-DOF robotic arm using Feetech SCS servos.

## 🚀 Quick Start

### 1. Installation
```bash
pip install -r requirements.txt
```

### 2. Calibrate Your Robot
```bash
python3 interactive_calibration.py
```

Follow the interactive prompts to:
- Set zero positions for all 6 joints
- Measure link lengths
- Test forward kinematics
- Save calibration data

**See [docs/MANUAL_CALIBRATION_GUIDE.md](docs/MANUAL_CALIBRATION_GUIDE.md) for detailed instructions.**

### 3. Control Your Robot
```python
from robot_controller import RobotController

robot = RobotController()

# Move to position (in degrees)
robot.set_joint_angles([0, 45, -90, 45, 0, 0])

# Read current position
positions = robot.read_all_positions()
print(positions)
```

---

## 📁 Project Structure

```
├── README.md                       # This file
├── requirements.txt                # Python dependencies
│
├── interactive_calibration.py      # 🎯 Main calibration tool
├── robot_controller.py             # Core robot control library
├── servo_limits_config.py          # Servo configuration
├── saved_positions.json            # Saved robot positions
│
├── docs/                           # 📚 Documentation
│   └── MANUAL_CALIBRATION_GUIDE.md # Complete calibration guide
│
├── calibration/                    # 🎛️ Calibration tools
│   ├── robot_calibration.py        # Advanced calibration with optimization
│   ├── simple_calibration.py       # Simple calibration workflow
│   └── visualize_calibration.py    # Calibration visualization
│
├── utilities/                      # 🔧 Utility scripts
│   ├── check_servos.py             # Test servo communication
│   ├── scan_and_change_servo_ids.py# Servo ID management
│   ├── test_position_reading.py    # Position reading tests
│   └── servo_control_gui.py        # GUI for manual control
│
├── examples/                       # 📝 Example programs
│   ├── leader_follower.py          # Leader-follower teleoperation
│   ├── test_shapes.py              # Draw shapes (circles, lines)
│   └── robot_state_publisher_node.py # ROS integration
│
├── lerobot_integration/            # 🤖 LeRobot dataset integration
│   └── ...
│
└── external/                       # 📦 External libraries & references
    └── SCServo_Linux_220329/       # Feetech servo library (C++)
```

---

## 🎯 Core Components

### `robot_controller.py`
Main library for robot control:
- Servo communication (read/write positions)
- Joint angle control
- Position reading and conversion
- Safe movement commands

### `interactive_calibration.py`
Interactive calibration tool:
- Manual joint-by-joint calibration
- Zero position establishment
- Servo-to-angle mapping
- Forward kinematics testing
- **Start here for a new robot!**

### `servo_limits_config.py`
Configuration file:
- Joint limits (degrees and servo steps)
- Servo ID mappings
- Conversion functions (degrees ↔ steps)

---

## 🛠️ Common Tasks

### Check Servo Connection
```bash
python3 utilities/check_servos.py
```

### Manual Control with GUI
```bash
python3 utilities/servo_control_gui.py
```

### Test Shape Drawing
```bash
python3 examples/test_shapes.py
```

### Leader-Follower Mode
```bash
python3 examples/leader_follower.py
```

---

## 📖 Documentation

- **[Manual Calibration Guide](docs/MANUAL_CALIBRATION_GUIDE.md)** - Complete calibration walkthrough
- **[LeRobot Integration](lerobot_integration/README.md)** - Dataset collection for learning

---

## 🔧 Hardware Setup

### Requirements
- 6-DOF robotic arm with Feetech SCS servos
- USB-to-serial adapter (for servo communication)
- Linux system (tested on Ubuntu)

### Servo Configuration
- **Protocol**: Feetech SCS serial protocol
- **Baud rate**: 1000000
- **Servo IDs**: 1-6 (base to end effector)
- **Servo range**: 0-4095 steps (0-360°)

### Wiring
- All servos daisy-chained on single serial bus
- Each servo must have unique ID (1-6)
- Use `utilities/scan_and_change_servo_ids.py` to configure IDs

---

## 🎓 Kinematics

### Forward Kinematics
**Base frame**: (0, 0, 0) - fixed reference  
**Input**: Joint angles [θ₁, θ₂, θ₃, θ₄, θ₅, θ₆]  
**Output**: End effector position [x, y, z]

Uses DH (Denavit-Hartenberg) parameters for transformation chain:
```
Base → J1 → J2 → J3 → J4 → J5 → J6 → End Effector
```

### Calibration Approach
1. Manually move each joint to zero position
2. Record servo values at reference positions
3. Measure physical link lengths
4. Calculate DH parameters
5. Test FK accuracy

---

## 🐛 Troubleshooting

### Servos not responding
```bash
# Check connections
python3 utilities/check_servos.py

# Scan for servo IDs
python3 utilities/scan_and_change_servo_ids.py
```

### Permission denied on serial port
```bash
sudo usermod -a -G dialout $USER
# Log out and back in
```

### Position reading errors
- Check power supply (servos need adequate current)
- Verify baud rate (1000000)
- Check serial cable quality

---

## 📝 License

This project is for educational and research purposes.

---

## 🤝 Contributing

This is a personal robot project. Feel free to fork and adapt for your own robot!

---

**Ready to start?** Run `python3 interactive_calibration.py` to calibrate your robot! 🚀


**Ready to start?** Run `python3 interactive_calibration.py` to calibrate your robot! 🚀
