#!/bin/bash
# Quick launch script for Servo Control GUI

echo "======================================"
echo "7-Axis Manipulator Control GUI"
echo "======================================"
echo ""

# Check if PyQt5 is installed
if ! python3 -c "import PyQt5" 2>/dev/null; then
    echo "⚠️  PyQt5 not found. Installing dependencies..."
    pip install -r requirements.txt
    echo ""
fi

# Check for serial port
if [ -e /dev/ttyACM0 ]; then
    echo "✓ Found serial port: /dev/ttyACM0"
elif [ -e /dev/ttyUSB0 ]; then
    echo "✓ Found serial port: /dev/ttyUSB0"
else
    echo "⚠️  No serial port detected. Please check connections."
fi
echo ""

# Check permissions
if groups | grep -q dialout; then
    echo "✓ User has dialout permissions"
else
    echo "⚠️  Warning: User not in dialout group"
    echo "   Run: sudo usermod -a -G dialout $USER"
    echo "   Then log out and back in"
fi
echo ""

echo "Starting GUI..."
python3 servo_control_gui.py
