#!/usr/bin/env python3

# Copyright 2025 Kikobot LeRobot Integration
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Kikobot Leader-Follower Teleoperation

This script demonstrates real-time teleoperation where the follower arm
mirrors the movements of the leader arm. The leader arm is manually
positioned by a human operator, and the follower arm executes the same
positions with active torque control.

Usage:
    python teleoperate_kikobot.py [--leader-port PORT] [--follower-port PORT] [--frequency HZ]

Example:
    python teleoperate_kikobot.py --leader-port /dev/ttyACM1 --follower-port /dev/ttyACM0 --frequency 50

Hardware Setup:
    - Leader arm: Torque disabled, manually movable
    - Follower arm: Torque enabled, follows leader positions
    - Both arms must be calibrated before use
"""

import argparse
import logging
import sys
import time
from pathlib import Path
import select
import termios
import tty

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from robots.kikobot import (
    KikobotFollower,
    KikobotFollowerConfig,
    KikobotLeader,
    KikobotLeaderConfig,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KeyboardInput:
    """Non-blocking keyboard input handler for arrow keys."""
    
    def __init__(self):
        self.fd = sys.stdin.fileno()
        self.old_settings = termios.tcgetattr(self.fd)
        
    def __enter__(self):
        tty.setcbreak(self.fd)
        return self
        
    def __exit__(self, *args):
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)
    
    def get_key(self, timeout=0.0):
        """Get a keypress if available, non-blocking."""
        if select.select([sys.stdin], [], [], timeout)[0]:
            ch = sys.stdin.read(1)
            # Handle arrow keys (escape sequences)
            if ch == '\x1b':  # ESC
                ch2 = sys.stdin.read(1)
                if ch2 == '[':
                    ch3 = sys.stdin.read(1)
                    if ch3 == 'A':
                        return 'UP'
                    elif ch3 == 'B':
                        return 'DOWN'
                    elif ch3 == 'C':
                        return 'RIGHT'
                    elif ch3 == 'D':
                        return 'LEFT'
            return ch
        return None


class KikobotTeleoperator:
    """
    Leader-Follower teleoperation controller for Kikobot arms.
    
    Continuously reads the leader arm position and commands the follower
    arm to match it, enabling real-time mirroring of movements.
    """
    
    def __init__(
        self,
        leader_port: str = "/dev/ttyACM1",
        follower_port: str = "/dev/ttyACM0",
        frequency: float = 50.0,
    ):
        """
        Initialize the teleoperation controller.
        
        Args:
            leader_port: Serial port for leader arm
            follower_port: Serial port for follower arm
            frequency: Control loop frequency in Hz
        """
        self.frequency = frequency
        self.dt = 1.0 / frequency
        
        # Create robot configurations
        logger.info("Creating robot configurations...")
        self.leader_config = KikobotLeaderConfig(
            port=leader_port,
            use_degrees=True,
            position_smoothing_alpha=0.3,  # Smooth out jitter
        )
        
        self.follower_config = KikobotFollowerConfig(
            port=follower_port,
            use_degrees=True,
            max_relative_target=30.0,  # Limit sudden movements
        )
        
        # Create robot instances
        logger.info("Creating robot instances...")
        self.leader = KikobotLeader(self.leader_config)
        self.follower = KikobotFollower(self.follower_config)
        
        self.is_connected = False
        self.is_running = False
        
        # Gripper control state
        self.gripper_position = 0.0  # 0=closed, 100=open
        self.gripper_step = 5.0  # Movement step size

    def connect(self, calibrate: bool = False) -> bool:
        """
        Connect to both leader and follower arms.
        
        Args:
            calibrate: If True, run calibration if not already calibrated
        
        Returns:
            True if both arms connected successfully
        """
        try:
            logger.info("="*60)
            logger.info("Connecting to Kikobot Leader-Follower System")
            logger.info("="*60)
            
            # Connect leader arm
            logger.info("\n1. Connecting to LEADER arm...")
            self.leader.connect(calibrate=calibrate)
            logger.info(f"   ✓ Leader connected on {self.leader_config.port}")
            logger.info("   → Leader arm should be freely movable (no torque)")
            
            # Connect follower arm
            logger.info("\n2. Connecting to FOLLOWER arm...")
            self.follower.connect(calibrate=calibrate)
            logger.info(f"   ✓ Follower connected on {self.follower_config.port}")
            logger.info("   → Follower arm has active torque")
            
            self.is_connected = True
            
            logger.info("\n" + "="*60)
            logger.info("✓ Both arms connected successfully!")
            logger.info("="*60 + "\n")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            self.disconnect()
            return False

    def run_calibration(self) -> bool:
        """
        Run calibration procedure for both arms.
        
        Returns:
            True if calibration completed successfully
        """
        if not self.is_connected:
            logger.error("Not connected! Call connect() first.")
            return False
        
        try:
            logger.info("\n" + "="*60)
            logger.info("CALIBRATION PROCEDURE")
            logger.info("="*60)
            logger.info("\nYou will calibrate both arms one at a time.")
            logger.info("Follow the on-screen instructions carefully.\n")
            
            # Calibrate leader arm
            logger.info("="*60)
            logger.info("CALIBRATING LEADER ARM")
            logger.info("="*60)
            self.leader.calibrate()
            
            # Calibrate follower arm
            logger.info("\n" + "="*60)
            logger.info("CALIBRATING FOLLOWER ARM")
            logger.info("="*60)
            self.follower.calibrate()
            
            logger.info("\n" + "="*60)
            logger.info("✓ CALIBRATION COMPLETE FOR BOTH ARMS!")
            logger.info("="*60 + "\n")
            
            return True
            
        except Exception as e:
            logger.error(f"Calibration failed: {e}")
            return False

    def run(self) -> None:
        """
        Run the teleoperation loop.
        
        Continuously reads leader positions and commands follower to match.
        Gripper is controlled manually with arrow keys:
        - UP/DOWN: Open/Close gripper
        - LEFT/RIGHT: Fine adjust gripper
        
        Press Ctrl+C to stop.
        """
        if not self.is_connected:
            logger.error("Not connected! Call connect() first.")
            return
        
        logger.info("="*60)
        logger.info("Starting Teleoperation with Manual Gripper Control")
        logger.info("="*60)
        logger.info(f"Control frequency: {self.frequency} Hz")
        logger.info(f"Update period: {self.dt*1000:.1f} ms")
        logger.info("\n" + "="*60)
        logger.info("CONTROLS:")
        logger.info("="*60)
        logger.info("  Leader Arm: Move manually (mirrors to follower)")
        logger.info("  Gripper:    Arrow Keys")
        logger.info("    ↑ UP    = Open gripper (+5)")
        logger.info("    ↓ DOWN  = Close gripper (-5)")
        logger.info("    → RIGHT = Fine open (+1)")
        logger.info("    ← LEFT  = Fine close (-1)")
        logger.info("\nPress Ctrl+C to stop.")
        logger.info("="*60 + "\n")
        
        # Initialize gripper to middle position
        self.gripper_position = 50.0
        
        self.is_running = True
        iteration = 0
        errors = 0
        
        try:
            with KeyboardInput() as kbd:
                while self.is_running:
                    start_time = time.perf_counter()
                    
                    try:
                        # Check for gripper control keys (non-blocking)
                        key = kbd.get_key(timeout=0.001)
                        if key == 'UP':
                            self.gripper_position = min(100.0, self.gripper_position + self.gripper_step)
                            logger.info(f"Gripper: {self.gripper_position:.1f}% (opening)")
                        elif key == 'DOWN':
                            self.gripper_position = max(0.0, self.gripper_position - self.gripper_step)
                            logger.info(f"Gripper: {self.gripper_position:.1f}% (closing)")
                        elif key == 'RIGHT':
                            self.gripper_position = min(100.0, self.gripper_position + 1.0)
                            logger.info(f"Gripper: {self.gripper_position:.1f}%")
                        elif key == 'LEFT':
                            self.gripper_position = max(0.0, self.gripper_position - 1.0)
                            logger.info(f"Gripper: {self.gripper_position:.1f}%")
                        
                        # Read leader arm position (exclude gripper since leader has no gripper)
                        leader_obs = self.leader.get_observation()
                        
                        # Extract motor positions from leader
                        leader_positions = {
                            key: value for key, value in leader_obs.items()
                            if key.endswith('.pos') and 'gripper' not in key
                        }
                        
                        # Add gripper position from manual control
                        leader_positions['gripper.pos'] = self.gripper_position
                        
                        # Send positions to follower
                        self.follower.send_action(leader_positions)
                        
                        # Log progress every 50 iterations (~1 second at 50Hz)
                        iteration += 1
                        if iteration % 50 == 0:
                            # Show current positions
                            pos_str = ", ".join([
                                f"{key.split('.')[0]}: {value:.1f}°"
                                for key, value in list(leader_positions.items())[:3]
                            ])
                            logger.info(f"Iter {iteration:5d} | {pos_str} | Gripper: {self.gripper_position:.0f}% | Errors: {errors}")
                    
                    except Exception as e:
                        errors += 1
                        import traceback
                        logger.error(f"Error in teleoperation loop: {e}")
                        logger.error(f"Traceback: {traceback.format_exc()}")
                        if errors > 10:
                            logger.error("Too many errors, stopping...")
                            break
                    
                    # Sleep to maintain desired frequency
                    elapsed = time.perf_counter() - start_time
                    sleep_time = self.dt - elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                    elif iteration % 50 == 0:
                        logger.warning(
                            f"Control loop running slow: {elapsed*1000:.1f} ms "
                            f"(target: {self.dt*1000:.1f} ms)"
                        )
        
        except KeyboardInterrupt:
            logger.info("\n\nKeyboard interrupt received. Stopping...")
        
        finally:
            self.is_running = False
            logger.info(f"\n{'='*60}")
            logger.info(f"Teleoperation Statistics:")
            logger.info(f"  Total iterations: {iteration}")
            logger.info(f"  Errors: {errors}")
            logger.info(f"  Duration: {iteration * self.dt:.1f} seconds")
            logger.info(f"{'='*60}\n")

    def disconnect(self) -> None:
        """Disconnect both arms."""
        logger.info("\nDisconnecting...")
        
        if hasattr(self, 'follower') and self.follower.is_connected:
            self.follower.disconnect()
            logger.info("✓ Follower disconnected")
        
        if hasattr(self, 'leader') and self.leader.is_connected:
            self.leader.disconnect()
            logger.info("✓ Leader disconnected")
        
        self.is_connected = False
        logger.info("✓ All devices disconnected\n")


def main():
    """Main entry point for teleoperation script."""
    parser = argparse.ArgumentParser(
        description="Kikobot Leader-Follower Teleoperation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default ports
  python teleoperate_kikobot.py
  
  # Run with custom ports
  python teleoperate_kikobot.py --leader-port /dev/ttyUSB1 --follower-port /dev/ttyUSB0
  
  # Run with calibration
  python teleoperate_kikobot.py --calibrate
  
  # Run at different frequency
  python teleoperate_kikobot.py --frequency 30

Hardware Setup:
  - Leader arm (manual control): /dev/ttyACM1
  - Follower arm (active control): /dev/ttyACM0
  - Baudrate: 1000000 (fixed for ST3215 servos)
        """
    )
    
    parser.add_argument(
        "--leader-port",
        type=str,
        default="/dev/ttyACM1",
        help="Serial port for leader arm (default: /dev/ttyACM1)"
    )
    
    parser.add_argument(
        "--follower-port",
        type=str,
        default="/dev/ttyACM0",
        help="Serial port for follower arm (default: /dev/ttyACM0)"
    )
    
    parser.add_argument(
        "--frequency",
        type=float,
        default=50.0,
        help="Control loop frequency in Hz (default: 50)"
    )
    
    parser.add_argument(
        "--calibrate",
        action="store_true",
        help="Run calibration if needed, then start teleoperation"
    )
    
    parser.add_argument(
        "--calibrate-only",
        action="store_true",
        help="Run calibration only and exit (don't start teleoperation)"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose debug logging"
    )
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create teleoperator
    teleop = KikobotTeleoperator(
        leader_port=args.leader_port,
        follower_port=args.follower_port,
        frequency=args.frequency,
    )
    
    # Connect to robots
    calibrate_mode = args.calibrate or args.calibrate_only
    if not teleop.connect(calibrate=False):  # Don't auto-calibrate on connect
        logger.error("Failed to connect to robots. Exiting.")
        return 1
    
    # If calibrate mode, run calibration procedure
    if calibrate_mode:
        if not teleop.run_calibration():
            logger.error("Calibration failed. Exiting.")
            teleop.disconnect()
            return 1
    
    # If calibrate-only mode, disconnect and exit
    if args.calibrate_only:
        logger.info("\n✓ You can now run teleoperation with:")
        logger.info("  python teleoperate_kikobot.py\n")
        teleop.disconnect()
        return 0
    
    # Run teleoperation
    try:
        teleop.run()
    finally:
        teleop.disconnect()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
