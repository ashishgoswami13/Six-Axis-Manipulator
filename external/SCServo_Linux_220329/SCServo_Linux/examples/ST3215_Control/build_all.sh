#!/bin/bash
# Build script for ST3215 Control Examples
# This script builds all three examples: Ping, WritePos, and FeedBack

set -e  # Exit on error

echo "======================================"
echo "ST3215 Servo Control - Build Script"
echo "======================================"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# First, ensure the main library is built
echo "Step 1: Building SCServo library..."
LIB_DIR="$SCRIPT_DIR/../.."
cd "$LIB_DIR"
echo "Library directory: $(pwd)"
if [ ! -f "libSCServo.a" ]; then
    echo "Library not found. Building..."
    mkdir -p build
    cd build
    cmake ..
    make
    # Copy library to root for easier linking
    cp libSCServo.a ..
    cd ..
    echo "Library built successfully!"
else
    echo "Library already exists."
fi

# Return to ST3215_Control directory
cd "$SCRIPT_DIR"

# Create main build directory
mkdir -p build
cd build

echo ""
echo "Step 2: Building Ping example..."
mkdir -p Ping
cd Ping
cmake ../../Ping
make
cd ..
echo "✓ Ping built successfully!"

echo ""
echo "Step 3: Building WritePos example..."
mkdir -p WritePos
cd WritePos
cmake ../../WritePos
make
cd ..
echo "✓ WritePos built successfully!"

echo ""
echo "Step 4: Building FeedBack example..."
mkdir -p FeedBack
cd FeedBack
cmake ../../FeedBack
make
cd ..
echo "✓ FeedBack built successfully!"

echo ""
echo "Step 5: Building HomeAll example..."
mkdir -p HomeAll
cd HomeAll
cmake ../../HomeAll
make
cd ..
echo "✓ HomeAll built successfully!"

echo ""
echo "Step 6: Building TeachMode..."
mkdir -p TeachMode
cd TeachMode
cmake ../../TeachMode
make
cd ..
echo "✓ TeachMode built successfully!"

echo ""
echo "Step 7: Building ContinuousTeach..."
mkdir -p ContinuousTeach
cd ContinuousTeach
cmake ../../ContinuousTeach
make
cd ..
echo "✓ ContinuousTeach built successfully!"

echo ""
echo "======================================"
echo "Build completed successfully!"
echo "======================================"
echo ""
echo "Executables are in build/ directory:"
echo "  - build/Ping/Ping"
echo "  - build/WritePos/WritePos"
echo "  - build/FeedBack/FeedBack"
echo "  - build/HomeAll/HomeAll"
echo "  - build/TeachMode/TeachMode           (waypoint-based teaching)"
echo "  - build/ContinuousTeach/ContinuousTeach (continuous recording)"
echo ""
echo "To run examples:"
echo "  ./build/Ping/Ping"
echo "  ./build/WritePos/WritePos"
echo "  ./build/FeedBack/FeedBack"
echo "  ./build/HomeAll/HomeAll"
echo "  ./build/TeachMode/TeachMode"
echo "  ./build/ContinuousTeach/ContinuousTeach"
echo ""
