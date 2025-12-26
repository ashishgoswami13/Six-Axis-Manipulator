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
Configuration for Kikobot 6 DOF Robot Arm with ST3215 Servos

Hardware Specifications:
- 6 DOF Robot Arm (Kikobot)
- Waveshare ST3215 Serial Bus Servo Motors (Feetech STS3215 compatible)
- Waveshare Bus Servo Adapter board
- Communication: UART/USB at 1000000 baud

Motor Configuration:
- ID 1: Base/Shoulder Pan
- ID 2: Shoulder Lift  
- ID 3: Elbow Flex
- ID 4: Wrist Flex
- ID 5: Wrist Roll
- ID 6: Gripper
"""

from dataclasses import dataclass, field

from lerobot.cameras import CameraConfig

try:
    from lerobot.robots.config import RobotConfig
except ImportError:
    # Fallback for different lerobot versions
    from lerobot.common.robot_devices.robots.config import RobotConfig


@RobotConfig.register_subclass("kikobot_follower")
@dataclass
class KikobotFollowerConfig(RobotConfig):
    """Configuration for Kikobot Follower arm (controlled by policy/leader)"""
    
    # Serial port for follower arm
    port: str = "/dev/ttyACM1"
    
    # Baudrate for ST3215 servos
    baudrate: int = 1000000
    
    # Disable torque when disconnecting for safety
    disable_torque_on_disconnect: bool = True
    
    # Maximum relative positional change per step (safety limit)
    # Prevents large sudden movements
    max_relative_target: float | dict[str, float] | None = 30.0  # degrees
    
    # Camera configurations for observation
    cameras: dict[str, CameraConfig] = field(default_factory=dict)
    
    # Use degrees instead of normalized [-1, 1] range
    use_degrees: bool = True
    
    # Motor IDs for follower arm
    motor_ids: dict[str, int] = field(default_factory=lambda: {
        "shoulder_pan": 1,
        "shoulder_lift": 2,
        "elbow_flex": 3,
        "wrist_flex": 4,
        "wrist_roll": 5,
        "wrist_roll_2": 6,
        "gripper": 7,  # Manually controlled with arrow keys
    })
    
    # Servo speed (steps/second) - ST3215 specific
    default_speed: int = 1500
    
    # Servo acceleration
    default_acceleration: int = 50
    
    # PID coefficients for position control
    # Lower P value reduces shakiness
    p_coefficient: int = 16
    i_coefficient: int = 0
    d_coefficient: int = 32
    
    # Torque limits (percentage of max)
    max_torque_limit: int = 1000  # 100% for most joints
    gripper_max_torque: int = 500  # 50% for gripper to avoid burnout
    
    # Current protection
    protection_current: int = 500  # 100% for most joints
    gripper_protection_current: int = 250  # 50% for gripper
    
    # Overload torque threshold
    overload_torque: int = 50  # 50% torque when overloaded
    gripper_overload_torque: int = 25  # 25% for gripper


@RobotConfig.register_subclass("kikobot_leader")
@dataclass
class KikobotLeaderConfig(RobotConfig):
    """Configuration for Kikobot Leader arm (teleoperation input device)"""
    
    # Serial port for leader arm
    port: str = "/dev/ttyACM0"
    
    # Baudrate for ST3215 servos
    baudrate: int = 1000000
    
    # Disable torque when disconnecting
    disable_torque_on_disconnect: bool = True
    
    # Leader arm should have torque disabled for manual control
    # This is set during configure() method
    enable_torque_on_connect: bool = False
    
    # Camera configurations (optional for leader)
    cameras: dict[str, CameraConfig] = field(default_factory=dict)
    
    # Use degrees instead of normalized [-1, 1] range
    use_degrees: bool = True
    
    # Motor IDs for leader arm (6 motors, no gripper)
    motor_ids: dict[str, int] = field(default_factory=lambda: {
        "shoulder_pan": 1,
        "shoulder_lift": 2,
        "elbow_flex": 3,
        "wrist_flex": 4,
        "wrist_roll": 5,
        "wrist_roll_2": 6,
    })
    
    # Read frequency for leader position updates
    read_frequency_hz: float = 50.0  # 50Hz = 20ms update rate
    
    # Smoothing for leader readings (exponential moving average)
    position_smoothing_alpha: float = 0.3  # 0 = no smoothing, 1 = no filtering


@RobotConfig.register_subclass("kikobot_bimanual")
@dataclass  
class KikobotBimanualConfig(RobotConfig):
    """Configuration for dual-arm Kikobot setup (leader + follower)"""
    
    # Leader arm configuration (6 motors, no gripper)
    leader: KikobotLeaderConfig = field(default_factory=lambda: KikobotLeaderConfig(
        port="/dev/ttyACM0"  # ACM0 has 6 servos
    ))
    
    # Follower arm configuration (7 motors, with gripper)
    follower: KikobotFollowerConfig = field(default_factory=lambda: KikobotFollowerConfig(
        port="/dev/ttyACM1"  # ACM1 has 7 servos
    ))
    
    # Camera configurations for observation
    cameras: dict[str, CameraConfig] = field(default_factory=dict)
    
    # Synchronization settings
    sync_frequency_hz: float = 50.0  # Teleoperation update rate
    
    # Enable dataset recording
    record_dataset: bool = False
    
    # Dataset save directory
    dataset_dir: str = "./data/kikobot_demos"
