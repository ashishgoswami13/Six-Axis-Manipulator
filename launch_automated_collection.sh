#!/bin/bash
# Launch Automated Data Collection

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║       Automated VLA Data Collection                           ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "This will automatically collect 100+ training episodes:"
echo "  1. Robot moves to RANDOM position"
echo "  2. Records journey back to HOME"
echo "  3. Repeats with different random positions"
echo ""
echo "This creates PROPER varied training data for OpenVLA!"
echo ""
echo "Estimated time: ~30-45 minutes for 100 episodes"
echo ""

# Clear old dataset
read -p "Delete old 20 episodes with same movements? [y/N]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "Deleting old dataset..."
    rm -rf ~/vla_dataset/*
    echo "✓ Old dataset cleared"
fi

# Source Orbbec camera workspace
echo "Starting Orbbec camera node..."
source /home/dev/ws/install/setup.bash

# Kill any existing camera nodes
pkill -9 -f orbbec_camera_node
sleep 1

# Launch Orbbec camera node in background
ros2 launch orbbec_camera astra.launch.py &
CAMERA_PID=$!

echo "Waiting for camera to initialize..."
sleep 3

# Source ROS2 environment
source /opt/ros/humble/setup.bash
source /home/dev/ws/install/setup.bash

# Run automated collection
cd "/home/dev/Six Axis Manipulator"
python3 automated_data_collection.py

# Cleanup on exit
echo ""
echo "Cleaning up..."
kill $CAMERA_PID 2>/dev/null
echo "Done!"
