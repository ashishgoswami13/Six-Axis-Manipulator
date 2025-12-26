# Kikobot LeRobot Integration

Leader-follower teleoperation system for Kikobot 6-DOF robot arms with LeRobot framework.

## Hardware Configuration

- **Leader Arm** (`/dev/ttyACM1`): 6 motors (IDs 1-6), no gripper - manually movable
- **Follower Arm** (`/dev/ttyACM0`): 7 motors (IDs 1-7), includes gripper - motorized

## Commands

### Calibration

Calibrate both arms (required before first use):
```bash
cd lerobot_integration/scripts
python teleoperate_kikobot.py --calibrate-only
```
**Action:** Connects to both arms, displays current positions, guides through calibration workflow, saves calibration data, then exits.

**Steps:**
1. Type `c` when prompted for each arm
2. Position arms in upright (home) position when asked
3. Move each joint through full range of motion when prompted

---

### Teleoperation

Start leader-follower teleoperation with manual gripper control:
```bash
cd lerobot_integration/scripts
python teleoperate_kikobot.py
```
**Action:** Starts real-time mirroring at 50 Hz. Follower arm copies leader arm movements. Gripper controlled via keyboard.

**Controls:**
- Move leader arm manually → Follower mirrors
- `↑` UP arrow: Open gripper (+5%)
- `↓` DOWN arrow: Close gripper (-5%)  
- `→` RIGHT arrow: Fine open (+1%)
- `←` LEFT arrow: Fine close (-1%)
- `Ctrl+C`: Stop teleoperation

---

### Dataset Recording

Record demonstration dataset for imitation learning:
```bash
cd lerobot_integration/scripts
python record_dataset.py --repo-id my_robot_dataset --num-episodes 50
```
**Action:** Records teleoperation episodes with timestamps, saves to LeRobot dataset format.

**Options:**
- `--repo-id`: Dataset name (required)
- `--num-episodes`: Number of episodes to record (default: 50)
- `--fps`: Recording frequency in Hz (default: 30)
- `--warmup-time`: Seconds before recording starts (default: 3)

---

## Files

- `robots/kikobot/` - Robot implementation classes
  - `config_kikobot.py` - Configuration dataclasses
  - `kikobot_leader.py` - Leader arm (manual input)
  - `kikobot_follower.py` - Follower arm (motorized control)
- `scripts/` - Executable scripts
  - `teleoperate_kikobot.py` - Leader-follower teleoperation
  - `record_dataset.py` - Dataset recording for ML
  - `examples.py` - Usage examples

---

## Calibration Files

Located in `~/.cache/lerobot/calibration/`:
- `kikobot_leader.json` - Leader arm calibration
- `kikobot_follower.json` - Follower arm calibration

To recalibrate, delete these files and run `--calibrate-only` again.

---

## Troubleshooting

**Arms won't connect:**
- Check USB connections: Leader=ACM1, Follower=ACM0
- Verify servo power supply is on
- Run: `ls /dev/ttyACM*` to confirm ports

**Calibration errors:**
- Ensure both arms are powered and connected
- Check all servo cables are properly seated
- Verify servo IDs are correct (Leader: 1-6, Follower: 1-7)

**Teleoperation not working:**
- Run calibration first: `--calibrate-only`
- Check that calibration files exist
- Ensure leader arm moves freely (torque disabled)
- Verify follower arm has torque enabled

---

## Quick Start

```bash
# 1. First time setup - calibrate both arms
python teleoperate_kikobot.py --calibrate-only

# 2. Start teleoperation
python teleoperate_kikobot.py

# 3. Record dataset (optional)
python record_dataset.py --repo-id my_demos --num-episodes 10
```
