#!/usr/bin/env python

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
Kikobot Leader Robot Implementation

This module implements the leader arm for the Kikobot 6 DOF robot using
the LeRobot framework. The leader arm is used for teleoperation - it has
torque disabled so a human operator can manually move it, and its positions
are read to control the follower arm.

Hardware:
- Kikobot 6 DOF Robot Arm
- 6x Waveshare ST3215 Serial Bus Servos (Feetech STS3215 compatible)
- Waveshare Bus Servo Adapter board
- Communication: UART/USB at 1000000 baud
"""

import logging
import time
from functools import cached_property
from typing import Any

try:
    from lerobot.cameras.utils import make_cameras_from_configs
    from lerobot.motors import Motor, MotorCalibration, MotorNormMode
    from lerobot.motors.feetech import FeetechMotorsBus, OperatingMode
    from lerobot.robots.robot import Robot
    from lerobot.utils.errors import DeviceAlreadyConnectedError, DeviceNotConnectedError
except ImportError as e:
    raise ImportError(
        "LeRobot not found. Please install it with: pip install lerobot[feetech]"
    ) from e

from .config_kikobot import KikobotLeaderConfig

logger = logging.getLogger(__name__)


class KikobotLeader(Robot):
    """
    Kikobot 6 DOF Leader Arm
    
    This class implements the leader robot arm for teleoperation:
    - Torque is DISABLED, allowing manual positioning by operator
    - Positions are continuously read and used to control follower arm
    - Optional position smoothing for stable control
    
    The leader arm acts as an input device for data collection.
    """

    config_class = KikobotLeaderConfig
    name = "kikobot_leader"

    def __init__(self, config: KikobotLeaderConfig):
        super().__init__(config)
        self.config = config
        
        # Set normalization mode (degrees or normalized range)
        norm_mode_body = MotorNormMode.DEGREES if config.use_degrees else MotorNormMode.RANGE_M100_100
        
        # Initialize Feetech motor bus with ST3215 servos
        self.bus = FeetechMotorsBus(
            port=self.config.port,
            motors={
                "shoulder_pan": Motor(
                    config.motor_ids["shoulder_pan"], 
                    "sts3215", 
                    norm_mode_body
                ),
                "shoulder_lift": Motor(
                    config.motor_ids["shoulder_lift"], 
                    "sts3215", 
                    norm_mode_body
                ),
                "elbow_flex": Motor(
                    config.motor_ids["elbow_flex"], 
                    "sts3215", 
                    norm_mode_body
                ),
                "wrist_flex": Motor(
                    config.motor_ids["wrist_flex"], 
                    "sts3215", 
                    norm_mode_body
                ),
                "wrist_roll": Motor(
                    config.motor_ids["wrist_roll"], 
                    "sts3215", 
                    norm_mode_body
                ),
                "wrist_roll_2": Motor(
                    config.motor_ids["wrist_roll_2"], 
                    "sts3215", 
                    norm_mode_body
                ),
            },
            # Note: Leader arm has no gripper (6 motors total)
            calibration=self.calibration,
        )
        
        # Initialize cameras if configured (usually not needed for leader)
        self.cameras = make_cameras_from_configs(config.cameras)
        
        # Position smoothing state (exponential moving average)
        self._smoothed_positions = None

    @property
    def _motors_ft(self) -> dict[str, type]:
        """Feature types for motor positions"""
        return {f"{motor}.pos": float for motor in self.bus.motors}

    @property
    def _cameras_ft(self) -> dict[str, tuple]:
        """Feature types for camera images"""
        return {
            cam: (self.config.cameras[cam].height, self.config.cameras[cam].width, 3)
            for cam in self.cameras
        }

    @cached_property
    def observation_features(self) -> dict[str, type | tuple]:
        """Define observation space (motor positions + optional cameras)"""
        return {**self._motors_ft, **self._cameras_ft}

    @cached_property
    def action_features(self) -> dict[str, type]:
        """
        Leader arm doesn't execute actions, but we define this for compatibility.
        In teleoperation, the leader's observations become the follower's actions.
        """
        return self._motors_ft

    @property
    def is_connected(self) -> bool:
        """Check if robot and all cameras are connected"""
        return self.bus.is_connected and all(cam.is_connected for cam in self.cameras.values())

    def connect(self, calibrate: bool = True) -> None:
        """
        Connect to the leader arm and configure it.
        
        Args:
            calibrate: If True, run calibration if not already calibrated
        
        Raises:
            DeviceAlreadyConnectedError: If already connected
        """
        if self.is_connected:
            raise DeviceAlreadyConnectedError(f"{self.name} already connected")
        
        logger.info(f"Connecting to {self.name} on {self.config.port}...")
        
        # Connect to motor bus
        self.bus.connect()
        
        # Run calibration if needed
        if not self.is_calibrated and calibrate:
            logger.warning(
                "Mismatch between calibration values in the motor and the calibration file, "
                "or no calibration file found"
            )
            self.calibrate()
        
        # Connect cameras (if any)
        for cam in self.cameras.values():
            cam.connect()
        
        # Configure motors
        self.configure()
        
        logger.info(f"{self.name} connected successfully.")

    @property
    def is_calibrated(self) -> bool:
        """Check if motors are calibrated"""
        return self.bus.is_calibrated

    def calibrate(self) -> None:
        """
        Run calibration procedure for the leader arm.
        
        This calibration establishes:
        1. Homing offsets (zero positions)
        2. Range of motion limits for each joint
        3. Drive modes
        
        The calibration data is saved to a JSON file for future use.
        """
        if self.calibration:
            # Calibration file exists, ask user whether to use it or run new calibration
            user_input = input(
                f"Press ENTER to use provided calibration file associated with the id {self.id}, "
                f"or type 'c' and press ENTER to run calibration: "
            )
            if user_input.strip().lower() != "c":
                logger.info(f"Writing calibration file associated with the id {self.id} to the motors")
                # Filter calibration to only include motors that exist in the bus (leader has no gripper)
                filtered_calibration = {
                    motor: calib 
                    for motor, calib in self.calibration.items() 
                    if motor in self.bus.motors
                }
                self.bus.write_calibration(filtered_calibration)
                return

        logger.info(f"\n{'='*60}")
        logger.info(f"Running calibration of {self.name}")
        logger.info(f"{'='*60}")
        
        # Disable torque for manual positioning
        self.bus.disable_torque()
        
        # Set all motors to position control mode
        for motor in self.bus.motors:
            self.bus.write("Operating_Mode", motor, OperatingMode.POSITION.value)
        
        # Show current positions
        logger.info("\nReading current joint positions...")
        current_positions = self.bus.sync_read("Present_Position")
        logger.info("\nCurrent positions (raw steps):")
        for motor, pos in current_positions.items():
            logger.info(f"  {motor:20s}: {pos:7.1f} steps")
        
        # Step 1: Set homing positions from current upright position
        input(
            f"\n[STEP 1/2] Position the {self.name} arm in UPRIGHT position (home/zero position).\n"
            f"This will be the reference position (all joints at 0°).\n"
            f"Press ENTER when ready..."
        )
        homing_offsets = self.bus.set_half_turn_homings()
        logger.info("✓ Homing offsets recorded from current position")

        # Step 2: Record range of motion for each joint
        full_turn_motor = "wrist_roll"
        limited_range_motors = [motor for motor in self.bus.motors if motor != full_turn_motor]
        
        print(
            f"\n[STEP 2/2] Move all joints EXCEPT '{full_turn_motor}' sequentially through their\n"
            f"ENTIRE ranges of motion (one at a time, moving each from minimum to maximum).\n"
            f"Recording positions. Press ENTER when done..."
        )
        range_mins, range_maxes = self.bus.record_ranges_of_motion(limited_range_motors)
        
        # Set full rotation range for wrist_roll
        range_mins[full_turn_motor] = 0
        range_maxes[full_turn_motor] = 4095  # Full 360° in steps
        
        logger.info("✓ Range of motion recorded")

        # Build calibration dictionary
        self.calibration = {}
        for motor, m in self.bus.motors.items():
            self.calibration[motor] = MotorCalibration(
                id=m.id,
                drive_mode=0,
                homing_offset=homing_offsets[motor],
                range_min=range_mins[motor],
                range_max=range_maxes[motor],
            )

        # Write calibration to motors
        self.bus.write_calibration(self.calibration)
        
        # Save to file
        self._save_calibration()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"✓ Calibration complete and saved to: {self.calibration_fpath}")
        logger.info(f"{'='*60}\n")

    def configure(self) -> None:
        """
        Configure leader arm for teleoperation.
        
        Key configuration:
        - Torque is DISABLED to allow manual manipulation
        - Operating mode set to position for reading positions
        
        The leader arm should be freely movable by hand.
        """
        logger.info(f"Configuring {self.name} for teleoperation...")
        
        # Torque must be disabled for manual control
        self.bus.disable_torque()
        
        # Set position control mode for reading positions
        for motor in self.bus.motors:
            self.bus.write("Operating_Mode", motor, OperatingMode.POSITION.value)
        
        logger.info("✓ Leader arm configured (torque disabled for manual control)")

    def setup_motors(self) -> None:
        """
        Interactive motor ID setup procedure.
        
        This should be run once when first setting up the robot to assign
        correct IDs to each motor. Connect motors one at a time as prompted.
        """
        logger.info(f"\n{'='*60}")
        logger.info("Motor ID Setup for Kikobot Leader")
        logger.info(f"{'='*60}\n")
        
        for motor in reversed(self.bus.motors):
            input(
                f"Connect the controller board to the '{motor}' motor ONLY and press ENTER.\n"
                f"(Disconnect all other motors first)"
            )
            self.bus.setup_motor(motor)
            logger.info(f"✓ '{motor}' motor ID set to {self.bus.motors[motor].id}\n")
        
        logger.info(f"{'='*60}")
        logger.info("✓ Motor ID setup complete!")
        logger.info(f"{'='*60}\n")

    def get_observation(self) -> dict[str, Any]:
        """
        Read current position of the leader arm.
        
        This reads the manually-positioned joints and optionally applies
        smoothing to reduce noise. The smoothed positions are used to
        control the follower arm.
        
        Returns:
            Dictionary containing:
            - Motor positions (e.g., 'shoulder_pan.pos': 45.0)
            - Camera images (if configured)
        
        Raises:
            DeviceNotConnectedError: If not connected
        """
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self.name} is not connected.")

        obs_dict = {}
        
        # Read arm position from all motors
        start = time.perf_counter()
        positions = self.bus.sync_read("Present_Position")
        
        # Apply position smoothing if configured
        if self.config.position_smoothing_alpha > 0:
            if self._smoothed_positions is None:
                # Initialize smoothed positions on first read
                self._smoothed_positions = positions.copy()
            else:
                # Exponential moving average: smoothed = alpha * new + (1-alpha) * old
                alpha = self.config.position_smoothing_alpha
                for motor, pos in positions.items():
                    self._smoothed_positions[motor] = (
                        alpha * pos + (1 - alpha) * self._smoothed_positions[motor]
                    )
            
            positions = self._smoothed_positions
        
        obs_dict = {f"{motor}.pos": val for motor, val in positions.items()}
        dt_ms = (time.perf_counter() - start) * 1000
        logger.debug(f"{self.name} read state: {dt_ms:.1f}ms")

        # Capture images from cameras (rarely used for leader)
        for cam_key, cam in self.cameras.items():
            start = time.perf_counter()
            obs_dict[cam_key] = cam.async_read()
            dt_ms = (time.perf_counter() - start) * 1000
            logger.debug(f"{self.name} read {cam_key}: {dt_ms:.1f}ms")

        return obs_dict

    def send_action(self, action: dict[str, Any]) -> dict[str, Any]:
        """
        Leader arm doesn't execute actions - it's manually positioned.
        
        This method is included for API compatibility but does nothing.
        
        Args:
            action: Ignored
        
        Returns:
            Empty dict
        
        Raises:
            DeviceNotConnectedError: If not connected
        """
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self.name} is not connected.")
        
        logger.debug(f"{self.name} ignoring send_action (leader arm is manually controlled)")
        return {}

    def disconnect(self) -> None:
        """
        Disconnect from the leader arm.
        
        Torque is already disabled, so this just closes connections.
        """
        if not self.is_connected:
            logger.warning(f"{self.name} is not connected.")
            return

        # Disconnect cameras
        for cam in self.cameras.values():
            cam.disconnect()

        # Disconnect motor bus
        self.bus.disconnect()
        
        logger.info(f"{self.name} disconnected.")

    def __repr__(self) -> str:
        return f"KikobotLeader(port={self.config.port}, motors={list(self.bus.motors.keys())})"
