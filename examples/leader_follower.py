#!/usr/bin/env python3
"""
Leader-Follower Robot Control

Two robots on same bus:
- Leader: No torque, manually movable
- Follower: Follows leader's movements in real-time
"""

import time
import json
from robot_controller import RobotController
from servo_limits_config import degrees_to_steps, steps_to_degrees

# Servo IDs for each robot
# Current detected: 1, 3, 5, 7 (both robots have same IDs - need to change one!)
LEADER_SERVO_IDS = [1, 2, 3, 4, 5, 6]       # Leader robot servo IDs (6 joints, no gripper)
FOLLOWER_SERVO_IDS = [8, 9, 10, 11, 12, 13, 14]  # Follower robot servo IDs (7 joints with gripper)

class LeaderFollowerController:
    def __init__(self):
        self.robot = RobotController()
        self.leader_positions = [0] * 6  # Leader has 6 joints (no gripper)
        self.follower_positions = [0] * 7  # Follower has 7 joints (with gripper)
        self.running = False
        self.gripper_position = 0.0  # Fixed gripper position for follower
        
        # Load home positions
        self.load_home_positions()
    
    def load_home_positions(self):
        """Load saved home positions for both robots"""
        try:
            with open('saved_positions.json', 'r') as f:
                data = json.load(f)
                
                # Convert from steps to degrees
                if 'home2' in data:
                    home2_steps = data['home2']
                    # Leader has 6 joints, take first 6
                    self.leader_home = [steps_to_degrees(s) for s in home2_steps[:6]]
                else:
                    self.leader_home = [0] * 6
                
                if 'Home' in data:
                    home_steps = data['Home']
                    self.follower_home = [steps_to_degrees(s) for s in home_steps[:7]]
                    # Store gripper position separately
                    if len(home_steps) >= 7:
                        self.gripper_position = steps_to_degrees(home_steps[6])
                else:
                    self.follower_home = [0] * 7
                
                print(f"✓ Loaded leader home (home2, 6 joints): {[f'{p:.1f}°' for p in self.leader_home]}")
                print(f"✓ Loaded follower home (Home, 7 joints): {[f'{p:.1f}°' for p in self.follower_home]}")
                print(f"  Follower gripper default: {self.gripper_position:.1f}°")
        except Exception as e:
            print(f"⚠ Warning: Could not load home positions: {e}")
            self.leader_home = [0] * 6
            self.follower_home = [0] * 7
    
    def connect(self):
        """Connect to serial bus"""
        if not self.robot.connect():
            print("❌ Failed to connect to robot")
            return False
        
        # Scan for all servos on bus (IDs 1-20)
        print("\nScanning all servos on bus (IDs 1-20)...")
        online_servos = []
        for servo_id in range(1, 21):
            if self.robot.ping(servo_id):
                online_servos.append(servo_id)
                print(f"  ✓ Servo {servo_id} online")
        
        print(f"\n✓ Found {len(online_servos)} total servos: {online_servos}")
        
        if len(online_servos) < 14:
            print(f"\n⚠ Warning: Expected 14 servos (2 robots × 7), found {len(online_servos)}")
            print("\nDetected servo groups:")
            
            # Try to auto-detect which IDs are which robot
            if len(online_servos) >= 7:
                print(f"  First 7: {online_servos[:7]}")
                if len(online_servos) >= 14:
                    print(f"  Second 7: {online_servos[7:14]}")
            
            response = input("\nContinue with detected servos? (y/n): ")
            if response.lower() != 'y':
                return False
            
            # Ask user to configure IDs
            print("\nCurrent configuration:")
            print(f"  Leader IDs: {LEADER_SERVO_IDS}")
            print(f"  Follower IDs: {FOLLOWER_SERVO_IDS}")
            print(f"\nUpdate the IDs in leader_follower.py if these don't match your setup.")
        
        # Check configured IDs
        leader_count = sum(1 for s in LEADER_SERVO_IDS if s in online_servos)
        follower_count = sum(1 for s in FOLLOWER_SERVO_IDS if s in online_servos)
        
        print(f"\nConfigured servo detection:")
        print(f"  Leader servos (IDs {LEADER_SERVO_IDS}): {leader_count}/6")
        print(f"  Follower servos (IDs {FOLLOWER_SERVO_IDS}): {follower_count}/7")
        
        if leader_count < 6 or follower_count < 7:
            print("\n⚠ Warning: Not all configured servos detected!")
            if len(online_servos) >= 4 and follower_count == 0:
                print("\n🔍 DIAGNOSIS: Both robots appear to have the same IDs!")
                print("   Detected IDs: " + str(online_servos))
                print("\n📝 TO FIX THIS:")
                print("   1. Disconnect the FOLLOWER robot (keep only LEADER connected)")
                print("   2. Run this program again to verify leader IDs")
                print("   3. Disconnect LEADER, connect only FOLLOWER")
                print("   4. Use option 5 to change follower IDs to 8-14")
                print("   5. Reconnect both robots")
        
        return True
    
    def set_leader_torque(self, enable=False):
        """Enable/disable torque on leader robot"""
        print(f"\n{'Enabling' if enable else 'Disabling'} torque on leader robot...")
        for servo_id in LEADER_SERVO_IDS:
            # Write to torque enable register (address 0x28, value 0=off, 1=on)
            self.robot.write_packet(servo_id, 0x03, [0x28, 1 if enable else 0])
            time.sleep(0.01)
        print(f"✓ Leader torque {'enabled' if enable else 'disabled'}")
    
    def read_leader_positions(self):
        """Read current positions from leader robot"""
        positions = []
        for servo_id in LEADER_SERVO_IDS:
            pos_steps = self.robot.read_position(servo_id)
            if pos_steps is not None:
                pos_deg = steps_to_degrees(pos_steps)
                positions.append(pos_deg)
            else:
                return None
        return positions
    
    def write_follower_positions(self, positions, speed=1500):
        """Write positions to follower robot"""
        for i, servo_id in enumerate(FOLLOWER_SERVO_IDS):
            if i < len(positions):
                steps = degrees_to_steps(positions[i])
                self.robot.write_position(servo_id, steps, speed=speed, acc=50)
    
    def move_to_home(self):
        """Move both robots to their home positions"""
        print("\nMoving robots to home positions...")
        
        # Enable torque on both
        print("Enabling torque on both robots...")
        for servo_id in LEADER_SERVO_IDS + FOLLOWER_SERVO_IDS:
            self.robot.write_packet(servo_id, 0x03, [0x28, 1])
            time.sleep(0.01)
        
        time.sleep(0.5)
        
        # Move leader to home2
        print("Moving leader to home2...")
        for i, servo_id in enumerate(LEADER_SERVO_IDS):
            steps = degrees_to_steps(self.leader_home[i])
            self.robot.write_position(servo_id, steps, speed=1000, acc=30)
        
        # Move follower to Home
        print("Moving follower to Home...")
        for i, servo_id in enumerate(FOLLOWER_SERVO_IDS):
            steps = degrees_to_steps(self.follower_home[i])
            self.robot.write_position(servo_id, steps, speed=1000, acc=30)
        
        print("✓ Moved to home positions")
        time.sleep(2)
    
    def run_leader_follower(self, update_rate=20):
        """
        Run leader-follower control loop
        
        Args:
            update_rate: Update frequency in Hz (default: 20Hz = 50ms)
        """
        print(f"\n{'='*70}")
        print("Leader-Follower Mode")
        print(f"{'='*70}")
        print("\nLeader robot: NO TORQUE - move manually")
        print("Follower robot: Will mirror leader's movements")
        print("\nPress Ctrl+C to stop")
        print(f"{'='*70}\n")
        
        # Disable torque on leader
        self.set_leader_torque(enable=False)
        
        # Enable torque on follower
        print("Enabling torque on follower robot...")
        for servo_id in FOLLOWER_SERVO_IDS:
            self.robot.write_packet(servo_id, 0x03, [0x28, 1])
            time.sleep(0.01)
        
        time.sleep(0.5)
        
        self.running = True
        update_interval = 1.0 / update_rate
        
        print(f"✅ Leader-follower active (updating at {update_rate}Hz)\n")
        
        try:
            loop_count = 0
            while self.running:
                start_time = time.time()
                
                # Read leader positions
                leader_pos = self.read_leader_positions()
                
                if leader_pos:
                    # Write to follower
                    self.write_follower_positions(leader_pos, speed=2000)
                    
                    # Display every 10th iteration (0.5s at 20Hz)
                    if loop_count % 10 == 0:
                        print(f"\rLeader: {[f'{p:6.1f}°' for p in leader_pos[:3]]}... → Follower", end='', flush=True)
                    
                    loop_count += 1
                else:
                    print("\r⚠ Failed to read leader positions", end='', flush=True)
                
                # Maintain update rate
                elapsed = time.time() - start_time
                if elapsed < update_interval:
                    time.sleep(update_interval - elapsed)
        
        except KeyboardInterrupt:
            print("\n\n🛑 Stopped by user")
        
        finally:
            # Re-enable torque on leader for safety
            print("\nRe-enabling torque on leader...")
            self.set_leader_torque(enable=True)
            self.running = False
    
    def calibrate_offset(self):
        """
        Calibrate offset between leader and follower
        Move both to known positions and measure difference
        """
        print("\n" + "="*70)
        print("Offset Calibration")
        print("="*70)
        print("\n1. Move both robots to same physical pose")
        print("2. This will measure the offset between them")
        input("\nPress Enter when both robots are in matching pose...")
        
        # Read positions
        leader_pos = self.read_leader_positions()
        
        # Read follower (need to enable torque first to get accurate reading)
        follower_pos = []
        for servo_id in FOLLOWER_SERVO_IDS:
            pos_steps = self.robot.read_position(servo_id)
            if pos_steps is not None:
                follower_pos.append(steps_to_degrees(pos_steps))
        
        if leader_pos and len(follower_pos) == 7:
            print("\nMeasured positions:")
            print(f"{'Joint':<10} {'Leader':<12} {'Follower':<12} {'Offset':<12}")
            print("-" * 50)
            offsets = []
            for i in range(7):
                offset = follower_pos[i] - leader_pos[i]
                offsets.append(offset)
                print(f"Joint {i+1:<3} {leader_pos[i]:>10.1f}° {follower_pos[i]:>10.1f}° {offset:>10.1f}°")
            
            print(f"\nOffset array: {offsets}")
            print("\nYou can apply this offset in the code if needed.")
        else:
            print("❌ Failed to read positions")
    
    def disconnect(self):
        """Disconnect and cleanup"""
        self.running = False
        if self.robot:
            self.robot.disconnect()


def main():
    print("""
╔════════════════════════════════════════════════════════════════════╗
║                 Leader-Follower Robot Control                      ║
║                                                                    ║
║  Two robots on same serial bus:                                   ║
║    • Leader (IDs 1-7):   No torque, manually movable              ║
║    • Follower (IDs 8-14): Mirrors leader movements                ║
╚════════════════════════════════════════════════════════════════════╝
""")
    
    controller = LeaderFollowerController()
    
    if not controller.connect():
        return
    
    print("\nOptions:")
    print("  1. Move both to home positions")
    print("  2. Start leader-follower mode")
    print("  3. Calibrate offset (optional)")
    print("  4. Change servo IDs (for follower robot)")
    print("  5. Exit")
    
    while True:
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == '1':
            controller.move_to_home()
        
        elif choice == '2':
            try:
                rate = input("Update rate in Hz (default: 20): ").strip()
                rate = int(rate) if rate else 20
                controller.run_leader_follower(update_rate=rate)
            except ValueError:
                print("Invalid rate, using default 20Hz")
                controller.run_leader_follower()
        
        elif choice == '3':
            controller.calibrate_offset()
        
        elif choice == '4':
            print("\n" + "="*70)
            print("Change Servo IDs")
            print("="*70)
            print("\nThis will change follower robot IDs from current to 8-14")
            print("\n⚠️  IMPORTANT:")
            print("  1. Disconnect the LEADER robot first!")
            print("  2. Keep only FOLLOWER robot connected")
            print("  3. This will change IDs: 1→8, 2→9, 3→10, 4→11, 5→12, 6→13, 7→14")
            
            response = input("\nIs ONLY the follower robot connected? (yes/no): ").strip().lower()
            if response == 'yes':
                # Scan current IDs
                print("\nScanning current servo IDs...")
                current_ids = []
                for test_id in range(1, 15):
                    if controller.robot.ping(test_id):
                        current_ids.append(test_id)
                
                print(f"Found servos: {current_ids}")
                
                if len(current_ids) == 7:
                    print(f"\n✓ Found 7 servos (follower with gripper)")
                    print("\nWill change IDs:")
                    for i, old_id in enumerate(sorted(current_ids)):
                        new_id = i + 8
                        print(f"  {old_id} → {new_id}")
                    
                    confirm = input("\nProceed with ID changes? (yes/no): ").strip().lower()
                    if confirm == 'yes':
                        for i, old_id in enumerate(sorted(current_ids)):
                            new_id = i + 8
                            print(f"\nChanging ID {old_id} → {new_id}...")
                            # Write new ID to register 5 (SMS_STS_ID)
                            controller.robot.serial.flushInput()
                            controller.robot.write_packet(old_id, 0x03, [5, new_id])
                            time.sleep(0.2)
                            if controller.robot.ping(new_id):
                                print(f"  ✓ Success!")
                            else:
                                print(f"  ✗ Failed - servo may need power cycle")
                        
                        print("\n✅ ID changes complete!")
                        print("\nNext steps:")
                        print("  1. Disconnect follower robot")
                        print("  2. Connect leader robot")
                        print("  3. Connect follower robot")
                        print("  4. Run this program again")
                elif len(current_ids) == 6:
                    print(f"\n⚠️  Found 6 servos (this might be the leader!)")
                    print("Make sure you have the FOLLOWER robot connected (7 servos)")
                else:
                    print(f"\n⚠️  Expected 7 servos, found {len(current_ids)}")
            else:
                print("Cancelled - make sure only follower is connected")
        
        elif choice == '5':
            print("Exiting...")
            break
        
        else:
            print("Invalid option")
    
    controller.disconnect()
    print("\n✅ Disconnected")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
