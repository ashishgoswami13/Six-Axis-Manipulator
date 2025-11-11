"""
FORWARD KINEMATICS - 2-Link Planar Arm
========================================

WHAT IS FORWARD KINEMATICS (FK)?
---------------------------------
Given: Joint angles (θ1, θ2)
Find: End-effector position (x, y)

ANALOGY: 
Imagine your arm. If I tell you:
- Bend your shoulder 30°
- Bend your elbow 45°

You can figure out where your hand ends up, right? That's Forward Kinematics!

YOUR ROBOT:
-----------
Joint 3 (θ1) → "Shoulder" → Link 1 (147mm) → Joint 4 (θ2) → "Elbow" → Link 2 (84.63mm) → End

"""

import math
from transformations import deg_to_rad, Point2D

# ============================================================================
# YOUR ROBOT'S PHYSICAL PARAMETERS
# ============================================================================

# Link lengths (from your robot specs)
L1 = 147.0      # mm - Length from Joint 3 to Joint 4
L2 = 84.63      # mm - Length from Joint 4 to Joint 5 (end-effector)

print(f"Robot Configuration:")
print(f"  Link 1 (J3→J4): {L1} mm")
print(f"  Link 2 (J4→J5): {L2} mm")
print(f"  Max Reach: {L1 + L2} mm")
print(f"  Min Reach: {abs(L1 - L2)} mm")
print()

# ============================================================================
# LESSON: THE FORWARD KINEMATICS EQUATION
# ============================================================================
"""
STEP-BY-STEP BREAKDOWN:

Imagine the robot from the side:

1. Joint 3 is at origin (0, 0)
2. Joint 3 rotates by angle θ1
3. This moves Joint 4 to position:
   - J4_x = L1 × cos(θ1)
   - J4_y = L1 × sin(θ1)
   
4. Joint 4 rotates by angle θ2 (RELATIVE to Link 1's direction)
5. The total angle of Link 2 is (θ1 + θ2)
6. End-effector position:
   - End_x = L1×cos(θ1) + L2×cos(θ1+θ2)
   - End_y = L1×sin(θ1) + L2×sin(θ1+θ2)

VISUAL:
       End (x,y)
        *
       /  \
      /    \ L2
     /      \
    * Joint4 (J4_x, J4_y)
    |
    | L1
    |
    * Joint3 (0,0)
"""

# ============================================================================
# FORWARD KINEMATICS IMPLEMENTATION
# ============================================================================

def forward_kinematics_2link(theta1_deg, theta2_deg, verbose=False):
    """
    Calculate end-effector position from joint angles.
    
    Args:
        theta1_deg: Joint 3 angle in degrees
        theta2_deg: Joint 4 angle in degrees  
        verbose: If True, print step-by-step calculation
    
    Returns:
        tuple: (end_x, end_y, joint4_x, joint4_y)
    
    CONCEPT:
    We build the arm link by link:
    1. Position Joint 4 based on θ1
    2. Position end-effector based on θ1 + θ2
    """
    
    # Convert to radians (math functions need radians!)
    theta1_rad = deg_to_rad(theta1_deg)
    theta2_rad = deg_to_rad(theta2_deg)
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"FORWARD KINEMATICS CALCULATION")
        print(f"{'='*60}")
        print(f"Input:")
        print(f"  Joint 3 (θ1): {theta1_deg}° = {theta1_rad:.4f} rad")
        print(f"  Joint 4 (θ2): {theta2_deg}° = {theta2_rad:.4f} rad")
        print()
    
    # Step 1: Calculate Joint 4 position
    # This is where the "elbow" joint ends up after rotating the "shoulder"
    joint4_x = L1 * math.cos(theta1_rad)
    joint4_y = L1 * math.sin(theta1_rad)
    
    if verbose:
        print(f"Step 1: Position of Joint 4 (elbow)")
        print(f"  J4_x = L1 × cos(θ1) = {L1} × {math.cos(theta1_rad):.4f} = {joint4_x:.2f} mm")
        print(f"  J4_y = L1 × sin(θ1) = {L1} × {math.sin(theta1_rad):.4f} = {joint4_y:.2f} mm")
        print(f"  Joint 4 is at: ({joint4_x:.2f}, {joint4_y:.2f})")
        print()
    
    # Step 2: Calculate end-effector position
    # The second link's angle is cumulative (θ1 + θ2)
    total_angle = theta1_rad + theta2_rad
    
    end_x = joint4_x + L2 * math.cos(total_angle)
    end_y = joint4_y + L2 * math.sin(total_angle)
    
    if verbose:
        print(f"Step 2: Position of End-Effector")
        print(f"  Total angle = θ1 + θ2 = {theta1_deg}° + {theta2_deg}° = {theta1_deg + theta2_deg}°")
        print(f"  End_x = J4_x + L2×cos(θ1+θ2)")
        print(f"        = {joint4_x:.2f} + {L2}×{math.cos(total_angle):.4f}")
        print(f"        = {end_x:.2f} mm")
        print(f"  End_y = J4_y + L2×sin(θ1+θ2)")
        print(f"        = {joint4_y:.2f} + {L2}×{math.sin(total_angle):.4f}")
        print(f"        = {end_y:.2f} mm")
        print()
        print(f"RESULT: End-effector is at ({end_x:.2f}, {end_y:.2f})")
        print(f"{'='*60}\n")
    
    return end_x, end_y, joint4_x, joint4_y


def get_all_joint_positions(theta1_deg, theta2_deg):
    """
    Get positions of all joints and end-effector.
    
    Returns:
        dict: Positions of each joint
        
    USEFUL FOR: Visualization - we need to draw the whole arm!
    """
    end_x, end_y, joint4_x, joint4_y = forward_kinematics_2link(theta1_deg, theta2_deg)
    
    return {
        'joint3': Point2D(0, 0),              # Base joint (origin)
        'joint4': Point2D(joint4_x, joint4_y), # Elbow
        'end': Point2D(end_x, end_y)          # End-effector
    }


def is_reachable(x, y):
    """
    Check if a point (x, y) is within the robot's workspace.
    
    CONCEPT: The robot can only reach points within a certain area:
    - Too close: Links can't fold that much
    - Too far: Links can't stretch that much
    
    MATH:
    - Max reach = L1 + L2 (arm fully extended)
    - Min reach = |L1 - L2| (arm fully folded)
    """
    distance = math.sqrt(x**2 + y**2)
    max_reach = L1 + L2
    min_reach = abs(L1 - L2)
    
    return min_reach <= distance <= max_reach


# ============================================================================
# TESTING AND EXAMPLES
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("TESTING FORWARD KINEMATICS")
    print("="*60)
    
    # Test Case 1: Both joints at 0° (arm pointing right)
    print("\n### TEST 1: Arm pointing horizontally right")
    print("Angles: θ1=0°, θ2=0°")
    forward_kinematics_2link(0, 0, verbose=True)
    print("Expected: End should be at (231.63, 0) - fully extended to the right")
    
    # Test Case 2: First joint at 90° (arm pointing up)
    print("\n### TEST 2: First joint points up, second joint straight")
    print("Angles: θ1=90°, θ2=0°")
    forward_kinematics_2link(90, 0, verbose=True)
    print("Expected: End should be at (0, 231.63) - fully extended upward")
    
    # Test Case 3: Both joints at 45°
    print("\n### TEST 3: Both joints at 45°")
    print("Angles: θ1=45°, θ2=45°")
    forward_kinematics_2link(45, 45, verbose=True)
    
    # Test Case 4: Folded configuration
    print("\n### TEST 4: Elbow bent backwards")
    print("Angles: θ1=0°, θ2=-90°")
    forward_kinematics_2link(0, -90, verbose=True)
    
    # Workspace test
    print("\n" + "="*60)
    print("WORKSPACE ANALYSIS")
    print("="*60)
    test_points = [
        (200, 0, "Far right"),
        (0, 200, "Straight up"),
        (100, 100, "Diagonal"),
        (300, 0, "Too far!"),
        (50, 0, "Too close!"),
    ]
    
    for x, y, description in test_points:
        reachable = is_reachable(x, y)
        status = "✓ REACHABLE" if reachable else "✗ OUT OF REACH"
        print(f"({x:3}, {y:3}) - {description:15} → {status}")
    
    print("\n✓ Forward Kinematics working correctly!")
