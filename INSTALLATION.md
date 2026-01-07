# Installation Guide

Complete setup instructions for a fresh installation on a new device.

## Prerequisites

- Ubuntu 20.04+ (or similar Linux distribution)
- Python 3.8+
- Git
- CMake and build tools
- USB port access

## Quick Start (Automated)

For a quick automated setup, follow these steps:

```bash
# 1. Clone your repo
git clone <your-repo-url>
cd "Six Axis Manipulator"

# 2. Run automated setup
./setup.sh

# 3. Activate environment & calibrate
source venv/bin/activate
cd lerobot_integration/scripts
python teleoperate_kikobot.py --calibrate-only

# 4. Start using!
python teleoperate_kikobot.py
```

**That's it!** The setup script handles dependency installation and building.

---

## Manual Installation Steps

For manual control or troubleshooting, follow these detailed steps:

### 1. Clone the Repository

```bash
git clone <your-repo-url> "Six Axis Manipulator"
cd "Six Axis Manipulator"
```

### 2. Install System Dependencies

```bash
# Build tools for C++ examples
sudo apt update
sudo apt install -y build-essential cmake

# Python development headers
sudo apt install -y python3-dev python3-pip

# USB serial access
sudo usermod -a -G dialout $USER
# Log out and back in for group changes to take effect
```

### 3. Set Up Python Environment

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Install LeRobot Integration Dependencies

```bash
cd lerobot_integration
pip install -r requirements.txt
cd ..
```

### 5. Build C++ Servo Library (Optional)

If you want to use the C++ examples:

```bash
cd external/SCServo_Linux_220329/SCServo_Linux

# Build the library
mkdir -p build
cd build
cmake ..
make

# Build ST3215 Control examples
cd ../examples/ST3215_Control
./build_all.sh
```

### 6. Configure Hardware

Connect your robot arms:
- **Leader arm** → `/dev/ttyACM1` (6 servos)
- **Follower arm** → `/dev/ttyACM0` (7 servos)

Check connections:
```bash
ls /dev/ttyACM*
```

### 7. Calibrate Robot Arms

**Required before first use:**

```bash
cd lerobot_integration/scripts
python teleoperate_kikobot.py --calibrate-only
```

Follow the interactive prompts to calibrate both arms.

### 8. Test Installation

```bash
# Test teleoperation
python teleoperate_kikobot.py

# Move the leader arm - follower should mirror!
```

## Verification Checklist

- [ ] USB ports accessible (in `dialout` group)
- [ ] Python packages installed
- [ ] Both robot arms connected
- [ ] Calibration completed
- [ ] Teleoperation works

## Troubleshooting

**Permission denied on serial port:**
```bash
sudo usermod -a -G dialout $USER
# Log out and log back in
```

**Python packages fail to install:**
```bash
# Upgrade pip first
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

**Arms not detected:**
- Check USB connections
- Verify servo power supply is on
- Run: `dmesg | grep tty` to see USB device detection

## Next Steps

- Read [README.md](README.md) for robot control basics
- Read [lerobot_integration/README.md](lerobot_integration/README.md) for dataset recording and policy training
- Check [docs/](docs/) for detailed documentation

---

**Installation complete!** 🎉 You're ready to use the Six Axis Manipulator.
