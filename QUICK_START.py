#!/usr/bin/env python3
"""
Quick Start Guide for VLA Robot Integration

Run this to see available commands and test the system
"""

print("""
╔═══════════════════════════════════════════════════════════════════╗
║           VLA ROBOT INTEGRATION - QUICK START GUIDE               ║
╔═══════════════════════════════════════════════════════════════════╝

📋 WHAT YOU'VE BUILT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ robot_controller.py     - Low-level robot control interface
✅ action_transformer.py   - VLA action → robot joint transformer
✅ vla_robot_controller.py - Main integration (Camera→VLA→Robot)
✅ URDF specifications      - Exact robot kinematics and limits
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 CURRENT STATUS: Phase 2 Complete → Ready for Phase 3 Calibration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 STEP-BY-STEP TESTING:

1️⃣  TEST ROBOT CONNECTION (Safe - No Movement)
   └─ python3 robot_controller.py
      • Pings all servos
      • Reads current positions
      • Tests safety checks

2️⃣  TEST ACTION TRANSFORMER (Pure Math - No Hardware)
   └─ python3 action_transformer.py
      • Tests coordinate transformations
      • Shows sample joint mappings
      • Validates scaling factors

3️⃣  TEST VLA INFERENCE ONLY (Safe - No Robot)
   └─ python3 vla_robot_controller.py --mode visualization --interactive
      • Captures camera images
      • Runs OpenVLA predictions
      • Shows what actions would be sent
      • NO ROBOT MOTION - completely safe!
      
      Try these commands:
      - "move forward"
      - "move left"
      - "move up"
      - "close the gripper"
      - "pick up the red block"

4️⃣  TEST WITH REAL ROBOT (⚠️  CAREFUL!)
   └─ python3 vla_robot_controller.py --mode live --interactive
      • ⚠️  ROBOT WILL ACTUALLY MOVE
      • Clear workspace first
      • Keep emergency stop ready
      • Start with small commands: "move up slightly"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🛠️  USEFUL COMMANDS:

Test Everything (Automated):
  └─ ./test_integration.sh

Manual Robot Control (Existing GUI):
  └─ ./launch_gui.sh

Emergency Stop (if robot connected):
  └─ python3 -c "from robot_controller import RobotController; r=RobotController(); r.connect(); r.emergency_stop()"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 WHAT TO EXPECT:

Inference Time:  ~150ms (OpenVLA on AGX Orin)
Control Rate:    ~5 Hz (realistic maximum)
Safety Checks:   ✓ Joint limits enforced
                 ✓ Max movement per step limited
                 ✓ Emergency stop available

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  IMPORTANT NOTES:

1. ALWAYS test in visualization mode first!
2. Action scaling factors are UNCALIBRATED initial guesses
3. Phase 3 (next): Calibrate these factors based on actual robot behavior
4. Document results in Modified_VLA_Tutor_Prompt.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 ROBOT SPECIFICATIONS (From URDF):

Total DOF:       7 (6 arm joints + 1 gripper)
Total Reach:     ~450mm
Base Height:     137.8mm
Main Links:      147mm (shoulder), 147mm (elbow)

Joint Limits:
  J1 (Base):     ±165°
  J2 (Shoulder): -100° to +150°
  J3 (Elbow):    ±140°
  J4-6 (Wrist):  ±140° to ±175°
  J7 (Gripper):  ±180°

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎓 NEXT PHASE: CALIBRATION

Goal: Get coordinate frames aligned so "move left" actually moves left!

Process:
1. Run baseline tests in visualization mode
2. Observe which joints move for each direction
3. Test with real robot (carefully!)
4. Adjust scaling factors in action_transformer.py
5. Repeat until all directions work correctly

See Modified_VLA_Tutor_Prompt.md for detailed calibration guide.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✨ YOU'RE READY TO START TESTING!

Begin with: python3 robot_controller.py

╚═══════════════════════════════════════════════════════════════════╝
""")
