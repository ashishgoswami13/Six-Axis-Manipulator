#!/usr/bin/env python3
"""
Servo Scanner and ID Changer

Helps identify all servos on the bus and change their IDs
"""

import time
import serial

# Serial port settings
DEVICENAME = '/dev/ttyACM0'
BAUDRATE = 1000000

# Protocol constants
INST_PING = 0x01
INST_READ = 0x02
INST_WRITE = 0x03
INST_REG_WRITE = 0x04
INST_ACTION = 0x05
INST_SYNC_WRITE = 0x83

# Register addresses
SMS_STS_ID = 5

class ServoScanner:
    def __init__(self):
        self.serial = None
        
    def connect(self):
        """Connect to serial port"""
        try:
            self.serial = serial.Serial(DEVICENAME, BAUDRATE, timeout=0.01)
            print(f"✓ Opened port {DEVICENAME} at {BAUDRATE} baud")
            time.sleep(0.1)
            return True
        except Exception as e:
            print(f"❌ Failed to open port: {e}")
            return False
    
    def checksum(self, data):
        """Calculate checksum"""
        return (~sum(data)) & 0xFF
    
    def write_packet(self, servo_id, instruction, params=None):
        """Write packet to servo"""
        if params is None:
            params = []
        
        length = len(params) + 2
        packet = [0xFF, 0xFF, servo_id, length, instruction] + params
        packet.append(self.checksum(packet[2:]))
        
        self.serial.write(bytes(packet))
        return True
    
    def read_packet(self):
        """Read response packet"""
        # Look for header
        while True:
            b = self.serial.read(1)
            if not b or b[0] != 0xFF:
                continue
            b = self.serial.read(1)
            if not b or b[0] != 0xFF:
                continue
            break
        
        # Read ID, length, error
        header = self.serial.read(3)
        if len(header) < 3:
            return None
        
        servo_id, length, error = header
        
        # Read parameters and checksum
        remaining = length - 2
        data = self.serial.read(remaining + 1)
        if len(data) < remaining + 1:
            return None
        
        params = list(data[:remaining])
        checksum = data[remaining]
        
        return {'id': servo_id, 'error': error, 'params': params}
    
    def ping(self, servo_id):
        """Ping a servo"""
        self.serial.flushInput()
        self.write_packet(servo_id, INST_PING)
        time.sleep(0.01)
        response = self.read_packet()
        return response is not None and response['id'] == servo_id
    
    def scan_all_servos(self, max_id=20, retries=2):
        """
        Scan for all servos on the bus
        
        Args:
            max_id: Maximum servo ID to scan
            retries: Number of retry attempts per ID
        """
        print(f"\nScanning servo IDs 1-{max_id}...")
        print(f"{'ID':<5} {'Status':<10}")
        print("-" * 20)
        
        found_servos = []
        
        for servo_id in range(1, max_id + 1):
            # Try pinging with retries
            success = False
            for attempt in range(retries):
                if self.ping(servo_id):
                    success = True
                    break
                time.sleep(0.01)
            
            if success:
                print(f"{servo_id:<5} {'✓ Online':<10}")
                found_servos.append(servo_id)
            else:
                print(f"{servo_id:<5} {'✗ Offline':<10}")
        
        print(f"\n✓ Found {len(found_servos)} servos: {found_servos}")
        return found_servos
    
    def change_servo_id(self, old_id, new_id):
        """
        Change a servo's ID
        
        Args:
            old_id: Current servo ID
            new_id: New servo ID to assign
        """
        print(f"\nChanging servo ID {old_id} → {new_id}...")
        
        # Verify servo exists
        if not self.ping(old_id):
            print(f"❌ Servo {old_id} not found")
            return False
        
        print(f"  ✓ Servo {old_id} detected")
        
        # Check if new ID is already in use
        if self.ping(new_id):
            print(f"  ⚠ Warning: ID {new_id} is already in use!")
            response = input("  Continue anyway? (y/n): ")
            if response.lower() != 'y':
                return False
        
        # Write new ID
        self.serial.flushInput()
        self.write_packet(old_id, INST_WRITE, [SMS_STS_ID, new_id])
        time.sleep(0.1)
        
        # Verify change
        if self.ping(new_id):
            print(f"✓ Successfully changed ID {old_id} → {new_id}")
            return True
        else:
            print(f"❌ Failed to verify new ID {new_id}")
            return False
    
    def batch_change_ids(self, mapping):
        """
        Change multiple servo IDs
        
        Args:
            mapping: Dictionary of {old_id: new_id}
        """
        print(f"\n{'='*60}")
        print("Batch ID Change")
        print(f"{'='*60}")
        
        for old_id, new_id in mapping.items():
            print(f"\nChanging {old_id} → {new_id}")
            if not self.change_servo_id(old_id, new_id):
                print(f"⚠ Skipping remaining changes")
                return False
            time.sleep(0.2)
        
        print(f"\n✓ All ID changes completed!")
        return True
    
    def disconnect(self):
        """Close serial port"""
        if self.serial:
            self.serial.close()
        print("\n✓ Disconnected")


def interactive_mode():
    """Interactive menu for servo management"""
    scanner = ServoScanner()
    
    if not scanner.connect():
        return
    
    found_servos = []
    
    while True:
        print(f"\n{'='*60}")
        print("Servo Scanner & ID Changer")
        print(f"{'='*60}")
        print("\nOptions:")
        print("  1. Scan all servos (IDs 1-20)")
        print("  2. Scan all servos (IDs 1-50)")
        print("  3. Change single servo ID")
        print("  4. Setup for leader-follower (2 robots)")
        print("  5. Reset all servos to sequential IDs (1-N)")
        print("  6. Exit")
        
        choice = input("\nSelect option (1-6): ").strip()
        
        if choice == '1':
            found_servos = scanner.scan_all_servos(max_id=20)
        
        elif choice == '2':
            found_servos = scanner.scan_all_servos(max_id=50)
        
        elif choice == '3':
            try:
                old_id = int(input("Enter current servo ID: "))
                new_id = int(input("Enter new servo ID: "))
                scanner.change_servo_id(old_id, new_id)
            except ValueError:
                print("❌ Invalid input")
        
        elif choice == '4':
            print("\nLeader-Follower Setup")
            print("This will configure 2 robots (14 servos total)")
            print("  Robot 1 (Leader): IDs 1-7")
            print("  Robot 2 (Follower): IDs 8-14")
            
            if not found_servos:
                print("\n⚠ Please scan servos first (option 1 or 2)")
                continue
            
            print(f"\nFound {len(found_servos)} servos: {found_servos}")
            
            if len(found_servos) < 14:
                print(f"⚠ Warning: Need 14 servos, found {len(found_servos)}")
                response = input("Continue anyway? (y/n): ")
                if response.lower() != 'y':
                    continue
            
            print("\nIdentify which robot is which:")
            print("1. Disconnect one robot temporarily")
            print("2. Scan to see which IDs remain (that's robot 1)")
            print("3. Reconnect both robots")
            
            response = input("\nReady to configure? (y/n): ")
            if response.lower() != 'y':
                continue
            
            # For now, assume first 7 found are robot 1, rest are robot 2
            if len(found_servos) >= 14:
                robot1_ids = found_servos[:7]
                robot2_ids = found_servos[7:14]
                
                print(f"\nRobot 1 (Leader): {robot1_ids}")
                print(f"Robot 2 (Follower): {robot2_ids}")
                
                # Create mapping for robot 2 to IDs 8-14
                mapping = {}
                for i, old_id in enumerate(robot2_ids):
                    new_id = i + 8
                    if old_id != new_id:
                        mapping[old_id] = new_id
                
                if mapping:
                    print(f"\nWill change: {mapping}")
                    response = input("Proceed? (y/n): ")
                    if response.lower() == 'y':
                        scanner.batch_change_ids(mapping)
                else:
                    print("\n✓ IDs already correctly configured")
        
        elif choice == '5':
            if not found_servos:
                print("\n⚠ Please scan servos first (option 1 or 2)")
                continue
            
            print(f"\nFound servos: {found_servos}")
            print(f"Will reassign to sequential IDs 1-{len(found_servos)}")
            
            response = input("Continue? (y/n): ")
            if response.lower() != 'y':
                continue
            
            # Create mapping
            mapping = {}
            for i, old_id in enumerate(found_servos):
                new_id = i + 1
                if old_id != new_id:
                    mapping[old_id] = new_id
            
            if mapping:
                print(f"\nWill change: {mapping}")
                response = input("Proceed? (y/n): ")
                if response.lower() == 'y':
                    scanner.batch_change_ids(mapping)
            else:
                print("\n✓ IDs already sequential")
        
        elif choice == '6':
            break
        
        else:
            print("❌ Invalid option")
    
    scanner.disconnect()


if __name__ == "__main__":
    try:
        interactive_mode()
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
