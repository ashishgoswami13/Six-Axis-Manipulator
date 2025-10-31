# Smooth Movement & Continuous Teaching Guide

This guide covers the improved teaching modes for your 7-DOF robotic arm.

## 🆕 What's New

### 1. **Smooth Motion in TeachMode** 
The original TeachMode now uses smoother acceleration and deceleration:
- **Reduced speed**: 800 steps/sec (was 1500) for gentler movements
- **Increased acceleration**: 100 (was 50) for smoother curves
- **Result**: Less jerky, more fluid playback

### 2. **ContinuousTeach** - New Fluid Recording Mode
A completely new program that records continuously rather than using discrete waypoints:
- **High-frequency sampling**: Records positions every 100ms (10 Hz) by default
- **Automatic recording**: No need to press Enter for each waypoint
- **Adaptive playback**: Speed adjusts based on movement complexity
- **Smoother trajectories**: Captures subtle movements and flows

---

## 📊 Comparison: TeachMode vs ContinuousTeach

| Feature | TeachMode | ContinuousTeach |
|---------|-----------|-----------------|
| **Recording style** | Manual waypoints (press Enter) | Continuous auto-sampling |
| **Best for** | Simple pick-place, defined poses | Complex fluid motions |
| **Sample rate** | User-controlled (when Enter pressed) | Fixed interval (default 100ms) |
| **File size** | Small (few waypoints) | Larger (many samples) |
| **Playback** | Point-to-point with delays | Continuous smooth flow |
| **Precision** | High (exact positions saved) | High temporal resolution |

---

## 🎯 When to Use Each Mode

### Use **TeachMode** for:
- ✅ Pick-and-place operations
- ✅ Assembly tasks with specific positions
- ✅ Inspection points
- ✅ Simple repetitive motions
- ✅ When you need small file sizes

### Use **ContinuousTeach** for:
- ✅ Painting or drawing motions
- ✅ Welding paths
- ✅ Polishing or grinding
- ✅ Complex curved trajectories
- ✅ Demonstrations requiring fluidity
- ✅ Human-like smooth movements

---

## 🚀 Quick Start

### TeachMode (Waypoint-Based)

```bash
sudo ./build/TeachMode/TeachMode
```

**Workflow:**
1. Choose `r` to record
2. Move arm to position 1, press **Enter**
3. Move arm to position 2, press **Enter**
4. Continue for all waypoints
5. Type `q` and press **Enter** when done
6. Choose `p` to playback

**Movement is now smoother with reduced jerk!**

---

### ContinuousTeach (Fluid Recording)

```bash
sudo ./build/ContinuousTeach/ContinuousTeach
```

**Workflow:**
1. Choose `r` to record
2. Move arm to starting position
3. Press **Enter** to start recording
4. Smoothly move the arm through your desired trajectory
5. Press `q` when done
6. Choose `p` to playback

**Tips for best results:**
- Move slowly and smoothly during recording
- Avoid sudden jerks or stops
- The robot will replay exactly what you demonstrated

---

## ⚙️ Advanced Usage

### Custom Sample Rate (ContinuousTeach)

For very fast movements, use higher sampling:
```bash
sudo ./build/ContinuousTeach/ContinuousTeach /dev/ttyACM0 50
```
- `50` = 50ms interval = 20 Hz sampling
- Lower interval = more samples = smoother but larger files

For slower movements or to save memory:
```bash
sudo ./build/ContinuousTeach/ContinuousTeach /dev/ttyACM0 200
```
- `200` = 200ms interval = 5 Hz sampling

### File Management

**Save your recording:**
```
Menu: s
Filename: my_trajectory.txt
```

**Load a recording:**
```
Menu: o
Filename: my_trajectory.txt
```

**View trajectory info:**
```
Menu: i
```
Shows: samples, duration, sample rate, memory usage

---

## 🎨 Motion Parameters Explained

### Speed (steps/sec)
- **Higher values** (e.g., 2400): Fast movement
- **Lower values** (e.g., 400-800): Smooth, gentle movement
- TeachMode uses 800 for smooth playback
- ContinuousTeach adapts: 600-1200 based on trajectory

### Acceleration (acc parameter)
- **Lower values** (e.g., 50): Slower acceleration, more abrupt
- **Higher values** (e.g., 100-150): Faster acceleration ramp, smoother curves
- TeachMode uses 100 for smoothness
- ContinuousTeach uses 80-150 adaptively

### How ContinuousTeach Adapts Speed:

```
Time between samples > 200ms  → speed=1200, acc=80  (medium)
Time between samples > 100ms  → speed=800,  acc=120 (slower, smoother)
Time between samples < 100ms  → speed=600,  acc=150 (very smooth)
Final position               → speed=400,  acc=150 (gentle stop)
```

This ensures smooth motion regardless of recording speed.

---

## 📝 Example Workflows

### Example 1: Simple Pick-and-Place (TeachMode)

```bash
sudo ./build/TeachMode/TeachMode
```

1. Record (`r`)
2. Home position → **Enter**
3. Above object → **Enter**
4. Grasp object → **Enter**
5. Lift object → **Enter**
6. Move to drop zone → **Enter**
7. Release → **Enter**
8. Return home → **Enter**
9. Quit (`q`)
10. Playback (`p`)

**Result:** 7 waypoints, smooth transitions, small file (~100 bytes)

---

### Example 2: Continuous Painting Motion (ContinuousTeach)

```bash
sudo ./build/ContinuousTeach/ContinuousTeach /dev/ttyACM0 50
```

1. Record (`r`)
2. Move to canvas start position
3. Press **Enter** to start recording
4. Slowly paint a curve or pattern
5. Press `q` when finished
6. Save (`s`) → `painting_pattern.txt`
7. Playback (`p`)

**Result:** 60 samples for 3 seconds, very smooth curve, ~2KB file

---

## 🔧 Troubleshooting

### Movements still too jerky?

**In TeachMode:**
- Edit `/examples/ST3215_Control/TeachMode/TeachMode.cpp`
- Line ~194: Reduce `speed` further (try 600 or 400)
- Line ~195: Increase `acc` (try 120 or 150)
- Rebuild: `cd build/TeachMode && make`

**In ContinuousTeach:**
- Use faster sampling: `./ContinuousTeach /dev/ttyACM0 50`
- Move more slowly during recording
- Adjust speed ranges in code (lines 179-194)

### Playback too slow?

Increase speed values while keeping high acceleration for smoothness.

### Recording captures too many samples?

Use longer interval: `./ContinuousTeach /dev/ttyACM0 200`

---

## 📊 Performance Metrics

### Memory Usage:
- **Waypoint** (TeachMode): ~60 bytes per waypoint
- **Sample** (ContinuousTeach): ~64 bytes per sample

**Example:**
- 10-second recording at 100ms interval = 100 samples = ~6.4 KB
- 10-second recording at 50ms interval = 200 samples = ~12.8 KB

### Recommended Settings:

| Application | Interval | Expected Samples/10s | File Size/10s |
|-------------|----------|---------------------|---------------|
| Slow precise work | 200ms | 50 | ~3 KB |
| General use | 100ms | 100 | ~6 KB |
| Fast smooth motion | 50ms | 200 | ~12 KB |
| High-speed capture | 25ms | 400 | ~25 KB |

---

## 🎓 Best Practices

### For Smooth Recordings:
1. **Move slowly** during teaching - robot can't move faster than you taught it
2. **Use continuous mode** for curved paths
3. **Use waypoint mode** for angular movements
4. **Practice first** - do a dry run without recording
5. **Start and end gently** - ContinuousTeach automatically slows at endpoints

### For Reliable Playback:
1. **Test with loop mode** (`l`) to verify repeatability
2. **Save trajectories** after successful recording
3. **Use descriptive filenames** (`welding_seam_1.txt`)
4. **Keep a library** of common trajectories
5. **Check joint limits** - HomeAll respects limits, teaching modes don't enforce them during recording

---

## 🔄 Building from Source

After any changes to the code:

```bash
cd /home/dev/Downloads/SCServo_Linux/SCServo_Linux_220329/SCServo_Linux/examples/ST3215_Control
./build_all.sh
```

Or build individually:
```bash
cd build/TeachMode && cmake ../../TeachMode && make
cd ../ContinuousTeach && cmake ../../ContinuousTeach && make
```

---

## 🎯 Summary

- ✅ **TeachMode**: Updated with smoother motion (speed=800, acc=100)
- ✅ **ContinuousTeach**: New program for fluid trajectory capture
- ✅ **Adaptive playback**: Speed automatically adjusts for smoothness
- ✅ **Both built and ready** to use!

**Get started now:**
```bash
cd /home/dev/Downloads/SCServo_Linux/SCServo_Linux_220329/SCServo_Linux/examples/ST3215_Control
sudo ./build/TeachMode/TeachMode          # Waypoint mode
sudo ./build/ContinuousTeach/ContinuousTeach  # Continuous mode
```

Enjoy your smooth robotic movements! 🤖✨
