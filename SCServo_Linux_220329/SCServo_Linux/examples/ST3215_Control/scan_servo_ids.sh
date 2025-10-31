#!/bin/bash
# Scan for ST3215 servo on different IDs
# Usage: sudo ./scan_servo_ids.sh [port]

PORT="${1:-/dev/ttyACM0}"

echo "═══════════════════════════════════════════════════════════"
echo "🔍 Scanning for ST3215 Servos on $PORT"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Scanning IDs 1-7 (Joints 1-6 + Gripper)..."
echo ""

FOUND=0
FOUND_IDS=()

for ID in {1..7}; do
    echo -n "Testing ID $ID... "
    
    # Run ping and capture output
    OUTPUT=$(./build/Ping/Ping "$PORT" "$ID" 2>&1)
    
    if echo "$OUTPUT" | grep -q "SUCCESS"; then
        echo "✓ FOUND!"
        FOUND=$((FOUND + 1))
        FOUND_IDS+=($ID)
    else
        echo "✗ No response"
    fi
done

echo ""
echo "═══════════════════════════════════════════════════════════"

if [ $FOUND -eq 0 ]; then
    echo "❌ No servos found on IDs 1-7"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check servo power (12V DC connected and ON)"
    echo "  2. Check USB cable connection"
    echo "  3. Try different baud rates (servo might be configured differently)"
    echo "  4. Check if device is at different port:"
    echo "     ls -l /dev/ttyACM* /dev/ttyUSB*"
    echo ""
else
    echo "✅ Found $FOUND servo(s): ${FOUND_IDS[@]}"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    echo "Servo Mapping:"
    echo "  IDs 1-6: Joint servos (J1-J6)"
    echo "  ID 7:    Gripper servo"
    echo ""
    echo "Usage examples:"
    echo "  # Test specific servo"
    echo "  sudo ./build/Ping/Ping $PORT <ID>"
    echo ""
    echo "  # Monitor specific servo"
    echo "  sudo ./build/FeedBack/FeedBack $PORT <ID>"
    echo ""
    echo "  # Home all 7 servos (joints + gripper)"
    echo "  sudo ./build/HomeAll/HomeAll $PORT"
    echo ""
fi
