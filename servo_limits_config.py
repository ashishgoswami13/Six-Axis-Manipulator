"""
Servo Limits Configuration
Based on HomeAll.cpp - tested and verified limits
"""

def degrees_to_steps(deg):
    """
    Convert degrees to servo steps
    Servo range: 0-4095 steps = 0-360 degrees
    Convention: 2048 steps = 180° (center position)
    """
    # Normalize to 0-360 range
    normalized = deg % 360.0
    if normalized < 0:
        normalized += 360.0
    
    # Convert to steps
    steps = int(round((normalized / 360.0) * 4096.0))
    
    # Clamp to valid range
    if steps >= 4096:
        steps = 4095
    
    return steps

def steps_to_degrees(steps):
    """
    Convert servo steps to degrees
    Returns angle in -180 to +180 range
    """
    # Convert steps to 0-360 range
    angle = (steps / 4096.0) * 360.0
    
    # Convert to -180 to +180 range (centered at 0°)
    if angle > 180.0:
        angle -= 360.0
    
    return angle

# Coordinate transform - robot mounted with 90° clockwise rotation
J1_OFFSET = 90.0

# Joint limits in degrees
# NOTE: These limits are adjusted to include the actual home positions
# The home positions from your C++ code are the reference points
JOINT_LIMITS_DEG = [
    (1, "Joint 1 (Base)", -180, 180),           # Full range (training data uses full range)
    (2, "Joint 2 (Shoulder)", -180, 180),       # Full range (training data uses full range)
    (3, "Joint 3 (Elbow)", -180, 180),          # Full range (training data uses full range)
    (4, "Joint 4 (Wrist 1)", -180, 180),        # Full range (training data uses full range)
    (5, "Joint 5 (Wrist 2)", -180, 180),        # Full range (training data uses full range)
    (6, "Joint 6 (Wrist 3)", -180, 180),        # Full range (training data uses full range)
    (7, "Joint 7 (Gripper)", 0, 45)             # Gripper: limited range (0° closed, 45° open)
]

# Actual home positions from your robot (in steps)
ACTUAL_HOME_STEPS = [2911, 2167, 1179, 2010, 1058, 1732, 468]

# Convert to servo steps format: (id, name, min_steps, max_steps, home_steps)
SERVO_CONFIG = []
for i, (servo_id, name, min_deg, max_deg) in enumerate(JOINT_LIMITS_DEG):
    # Use actual home position from your robot
    home_steps = ACTUAL_HOME_STEPS[i]
    
    # Convert degrees to steps for limits
    min_steps = degrees_to_steps(min_deg)
    max_steps = degrees_to_steps(max_deg)
    
    # Special handling for ranges that span across 0°/360°
    # If min > max in step space, the range wraps around (e.g., -165° to +165°)
    # In this case, we want to allow both ranges: [min_steps, 4095] and [0, max_steps]
    
    # For full rotation (-180 to +180), allow full range
    if min_deg <= -180 and max_deg >= 180:
        min_steps = 0
        max_steps = 4095
    
    SERVO_CONFIG.append((servo_id, name, min_steps, max_steps, home_steps))

# To customize limits, edit JOINT_LIMITS_DEG above and restart
# Run this to verify configuration:
# python3 -c "from servo_limits_config import verify_config; verify_config()"

def verify_config():
    """Verify that home positions are within defined limits"""
    print("\nServo Configuration Verification:")
    print("="*70)
    for servo_id, name, min_steps, max_steps, home_steps in SERVO_CONFIG:
        home_deg = steps_to_degrees(home_steps)
        min_deg = steps_to_degrees(min_steps)
        max_deg = steps_to_degrees(max_steps)
        
        # Check if home is in valid range
        in_range = False
        if min_steps <= max_steps:
            # Normal range
            in_range = min_steps <= home_steps <= max_steps
        else:
            # Wrap-around range
            in_range = home_steps >= min_steps or home_steps <= max_steps
        
        status = "✓" if in_range else "⚠"
        print(f"{status} {name:20s} Home: {home_steps:4d} steps ({home_deg:6.1f}°)")
        print(f"  {'':20s} Range: {min_steps:4d}-{max_steps:4d} steps ({min_deg:6.1f}° to {max_deg:6.1f}°)")
    print("="*70 + "\n")
