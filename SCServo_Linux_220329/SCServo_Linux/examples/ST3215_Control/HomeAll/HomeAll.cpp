/*
 * HomeAll.cpp - ROBOT ARM HOMING PROGRAM
 * ========================================
 * 
 * PURPOSE: Move all 7 servos (6 joints + gripper) to their "home" position (0°)
 *          while respecting mechanical joint limits for safety.
 * 
 * ROBOT CONFIGURATION:
 * - Servo IDs 1-6 map to robot joints J1-J6
 * - Servo ID 7 is the gripper (end-effector)
 * 
 * ST3215 SERVO SPECIFICATIONS:
 * - Position range: 0 to 4095 steps (12-bit resolution = 2^12 = 4096 values)
 * - Full rotation: 360° = 4096 steps
 * - Resolution: 360° / 4096 ≈ 0.088° per step (very precise!)
 * - Center position: 2048 steps = 0°
 *   * Position 0 = -180°
 *   * Position 2048 = 0° (home)
 *   * Position 4095 = +180°
 * 
 * COMMUNICATION:
 * - Baud rate: 1,000,000 bps (1M baud) - very fast serial communication
 * - Protocol: Half-duplex serial (TTL UART)
 * - Interface: USB-to-Serial (/dev/ttyACM0 on Linux)
 * 
 * SAFETY:
 * - Joint limits are enforced to prevent mechanical damage
 * - Speed is capped at 150°/s (robot's maximum safe speed)
 */

// ============================================================================
// INCLUDE LIBRARIES
// ============================================================================

#include <iostream>    // For console output (std::cout, std::cerr)
#include <unistd.h>    // For sleep() and usleep() - delays
#include "SCServo.h"   // Feetech/Waveshare servo control library

// ============================================================================
// JOINT SAFETY LIMITS (in degrees)
// ============================================================================
// 
// WHY LIMITS?
// - Physical constraints: Robot parts would collide if joints moved too far
// - Mechanical protection: Prevents damage to gears, brackets, wiring
// - Safety: Keeps robot movements predictable and controlled
//
// HOW TO READ THIS:
// Array index 0 = Joint 1 (base rotation)
// Array index 1 = Joint 2 (shoulder)
// Array index 2 = Joint 3 (elbow)
// Array index 3 = Joint 4 (wrist pitch)
// Array index 4 = Joint 5 (wrist roll)
// Array index 5 = Joint 6 (flange rotation)
// Array index 6 = Gripper
//
// EXAMPLE: Joint 1 can move from -165° to +165° (330° total range)
//          Joint 2 can move from -125° to +125° (250° total range)
//
static const int JOINT_MIN_DEG[7] = {-165, -125, -140, -140, -140, -175, -180};
static const int JOINT_MAX_DEG[7] = { 165,  125,  140,  140,  140,  175,  180};

// ============================================================================
// COORDINATE TRANSFORM
// ============================================================================
// Physical robot is mounted with 90° clockwise rotation from zero position
// To align with camera/code coordinates, we apply +90° offset to J1 commands
static const double J1_OFFSET = 90.0;

// ============================================================================
// CONVERSION FUNCTION: Degrees → Servo Steps
// ============================================================================
//
// PURPOSE: Convert human-readable angles (degrees) to servo position values
//
// CONCEPT:
// - We think in degrees: "move joint to 45°"
// - Servo understands steps: "go to position 2560"
// - This function translates between the two
//
// MATH BREAKDOWN:
// 1. Start with center: 2048 steps = 0°
// 2. Calculate offset: (deg / 360°) × 4096 steps
//    - Example: 45° / 360° = 0.125 rotations
//    - 0.125 × 4096 = 512 steps from center
// 3. Add to center: 2048 + 512 = 2560 steps
//
// WRAPPING:
// - If result < 0, add 4096 (wrap around)
// - If result >= 4096, subtract 4096 (wrap around)
// - This handles the circular nature of rotation
//
// EXAMPLE CONVERSIONS:
//   0° → 2048 steps (center)
//  45° → 2560 steps (2048 + 512)
//  90° → 3072 steps (2048 + 1024)
// -45° → 1536 steps (2048 - 512)
// -90° → 1024 steps (2048 - 1024)
//
static int degreesToSteps(double deg){
    // Calculate servo position: center (2048) + offset
    double steps = 2048.0 + (deg / 360.0) * 4096.0;
    
    // Normalize to valid range [0, 4095]
    // This handles cases where calculation goes outside bounds
    while(steps < 0) steps += 4096.0;          // Wrap negative values
    while(steps >= 4096.0) steps -= 4096.0;    // Wrap values >= 4096
    
    // Round to nearest integer (0.5 ensures proper rounding)
    return (int)(steps + 0.5);
}

// ============================================================================
// MAIN PROGRAM
// ============================================================================
int main(int argc, char** argv){
    // ------------------------------------------------------------------------
    // STEP 1: Setup serial port configuration
    // ------------------------------------------------------------------------
    // 
    // SERIAL PORT:
    // - Default: /dev/ttyACM0 (common for USB-to-Serial on Linux)
    // - Can be overridden via command line argument
    //   Example: ./HomeAll /dev/ttyUSB0
    //
    // WHY /dev/ttyACM0?
    // - "tty" = teletype (terminal device)
    // - "ACM" = Abstract Control Model (USB CDC class)
    // - "0" = first device of this type
    //
    const char* port = "/dev/ttyACM0";      // Default USB serial port
    if(argc >= 2) port = argv[1];           // Use command line arg if provided
    
    // Print program info to console
    std::cout << "HomeAll - Move joints 1..6 + gripper (7) to home (0°) respecting joint limits" << std::endl;
    std::cout << "Port: " << port << std::endl;
    std::cout << "Baud: 1000000 (1M)" << std::endl;

    // ------------------------------------------------------------------------
    // STEP 2: Initialize servo controller
    // ------------------------------------------------------------------------
    //
    // SMS_STS CLASS:
    // - SMS = "Feetech SCS/SMS Protocol"
    // - STS = "Serial Servo" (another Feetech series)
    // - This object handles all communication with servos
    //
    // WHAT begin() DOES:
    // 1. Opens the serial port
    // 2. Sets baud rate to 1,000,000 bps
    // 3. Configures serial parameters (8N1: 8 data bits, No parity, 1 stop bit)
    // 4. Initializes communication buffers
    //
    // WHY CHECK RETURN VALUE?
    // - begin() returns false if:
    //   * Serial port doesn't exist
    //   * Port is already in use by another program
    //   * No permission to access port (need sudo or user in dialout group)
    //   * Hardware not connected
    //
    SMS_STS sm_st;                                      // Create servo controller object
    if(!sm_st.begin(1000000, port)){                    // Initialize at 1M baud
        std::cerr << "ERROR: Failed to initialize serial on " << port << std::endl;
        return 1;                                       // Exit with error code
    }

    // ------------------------------------------------------------------------
    // STEP 3: Configure motion parameters (speed and acceleration)
    // ------------------------------------------------------------------------
    //
    // MOTION CONTROL:
    // Servos don't just "jump" to positions - they move smoothly.
    // We control HOW they move:
    //
    // SPEED CALCULATION:
    // - Robot spec: Max speed = 150°/second
    // - Convert to steps/second: 150° / 360° × 4096 steps ≈ 1707 steps/sec
    // - We use 1000 steps/sec for smoother, safer motion
    //
    // WHY LIMIT SPEED?
    // - Too fast: jerky motion, mechanical stress, inaccuracy
    // - Too slow: inefficient, but very smooth and precise
    // - 1000 steps/sec ≈ 88°/sec - good balance for homing
    //
    // ACCELERATION:
    // - Controls how quickly speed changes (ramp up/down)
    // - Value of 50 = gentle acceleration (smooth start/stop)
    // - Higher values = more aggressive (jerky)
    // - Lower values = more gentle (slower to reach full speed)
    //
    const double max_deg_per_sec = 150.0;               // Robot's max safe speed (from specs)
    int max_steps_per_sec = (int)((max_deg_per_sec / 360.0) * 4096.0 + 0.5); // Convert to steps: ~1707
    int travel_speed = std::min(1000, max_steps_per_sec); // Use 1000 steps/sec (conservative)
    int acc = 50;                                       // Acceleration value (gentle ramp)

    std::cout << "Using speed (steps/s): " << travel_speed << " (capped to 150 deg/s)" << std::endl;

    // ------------------------------------------------------------------------
    // STEP 4: Move each servo to home position (0°)
    // ------------------------------------------------------------------------
    //
    // LOOP STRUCTURE:
    // - i = 0 to 6 (array indices)
    // - id = 1 to 7 (actual servo IDs on the bus)
    //
    // FOR EACH SERVO:
    // 1. Calculate target position (0° clamped to limits)
    // 2. Convert degrees to servo steps
    // 3. Enable motor torque (allows movement)
    // 4. Send position command
    // 5. Small delay before next servo (prevents bus congestion)
    //
    for(int i=0; i<7; i++){
        // Get servo ID (servos are numbered 1-7, not 0-6)
        int id = i+1;
        
        // ----------------------------------------------------------------
        // Target angle: 0° (home position)
        // ----------------------------------------------------------------
        double want_deg = 0.0;
        
        // ----------------------------------------------------------------
        // Apply coordinate transform for J1 (base rotation)
        // ----------------------------------------------------------------
        // Physical robot is rotated 90° clockwise, compensate with offset
        if(i == 0){  // J1 only
            want_deg += J1_OFFSET;
        }
        
        // ----------------------------------------------------------------
        // SAFETY: Clamp to joint limits
        // ----------------------------------------------------------------
        // WHY? Some joints might not be able to reach 0° due to:
        // - Mechanical constraints
        // - Assembly variations
        // - Calibration offsets
        //
        // This ensures we never command an impossible position
        //
        if(want_deg < JOINT_MIN_DEG[i]) want_deg = JOINT_MIN_DEG[i];
        if(want_deg > JOINT_MAX_DEG[i]) want_deg = JOINT_MAX_DEG[i];
        
        // ----------------------------------------------------------------
        // Convert angle to servo steps
        // ----------------------------------------------------------------
        int steps = degreesToSteps(want_deg);
        
        // Print what we're about to do
        const char* label = (i < 6) ? "Joint" : "Gripper";
        std::cout << label << " "<< id << ": target "<< want_deg << "° -> "<< steps << " steps" << std::endl;
        
        // ----------------------------------------------------------------
        // ENABLE TORQUE
        // ----------------------------------------------------------------
        // WHY?
        // - Servos start in "free" mode (can be moved by hand)
        // - EnableTorque(id, 1) locks the servo and allows motor control
        // - EnableTorque(id, 0) would release the servo (power off motor)
        //
        // IMPORTANT: Must enable torque before movement commands work!
        //
        sm_st.EnableTorque(id, 1);
        
        // ----------------------------------------------------------------
        // SEND POSITION COMMAND
        // ----------------------------------------------------------------
        // WritePosEx() = "Write Position Extended"
        // Parameters:
        //   - id: Which servo (1-7)
        //   - steps: Target position (0-4095)
        //   - travel_speed: How fast to move (steps/sec)
        //   - acc: Acceleration profile
        //
        // RETURN VALUE:
        //   - Returns -1 on failure (communication error)
        //   - Returns 0 on success
        //
        // COMMUNICATION:
        // This sends a packet over serial:
        // [Header][ID][Length][Instruction][Position][Speed][Acc][Checksum]
        //
        int res = sm_st.WritePosEx(id, steps, travel_speed, acc);
        if(res == -1){
            std::cerr << "Failed to send position to servo "<< id << std::endl;
        }
        
        // ----------------------------------------------------------------
        // SHORT DELAY between commands
        // ----------------------------------------------------------------
        // WHY?
        // - Gives servo time to process command
        // - Prevents overwhelming the serial bus
        // - 100ms = 0.1 second (100,000 microseconds)
        // - With 7 servos: 0.7 seconds total delay (acceptable)
        //
        usleep(100000);  // Sleep for 100 milliseconds
    }

    // ------------------------------------------------------------------------
    // STEP 5: Wait for all servos to reach target positions
    // ------------------------------------------------------------------------
    //
    // WHY WAIT?
    // - Commands were sent, but servos are still MOVING
    // - Takes time to physically move to target (depends on distance & speed)
    // - If we read positions immediately, we'd get intermediate values
    //
    // HOW LONG?
    // - 2 seconds is generous for homing (0° is usually close to start position)
    // - At 1000 steps/sec, worst case:
    //   * Max distance: ~2048 steps (from one extreme to center)
    //   * Time needed: 2048/1000 = ~2 seconds
    //
    // ALTERNATIVE:
    // - Could poll each servo's "moving" flag until all stop
    // - But simple sleep() is more reliable and easier to understand
    //
    std::cout << "Waiting for motion to complete..." << std::endl;
    sleep(2);  // Block program for 2 seconds

    // ------------------------------------------------------------------------
    // STEP 6: Read back actual positions (VERIFICATION)
    // ------------------------------------------------------------------------
    //
    // WHY READ BACK?
    // - Verify servos actually moved to commanded positions
    // - Detect if servo failed to move (mechanical jam, no power, etc.)
    // - Good practice: always verify critical movements
    //
    // HOW IT WORKS:
    // 1. FeedBack(id) - Request status packet from servo
    //    * Servo sends back: position, speed, load, voltage, temperature, etc.
    //    * Returns -1 if communication fails
    //    * Returns 0 if successful (data cached in library)
    //
    // 2. ReadPos(-1) - Read position from cached data
    //    * -1 means "use last FeedBack data" (no new request)
    //    * More efficient than requesting position again
    //
    // 3. Convert steps → degrees → centered angle
    //    * steps (0-4095) → angle (0-360°) → centered (-180° to +180°)
    //
    for(int i=0; i<7; i++){
        int id = i+1;
        const char* label = (i < 6) ? "Joint" : "Gripper";
        
        // ----------------------------------------------------------------
        // Request feedback from servo
        // ----------------------------------------------------------------
        if(sm_st.FeedBack(id) != -1){
            // Successfully received data
            
            // ----------------------------------------------------------------
            // Read position from cached feedback
            // ----------------------------------------------------------------
            int pos = sm_st.ReadPos(-1);  // -1 = read from cache (don't query again)
            
            // ----------------------------------------------------------------
            // Convert steps to degrees
            // ----------------------------------------------------------------
            // Formula: degrees = (steps / 4096) × 360°
            // Example: 2048 steps → (2048/4096) × 360° = 0.5 × 360° = 180°
            //
            double angle = (pos / 4096.0) * 360.0;
            
            // ----------------------------------------------------------------
            // Normalize angle to -180° to +180° range
            // ----------------------------------------------------------------
            // WHY?
            // - Above calculation gives 0° to 360°
            // - More intuitive to think: -90° (left) vs 270° (also left)
            // - Centered around 0° matches our "home" concept
            //
            // LOGIC:
            // - If angle >= 360°: subtract 360° (shouldn't happen, but safety)
            // - If angle > 180°: subtract 360° (convert to negative)
            //   Example: 270° → 270° - 360° = -90°
            //
            double centered = angle;
            if(centered >= 360.0) centered -= 360.0;
            if(centered > 180.0) centered -= 360.0;
            
            // Print current position
            std::cout << label <<" "<<id<<" current steps="<<pos<<" angle="<<centered<<"°"<<std::endl;
        }else{
            // Communication failed
            std::cout << "Failed to read feedback for servo "<<id<<std::endl;
        }
    }

    // ------------------------------------------------------------------------
    // STEP 7: Cleanup and exit
    // ------------------------------------------------------------------------
    //
    // sm_st.end():
    // - Closes the serial port
    // - Releases system resources
    // - Good practice: clean up before program exits
    // - Allows other programs to use the port
    //
    // WHY IMPORTANT?
    // - If port not closed properly:
    //   * Port may stay "locked"
    //   * Next program run might fail to open port
    //   * May need to replug USB or reboot
    //
    sm_st.end();
    
    std::cout << "Done." << std::endl;
    return 0;  // Exit code 0 = success (standard Unix convention)
}

// ============================================================================
// END OF PROGRAM
// ============================================================================
//
// SUMMARY OF WHAT THIS PROGRAM DOES:
// 1. Opens serial connection to servo controller
// 2. Calculates safe home positions (0° clamped to limits)
// 3. Enables torque on all servos
// 4. Commands all servos to move to home position
// 5. Waits for movement to complete
// 6. Reads back actual positions to verify
// 7. Closes serial connection and exits
//
// KEY CONCEPTS YOU LEARNED:
// - Servo position encoding (steps vs degrees)
// - Serial communication with hardware
// - Safety limits and clamping
// - Motion control (speed & acceleration)
// - Feedback and verification
// - Resource management (open/close port)
//
// NEXT STEPS TO TRY:
// - Modify target angles (change want_deg)
// - Adjust speed and acceleration values
// - Add individual joint control
// - Read positions in a continuous loop
// - Combine with forward kinematics to move to X,Y,Z positions!
//
