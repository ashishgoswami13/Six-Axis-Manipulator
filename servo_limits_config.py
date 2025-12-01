"""
Servo Limits Configuration
Based on HomeAll.cpp - tested and verified limits
"""

def degrees_to_steps(deg):
    """Convert degrees to servo steps"""
    steps = 2048.0 + (deg / 360.0) * 4096.0
    while steps < 0:
        steps += 4096.0
    while steps >= 4096.0:
        steps -= 4096.0
    return int(steps + 0.5)

def steps_to_degrees(steps):
    """Convert servo steps to degrees (centered around 0°)"""
    angle = (steps / 4096.0) * 360.0
    if angle >= 360.0:
        angle -= 360.0
    if angle > 180.0:
        angle -= 360.0
    return angle

# Coordinate transform - robot mounted with 90° clockwise rotation
J1_OFFSET = 90.0

# Joint limits in degrees (from HomeAll.cpp)
# These are TESTED and SAFE limits from the working C++ code
JOINT_LIMITS_DEG = [
    (1, "Joint 1 (Base)", -165, 165),
    (2, "Joint 2 (Shoulder)", -125, 125),
    (3, "Joint 3 (Elbow)", -140, 140),
    (4, "Joint 4 (Wrist 1)", -140, 140),
    (5, "Joint 5 (Wrist 2)", -140, 140),
    (6, "Joint 6 (Wrist 3)", -175, 175),
    (7, "Joint 7 (Gripper)", -180, 180)
]

# Actual home positions from your robot (in steps)
ACTUAL_HOME_STEPS = [2911, 2167, 1179, 2010, 1058, 1732, 468]

# Convert to servo steps format: (id, name, min_steps, max_steps, home_steps)
SERVO_CONFIG = []
for i, (servo_id, name, min_deg, max_deg) in enumerate(JOINT_LIMITS_DEG):
    # Use actual home position from your robot
    home_steps = ACTUAL_HOME_STEPS[i]
    
    # Convert to steps for limits
    min_steps = degrees_to_steps(min_deg)
    max_steps = degrees_to_steps(max_deg)
    
    SERVO_CONFIG.append((servo_id, name, min_steps, max_steps, home_steps))

# To customize limits, edit JOINT_LIMITS_DEG above and restart the GUI
