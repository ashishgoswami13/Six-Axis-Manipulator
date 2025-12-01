#!/bin/bash
# Launch Data Collection GUI

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║          OpenVLA Data Collection GUI                          ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "This will launch the data collection interface."
echo "You can manually control the robot while recording demonstrations."
echo ""
echo "Instructions:"
echo "  1. Enter task instruction (e.g., 'pick up cup')"
echo "  2. Click 'Start Recording'"
echo "  3. Manually move robot to demonstrate task"
echo "  4. Click 'Stop Recording'"
echo "  5. Click 'Save Episode' or 'Discard'"
echo ""
echo "Dataset will be saved to: ~/vla_dataset/"
echo ""

# Source Orbbec camera workspace
echo "Starting Orbbec camera node..."
source /home/dev/ws/install/setup.bash

# Kill any existing camera nodes
pkill -9 -f orbbec_camera_node
sleep 1

# Launch Orbbec camera node in background
# Use astra.launch.py for Astra Pro Plus
ros2 launch orbbec_camera astra.launch.py &
CAMERA_PID=$!

echo "Waiting for camera to initialize..."
sleep 3

# Source ROS2 for the GUI
source /opt/ros/humble/setup.bash
source /home/dev/ws/install/setup.bash

# Launch data collection GUI
cd "/home/dev/Six Axis Manipulator"
python3 data_collection_gui.py

# Cleanup on exit
kill $CAMERA_PID 2>/dev/null
