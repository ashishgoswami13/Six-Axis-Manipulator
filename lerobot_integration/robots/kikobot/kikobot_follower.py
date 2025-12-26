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
Kikobot Follower Robot Implementation

This module implements the follower arm for the Kikobot 6 DOF robot using
the LeRobot framework. The follower arm is controlled by policies or mirrors
the leader arm movements during teleoperation.

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

from .config_kikobot import KikobotFollowerConfig

logger = logging.getLogger(__name__)


class KikobotFollower(Robot):
    """
    Kikobot 6 DOF Follower Arm
    
    This class implements the follower robot arm that can be controlled by:
    1. Trained policies for autonomous operation
    2. Leader arm during teleoperation for data collection
    
    The follower arm has active torque and executes commanded positions.
    """

    config_class = KikobotFollowerConfig
    name = "kikobot_follower"

    def __init__(self, config: KikobotFollowerConfig):
        super().__init__(config)
        self.config = config
        
        # Set normalization mode (degrees or normalized range)
        norm_mode_body = MotorNormMode.DEGREES if config.use_degrees else MotorNormMode.RANGE_M100_100
        
        # Initialize Feetech motor bus (6 motors only, gripper controlled separately)
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
                # Note: Gripper (ID 7) is controlled separately due to different model number
            },
            calibration=self.calibration,
        )
        
        # Initialize gripper control separately (different servo model)
        self.gripper_id = config.motor_ids.get("gripper", 7)
        self.gripper_port = self.bus.port_handler  # Reuse same serial port
        
        # Initialize cameras if configured
        self.cameras = make_cameras_from_configs(config.cameras)

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
        """Define observation space (motor positions + camera images)"""
        return {**self._motors_ft, **self._cameras_ft}

    @cached_property
    def action_features(self) -> dict[str, type]:
        """Define action space (target motor positions)"""
        return self._motors_ft

    @property
    def is_connected(self) -> bool:
        """Check if robot and all cameras are connected"""
        return self.bus.is_connected and all(cam.is_connected for cam in self.cameras.values())

    def connect(self, calibrate: bool = True) -> None:
        """
        Connect to the follower arm and configure it.
        
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
        
        # Connect cameras
        for cam in self.cameras.values():
            cam.connect()
        
        # Configure motors with custom parameters
        self.configure()
        
        logger.info(f"{self.name} connected successfully.")

    @property
    def is_calibrated(self) -> bool:
        """Check if motors are calibrated"""
        return self.bus.is_calibrated

    def calibrate(self) -> None:
        """
        Run calibration procedure for the follower arm.
        
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
                # Filter calibration to only include motors that exist in the bus (no gripper for now)
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
        # Note: wrist_roll can do full 360° rotation, others are limited
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
        Configure motor parameters for optimal performance.
        
        Sets:
        - Operating mode (position control)
        - PID coefficients for smooth motion
        - Torque limits (especially for gripper)
        - Current protection
        - Overload protection
        """
        logger.info(f"Configuring {self.name} motors...")
        
        with self.bus.torque_disabled():
            # Apply base motor configuration (with error handling)
            try:
                self.bus.configure_motors()
            except Exception as e:
                logger.warning(f"Error in configure_motors(), continuing: {e}")
            
            # Configure each motor individually
            for motor in self.bus.motors:
                try:
                    # Set position control mode
                    self.bus.write("Operating_Mode", motor, OperatingMode.POSITION.value)
                    
                    # Set PID coefficients (lower P to reduce shakiness)
                    self.bus.write("P_Coefficient", motor, self.config.p_coefficient)
                    self.bus.write("I_Coefficient", motor, self.config.i_coefficient)
                    self.bus.write("D_Coefficient", motor, self.config.d_coefficient)
                    
                    # Configure gripper with special limits to prevent burnout
                    if motor == "gripper":
                        self.bus.write("Max_Torque_Limit", motor, self.config.gripper_max_torque)
                        self.bus.write("Protection_Current", motor, self.config.gripper_protection_current)
                        self.bus.write("Overload_Torque", motor, self.config.gripper_overload_torque)
                    else:
                        # Regular joints use default limits
                        self.bus.write("Max_Torque_Limit", motor, self.config.max_torque_limit)
                        self.bus.write("Protection_Current", motor, self.config.protection_current)
                        self.bus.write("Overload_Torque", motor, self.config.overload_torque)
                except Exception as e:
                    logger.warning(f"Error configuring motor '{motor}': {e}")
                    continue
        
        logger.info("✓ Motor configuration complete")

    def setup_motors(self) -> None:
        """
        Interactive motor ID setup procedure.
        
        This should be run once when first setting up the robot to assign
        correct IDs to each motor. Connect motors one at a time as prompted.
        """
        logger.info(f"\n{'='*60}")
        logger.info("Motor ID Setup for Kikobot Follower")
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
        Read current state of the follower arm.
        
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
        obs_dict = {f"{motor}.pos": val for motor, val in positions.items()}
        dt_ms = (time.perf_counter() - start) * 1000
        logger.debug(f"{self.name} read state: {dt_ms:.1f}ms")

        # Capture images from cameras
        for cam_key, cam in self.cameras.items():
            start = time.perf_counter()
            obs_dict[cam_key] = cam.async_read()
            dt_ms = (time.perf_counter() - start) * 1000
            logger.debug(f"{self.name} read {cam_key}: {dt_ms:.1f}ms")

        return obs_dict

    def send_action(self, action: dict[str, Any]) -> dict[str, Any]:
        """
        Command follower arm to move to target joint configuration.
        
        The action magnitude may be clipped based on max_relative_target
        configuration for safety. The function returns the actual action sent.
        
        Args:
            action: Dictionary of target positions (e.g., {'shoulder_pan.pos': 45.0})
        
        Returns:
            Dictionary of actual commanded positions (may differ if clipped)
        
        Raises:
            DeviceNotConnectedError: If not connected
        """
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self.name} is not connected.")

        # Extract motor positions from action dict (excluding gripper)
        try:
            goal_pos = {motor: action[f"{motor}.pos"] for motor in self.bus.motors}
        except KeyError as e:
            logger.error(f"Missing motor in action dict: {e}")
            logger.error(f"Expected motors: {list(self.bus.motors.keys())}")
            logger.error(f"Received action keys: {list(action.keys())}")
            raise
        
        # Handle gripper separately if present in action
        gripper_pos = action.get("gripper.pos")

        # Apply safety checks and clipping if configured
        if self.config.max_relative_target is not None:
            # Read current positions
            present_pos = self.bus.sync_read("Present_Position")
            
            # Clip goal positions to safe range (prevent large jumps)
            max_delta = self.config.max_relative_target
            for motor in goal_pos:
                if motor in present_pos:
                    current = present_pos[motor]
                    target = goal_pos[motor]
                    delta = target - current
                    
                    # Clip to max_relative_target
                    if isinstance(max_delta, dict):
                        motor_max_delta = max_delta.get(motor, 30.0)
                    else:
                        motor_max_delta = max_delta
                    
                    if abs(delta) > motor_max_delta:
                        clipped_delta = max(-motor_max_delta, min(motor_max_delta, delta))
                        goal_pos[motor] = current + clipped_delta
                        logger.debug(
                            f"Clipped {motor}: delta {delta:.1f}° → {clipped_delta:.1f}° "
                            f"(max: {motor_max_delta:.1f}°)"
                        )

        # Send position commands to motors
        start = time.perf_counter()
        self.bus.sync_write("Goal_Position", goal_pos)
        dt_ms = (time.perf_counter() - start) * 1000
        logger.debug(f"{self.name} write goal position: {dt_ms:.1f}ms")
        
        # Send gripper command if present
        if gripper_pos is not None:
            try:
                # Convert 0-100 range to servo steps (0-4095)
                gripper_steps = int((gripper_pos / 100.0) * 4095)
                gripper_steps = max(0, min(4095, gripper_steps))
                
                # Write position using packet handler directly
                self.bus.packet_handler.write4ByteTxRx(
                    self.gripper_port,
                    self.gripper_id,
                    42,  # Goal_Position address for STS3215
                    gripper_steps
                )
                logger.debug(f"Gripper set to {gripper_pos:.1f}% ({gripper_steps} steps)")
            except Exception as e:
                logger.warning(f"Failed to control gripper: {e}")

        # Return actual commanded action
        commanded_action = {f"{motor}.pos": val for motor, val in goal_pos.items()}
        if gripper_pos is not None:
            commanded_action["gripper.pos"] = gripper_pos
        return commanded_action

    def disconnect(self) -> None:
        """
        Disconnect from the follower arm.
        
        Optionally disables torque based on configuration for safety.
        """
        if not self.is_connected:
            logger.warning(f"{self.name} is not connected.")
            return

        # Disable torque if configured (allows manual positioning when off)
        if self.config.disable_torque_on_disconnect:
            try:
                logger.info(f"Disabling torque on {self.name}...")
                self.bus.disable_torque()
            except Exception as e:
                logger.warning(f"Could not disable torque on disconnect: {e}")

        # Disconnect cameras
        for cam in self.cameras.values():
            try:
                cam.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting camera: {e}")

        # Disconnect motor bus
        try:
            self.bus.disconnect()
        except Exception as e:
            logger.warning(f"Error disconnecting motor bus: {e}")
        
        logger.info(f"{self.name} disconnected.")

    def __repr__(self) -> str:
        return f"KikobotFollower(port={self.config.port}, motors={list(self.bus.motors.keys())})"
