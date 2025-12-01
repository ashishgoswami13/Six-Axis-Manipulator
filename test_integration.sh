#!/bin/bash
# Test VLA Robot Integration (Safe Mode)

echo "=================================="
echo "VLA Robot Integration - Test Suite"
echo "=================================="
echo ""

# Test 1: Robot Controller
echo "[Test 1/3] Testing Robot Controller..."
echo "This will connect to the robot and read positions"
python3 robot_controller.py
if [ $? -eq 0 ]; then
    echo "✓ Robot controller test passed"
else
    echo "✗ Robot controller test failed"
fi
echo ""

# Test 2: Action Transformer
echo "[Test 2/3] Testing Action Transformer..."
python3 action_transformer.py
if [ $? -eq 0 ]; then
    echo "✓ Action transformer test passed"
else
    echo "✗ Action transformer test failed"
fi
echo ""

# Test 3: VLA Controller (Visualization Mode - SAFE)
echo "[Test 3/3] Testing VLA Controller (Visualization Mode)..."
echo "This will run OpenVLA inference but NOT move the robot"
echo "Press Ctrl+C after testing a few commands"
echo ""
python3 vla_robot_controller.py --mode visualization --interactive

echo ""
echo "=================================="
echo "Test Suite Complete!"
echo "=================================="
echo ""
echo "Next Steps:"
echo "1. If all tests passed, you're ready for Phase 3 calibration"
echo "2. To run with actual robot: python3 vla_robot_controller.py --mode live --interactive"
echo "   (WARNING: This will move the robot!)"
echo ""
