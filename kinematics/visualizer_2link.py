"""
2-LINK ARM VISUALIZER
=====================

CONCEPT: See your robot arm move in real-time!

This creates an interactive window where you can:
1. Adjust joint angles with sliders
2. See the arm configuration
3. Watch how FK calculates the end position

Press ESC or close window to exit.
"""

import pygame
import math
from forward_kinematics_2link import forward_kinematics_2link, L1, L2, is_reachable
from transformations import Point2D

# ============================================================================
# VISUALIZATION SETTINGS
# ============================================================================

# Window size
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600

# Colors (RGB values)
COLOR_BACKGROUND = (20, 20, 30)      # Dark blue-gray
COLOR_GRID = (40, 40, 50)            # Subtle grid
COLOR_LINK1 = (100, 200, 255)        # Light blue - First link
COLOR_LINK2 = (255, 150, 100)        # Orange - Second link
COLOR_JOINT = (255, 255, 0)          # Yellow - Joints
COLOR_END = (0, 255, 100)            # Green - End-effector
COLOR_TEXT = (200, 200, 200)         # Light gray - Text
COLOR_WORKSPACE = (60, 60, 80)       # Workspace circle
COLOR_REACH_YES = (0, 255, 0)        # Green - Reachable
COLOR_REACH_NO = (255, 0, 0)         # Red - Not reachable

# Scale: pixels per mm
SCALE = 2.0  # 1mm = 2 pixels

# Origin position in window (center)
ORIGIN_X = WINDOW_WIDTH // 2
ORIGIN_Y = WINDOW_HEIGHT // 2

# ============================================================================
# COORDINATE CONVERSION
# ============================================================================

def world_to_screen(x_mm, y_mm):
    """
    Convert robot coordinates (mm) to screen coordinates (pixels).
    
    CONCEPT: 
    - Robot: Origin at base, Y-up (standard math)
    - Screen: Origin at top-left, Y-down (graphics convention)
    
    We need to:
    1. Scale mm to pixels
    2. Flip Y-axis
    3. Translate to screen center
    """
    screen_x = ORIGIN_X + int(x_mm * SCALE)
    screen_y = ORIGIN_Y - int(y_mm * SCALE)  # Flip Y
    return screen_x, screen_y

# ============================================================================
# DRAWING FUNCTIONS
# ============================================================================

def draw_grid(screen):
    """Draw a coordinate grid for reference."""
    # Draw circles showing reach distances
    for radius_mm in [50, 100, 150, 200, 250]:
        screen_radius = int(radius_mm * SCALE)
        pygame.draw.circle(screen, COLOR_GRID, (ORIGIN_X, ORIGIN_Y), 
                         screen_radius, 1)

def draw_workspace(screen):
    """Draw the reachable workspace (annulus)."""
    max_reach = int((L1 + L2) * SCALE)
    min_reach = int(abs(L1 - L2) * SCALE)
    
    # Draw max reach circle
    pygame.draw.circle(screen, COLOR_WORKSPACE, (ORIGIN_X, ORIGIN_Y), 
                      max_reach, 2)
    # Draw min reach circle
    pygame.draw.circle(screen, COLOR_WORKSPACE, (ORIGIN_X, ORIGIN_Y), 
                      min_reach, 2)

def draw_arm(screen, theta1, theta2):
    """
    Draw the robot arm with current joint angles.
    
    Returns: (end_x, end_y) in mm for display
    """
    # Calculate positions using FK
    end_x, end_y, joint4_x, joint4_y = forward_kinematics_2link(theta1, theta2)
    
    # Convert to screen coordinates
    j3_screen = world_to_screen(0, 0)
    j4_screen = world_to_screen(joint4_x, joint4_y)
    end_screen = world_to_screen(end_x, end_y)
    
    # Draw Link 1 (Joint 3 to Joint 4)
    pygame.draw.line(screen, COLOR_LINK1, j3_screen, j4_screen, 8)
    
    # Draw Link 2 (Joint 4 to End)
    pygame.draw.line(screen, COLOR_LINK2, j4_screen, end_screen, 8)
    
    # Draw joints as circles
    pygame.draw.circle(screen, COLOR_JOINT, j3_screen, 10)      # Joint 3
    pygame.draw.circle(screen, COLOR_JOINT, j4_screen, 10)      # Joint 4
    pygame.draw.circle(screen, COLOR_END, end_screen, 12)       # End-effector
    
    return end_x, end_y

def draw_text_info(screen, theta1, theta2, end_x, end_y, font):
    """Display current angles and position."""
    y_offset = 10
    line_height = 25
    
    # Title
    title = font.render("2-LINK ARM VISUALIZER", True, COLOR_TEXT)
    screen.blit(title, (10, y_offset))
    y_offset += line_height * 1.5
    
    # Joint angles
    text1 = font.render(f"Joint 3 (θ1): {theta1:6.1f}°", True, COLOR_LINK1)
    screen.blit(text1, (10, y_offset))
    y_offset += line_height
    
    text2 = font.render(f"Joint 4 (θ2): {theta2:6.1f}°", True, COLOR_LINK2)
    screen.blit(text2, (10, y_offset))
    y_offset += line_height * 1.5
    
    # End-effector position
    distance = math.sqrt(end_x**2 + end_y**2)
    reachable = is_reachable(end_x, end_y)
    reach_color = COLOR_REACH_YES if reachable else COLOR_REACH_NO
    
    text3 = font.render(f"End Position:", True, COLOR_TEXT)
    screen.blit(text3, (10, y_offset))
    y_offset += line_height
    
    text4 = font.render(f"  X: {end_x:7.2f} mm", True, COLOR_END)
    screen.blit(text4, (10, y_offset))
    y_offset += line_height
    
    text5 = font.render(f"  Y: {end_y:7.2f} mm", True, COLOR_END)
    screen.blit(text5, (10, y_offset))
    y_offset += line_height
    
    text6 = font.render(f"  Distance: {distance:6.2f} mm", True, reach_color)
    screen.blit(text6, (10, y_offset))
    y_offset += line_height * 2
    
    # Instructions
    instructions = [
        "Controls:",
        "  Q/A: Joint 3 ± 5°",
        "  W/S: Joint 4 ± 5°",
        "  Arrow Keys: ± 1°",
        "  R: Reset to 0°",
        "  ESC: Exit"
    ]
    
    for instruction in instructions:
        text = font.render(instruction, True, COLOR_TEXT)
        screen.blit(text, (10, y_offset))
        y_offset += line_height

# ============================================================================
# MAIN VISUALIZATION LOOP
# ============================================================================

def run_visualizer():
    """
    Main interactive visualization.
    
    LEARNING MOMENT:
    Watch how changing θ1 and θ2 affects the end position!
    - θ1 rotates the whole arm
    - θ2 bends the elbow
    """
    # Initialize Pygame
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("2-Link Robot Arm - Forward Kinematics")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 24)
    
    # Initial joint angles
    theta1 = 0.0
    theta2 = 0.0
    
    # Main loop
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
                    # Reset
                    theta1 = 0.0
                    theta2 = 0.0
        
        # Handle continuous key presses
        keys = pygame.key.get_pressed()
        
        # Joint 3 controls
        if keys[pygame.K_q]:
            theta1 += 1.0
        if keys[pygame.K_a]:
            theta1 -= 1.0
        
        # Joint 4 controls  
        if keys[pygame.K_w]:
            theta2 += 1.0
        if keys[pygame.K_s]:
            theta2 -= 1.0
            
        # Fine control with arrow keys
        if keys[pygame.K_UP]:
            theta2 += 0.5
        if keys[pygame.K_DOWN]:
            theta2 -= 0.5
        if keys[pygame.K_RIGHT]:
            theta1 += 0.5
        if keys[pygame.K_LEFT]:
            theta1 -= 0.5
        
        # Clamp angles to joint limits (±140°)
        theta1 = max(-140, min(140, theta1))
        theta2 = max(-140, min(140, theta2))
        
        # Clear screen
        screen.fill(COLOR_BACKGROUND)
        
        # Draw elements
        draw_grid(screen)
        draw_workspace(screen)
        end_x, end_y = draw_arm(screen, theta1, theta2)
        draw_text_info(screen, theta1, theta2, end_x, end_y, font)
        
        # Update display
        pygame.display.flip()
        clock.tick(60)  # 60 FPS
    
    pygame.quit()
    print("\nVisualization closed. Hope you learned something! 🎓")

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    print("="*60)
    print("INTERACTIVE 2-LINK ARM VISUALIZER")
    print("="*60)
    print("\nStarting visualization...")
    print("Use keyboard controls to move the arm and see FK in action!")
    print()
    
    try:
        run_visualizer()
    except KeyboardInterrupt:
        print("\n\nVisualization interrupted by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
        print("\nNote: Make sure you have pygame installed:")
        print("  pip install pygame")
