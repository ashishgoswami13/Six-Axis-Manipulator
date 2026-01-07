# 🤖 Kikobot LeRobot Integration

LeRobot integration for Kikobot 6-DOF robotic arm: teleoperation, dataset recording, and imitation learning policy training.

## Overview

Dual-arm setup for collecting demonstration data and training robot policies:
- **Leader arm** (manual, torque off) → provides demonstrations
- **Follower arm** (motorized, torque on) → executes actions or trained policies
- Supports **ACT**, **Diffusion Policy**, and **TDMPC** training

## Hardware

| Component | Port | Motors | Gripper | Mode |
|-----------|------|--------|---------|------|
| **Leader** | `/dev/ttyACM1` | 6 (IDs 1-6) | No | Manual (torque off) |
| **Follower** | `/dev/ttyACM0` | 7 (IDs 1-7) | Yes (ID 7) | Motorized (torque on) |

- Servos: Waveshare ST3215 (Feetech STS3215), 1M baud
- Control frequency: 50 Hz

## Installation

```bash
pip install -r requirements.txt
sudo usermod -a -G dialout $USER  # USB permissions
```

## Usage

### 1. Calibration
Establishes joint zero positions and ranges. **Required before first use.**

```bash
python teleoperate_kikobot.py --calibrate-only
```

Saves calibration to `~/.cache/lerobot/calibration/kikobot_{leader,follower}.json`

### 2. Teleoperation
Leader-follower real-time mirroring at 50 Hz.

```bash
python teleoperate_kikobot.py
```

**Controls:** Move leader manually, follower mirrors. Arrow keys: `↑↓` gripper open/close (±5%), `←→` fine adjust (±1%)

### 3. Dataset Recording
Records demonstrations in LeRobot HDF5 format for policy training.

```bash
python record_dataset.py --repo-id username/dataset_name --num-episodes 50
```

**Workflow:** Press `r` to start, demonstrate task, press `s` to save, `q` to quit

### 4. Policy Training
Train imitation learning policies on collected demonstrations.

**ACT (Action Chunking Transformer)** - Good for sequential tasks:
```bash
python -m lerobot.scripts.train \
    policy=act \
    dataset_repo_id=username/dataset_name \
    training.offline_steps=50000 \
    device=cuda
```

**Diffusion Policy** - Good for dexterous manipulation:
```bash
python -m lerobot.scripts.train \
    policy=diffusion \
    dataset_repo_id=username/dataset_name \
    training.offline_steps=50000 \
    device=cuda
```

**TDMPC** - Model-based approach:
```bash
python -m lerobot.scripts.train \
    policy=tdmpc \
    dataset_repo_id=username/dataset_name \
    device=cuda
```

**Key training options:**
- `policy.chunk_size=100` - Action prediction horizon (ACT)
- `training.batch_size=8` - Batch size (adjust for GPU memory)
- `training.lr=1e-4` - Learning rate
- `wandb.enable=true` - Enable experiment tracking

### 5. Policy Deployment
Run trained policy on robot hardware.

```python
# Load policy and run on follower arm
from lerobot.common.policies.factory import make_policy
from robots.kikobot import KikobotFollower, KikobotFollowerConfig

policy = make_policy("outputs/train/.../checkpoints/050000", device="cuda")
robot = KikobotFollower(KikobotFollowerConfig(port="/dev/ttyACM0"))
robot.connect()

# Policy loop: observation → policy → action → robot
```

## Troubleshooting

**Arms won't connect:**
```bash
ls /dev/ttyACM*  # Check ports exist
sudo usermod -a -G dialout $USER  # Fix permissions, then logout/login
```

**Calibration fails:** Delete `~/.cache/lerobot/calibration/kikobot_*.json` and recalibrate

**Jerky movement:** Increase `position_smoothing_alpha` (leader) or lower `p_coefficient` (follower)

**Training issues:**
- CUDA OOM: Reduce `training.batch_size`
- Loss not decreasing: Need 50-100 quality episodes, check data consistency
- Dataset not found: Verify path with `ls -la data/username/dataset_name/`

## Files

```
lerobot_integration/
├── robots/kikobot/          # Robot implementations
│   ├── config_kikobot.py    # Configuration classes
│   ├── kikobot_leader.py    # Leader arm (input device)
│   └── kikobot_follower.py  # Follower arm (control)
└── scripts/
    ├── teleoperate_kikobot.py   # Teleoperation & calibration
    ├── record_dataset.py        # Dataset recording
    └── examples.py              # Code examples
```

## Resources

- [LeRobot Documentation](https://github.com/huggingface/lerobot)
- [ACT Paper](https://arxiv.org/abs/2304.13705) - Transformer-based action chunking
- [Diffusion Policy Paper](https://arxiv.org/abs/2303.04137) - Diffusion models for manipulation

---

**Quick Start:** `python teleoperate_kikobot.py --calibrate-only` → `python record_dataset.py --repo-id user/dataset` → Train policy → Deploy! 🚀