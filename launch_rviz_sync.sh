#!/bin/bash
# Launch RViz with robot visualization synchronized to real robot

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║          RViz Real-time Robot Visualization                   ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "This will:"
echo "  1. Start robot_state_publisher (reads real servo positions)"
echo "  2. Launch RViz with your URDF model"
echo "  3. Show real-time robot movement in RViz"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Build ROS2 workspace
echo "Building ROS2 workspace..."
cd /home/dev/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install > /dev/null 2>&1
echo "✓ Build complete"
echo ""

# Source ROS2 and workspace
source /opt/ros/humble/setup.bash
source "/home/dev/ros2_ws/install/setup.bash"

# Set ROS_DOMAIN_ID (change if needed)
export ROS_DOMAIN_ID=0

# Kill any existing processes
pkill -9 -f robot_state_publisher_node
pkill -9 -f robot_state_publisher
pkill -9 -f joint_state_publisher
pkill -9 -f rviz2
sleep 1

# Get URDF content
SHARE_DIR="/home/dev/ros2_ws/install/urdf_kikobot_description_v1_description/share/urdf_kikobot_description_v1_description"
XACRO_FILE="$SHARE_DIR/urdf/urdf_kikobot_description_v1.xacro"
RVIZ_CONFIG="$SHARE_DIR/config/display.rviz"

# Process xacro to URDF
echo "Processing URDF..."
ROBOT_DESCRIPTION=$(xacro "$XACRO_FILE")

# Start ROS robot_state_publisher (TF publisher, NOT joint_state publisher)
echo "Starting TF publisher..."
ros2 run robot_state_publisher robot_state_publisher --ros-args -p robot_description:="$ROBOT_DESCRIPTION" &
TF_PID=$!

sleep 1

# Start our custom node that reads real robot and publishes joint_states
echo "Starting real robot joint state publisher..."
cd "/home/dev/Six Axis Manipulator"
python3 robot_state_publisher_node.py &
PUBLISHER_PID=$!

sleep 2

# Launch RViz
echo "Launching RViz..."
ros2 run rviz2 rviz2 -d "$RVIZ_CONFIG" &
RVIZ_PID=$!

echo ""
echo "✓ RViz launched! Move your robot and watch it update in RViz"
echo ""
echo "To test:"
echo "  1. Open another terminal"
echo "  2. Run: ./launch_gui.sh"
echo "  3. Move robot joints manually"
echo "  4. Watch RViz mirror the movements!"
echo ""

# Wait for user interrupt
trap "echo ''; echo 'Shutting down...'; kill $TF_PID $PUBLISHER_PID $RVIZ_PID 2>/dev/null; exit 0" INT
wait
