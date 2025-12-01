# Robot Arm Control Programs - Quick Reference

## 📂 Clean Directory Structure

```
ST3215_Control/
├── 🏠 Core Programs (Use These)
│   ├── HomeAll/          - Return to home position
│   ├── ReachObject/      - Move to object & grasp (multi-attempt with verification)
│   └── TestAlignment/    - Test camera-robot alignment
│
├── 🎓 Teaching & Recording
│   ├── ContinuousTeach/  - Record smooth continuous motion
│   └── TeachMode/        - Record discrete waypoints
│
├── 🎮 Manual Control
│   └── ManualControl/    - Keyboard-based control
│
├── 🔧 Diagnostic Tools
│   ├── Ping/             - Test servo connection
│   ├── FeedBack/         - Read servo status
│   └── WritePos/         - Simple position control
│
└── 📄 Documentation
    ├── README.md          - Full detailed guide
    ├── README_PROGRAMS.md - This file
    └── README_SMOOTH_TEACH.md - ContinuousTeach guide
```

## 🚀 Quick Start Commands

### 1. Test Connection
```bash
cd Ping/build
./Ping
```

### 2. Go Home
```bash
cd HomeAll/build
./HomeAll
```

### 3. Test Camera Alignment
```bash
cd TestAlignment/build
./TestAlignment
```

### 4. Teach a Grasp Motion
```bash
cd ContinuousTeach/build
./ContinuousTeach
# Choose option 1 to record
# Manually move robot through grasp motion
# Press 'q' to stop, save trajectory
```

### 5. Reach & Grasp Object
```bash
cd ReachObject/build
./ReachObject 15.5 35.0 35.0 3
# Arguments: J1 J2 J3 [attempts]
```

## ⚙️ System Configuration

**Default Settings:**
- Serial Port: `/dev/ttyACM0`
- Baud Rate: 1,000,000 bps
- Servo IDs: 1-6 (joints), 7 (gripper)
- Coordinate Transform: J1 + 90° offset

**Position System:**
- Range: 0-4095 steps (12-bit)
- Center: 2048 = 0°
- Resolution: ~0.088°/step

## 🎯 Recommended Workflow

1. **Initial Setup**
   - Build all programs: `./build_all.sh`
   - Test servos: `Ping/build/Ping`
   
2. **Camera-Robot Integration**
   - Home robot: `HomeAll/build/HomeAll`
   - Test alignment: `TestAlignment/build/TestAlignment`
   - Run VLM camera sync (see VLM/README.md)
   
3. **Teach Accurate Grasping**
   - Record motion: `ContinuousTeach/build/ContinuousTeach`
   - Analyze trajectory: `python VLM/analyze_trajectory.py`
   - Use learned positions
   
4. **Autonomous Grasping**
   - Detect objects: `python VLM/detect_and_reach.py`
   - Grasp with verification: `ReachObject/build/ReachObject`

## 🧹 Clean State

**Removed:**
- ❌ `build/` (duplicate directory)
- ❌ `Test/` (basic test program)
- ❌ Old VLM analysis files
- ❌ Temporary screenshots/videos

**Kept:**
- ✅ All functional programs
- ✅ Individual build directories
- ✅ Documentation
- ✅ Utility scripts

## 📚 More Information

- Full servo API: `README.md`
- ContinuousTeach details: `README_SMOOTH_TEACH.md`
- VLM integration: `../../../VLM/README.md`
