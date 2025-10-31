# Waveshare ST3215 Servo Motor Control Guide

This guide will help you set up and control the Waveshare ST3215 servo motor connected to `/dev/ttyACM0` on Linux.

## Table of Contents
- [Hardware Overview](#hardware-overview)
- [System Requirements](#system-requirements)
- [Hardware Setup](#hardware-setup)
- [Software Installation](#software-installation)
- [Compilation](#compilation)
- [Running the Examples](#running-the-examples)
- [Troubleshooting](#troubleshooting)
- [API Reference](#api-reference)

---

## Hardware Overview

**Waveshare ST3215 Servo Motor Specifications:**
- **Protocol:** SMS/STS (Serial Total Servo) Protocol
- **Communication:** Serial UART (USB Type-C via /dev/ttyACM0)
- **Baud Rate:** 1000000 (1M) - Factory Default
- **Position Range:** 0-4095 (approximately 0-360°)
- **Max Speed:** 150°/s (2400 steps/sec)
- **Voltage:** 12V DC, 10A
- **Default ID:** 1

The ST3215 is part of the STS series servo motors and uses the SMS_STS communication protocol.

---

## System Requirements

- **OS:** Linux (tested on Ubuntu/Debian)
- **Compiler:** GCC with C++11 support
- **Build System:** CMake 2.8.3 or higher
- **Port:** /dev/ttyACM0 (USB serial connection)
- **Permissions:** User must have access to serial ports (dialout group)

---

## Hardware Setup

1. **Power Connection:**
   - Connect 12V DC, 10A power supply to the servo motor
   - Ensure proper grounding

2. **USB Connection:**
   - Connect the servo motor to your computer via USB Type-C
   - The device should appear as `/dev/ttyACM0`
   - Verify connection: `ls -l /dev/ttyACM*`

3. **Check Device:**
   ```bash
   # List USB serial devices
   ls -l /dev/ttyACM*
   
   # Check device info
   dmesg | grep tty
   ```

---

## Software Installation

### Step 1: Add User to Dialout Group

To access serial ports without sudo, add your user to the `dialout` group:

```bash
sudo usermod -a -G dialout $USER
```

**Important:** Log out and log back in for this to take effect!

Verify membership:
```bash
groups $USER
```

### Step 2: Set Port Permissions (Alternative)

If you don't want to log out, temporarily set permissions:

```bash
sudo chmod 666 /dev/ttyACM0
```

**Note:** This is temporary and will reset on reboot or device reconnection.

### Step 3: Install Build Dependencies

```bash
sudo apt-get update
sudo apt-get install build-essential cmake git
```

---

## Compilation

### Build the SCServo Library

1. Navigate to the library directory:
   ```bash
   cd /home/dev/Downloads/SCServo_Linux/SCServo_Linux_220329/SCServo_Linux
   ```

2. Create build directory and compile:
   ```bash
   mkdir -p build
   cd build
   cmake ..
   make
   cd ..
   ```

   This creates `libSCServo.a` in the main directory.

### Build ST3215 Control Examples

1. Navigate to ST3215_Control directory:
   ```bash
   cd examples/ST3215_Control
   ```

2. Create build directory:
   ```bash
   mkdir -p build
   cd build
   ```

3. Compile all examples:
   ```bash
   # Compile Ping
   cmake ../Ping
   make
   ./Ping
   
   # Compile WritePos
   cmake ../WritePos
   make
   ./WritePos
   
   # Compile FeedBack
   cmake ../FeedBack
   make
   ./FeedBack
   ```

**Alternative:** Use the provided build script (if created):
```bash
./build_all.sh
```

---

## Running the Examples

All examples default to `/dev/ttyACM0` and servo ID 1. You can override these:

### 1. Ping Test
Tests if the servo is connected and responsive.

```bash
cd examples/ST3215_Control/build

# Default usage (port: /dev/ttyACM0, ID: 1)
./Ping

# Custom port
./Ping /dev/ttyUSB0

# Custom port and ID
./Ping /dev/ttyACM0 2
```

**Expected Output:**
```
=== ST3215 Servo Ping Test ===
Port: /dev/ttyACM0
Servo ID: 1
Baud Rate: 1000000 (1M)
===============================
Serial port initialized successfully!
SUCCESS: Servo responded!
Servo ID: 1
```

### 2. Position Control (WritePos)
Moves the servo between min (0) and max (4095) positions.

```bash
# Default usage
./WritePos

# Custom port and ID
./WritePos /dev/ttyACM0 1
```

**Expected Output:**
```
=== ST3215 Servo Position Control ===
Port: /dev/ttyACM0
Servo ID: 1
Baud Rate: 1000000 (1M)
=====================================
Serial port initialized successfully!
Moving servo between positions...
Press Ctrl+C to stop

Position: 4095 (Max)
Position: 0 (Min)
Position: 4095 (Max)
...
```

**Press Ctrl+C to stop the program.**

### 3. Feedback Reading (FeedBack)
Continuously reads servo status data.

```bash
# Default usage
./FeedBack

# Custom port and ID
./FeedBack /dev/ttyACM0 1
```

**Expected Output:**
```
=== ST3215 Servo Feedback Reader ===
Port: /dev/ttyACM0
Servo ID: 1
Baud Rate: 1000000 (1M)
=====================================
Serial port initialized successfully!
Reading servo feedback data...
Press Ctrl+C to stop

=== Read #1 ===
  Position:    2048 (0-4095)
  Speed:       0 steps/sec
  Load:        150 (0-1000)
  Voltage:     120 (×0.1V = 12.0V)
  Temperature: 32 °C
  Moving:      No
  Current:     80 mA
...
```

**Press Ctrl+C to stop the program.**

---

## Troubleshooting

### Issue: "Failed to initialize serial port"

**Solutions:**
1. Check if device exists:
   ```bash
   ls -l /dev/ttyACM0
   ```

2. Verify permissions:
   ```bash
   groups $USER  # Should include 'dialout'
   ```

3. Add user to dialout group:
   ```bash
   sudo usermod -a -G dialout $USER
   # Log out and log back in
   ```

4. Or use sudo (temporary):
   ```bash
   sudo ./Ping
   ```

### Issue: "No response from servo"

**Check:**
1. Servo is powered ON (12V DC connected)
2. USB cable is properly connected
3. Servo ID matches (default is 1)
4. Baud rate is correct (115200)
5. Try different servo IDs:
   ```bash
   ./Ping /dev/ttyACM0 1
   ./Ping /dev/ttyACM0 2
   ```

### Issue: Device not found at /dev/ttyACM0

**Check:**
1. List all USB devices:
   ```bash
   ls -l /dev/ttyUSB* /dev/ttyACM*
   ```

2. Check dmesg for device name:
   ```bash
   dmesg | tail -20
   ```

3. Use the correct device name:
   ```bash
   ./Ping /dev/ttyUSB0
   ```

### Issue: Compilation errors

**Solutions:**
1. Ensure CMake is installed:
   ```bash
   cmake --version
   ```

2. Ensure library is built first:
   ```bash
   cd /home/dev/Downloads/SCServo_Linux/SCServo_Linux_220329/SCServo_Linux
   mkdir build && cd build
   cmake .. && make
   ```

3. Check C++11 support:
   ```bash
   g++ --version  # Should be 4.8 or higher
   ```

---

## API Reference

### Main Functions

#### Initialization
```cpp
SMS_STS sm_st;
sm_st.begin(1000000, "/dev/ttyACM0");  // 1M baud (ST3215 default), port
sm_st.end();  // Close connection
```

#### Ping
```cpp
int id = sm_st.Ping(servo_id);
// Returns: servo ID if successful, -1 if failed
```

#### Position Control
```cpp
sm_st.WritePosEx(ID, Position, Speed, Acceleration);
// ID: Servo ID (1-253)
// Position: 0-4095 (0° to ~360°)
// Speed: 0-2400 steps/sec (max ~150°/s)
// Acceleration: 0-254 (×100 steps/sec²)
```

**Example:**
```cpp
// Move to center position, medium speed
sm_st.WritePosEx(1, 2048, 1200, 50);
```

#### Feedback Reading
```cpp
// Read all parameters efficiently
if(sm_st.FeedBack(servo_id) != -1){
    int pos = sm_st.ReadPos(-1);        // Position (0-4095)
    int speed = sm_st.ReadSpeed(-1);    // Speed (steps/sec)
    int load = sm_st.ReadLoad(-1);      // Load (0-1000)
    int voltage = sm_st.ReadVoltage(-1); // Voltage (×0.1V)
    int temp = sm_st.ReadTemper(-1);    // Temperature (°C)
    int moving = sm_st.ReadMove(-1);    // 0=stopped, 1=moving
    int current = sm_st.ReadCurrent(-1); // Current (mA)
}

// Or read individual parameters
int pos = sm_st.ReadPos(servo_id);
int voltage = sm_st.ReadVoltage(servo_id);
```

#### Advanced Functions
```cpp
sm_st.EnableTorque(ID, Enable);     // 1=enable, 0=disable
sm_st.WheelMode(ID);                // Switch to continuous rotation
sm_st.WriteSpe(ID, Speed, ACC);     // Control speed in wheel mode
sm_st.CalibrationOfs(ID);           // Center calibration
sm_st.LockEprom(ID);                // Lock EPROM
sm_st.unLockEprom(ID);              // Unlock EPROM
```

### Position Calculations

**Degrees to Steps:**
```cpp
int steps = (degrees / 360.0) * 4096;
```

**Steps to Degrees:**
```cpp
float degrees = (steps / 4096.0) * 360.0;
```

**Common Positions:**
- 0° → 0 steps
- 90° → ~1024 steps
- 180° → ~2048 steps
- 270° → ~3072 steps
- 360° → 4095 steps

---

## Example Code Snippets

### Move to Specific Angle
```cpp
#include <iostream>
#include "SCServo.h"

void moveToAngle(SMS_STS& servo, int id, float degrees) {
    int steps = (degrees / 360.0) * 4096;
    servo.WritePosEx(id, steps, 1200, 50);
    std::cout << "Moving to " << degrees << "° (" << steps << " steps)" << std::endl;
}

int main() {
    SMS_STS servo;
    if(!servo.begin(1000000, "/dev/ttyACM0")) return 0;
    
    moveToAngle(servo, 1, 90.0);   // Move to 90°
    sleep(2);
    moveToAngle(servo, 1, 180.0);  // Move to 180°
    
    servo.end();
    return 0;
}
```

### Monitor Servo Status
```cpp
#include <iostream>
#include "SCServo.h"

int main() {
    SMS_STS servo;
    if(!servo.begin(1000000, "/dev/ttyACM0")) return 0;
    
    while(true) {
        if(servo.FeedBack(1) != -1) {
            int pos = servo.ReadPos(-1);
            int temp = servo.ReadTemper(-1);
            float angle = (pos / 4096.0) * 360.0;
            
            std::cout << "Angle: " << angle << "°, Temp: " << temp << "°C" << std::endl;
        }
        usleep(100000);  // 100ms
    }
    
    servo.end();
    return 0;
}
```

---

## Additional Resources

- **ST3215 Datasheet:** Check Waveshare official documentation
- **Protocol Details:** See `SMS_STS.h` for memory map and register definitions
- **More Examples:** Check `examples/SMS_STS/` directory for advanced usage

---

## Quick Start Summary

```bash
# 1. Add user to dialout group
sudo usermod -a -G dialout $USER
# (Log out and back in)

# 2. Build library
cd /home/dev/Downloads/SCServo_Linux/SCServo_Linux_220329/SCServo_Linux
mkdir build && cd build && cmake .. && make && cd ..

# 3. Test connection
cd examples/ST3215_Control/build
cmake ../Ping && make
./Ping

# 4. Control servo
cmake ../WritePos && make
./WritePos

# 5. Read feedback
cmake ../FeedBack && make
./FeedBack
```

---

## License

This code is based on the SCServo Linux library. Refer to the original library for licensing information.

**Created:** October 31, 2025  
**For:** Waveshare ST3215 Servo Motor on /dev/ttyACM0
