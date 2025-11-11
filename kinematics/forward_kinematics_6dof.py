"""
FORWARD KINEMATICS - 6-DOF Robot Arm
=====================================

LESSON: Scaling Up from 2-Link to 6-Link
-----------------------------------------

What you learned with 2 links:
- FK calculates position from angles
- Each link adds its contribution
- Angles are cumulative

With 6 joints, the CONCEPT is the same, but we use a more systematic approach:
**Denavit-Hartenberg (DH) Parameters**

WHY DH PARAMETERS?
- Standardized way to describe ANY robot arm
- Each joint described by 4 numbers: (a, α, d, θ)
- Transforms stack together like building blocks
- Industry standard used everywhere

YOUR ROBOT (Kikobot C1 / 6-Axis Manipulator):
----------------------------------------------
Joint 1 (J1): Base rotation (yaw) - rotates whole arm left/right
Joint 2 (J2): Shoulder pitch - moves arm up/down
Joint 3 (J3): Elbow pitch - bends forearm
Joint 4 (J4): Wrist pitch - tilts wrist up/down
Joint 5 (J5): Wrist roll - rotates wrist
Joint 6 (J6): Flange rotation - spins end-effector
"""

import numpy as np
import math
from transformations import deg_to_rad, position_to_degrees, degrees_to_position

# ============================================================================
# ROBOT PHYSICAL PARAMETERS (from your specs)
# ============================================================================

# Link lengths in mm (measured from your dimension diagram)
D1 = 135.93   # Base height (ground to J2 axis)
A2 = 149.11   # Upper arm length (J2 to J3)
A3 = 147.0    # Forearm length (J3 to J4)
D4 = 84.63    # Wrist offset (J3 to J4 vertical)
D6 = 87.18    # End-effector length (J5 to flange center)

# Joint limits from your specs
JOINT_LIMITS_DEG = {
    1: (-165, 165),
    2: (-125, 125),
    3: (-140, 140),
    4: (-140, 140),
    5: (-140, 140),
    6: (-175, 175)
}

# Servo configuration
SERVO_CENTER = 2048
SERVO_RANGE = (0, 4095)

print("="*70)
print("6-DOF ROBOT ARM CONFIGURATION")
print("="*70)
print(f"Base height (D1):       {D1:.2f} mm")
print(f"Upper arm (A2):         {A2:.2f} mm")
print(f"Forearm (A3):           {A3:.2f} mm")
print(f"Wrist offset (D4):      {D4:.2f} mm")
print(f"End-effector (D6):      {D6:.2f} mm")
print(f"Total max reach:        ~{A2 + A3 + D6:.2f} mm")
print("="*70)
print()

# ============================================================================
# LESSON: DENAVIT-HARTENBERG (DH) PARAMETERS
# ============================================================================
"""
DH PARAMETERS EXPLAINED:

Each joint has 4 parameters that describe how it connects to the next:

1. θ (theta) - Joint angle (THIS IS WHAT WE CONTROL)
2. d - Offset along previous Z axis
3. a - Link length along new X axis  
4. α (alpha) - Twist angle between Z axes

These create a transformation matrix that moves us from one joint to the next.

THINK OF IT LIKE DIRECTIONS:
- "Go forward 'a' mm"
- "Turn 'α' degrees"
- "Go up 'd' mm"
- "Rotate joint by 'θ' degrees"

Modified DH parameters for your robot (common in industrial robots):
"""

# DH Table: [a, alpha, d, theta_offset]
# theta_offset accounts for zero position differences
# 
# CORRECTED: Joint 4 rotates in Y-Z plane (perpendicular to J2/J3 plane)
#
# Standard 6R configuration (similar to PUMA, UR, ABB robots):
# - J1: Base yaw (vertical axis)
# - J2: Shoulder pitch (horizontal plane when at 0)
# - J3: Elbow pitch (parallel to J2)
# - J4: Wrist yaw (perpendicular to forearm) - rotates around forearm axis
# - J5: Wrist pitch (bends wrist up/down)
# - J6: Flange roll (spins end-effector)
#
DH_PARAMS = [
    # Joint 1: Base rotation (Z-axis)
    [0,      -np.pi/2,  D1,     0],
    # Joint 2: Shoulder pitch
    [A2,     0,         0,      -np.pi/2],  # -90° offset for mechanical zero
    # Joint 3: Elbow pitch (parallel to J2)
    [A3,     -np.pi/2,  0,      0],         # -90° alpha to change plane for J4
    # Joint 4: Wrist roll/yaw (rotates around forearm axis, affects Y-Z plane)
    [0,      np.pi/2,   D4,     0],
    # Joint 5: Wrist pitch
    [0,      -np.pi/2,  0,      0],
    # Joint 6: Flange rotation
    [0,      0,         D6,     0]
]

# ============================================================================
# TRANSFORMATION MATRIX FUNCTIONS
# ============================================================================

def dh_transform_matrix(a, alpha, d, theta):
    """
    Create a 4x4 transformation matrix from DH parameters.
    
    CONCEPT: This matrix encodes both rotation and translation.
    
    WHY 4x4? Homogeneous coordinates let us combine rotation + translation
    in a single matrix multiplication. It's elegant math magic!
    
    DON'T WORRY about memorizing this - just know it transforms from
    one joint's coordinate system to the next.
    """
    ct = math.cos(theta)
    st = math.sin(theta)
    ca = math.cos(alpha)
    sa = math.sin(alpha)
    
    return np.array([
        [ct,    -st*ca,  st*sa,   a*ct],
        [st,     ct*ca, -ct*sa,   a*st],
        [0,      sa,     ca,      d   ],
        [0,      0,      0,       1   ]
    ])

# ============================================================================
# FORWARD KINEMATICS - 6 DOF
# ============================================================================

def forward_kinematics_6dof(joint_angles_deg, verbose=False):
    """
    Calculate end-effector pose from 6 joint angles.
    
    Args:
        joint_angles_deg: List/array of 6 joint angles in degrees [θ1, θ2, ..., θ6]
        verbose: If True, print detailed calculations
    
    Returns:
        tuple: (x, y, z, rotation_matrix)
            x, y, z: End-effector position in mm
            rotation_matrix: 3x3 orientation matrix
    
    CONCEPT:
    We multiply transformation matrices together, starting from the base:
    T_total = T1 × T2 × T3 × T4 × T5 × T6
    
    Each multiplication "adds" another joint's contribution.
    Final matrix tells us where the end-effector is!
    """
    
    if len(joint_angles_deg) != 6:
        raise ValueError("Need exactly 6 joint angles")
    
    # Convert to radians
    joint_angles_rad = [deg_to_rad(angle) for angle in joint_angles_deg]
    
    if verbose:
        print("\n" + "="*70)
        print("FORWARD KINEMATICS - 6 DOF")
        print("="*70)
        print("Joint Angles (degrees):")
        for i, angle in enumerate(joint_angles_deg, 1):
            print(f"  θ{i} = {angle:7.2f}°")
        print()
    
    # Start with identity matrix (no transformation)
    T = np.eye(4)
    
    # Multiply each joint's transformation
    for i, (theta_deg, theta_rad) in enumerate(zip(joint_angles_deg, joint_angles_rad), 1):
        # Get DH parameters for this joint
        a, alpha, d, theta_offset = DH_PARAMS[i-1]
        
        # Total theta = input angle + offset
        theta_total = theta_rad + theta_offset
        
        # Create transformation matrix for this joint
        T_i = dh_transform_matrix(a, alpha, d, theta_total)
        
        # Accumulate transformation
        T = T @ T_i  # @ is matrix multiplication in numpy
        
        if verbose:
            pos = T[:3, 3]
            print(f"After Joint {i} (θ={theta_deg:.1f}°):")
            print(f"  Position: ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f}) mm")
    
    # Extract position and orientation
    x, y, z = T[0, 3], T[1, 3], T[2, 3]
    rotation_matrix = T[:3, :3]
    
    if verbose:
        print("\n" + "="*70)
        print("FINAL END-EFFECTOR POSE:")
        print(f"  Position: ({x:.2f}, {y:.2f}, {z:.2f}) mm")
        print(f"  Distance from base: {math.sqrt(x**2 + y**2 + z**2):.2f} mm")
        print("="*70 + "\n")
    
    return x, y, z, rotation_matrix


def get_all_joint_positions_6dof(joint_angles_deg):
    """
    Get positions of ALL joints (for visualization).
    
    Returns:
        dict: {joint_name: (x, y, z)}
    """
    joint_angles_rad = [deg_to_rad(angle) for angle in joint_angles_deg]
    
    positions = {'base': (0, 0, 0)}
    T = np.eye(4)
    
    for i, theta_rad in enumerate(joint_angles_rad, 1):
        a, alpha, d, theta_offset = DH_PARAMS[i-1]
        theta_total = theta_rad + theta_offset
        T_i = dh_transform_matrix(a, alpha, d, theta_total)
        T = T @ T_i
        
        x, y, z = T[0, 3], T[1, 3], T[2, 3]
        positions[f'joint{i}'] = (x, y, z)
    
    return positions


# ============================================================================
# SERVO POSITION CONVERSION
# ============================================================================

def joint_angles_to_servo_positions(joint_angles_deg):
    """
    Convert joint angles (degrees) to servo positions (0-4095).
    
    PRACTICAL USE: This is what you send to your actual robot!
    """
    positions = []
    for i, angle in enumerate(joint_angles_deg, 1):
        # Check joint limits
        min_deg, max_deg = JOINT_LIMITS_DEG[i]
        if angle < min_deg or angle > max_deg:
            print(f"WARNING: Joint {i} angle {angle:.1f}° exceeds limits ({min_deg}, {max_deg})")
        
        # Convert to servo position
        pos = degrees_to_position(angle)
        positions.append(pos)
    
    return positions


def servo_positions_to_joint_angles(servo_positions):
    """
    Convert servo positions (0-4095) to joint angles (degrees).
    
    PRACTICAL USE: Read current robot position and calculate FK.
    """
    angles = []
    for pos in servo_positions:
        angle = position_to_degrees(pos)
        angles.append(angle)
    
    return angles


# ============================================================================
# WORKSPACE ANALYSIS
# ============================================================================

def calculate_workspace_radius():
    """
    Estimate the robot's maximum reach.
    
    SIMPLIFIED: Assumes all joints extended in optimal direction.
    Real workspace is more complex (not a perfect sphere).
    """
    # Maximum reach when J2, J3 extended, J1 rotated
    max_reach = A2 + A3 + D6
    
    # Height range
    max_height = D1 + max_reach
    min_height = D1 - max_reach  # Can reach below base
    
    return {
        'max_horizontal_reach': max_reach,
        'max_height': max_height,
        'min_height': min_height,
        'workspace_volume': 'Approximately spherical shell'
    }


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("TESTING 6-DOF FORWARD KINEMATICS")
    print("="*70)
    
    # Test 1: All joints at zero (home position)
    print("\n### TEST 1: Home Position (all joints at 0°)")
    angles_home = [0, 0, 0, 0, 0, 0]
    x, y, z, R = forward_kinematics_6dof(angles_home, verbose=True)
    
    # Test 2: J1 rotates base 90°
    print("\n### TEST 2: Rotate base 90°")
    angles_j1 = [90, 0, 0, 0, 0, 0]
    x, y, z, R = forward_kinematics_6dof(angles_j1, verbose=True)
    
    # Test 3: Reach forward
    print("\n### TEST 3: Reach forward (J2=45°, J3=-45°)")
    angles_reach = [0, 45, -45, 0, 0, 0]
    x, y, z, R = forward_kinematics_6dof(angles_reach, verbose=True)
    
    # Test 4: Complex pose
    print("\n### TEST 4: Complex pose")
    angles_complex = [30, 45, -30, 20, -15, 60]
    x, y, z, R = forward_kinematics_6dof(angles_complex, verbose=True)
    
    # Workspace info
    print("\n" + "="*70)
    print("WORKSPACE ANALYSIS")
    print("="*70)
    ws = calculate_workspace_radius()
    for key, value in ws.items():
        print(f"{key:25}: {value}")
    
    # Servo conversion test
    print("\n" + "="*70)
    print("SERVO POSITION CONVERSION TEST")
    print("="*70)
    test_angles = [0, 45, -45, 90, -90, 0]
    print(f"Joint angles: {test_angles}")
    servo_pos = joint_angles_to_servo_positions(test_angles)
    print(f"Servo positions: {servo_pos}")
    back_to_angles = servo_positions_to_joint_angles(servo_pos)
    print(f"Back to angles: {[f'{a:.1f}' for a in back_to_angles]}")
    
    print("\n✓ 6-DOF Forward Kinematics complete!")
    print("="*70)
