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
Kikobot Dataset Recording for LeRobot

This script records demonstration datasets using leader-follower teleoperation.
The data is saved in LeRobot format and can be used for training imitation
learning policies.

Usage:
    python record_dataset.py --repo-id my_username/kikobot_demos --episode-index 0

Features:
    - Records leader positions (actions) and follower observations
    - Synchronized timestamps for all data
    - Optional camera images
    - Episode-based recording with automatic indexing
    - LeRobot-compatible dataset format

Controls:
    - Press 'r' to start recording an episode
    - Press 's' to stop and save the episode
    - Press 'q' to quit
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from robots.kikobot import (
    KikobotFollower,
    KikobotFollowerConfig,
    KikobotLeader,
    KikobotLeaderConfig,
)

try:
    from lerobot.common.datasets.lerobot_dataset import LeRobotDataset
    from lerobot.common.datasets.push_dataset_to_hub.utils import save_episode
except ImportError:
    logger.error("LeRobot dataset utilities not found. Install with: pip install lerobot[feetech]")
    sys.exit(1)

import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KikobotDatasetRecorder:
    """
    Dataset recorder for Kikobot leader-follower teleoperation.
    
    Records demonstrations in LeRobot format for training imitation learning policies.
    """
    
    def __init__(
        self,
        repo_id: str,
        leader_port: str = "/dev/ttyACM1",
        follower_port: str = "/dev/ttyACM0",
        frequency: float = 50.0,
        root: str | Path = "data",
    ):
        """
        Initialize the dataset recorder.
        
        Args:
            repo_id: Dataset repository ID (e.g., 'username/kikobot_demos')
            leader_port: Serial port for leader arm
            follower_port: Serial port for follower arm
            frequency: Recording frequency in Hz
            root: Root directory for dataset storage
        """
        self.repo_id = repo_id
        self.frequency = frequency
        self.dt = 1.0 / frequency
        self.root = Path(root)
        
        # Create robot configurations
        logger.info("Creating robot configurations...")
        self.leader_config = KikobotLeaderConfig(
            port=leader_port,
            use_degrees=True,
            position_smoothing_alpha=0.3,
        )
        
        self.follower_config = KikobotFollowerConfig(
            port=follower_port,
            use_degrees=True,
            max_relative_target=30.0,
        )
        
        # Create robot instances
        logger.info("Creating robot instances...")
        self.leader = KikobotLeader(self.leader_config)
        self.follower = KikobotFollower(self.follower_config)
        
        # Recording state
        self.is_connected = False
        self.is_recording = False
        self.current_episode = []
        self.episode_index = 0
        
        # Dataset
        self.dataset = None

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
            
            # Connect follower arm
            logger.info("\n2. Connecting to FOLLOWER arm...")
            self.follower.connect(calibrate=calibrate)
            logger.info(f"   ✓ Follower connected on {self.follower_config.port}")
            
            self.is_connected = True
            
            logger.info("\n" + "="*60)
            logger.info("✓ Both arms connected successfully!")
            logger.info("="*60 + "\n")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            self.disconnect()
            return False

    def initialize_dataset(self) -> None:
        """Initialize or load the LeRobot dataset."""
        try:
            # Try to load existing dataset
            self.dataset = LeRobotDataset(
                repo_id=self.repo_id,
                root=self.root,
            )
            logger.info(f"Loaded existing dataset: {self.repo_id}")
            logger.info(f"  Episodes: {len(self.dataset.episode_data_index)}")
            self.episode_index = len(self.dataset.episode_data_index)
        except Exception:
            # Create new dataset
            logger.info(f"Creating new dataset: {self.repo_id}")
            
            # Define features based on robot configuration
            features = {}
            
            # Add motor features
            for motor in self.follower.bus.motors:
                features[f"{motor}.pos"] = {
                    "dtype": "float32",
                    "shape": (1,),
                    "names": None,
                }
            
            # TODO: Add camera features if configured
            # for cam_name in self.follower_config.cameras:
            #     cam_config = self.follower_config.cameras[cam_name]
            #     features[cam_name] = {
            #         "dtype": "uint8",
            #         "shape": (cam_config.height, cam_config.width, 3),
            #         "names": ["height", "width", "channel"],
            #     }
            
            self.dataset = LeRobotDataset.create(
                repo_id=self.repo_id,
                root=self.root,
                fps=self.frequency,
                features=features,
            )
            logger.info("✓ New dataset created")

    def start_episode(self) -> None:
        """Start recording a new episode."""
        if self.is_recording:
            logger.warning("Already recording! Stop current episode first.")
            return
        
        self.current_episode = []
        self.is_recording = True
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🔴 RECORDING Episode {self.episode_index}")
        logger.info(f"{'='*60}")
        logger.info("Move the leader arm to demonstrate the task.")
        logger.info("Press 's' to stop and save, 'q' to discard.\n")

    def stop_episode(self, save: bool = True) -> None:
        """
        Stop recording and optionally save the episode.
        
        Args:
            save: If True, save the episode to dataset
        """
        if not self.is_recording:
            logger.warning("Not currently recording!")
            return
        
        self.is_recording = False
        
        if not save or len(self.current_episode) == 0:
            logger.info("Episode discarded.")
            self.current_episode = []
            return
        
        logger.info(f"\n{'='*60}")
        logger.info(f"⏹ Saving Episode {self.episode_index}")
        logger.info(f"{'='*60}")
        logger.info(f"  Frames: {len(self.current_episode)}")
        logger.info(f"  Duration: {len(self.current_episode) / self.frequency:.2f} seconds")
        
        try:
            # Convert episode data to LeRobot format
            episode_data = {
                "observation": {},
                "action": {},
                "episode_index": np.full(len(self.current_episode), self.episode_index),
                "frame_index": np.arange(len(self.current_episode)),
                "timestamp": np.array([frame["timestamp"] for frame in self.current_episode]),
            }
            
            # Extract observations and actions
            for key in self.current_episode[0]["observation"].keys():
                episode_data["observation"][key] = np.array([
                    frame["observation"][key] for frame in self.current_episode
                ])
            
            for key in self.current_episode[0]["action"].keys():
                episode_data["action"][key] = np.array([
                    frame["action"][key] for frame in self.current_episode
                ])
            
            # Add to dataset
            save_episode(
                episode_data,
                episode_index=self.episode_index,
                dataset=self.dataset,
            )
            
            logger.info(f"✓ Episode {self.episode_index} saved successfully!")
            logger.info(f"{'='*60}\n")
            
            self.episode_index += 1
            self.current_episode = []
            
        except Exception as e:
            logger.error(f"Failed to save episode: {e}")
            self.current_episode = []

    def record_frame(self) -> None:
        """Record a single frame of data."""
        try:
            # Get current timestamp
            timestamp = time.time()
            
            # Read leader arm position (this becomes the action)
            leader_obs = self.leader.get_observation()
            action = {
                key: value for key, value in leader_obs.items()
                if key.endswith('.pos')
            }
            
            # Read follower arm observation
            follower_obs = self.follower.get_observation()
            observation = {
                key: value for key, value in follower_obs.items()
            }
            
            # Send action to follower (mirror leader)
            self.follower.send_action(action)
            
            # Store frame
            frame = {
                "timestamp": timestamp,
                "observation": observation,
                "action": action,
            }
            self.current_episode.append(frame)
            
        except Exception as e:
            logger.error(f"Error recording frame: {e}")

    def run_interactive(self) -> None:
        """
        Run interactive recording session.
        
        Allows user to control recording with keyboard input.
        """
        if not self.is_connected:
            logger.error("Not connected! Call connect() first.")
            return
        
        # Initialize dataset
        self.initialize_dataset()
        
        logger.info("="*60)
        logger.info("Interactive Dataset Recording")
        logger.info("="*60)
        logger.info("\nControls:")
        logger.info("  'r' - Start recording episode")
        logger.info("  's' - Stop and save episode")
        logger.info("  'd' - Discard current episode")
        logger.info("  'q' - Quit")
        logger.info("\nReady to record. Type a command and press ENTER.\n")
        logger.info("="*60 + "\n")
        
        # Note: For true interactive control, you'd want to use threading
        # or asyncio to handle keyboard input while recording.
        # This simplified version uses a command prompt between episodes.
        
        try:
            while True:
                if not self.is_recording:
                    # Wait for user command
                    cmd = input("\nCommand (r/s/d/q): ").strip().lower()
                    
                    if cmd == 'r':
                        self.start_episode()
                        # Record for a fixed duration or until stopped
                        self._record_until_stopped()
                    elif cmd == 'q':
                        logger.info("Quitting...")
                        break
                    elif cmd == 's':
                        logger.warning("Not recording. Use 'r' to start.")
                    else:
                        logger.warning(f"Unknown command: {cmd}")
        
        except KeyboardInterrupt:
            logger.info("\n\nKeyboard interrupt received.")
        
        finally:
            if self.is_recording:
                logger.info("\nStopping current episode...")
                user_input = input("Save episode? (y/n): ").strip().lower()
                self.stop_episode(save=(user_input == 'y'))

    def _record_until_stopped(self) -> None:
        """Record frames until user stops."""
        logger.info("\nRecording... Press Ctrl+C to stop.")
        
        try:
            while self.is_recording:
                start_time = time.perf_counter()
                
                self.record_frame()
                
                # Maintain frequency
                elapsed = time.perf_counter() - start_time
                sleep_time = self.dt - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
                # Log progress
                if len(self.current_episode) % 50 == 0:
                    logger.info(f"  Frames: {len(self.current_episode)}")
        
        except KeyboardInterrupt:
            logger.info("\n\nStopping episode...")
            user_input = input("Save episode? (y/n): ").strip().lower()
            self.stop_episode(save=(user_input == 'y'))

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
    """Main entry point for dataset recording script."""
    parser = argparse.ArgumentParser(
        description="Kikobot Dataset Recording for LeRobot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Record dataset with default settings
  python record_dataset.py --repo-id username/kikobot_demos
  
  # Record with custom ports
  python record_dataset.py --repo-id username/kikobot_demos \\
      --leader-port /dev/ttyUSB1 --follower-port /dev/ttyUSB0
  
  # Record at 30 Hz
  python record_dataset.py --repo-id username/kikobot_demos --frequency 30

The dataset will be saved in LeRobot format and can be used for training.
        """
    )
    
    parser.add_argument(
        "--repo-id",
        type=str,
        required=True,
        help="Dataset repository ID (e.g., 'username/kikobot_demos')"
    )
    
    parser.add_argument(
        "--root",
        type=str,
        default="data",
        help="Root directory for dataset storage (default: data)"
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
        help="Recording frequency in Hz (default: 50)"
    )
    
    parser.add_argument(
        "--calibrate",
        action="store_true",
        help="Run calibration if needed"
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
    
    # Create recorder
    recorder = KikobotDatasetRecorder(
        repo_id=args.repo_id,
        leader_port=args.leader_port,
        follower_port=args.follower_port,
        frequency=args.frequency,
        root=args.root,
    )
    
    # Connect to robots
    if not recorder.connect(calibrate=args.calibrate):
        logger.error("Failed to connect to robots. Exiting.")
        return 1
    
    # Run interactive recording
    try:
        recorder.run_interactive()
    finally:
        recorder.disconnect()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
