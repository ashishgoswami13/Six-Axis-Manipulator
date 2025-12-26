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
Kikobot 6 DOF Robot Integration for LeRobot

This package provides LeRobot integration for Kikobot robot arms using
Waveshare ST3215 serial bus servos (Feetech STS3215 compatible).

Classes:
    - KikobotFollower: Follower arm for policy execution
    - KikobotLeader: Leader arm for teleoperation
    - KikobotFollowerConfig: Configuration for follower arm
    - KikobotLeaderConfig: Configuration for leader arm
    - KikobotBimanualConfig: Configuration for dual-arm setup
"""

from .config_kikobot import (
    KikobotBimanualConfig,
    KikobotFollowerConfig,
    KikobotLeaderConfig,
)
from .kikobot_follower import KikobotFollower
from .kikobot_leader import KikobotLeader

__all__ = [
    "KikobotFollower",
    "KikobotLeader",
    "KikobotFollowerConfig",
    "KikobotLeaderConfig",
    "KikobotBimanualConfig",
]
