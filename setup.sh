#!/bin/bash
# Setup script for Six Axis Manipulator project
# Run this after cloning the repository

set -e  # Exit on error

echo "======================================"
echo "Six Axis Manipulator - Setup Script"
echo "======================================"
echo ""

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "⚠️  Warning: This script is designed for Linux (Ubuntu/Debian)"
    echo "   Setup may require manual adjustments on other systems."
    echo ""
fi

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✓ Found Python $PYTHON_VERSION"

# Check for build tools
if ! command -v cmake &> /dev/null; then
    echo "⚠️  CMake not found. C++ examples will not be built."
    echo "   Install with: sudo apt install cmake build-essential"
    SKIP_CPP=1
else
    echo "✓ Found CMake"
fi

# Create virtual environment
echo ""
echo "Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel > /dev/null 2>&1
echo "✓ pip upgraded"

# Install main requirements
echo ""
echo "Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✓ Main dependencies installed"
fi

# Install LeRobot integration requirements
if [ -f "lerobot_integration/requirements.txt" ]; then
    pip install -r lerobot_integration/requirements.txt
    echo "✓ LeRobot dependencies installed"
fi

# Build C++ library if possible
if [ -z "$SKIP_CPP" ]; then
    echo ""
    echo "Building C++ servo library..."
    
    SERVO_DIR="external/SCServo_Linux_220329/SCServo_Linux"
    
    if [ -d "$SERVO_DIR" ]; then
        cd "$SERVO_DIR"
        
        # Build main library
        mkdir -p build
        cd build
        cmake .. > /dev/null 2>&1
        make > /dev/null 2>&1
        cd ..
        
        echo "✓ C++ library built"
        
        # Build ST3215 examples
        cd examples/ST3215_Control
        if [ -f "build_all.sh" ]; then
            chmod +x build_all.sh
            ./build_all.sh > /dev/null 2>&1
            echo "✓ ST3215 examples built"
        fi
        
        cd - > /dev/null
    fi
fi

# Check USB permissions
echo ""
echo "Checking USB permissions..."
if groups | grep -q dialout; then
    echo "✓ User is in dialout group (USB access enabled)"
else
    echo "⚠️  User is NOT in dialout group"
    echo "   Run: sudo usermod -a -G dialout $USER"
    echo "   Then log out and back in for changes to take effect"
fi

# Create data directory
mkdir -p data
echo "✓ Data directory created"

# Summary
echo ""
echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Connect your robot arms"
echo "2. Activate virtual environment: source venv/bin/activate"
echo "3. Calibrate: cd lerobot_integration/scripts && python teleoperate_kikobot.py --calibrate-only"
echo "4. Test: python teleoperate_kikobot.py"
echo ""
echo "See INSTALLATION.md for detailed instructions."
echo ""
