"""
3D VISUALIZER - 6-DOF Robot Arm
================================

CONCEPT: See your full 6-axis robot arm in 3D!

This creates an interactive 3D visualization where you can:
1. Control all 6 joints with keyboard
2. See the arm configuration in real-time
3. View from different angles
4. Watch how FK calculates positions in 3D space

Controls:
- Number keys 1-6: Select joint to control
- Q/A: Increase/Decrease selected joint angle
- Arrow Keys: Fine control
- R: Reset all joints to 0°
- Mouse: Rotate camera view
- ESC: Exit
"""

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math
from forward_kinematics_6dof import (
    forward_kinematics_6dof,
    get_all_joint_positions_6dof,
    JOINT_LIMITS_DEG,
    D1, A2, A3, D4, D6
)

# ============================================================================
# VISUALIZATION SETTINGS
# ============================================================================

WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800

# Colors (RGB, normalized 0-1)
COLOR_BASE = (0.3, 0.3, 0.3)       # Gray
COLOR_LINK = [
    (1.0, 0.3, 0.3),  # J1 - Red
    (1.0, 0.6, 0.2),  # J2 - Orange
    (1.0, 1.0, 0.3),  # J3 - Yellow
    (0.3, 1.0, 0.3),  # J4 - Green
    (0.3, 0.6, 1.0),  # J5 - Blue
    (0.8, 0.3, 1.0),  # J6 - Purple
]
COLOR_JOINT = (1.0, 1.0, 0.0)      # Yellow
COLOR_END = (0.0, 1.0, 0.5)        # Bright green
COLOR_GRID = (0.2, 0.2, 0.2)       # Dark gray
COLOR_AXIS_X = (1.0, 0.0, 0.0)     # Red
COLOR_AXIS_Y = (0.0, 1.0, 0.0)     # Green
COLOR_AXIS_Z = (0.0, 0.0, 1.0)     # Blue

# Camera
CAMERA_DISTANCE = 800  # mm
CAMERA_ROTATION_SPEED = 2.0

# ============================================================================
# 3D DRAWING FUNCTIONS
# ============================================================================

def draw_sphere(position, radius, color):
    """Draw a sphere at given position."""
    glPushMatrix()
    glTranslatef(position[0], position[1], position[2])
    glColor3f(*color)
    
    # Create sphere
    quad = gluNewQuadric()
    gluSphere(quad, radius, 16, 16)
    gluDeleteQuadric(quad)
    
    glPopMatrix()


def draw_cylinder(start, end, radius, color):
    """Draw a cylinder from start to end position."""
    glPushMatrix()
    
    # Move to start position
    glTranslatef(start[0], start[1], start[2])
    
    # Calculate direction vector
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dz = end[2] - start[2]
    length = math.sqrt(dx**2 + dy**2 + dz**2)
    
    if length > 0.001:  # Avoid division by zero
        # Normalize
        dx /= length
        dy /= length
        dz /= length
        
        # Calculate rotation to align with direction
        # Default cylinder is along Z-axis, we need to rotate it
        if abs(dz) < 0.999:  # Not parallel to Z-axis
            # Rotation axis is cross product of (0,0,1) and direction
            ax = -dy
            ay = dx
            az = 0
            angle = math.acos(dz) * 180 / math.pi
            glRotatef(angle, ax, ay, az)
        elif dz < 0:  # Parallel but pointing down
            glRotatef(180, 1, 0, 0)
        
        # Draw cylinder
        glColor3f(*color)
        quad = gluNewQuadric()
        gluCylinder(quad, radius, radius, length, 16, 1)
        gluDeleteQuadric(quad)
    
    glPopMatrix()


def draw_coordinate_frame(size=50):
    """Draw X, Y, Z axes at origin."""
    glLineWidth(2.0)
    glBegin(GL_LINES)
    
    # X axis - Red
    glColor3f(*COLOR_AXIS_X)
    glVertex3f(0, 0, 0)
    glVertex3f(size, 0, 0)
    
    # Y axis - Green
    glColor3f(*COLOR_AXIS_Y)
    glVertex3f(0, 0, 0)
    glVertex3f(0, size, 0)
    
    # Z axis - Blue
    glColor3f(*COLOR_AXIS_Z)
    glVertex3f(0, 0, 0)
    glVertex3f(0, 0, size)
    
    glEnd()
    glLineWidth(1.0)


def draw_grid(size=500, spacing=50):
    """Draw a ground grid."""
    glColor3f(*COLOR_GRID)
    glBegin(GL_LINES)
    
    # Grid in XY plane at Z=0
    for i in range(-size, size+1, spacing):
        # Lines parallel to X
        glVertex3f(-size, i, 0)
        glVertex3f(size, i, 0)
        # Lines parallel to Y
        glVertex3f(i, -size, 0)
        glVertex3f(i, size, 0)
    
    glEnd()


def draw_robot_arm(joint_angles):
    """
    Draw the complete 6-DOF robot arm.
    
    Args:
        joint_angles: List of 6 joint angles in degrees
    """
    # Get all joint positions
    positions = get_all_joint_positions_6dof(joint_angles)
    
    # Extract positions
    joint_positions = [positions['base']]
    for i in range(1, 7):
        joint_positions.append(positions[f'joint{i}'])
    
    # Draw base
    draw_sphere((0, 0, 0), 20, COLOR_BASE)
    
    # Draw links and joints
    for i in range(len(joint_positions) - 1):
        start = joint_positions[i]
        end = joint_positions[i + 1]
        
        # Draw link
        link_radius = 8 if i < 3 else 5  # Thicker for main arm
        draw_cylinder(start, end, link_radius, COLOR_LINK[i])
        
        # Draw joint sphere
        draw_sphere(end, 12, COLOR_JOINT)
    
    # Draw end-effector
    end_pos = joint_positions[-1]
    draw_sphere(end_pos, 15, COLOR_END)
    
    # Draw coordinate frame at end-effector
    glPushMatrix()
    glTranslatef(end_pos[0], end_pos[1], end_pos[2])
    draw_coordinate_frame(30)
    glPopMatrix()


def draw_text_2d(x, y, text, font):
    """Draw 2D text overlay on the 3D scene."""
    # This will be rendered as a pygame surface overlay
    pass  # Handled separately in main loop


# ============================================================================
# MAIN VISUALIZATION CLASS
# ============================================================================

class RobotVisualizer:
    """Interactive 3D visualization of the 6-DOF robot arm."""
    
    def __init__(self):
        """Initialize the visualizer."""
        pygame.init()
        self.display = pygame.display.set_mode(
            (WINDOW_WIDTH, WINDOW_HEIGHT), 
            DOUBLEBUF | OPENGL
        )
        pygame.display.set_caption("6-DOF Robot Arm - Forward Kinematics")
        
        # Setup OpenGL
        self.setup_opengl()
        
        # Robot state
        self.joint_angles = [0.0] * 6
        self.selected_joint = 0  # 0-5 for J1-J6
        
        # Camera state
        self.camera_rot_x = 30.0
        self.camera_rot_z = 45.0
        self.camera_distance = CAMERA_DISTANCE
        
        # Font for text
        self.font = pygame.font.Font(None, 24)
        
        # Clock for FPS control
        self.clock = pygame.time.Clock()
        
    def setup_opengl(self):
        """Configure OpenGL settings."""
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        
        # Light position
        glLightfv(GL_LIGHT0, GL_POSITION, (1, 1, 1, 0))
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0.3, 0.3, 0.3, 1))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.8, 0.8, 0.8, 1))
        
        # Perspective
        glMatrixMode(GL_PROJECTION)
        gluPerspective(45, (WINDOW_WIDTH / WINDOW_HEIGHT), 10, 5000)
        glMatrixMode(GL_MODELVIEW)
    
    def handle_input(self):
        """Handle keyboard and mouse input."""
        keys = pygame.key.get_pressed()
        
        # Joint selection (1-6 keys)
        for i in range(6):
            if keys[pygame.K_1 + i]:
                self.selected_joint = i
        
        # Joint control
        angle_change = 0
        if keys[pygame.K_q]:
            angle_change = 1.0
        if keys[pygame.K_a]:
            angle_change = -1.0
        if keys[pygame.K_UP]:
            angle_change = 0.5
        if keys[pygame.K_DOWN]:
            angle_change = -0.5
        
        # Apply angle change
        if angle_change != 0:
            self.joint_angles[self.selected_joint] += angle_change
            
            # Clamp to joint limits
            min_deg, max_deg = JOINT_LIMITS_DEG[self.selected_joint + 1]
            self.joint_angles[self.selected_joint] = max(
                min_deg, min(max_deg, self.joint_angles[self.selected_joint])
            )
        
        # Camera rotation
        if keys[pygame.K_LEFT]:
            self.camera_rot_z += CAMERA_ROTATION_SPEED
        if keys[pygame.K_RIGHT]:
            self.camera_rot_z -= CAMERA_ROTATION_SPEED
        if keys[pygame.K_PAGEUP]:
            self.camera_rot_x += CAMERA_ROTATION_SPEED
        if keys[pygame.K_PAGEDOWN]:
            self.camera_rot_x -= CAMERA_ROTATION_SPEED
        
        # Zoom
        if keys[pygame.K_PLUS] or keys[pygame.K_EQUALS]:
            self.camera_distance -= 10
        if keys[pygame.K_MINUS]:
            self.camera_distance += 10
        
        self.camera_distance = max(200, min(2000, self.camera_distance))
    
    def render(self):
        """Render the 3D scene."""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        # Setup camera
        gluLookAt(
            self.camera_distance, 0, 0,  # Camera position
            0, 0, 200,  # Look at point (center of workspace)
            0, 0, 1     # Up vector
        )
        
        # Apply camera rotation
        glRotatef(self.camera_rot_x, 1, 0, 0)
        glRotatef(self.camera_rot_z, 0, 0, 1)
        
        # Draw scene
        draw_grid()
        draw_coordinate_frame(100)
        draw_robot_arm(self.joint_angles)
    
    def render_text_overlay(self):
        """Render 2D text overlay."""
        # Get end-effector position
        x, y, z, _ = forward_kinematics_6dof(self.joint_angles)
        
        # Create text surface
        text_surface = pygame.Surface((400, 400), pygame.SRCALPHA)
        y_offset = 10
        line_height = 25
        
        # Title
        text = self.font.render("6-DOF ROBOT ARM", True, (255, 255, 255))
        text_surface.blit(text, (10, y_offset))
        y_offset += line_height * 1.5
        
        # Joint angles
        for i, angle in enumerate(self.joint_angles):
            color = (100, 255, 100) if i == self.selected_joint else (200, 200, 200)
            prefix = "►" if i == self.selected_joint else " "
            text = self.font.render(
                f"{prefix} J{i+1}: {angle:6.1f}°",
                True, color
            )
            text_surface.blit(text, (10, y_offset))
            y_offset += line_height
        
        y_offset += line_height * 0.5
        
        # End position
        text = self.font.render("End Position:", True, (255, 255, 255))
        text_surface.blit(text, (10, y_offset))
        y_offset += line_height
        
        text = self.font.render(f"  X: {x:7.1f} mm", True, (255, 100, 100))
        text_surface.blit(text, (10, y_offset))
        y_offset += line_height
        
        text = self.font.render(f"  Y: {y:7.1f} mm", True, (100, 255, 100))
        text_surface.blit(text, (10, y_offset))
        y_offset += line_height
        
        text = self.font.render(f"  Z: {z:7.1f} mm", True, (100, 100, 255))
        text_surface.blit(text, (10, y_offset))
        y_offset += line_height * 2
        
        # Controls
        controls = [
            "Controls:",
            "  1-6: Select joint",
            "  Q/A: Adjust angle",
            "  Arrows: Camera",
            "  +/-: Zoom",
            "  R: Reset",
            "  ESC: Exit"
        ]
        
        for line in controls:
            text = self.font.render(line, True, (200, 200, 200))
            text_surface.blit(text, (10, y_offset))
            y_offset += line_height
        
        # Convert to OpenGL texture and render
        text_data = pygame.image.tostring(text_surface, "RGBA", True)
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT, -1, 1)
        
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        # Draw text
        glRasterPos2f(0, WINDOW_HEIGHT - 400)
        glDrawPixels(400, 400, GL_RGBA, GL_UNSIGNED_BYTE, text_data)
        
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        
        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)
    
    def run(self):
        """Main visualization loop."""
        running = True
        
        while running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_r:
                        # Reset all joints
                        self.joint_angles = [0.0] * 6
            
            # Handle continuous input
            self.handle_input()
            
            # Render 3D scene
            self.render()
            
            # Render 2D overlay
            self.render_text_overlay()
            
            # Update display
            pygame.display.flip()
            self.clock.tick(60)  # 60 FPS
        
        pygame.quit()


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("3D ROBOT ARM VISUALIZER")
    print("="*70)
    print("\nStarting 3D visualization...")
    print("Use keyboard controls to manipulate the robot arm!")
    print()
    
    try:
        visualizer = RobotVisualizer()
        visualizer.run()
    except KeyboardInterrupt:
        print("\n\nVisualization interrupted by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
        print("\nNote: Make sure you have PyOpenGL installed:")
        print("  pip install PyOpenGL PyOpenGL_accelerate")
    
    print("\nVisualization closed. Great work! 🎉")
