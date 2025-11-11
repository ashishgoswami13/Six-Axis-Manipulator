# Manual Control for 7-Axis Servo Manipulator

Interactive manual control program for operating 7 servo joints (ST3215 servos) individually or together.

## Features

### Main Capabilities
- **Individual Servo Control**: Control each of the 7 servos with precise position, speed, and acceleration settings
- **Real-time Feedback**: Read position, temperature, voltage, current, and movement status from any servo
- **Batch Operations**: Move all servos to the same position or home them simultaneously
- **Quick Presets**: Save and execute common positions for your manipulator
- **Connection Testing**: Ping individual servos to verify connectivity
- **Adjustable Parameters**: Customize default speed and acceleration settings
- **Circle Motion**: Trace circular patterns in horizontal plane with coordinated multi-servo movement ★ NEW

### Menu Structure

#### 1. Control Individual Servo
- Set specific position (0-4095)
- Move to center/min/max positions
- Incremental control (+/- adjustment)
- Read detailed feedback (position, speed, load, voltage, temperature, current, moving status)

#### 2. Read All Servo Status
- Display status table for all 7 servos
- Shows: Position, Temperature, Voltage, and Movement status

#### 3. Home All Servos
- Move all servos to center position (2048) simultaneously

#### 4. Move All Servos to Same Position
- Set the same target position for all servos

#### 5. Quick Presets
- **Home Position**: All servos centered
- **Straight Up**: Vertical position
- **Rest Position**: Compact folded position
- **Custom Preset 1 & 2**: Customize for your needs (edit in code)

#### 6. Test Servo Connection (Ping)
- Verify each servo is connected and responding

#### 7. Set Default Speed & Acceleration
- Adjust movement speed (0-2400 steps/sec)
- Adjust acceleration (0-254, x100 steps/sec²)

#### 8. Circle Motion (Horizontal Plane) ★ NEW
- **Automated Circular Trajectory**: Trace perfect circles in horizontal plane
- **Coordinated Movement**: Uses Joint 1 (Base) and Joint 2 (Shoulder) in synchronized motion
- **Customizable Parameters**:
  - Center position for base rotation
  - Circle radius (50-1000 steps)
  - Number of points per circle (8-360 for smooth/segmented motion)
  - Number of loops to repeat
  - Option to position other joints at center
- **Visual Progress**: Real-time feedback showing points traced and angles
- **Applications**: Testing workspace, drawing patterns, calibration, demonstrations

## Joint Configuration

The program is configured for 7 servos with the following default IDs:

| Joint | Servo ID | Description |
|-------|----------|-------------|
| Joint 1 | 1 | Base |
| Joint 2 | 2 | Shoulder |
| Joint 3 | 3 | Elbow |
| Joint 4 | 4 | Wrist 1 |
| Joint 5 | 5 | Wrist 2 |
| Joint 6 | 6 | Wrist 3 |
| Joint 7 | 7 | Gripper |

### Customizing Servo IDs
If your servo IDs are different, edit these arrays in `ManualControl.cpp`:
```cpp
const int SERVO_IDS[NUM_SERVOS] = {1, 2, 3, 4, 5, 6, 7};
```

## Building the Program

### Option 1: Using the build script (recommended)
```bash
cd ManualControl
mkdir -p build
cd build
cmake ..
make
```

### Option 2: Using the parent build script
```bash
cd ../  # Go to ST3215_Control directory
./build_all.sh  # This will build all examples including ManualControl
```

## Running the Program

### Basic Usage
```bash
cd build
./ManualControl
```

### Custom Serial Port
```bash
./ManualControl /dev/ttyUSB0
```

### Custom Serial Port and Baud Rate
```bash
./ManualControl /dev/ttyACM0 1000000
```

### Default Parameters
- **Port**: `/dev/ttyACM0`
- **Baud Rate**: `1000000` (1M)
- **Default Speed**: `2400` steps/sec
- **Default Acceleration**: `50` (x100 steps/sec²)

## Troubleshooting

### "Failed to initialize serial port"
1. **Check connection**: Ensure servos are powered and connected
2. **Verify port name**: 
   ```bash
   ls /dev/ttyACM* /dev/ttyUSB*
   ```
3. **Check permissions**: Add your user to the dialout group
   ```bash
   sudo usermod -a -G dialout $USER
   ```
   Then logout and login again.
4. **Try with sudo**: As a temporary solution
   ```bash
   sudo ./ManualControl
   ```

### "No response from servo"
1. Check that the servo ID matches your configuration
2. Verify servo is powered on
3. Check baud rate matches servo settings (default: 1000000)
4. Use the Ping function (Menu option 6) to test connectivity

### Servo doesn't move
1. Check that servo is not in torque-disable mode
2. Verify position is within valid range (0-4095)
3. Check power supply voltage
4. Review load and temperature in feedback data

## Position Range Information

**ST3215 Servo Specifications:**
- Position Range: 0-4095 (12-bit resolution)
- Approximate Angle: 0-360 degrees
- Center Position: 2048 (approximately 180°)
- Resolution: ~0.088° per step

## Advanced Features

### Incremental Control
Use option 6 in the individual servo control menu to make small adjustments:
- Enter positive values to increase position
- Enter negative values to decrease position
- Automatically clamps to valid range (0-4095)

### Customizing Presets
Edit the `quickPresets()` function in `ManualControl.cpp` to add your own positions:
```cpp
case 4: // Custom 1
    positions[0] = 1536;  // Your custom position for Joint 1
    positions[1] = 2048;  // Your custom position for Joint 2
    // ... etc
    break;
```

### Reading Detailed Feedback
The detailed feedback option provides:
- **Position**: Current position (0-4095)
- **Speed**: Current movement speed
- **Load**: Output load percentage (0-1000)
- **Voltage**: Supply voltage (x0.1V, e.g., 120 = 12.0V)
- **Temperature**: Servo temperature in °C
- **Moving**: Whether servo is currently in motion
- **Current**: Current draw in mA

## Safety Notes

⚠️ **Important Safety Considerations:**
1. Always ensure the manipulator has clear space before moving
2. Start with slow speeds when testing new positions
3. Monitor temperature during extended use
4. Keep emergency stop accessible
5. Never exceed the mechanical limits of your manipulator
6. Verify positions in software before executing movements

## Example Workflow

### Initial Setup
1. Power on servos
2. Run the program: `./ManualControl`
3. Use option 6 to ping all servos and verify connectivity
4. Use option 3 to home all servos to center position

### Moving Individual Joints
1. Select option 1 (Control Individual Servo)
2. Choose the joint number
3. Select position control method
4. Monitor movement
5. Use option 5 to read detailed feedback if needed

### Creating a Movement Sequence
1. Move each joint individually to desired position
2. Note the positions
3. Add them as a custom preset in the code
4. Recompile and use the preset for quick recall

### Tracing a Circle (NEW Feature)
1. Select option 8 (Circle Motion - Horizontal Plane)
2. Configure circle parameters:
   - **Center Position**: Base position for Joint 1 (default: 2048)
   - **Radius**: Size of circle in servo steps (50-1000, recommend 300-500)
   - **Points per Circle**: Resolution (36 = smooth, 8 = octagon)
   - **Number of Loops**: How many times to repeat (1-100)
   - **Other Joints**: Keep at center or leave as-is
3. Press Enter to start the motion
4. Watch as the manipulator traces a perfect circle
5. Press Ctrl+C to abort if needed

**Circle Motion Tips:**
- Start with small radius (200-300) for safety
- Use 36 points for smooth circles
- Monitor servo load during motion
- Ensure adequate workspace clearance
- Adjust speed if motion is too fast/slow

**How It Works:**
- Joint 1 (Base) rotates to change the angle around the circle
- Joint 2 (Shoulder) adjusts position to maintain constant radius
- Mathematical calculation: Uses sine/cosine to compute positions
- Coordinated movement creates circular path in horizontal plane

## Technical Details

### Communication Protocol
- Protocol: SCServo protocol (compatible with Feetech SCS/STS series)
- Default Baud Rate: 1,000,000 bps
- Communication: Half-duplex serial

### Dependencies
- SCServo library (included in project)
- pthread (for serial communication)
- C++11 or later

## License

This program uses the SCServo library for Waveshare/Feetech servo control.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify servo specifications match ST3215
3. Review the example programs in the parent directory
4. Check servo documentation for specific parameters

---

**Version**: 1.1  
**Last Updated**: November 2025  
**Compatible with**: ST3215 servos and compatible SCS/STS series servos  
**New in v1.1**: Circle motion tracing feature for horizontal plane trajectory
