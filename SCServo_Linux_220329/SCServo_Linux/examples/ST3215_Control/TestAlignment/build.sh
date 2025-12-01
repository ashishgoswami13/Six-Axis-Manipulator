#!/bin/bash

echo "Building TestAlignment..."

# Create build directory
mkdir -p build
cd build

# Configure and build
cmake ..
make

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Build successful!"
    echo ""
    echo "To run the alignment test:"
    echo "  ./build/TestAlignment"
    echo ""
    echo "Make sure camera_arm_sync_test.py is running in another terminal to see the movements!"
else
    echo ""
    echo "❌ Build failed!"
    exit 1
fi
