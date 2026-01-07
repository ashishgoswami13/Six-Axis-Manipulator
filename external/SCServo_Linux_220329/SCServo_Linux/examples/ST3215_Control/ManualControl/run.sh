#!/bin/bash
# Quick run script for ManualControl

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BUILD_DIR="$SCRIPT_DIR/build"
EXECUTABLE="$BUILD_DIR/ManualControl"

# Check if executable exists
if [ ! -f "$EXECUTABLE" ]; then
    echo "ManualControl executable not found!"
    echo "Building now..."
    echo ""
    cd "$SCRIPT_DIR"
    ./build.sh
    echo ""
fi

# Check again after potential build
if [ ! -f "$EXECUTABLE" ]; then
    echo "Error: Failed to build ManualControl"
    exit 1
fi

# Run with passed arguments or defaults
echo "Starting ManualControl..."
echo ""

if [ $# -eq 0 ]; then
    # No arguments - use defaults
    echo "Using default port: /dev/ttyACM0"
    echo "Using default baud: 1000000"
    echo ""
    "$EXECUTABLE"
else
    # Pass all arguments to the program
    "$EXECUTABLE" "$@"
fi
