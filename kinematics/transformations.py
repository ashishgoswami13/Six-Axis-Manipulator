"""
TRANSFORMATIONS.PY - Basic Math Utilities for Robotics
=======================================================

CONCEPT: In robotics, we constantly convert between:
- Degrees and Radians (angles)
- Servo positions and actual angles
- 2D coordinates (x, y) 

This file provides the foundational math tools we'll use.
"""

import math

# ============================================================================
# LESSON 1: Angle Conversions
# ============================================================================
# Why? Servo motors use "positions" (0-4095), but math uses radians.
# We need to convert between three representations:
#   1. Servo Position (e.g., 2048)
#   2. Degrees (e.g., 45°) - Human readable
#   3. Radians (e.g., π/4) - Used in math (sin, cos, etc.)

def deg_to_rad(degrees):
    """
    Convert degrees to radians.
    
    WHY: Python's math.sin() and math.cos() require radians, not degrees.
    FORMULA: radians = degrees × (π / 180)
    
    Example: 90° = π/2 = 1.5707... radians
    """
    return degrees * (math.pi / 180.0)

def rad_to_deg(radians):
    """
    Convert radians to degrees.
    
    FORMULA: degrees = radians × (180 / π)
    
    Example: π radians = 180°
    """
    return radians * (180.0 / math.pi)

# ============================================================================
# LESSON 2: Servo Position Mapping
# ============================================================================
# Your ST3215 servos have:
# - Position range: 0 to 4095 (12-bit resolution = 2^12 values)
# - Center: 2048 = 0°
# - Each position ≈ 0.088° (360° / 4096 positions)

# Your robot's joint limits:
JOINT_3_MIN_DEG = -140
JOINT_3_MAX_DEG = 140
JOINT_4_MIN_DEG = -140
JOINT_4_MAX_DEG = 140

SERVO_CENTER = 2048
SERVO_MIN = 0
SERVO_MAX = 4095

def position_to_degrees(position):
    """
    Convert servo position (0-4095) to degrees.
    
    HOW IT WORKS:
    1. Center is 2048 = 0°
    2. Each step away from center = 0.088°
    3. If position > 2048, angle is positive
    4. If position < 2048, angle is negative
    
    FORMULA: degrees = (position - 2048) × (360 / 4096)
    
    Example: 
        position = 3048 → (3048-2048) × 0.088 = 1000 × 0.088 = 88°
    """
    degrees = (position - SERVO_CENTER) * (360.0 / 4096.0)
    return degrees

def degrees_to_position(degrees):
    """
    Convert degrees to servo position (0-4095).
    
    FORMULA: position = (degrees / 0.088) + 2048
    
    Example:
        degrees = 45° → (45 / 0.088) + 2048 = 511 + 2048 = 2559
    """
    position = int((degrees / (360.0 / 4096.0)) + SERVO_CENTER)
    # Clamp to valid range
    return max(SERVO_MIN, min(SERVO_MAX, position))

# ============================================================================
# LESSON 3: 2D Point Representation
# ============================================================================
# In 2D space, any point can be described by (x, y) coordinates

class Point2D:
    """
    Represents a point in 2D space.
    
    CONCEPT: Our robot arm moves in 3D, but for learning, we're looking at 
    it from the side (like a shadow). This gives us a 2D view where:
    - x = horizontal distance from joint 3
    - y = vertical height
    """
    def __init__(self, x, y):
        self.x = x
        self.y = y
    
    def __repr__(self):
        return f"Point2D(x={self.x:.2f}, y={self.y:.2f})"
    
    def distance_from_origin(self):
        """
        Calculate distance from (0, 0) to this point.
        
        FORMULA: distance = √(x² + y²)  [Pythagorean theorem]
        
        WHY: Useful to check if a point is within reach of the arm.
        """
        return math.sqrt(self.x**2 + self.y**2)

# ============================================================================
# LESSON 4: Forward Kinematics Helper Functions
# ============================================================================
# These are used to calculate end-effector position from joint angles

def rotate_point(point, angle_rad, pivot_x=0, pivot_y=0):
    """
    Rotate a point around a pivot by a given angle.
    
    CONCEPT: When a joint rotates, everything attached to it rotates too.
    This function calculates where a point ends up after rotation.
    
    ROTATION MATRIX (2D):
    [ cos(θ)  -sin(θ) ] [ x ]
    [ sin(θ)   cos(θ) ] [ y ]
    
    Don't worry about memorizing this - just know it rotates points!
    """
    # Translate point to origin
    x = point.x - pivot_x
    y = point.y - pivot_y
    
    # Apply rotation
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    
    new_x = x * cos_a - y * sin_a
    new_y = x * sin_a + y * cos_a
    
    # Translate back
    new_x += pivot_x
    new_y += pivot_y
    
    return Point2D(new_x, new_y)

# ============================================================================
# QUICK REFERENCE
# ============================================================================
"""
CHEAT SHEET:
- deg_to_rad(45) → Use when calculating sin/cos
- rad_to_deg(1.57) → Use when displaying angles
- position_to_degrees(2048) → 0°
- degrees_to_position(90) → 3072
- Point2D(100, 50) → A point 100mm right, 50mm up
"""

if __name__ == "__main__":
    # Let's test our functions!
    print("=" * 60)
    print("TESTING TRANSFORMATIONS")
    print("=" * 60)
    
    print("\n1. Angle Conversions:")
    print(f"   90° = {deg_to_rad(90):.4f} radians")
    print(f"   π radians = {rad_to_deg(math.pi):.1f}°")
    
    print("\n2. Servo Position Conversions:")
    print(f"   Position 2048 = {position_to_degrees(2048):.1f}°")
    print(f"   Position 3048 = {position_to_degrees(3048):.1f}°")
    print(f"   45° = Position {degrees_to_position(45)}")
    
    print("\n3. 2D Points:")
    p = Point2D(100, 100)
    print(f"   Point: {p}")
    print(f"   Distance from origin: {p.distance_from_origin():.2f}mm")
    
    print("\n✓ All transformations working!")
