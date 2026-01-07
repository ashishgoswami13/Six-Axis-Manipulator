#!/usr/bin/env python3
"""Quick script to check which servos are on which port"""

import time
import serial

BAUDRATE = 1000000

# Protocol constants
INST_PING = 0x01

def calculate_checksum(data):
    """Calculate checksum for packet"""
    return (~sum(data)) & 0xFF

def create_ping_packet(servo_id):
    """Create a PING packet"""
    length = 2  # ID + Checksum
    packet = [0xFF, 0xFF, servo_id, length, INST_PING]
    checksum = calculate_checksum(packet[2:])
    packet.append(checksum)
    return bytes(packet)

def scan_port(port_name):
    print(f"\n{'='*60}")
    print(f"Scanning {port_name}")
    print(f"{'='*60}")
    
    try:
        ser = serial.Serial(port_name, BAUDRATE, timeout=0.01)
        print(f"✓ Port opened successfully")
    except Exception as e:
        print(f"✗ Failed to open {port_name}: {e}")
        return []
    
    print(f"\nScanning IDs 1-10...")
    
    found_ids = []
    for servo_id in range(1, 11):
        # Clear any pending data
        ser.reset_input_buffer()
        
        # Send ping packet
        ping_packet = create_ping_packet(servo_id)
        ser.write(ping_packet)
        
        # Wait for response
        time.sleep(0.005)
        
        # Check if we got a response
        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting)
            if len(response) >= 6:  # Valid response packet
                print(f"  ID {servo_id}: ✓ Found")
                found_ids.append(servo_id)
            else:
                print(f"  ID {servo_id}: ✗ Not found (invalid response)")
        else:
            print(f"  ID {servo_id}: ✗ Not found")
    
    ser.close()
    print(f"\nTotal servos found: {len(found_ids)}")
    print(f"IDs: {found_ids}")
    return found_ids

if __name__ == "__main__":
    acm0_servos = scan_port("/dev/ttyACM0")
    acm1_servos = scan_port("/dev/ttyACM1")
    
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"/dev/ttyACM0 (Follower): {len(acm0_servos)} servos - IDs {acm0_servos}")
    print(f"/dev/ttyACM1 (Leader):   {len(acm1_servos)} servos - IDs {acm1_servos}")
    print()
    
    if len(acm0_servos) == 6:
        print("⚠ WARNING: Follower arm only has 6 servos, but should have 7 (including gripper)")
        print("  Possible issues:")
        print("  - Gripper servo (ID 7) not connected/powered")
        print("  - Gripper servo cable unplugged")
        print("  - Gripper servo has wrong ID")
        print("  - Communication issue with gripper servo")
    
    if len(acm1_servos) == 6:
        print("✓ Leader arm has 6 servos (correct - no gripper)")
