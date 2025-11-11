# Geometric Motion Patterns - Technical Guide

## Overview

The geometric motion features allow the manipulator's end effector to trace precise geometric patterns in a 2D plane perpendicular to the base link. This document explains the implementation and usage of these patterns.

## Available Patterns

### 1. Circle Motion
Traces a smooth circular path using coordinated movement of two joints.

### 2. Octagon Motion
Traces an 8-sided regular polygon path with linear interpolation between vertices.

## Technical Implementation

### Coordinate System

**Plane of Motion:**
- Vertical plane perpendicular to the base rotation axis
- X-axis: Controlled by Joint 2 (Shoulder) - horizontal movement
- Y-axis: Controlled by Joint 3 (Elbow) - vertical movement

**Center Point:**
- Both joints start at center position (2048)
- This becomes the origin (0,0) for the geometric calculations

### Circle Motion Algorithm

```
For each step i in [0, steps):
    angle = i × (2π / steps)
    
    J2_offset = radius × cos(angle)
    J3_offset = radius × sin(angle)
    
    J2_position = CENTER + J2_offset
    J3_position = CENTER + J3_offset
    
    Move servos to calculated positions
    Wait for movement completion
```

**Parameters:**
- `radius`: Distance from center (50-1000 steps)
- `steps`: Number of points around circle (8-100)
- `cycles`: Number of complete circles (1-20)

**Key Features:**
- Smooth continuous motion
- Configurable resolution (more steps = smoother)
- Multiple cycles for repetitive patterns
- Automatic range clamping

### Octagon Motion Algorithm

```
Calculate 8 vertices:
    For each vertex i in [0, 8):
        angle = i × (2π / 8)
        radius = side_length / (2 × sin(π/8))
        
        vertex[i].J2 = CENTER + radius × cos(angle)
        vertex[i].J3 = CENTER + radius × sin(angle)

Trace the octagon:
    For each side s in [0, 8):
        next = (s + 1) mod 8
        
        For each point p in [0, pointsPerSide]:
            t = p / pointsPerSide  // 0.0 to 1.0
            
            J2 = vertex[s].J2 + t × (vertex[next].J2 - vertex[s].J2)
            J3 = vertex[s].J3 + t × (vertex[next].J3 - vertex[s].J3)
            
            Move servos to interpolated position
            Wait for movement completion
```

**Parameters:**
- `side_length`: Length of each octagon side (50-800 steps)
- `pointsPerSide`: Interpolation points per side (2-30)
- `cycles`: Number of complete octagons (1-20)

**Key Features:**
- Linear interpolation for smooth edges
- Mathematically precise regular octagon
- Configurable edge smoothness
- Vertex-to-vertex motion

## Mathematical Formulas

### Regular Octagon Geometry

For a regular octagon with side length `s`:

**Circumradius (radius of circumscribed circle):**
```
R = s / (2 × sin(π/8))
R ≈ s × 1.3066
```

**Vertices (centered at origin):**
```
For vertex i (i = 0 to 7):
    angle = i × 45° = i × π/4
    x = R × cos(angle)
    y = R × sin(angle)
```

### Circle Parametric Equations

```
For angle θ in [0, 2π]:
    x = r × cos(θ)
    y = r × sin(θ)
```

## Usage Guidelines

### Recommended Parameters

**Circle Motion:**
- **Small workspace**: radius = 200, steps = 24
- **Medium workspace**: radius = 400, steps = 36
- **Large workspace**: radius = 600, steps = 48
- **Smooth motion**: steps ≥ 36
- **Fast motion**: steps = 12-18

**Octagon Motion:**
- **Small workspace**: side = 200, points = 8
- **Medium workspace**: side = 400, points = 12
- **Large workspace**: side = 600, points = 16
- **Sharp corners**: points = 3-5
- **Smooth edges**: points = 15-20

### Safety Considerations

1. **Workspace Limits:**
   - Circle: Ensure radius doesn't exceed workspace boundaries
   - Maximum safe radius ≈ (MAX_POSITION - CENTER_POSITION) / √2
   - For default center (2048): max radius ≈ 1400 steps

2. **Speed Settings:**
   - Start with slower speeds (1200-1800 steps/sec)
   - Increase speed gradually after confirming safe operation
   - Lower acceleration for smoother curved motion

3. **Testing Procedure:**
   - Always home servos first
   - Test with small radii/side lengths initially
   - Run single cycle before multiple cycles
   - Monitor servo temperature and load

### Timing Calculations

**Circle Motion Time per Cycle:**
```
Total_distance = 2π × radius
Points = steps
Distance_per_step = Total_distance / steps

Time_per_step = 100ms (fixed delay)
Total_time = steps × 100ms

Example: 36 steps = 3.6 seconds per cycle
```

**Octagon Motion Time per Cycle:**
```
Total_distance = 8 × side_length
Points_per_side = pointsPerSide
Total_points = 8 × pointsPerSide

Time_per_point = 80ms (fixed delay)
Total_time = Total_points × 80ms

Example: 8 points per side = 64 points × 80ms = 5.12 seconds
```

## Customization

### Adding New Patterns

To add additional geometric patterns, follow this structure:

```cpp
void newPatternMotion(int speed, int acc) {
    // 1. Get user parameters
    // 2. Calculate path points
    // 3. For each cycle:
    //    For each point:
    //        Calculate J2 and J3 positions
    //        Clamp to valid range
    //        Move servos
    //        Add delay
    // 4. Return to center
}
```

### Modifying Joint Usage

Current implementation uses Joints 2 and 3. To use different joints:

1. Change `SERVO_IDS[1]` and `SERVO_IDS[2]` to desired joint indices
2. Adjust center positions if needed
3. Update documentation to reflect changes

Example for using base rotation (Joint 1) and shoulder (Joint 2):
```cpp
sm_st.WritePosEx(SERVO_IDS[0], j1_pos, speed, acc);  // Base rotation
sm_st.WritePosEx(SERVO_IDS[1], j2_pos, speed, acc);  // Shoulder
```

## Advanced Features

### Multi-Joint Coordination

To add more complex 3D patterns:
1. Incorporate Joint 1 (base rotation) for spirals
2. Use Joints 4-6 (wrist) for end-effector orientation
3. Combine multiple geometric primitives

### Trajectory Planning

Current implementation uses:
- Fixed time delays between points
- No velocity profiling
- Constant acceleration settings

For smoother motion, consider:
- Variable delays based on distance
- Trapezoidal velocity profiles
- Cubic or quintic polynomial interpolation

### Inverse Kinematics

Current patterns use direct joint control. For true Cartesian space control:
1. Implement forward kinematics to calculate end-effector position
2. Implement inverse kinematics to convert Cartesian goals to joint angles
3. Use iterative methods (Jacobian, Newton-Raphson) for solving IK

## Troubleshooting

### Pattern Not Centered
- Verify center positions are correct (default: 2048)
- Check if servos are actually at center before starting
- Use "Home All Servos" option first

### Motion Clipped/Incomplete
- Radius or side length too large for workspace
- Reduce size parameters
- Check servo position limits

### Jerky Motion
- Increase number of steps/points for smoother paths
- Reduce movement speed
- Lower acceleration values

### Servo Overheating
- Too many cycles without rest
- Speed too high for continuous operation
- Add cooling delays between cycles

## Performance Metrics

**Typical Performance:**
- Circle (36 steps, 1 cycle): ~3.6 seconds
- Octagon (10 points/side, 1 cycle): ~6.4 seconds
- Positioning accuracy: ±1-2 steps
- Repeatability: <5 steps variance

## References

- ST3215 Servo Specifications
- SCServo Protocol Documentation
- Geometric Pattern Generation Algorithms
- Manipulator Kinematics Theory

---

**Last Updated:** November 2025  
**Version:** 1.0
