#!/bin/bash
# Build script for ManualControl

echo "=== Building ManualControl ==="

# Create build directory if it doesn't exist
mkdir -p build
cd build

# Run cmake and make
cmake .. && make

if [ $? -eq 0 ]; then
    echo ""
    echo "=== Build Successful! ==="
    echo "Executable: $(pwd)/ManualControl"
    echo ""
    echo "To run:"
    echo "  cd build"
    echo "  ./ManualControl"
    echo ""
    echo "Or with custom port:"
    echo "  ./ManualControl /dev/ttyUSB0"
else
    echo ""
    echo "=== Build Failed ==="
    exit 1
fi
