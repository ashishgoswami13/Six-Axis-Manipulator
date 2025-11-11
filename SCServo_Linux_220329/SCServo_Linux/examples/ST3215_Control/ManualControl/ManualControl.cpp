/*
 * ManualControl.cpp
 * Interactive manual control for 7 servo joints
 * For Waveshare ST3215 servo motors on /dev/ttyACM0
 * 
 * ST3215 Position Range: 0-4095 (approximately 0-360 degrees)
 * Center position: ~2048
 * 
 * Features:
 * - Control each of 7 servos individually
 * - Set position, speed, and acceleration
 * - Read feedback from each servo
 * - Home all servos to center position
 * - Quick presets for common positions
 * - Trace circular patterns in horizontal plane
 */

#include <iostream>
#include <iomanip>
#include <unistd.h>
#include <string>
#include <cstring>
#include <cmath>
#include "SCServo.h"

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

SMS_STS sm_st;

// Configuration
const int NUM_SERVOS = 7;
const int SERVO_IDS[NUM_SERVOS] = {1, 2, 3, 4, 5, 6, 7};
const char* JOINT_NAMES[NUM_SERVOS] = {
    "Joint 1 (Base)",
    "Joint 2 (Shoulder)",
    "Joint 3 (Elbow)",
    "Joint 4 (Wrist 1)",
    "Joint 5 (Wrist 2)",
    "Joint 6 (Wrist 3)",
    "Joint 7 (Gripper)"
};

// Default parameters
const int DEFAULT_SPEED = 2400;    // steps/sec (0-2400)
const int DEFAULT_ACC = 50;         // acceleration (50*100 steps/sec²)
const int CENTER_POSITION = 2048;
const int MIN_POSITION = 0;
const int MAX_POSITION = 4095;

// Clear screen (works on most terminals)
void clearScreen() {
    std::cout << "\033[2J\033[1;1H";
}

// Display main menu
void displayMenu() {
    clearScreen();
    std::cout << "╔═══════════════════════════════════════════════════════╗" << std::endl;
    std::cout << "║       7-AXIS MANIPULATOR MANUAL CONTROL SYSTEM       ║" << std::endl;
    std::cout << "╚═══════════════════════════════════════════════════════╝" << std::endl;
    std::cout << std::endl;
    std::cout << "MAIN MENU:" << std::endl;
    std::cout << "  1. Control Individual Servo" << std::endl;
    std::cout << "  2. Read All Servo Status" << std::endl;
    std::cout << "  3. Home All Servos (Center Position)" << std::endl;
    std::cout << "  4. Move All Servos to Same Position" << std::endl;
    std::cout << "  5. Quick Presets" << std::endl;
    std::cout << "  6. Test Servo Connection (Ping)" << std::endl;
    std::cout << "  7. Set Default Speed & Acceleration" << std::endl;
    std::cout << "  8. Circle Motion (Horizontal Plane) ★ NEW" << std::endl;
    std::cout << "  0. Exit" << std::endl;
    std::cout << std::endl;
    std::cout << "Enter choice: ";
}

// Display servo selection menu
void displayServoMenu() {
    std::cout << std::endl;
    std::cout << "Select Servo to Control:" << std::endl;
    for(int i = 0; i < NUM_SERVOS; i++) {
        std::cout << "  " << (i+1) << ". " << JOINT_NAMES[i] 
                  << " (ID: " << SERVO_IDS[i] << ")" << std::endl;
    }
    std::cout << "  0. Back to Main Menu" << std::endl;
    std::cout << std::endl;
    std::cout << "Enter choice: ";
}

// Control individual servo
void controlServo(int servoIndex, int currentSpeed, int currentAcc) {
    int servo_id = SERVO_IDS[servoIndex];
    std::string joint_name = JOINT_NAMES[servoIndex];
    
    while(true) {
        clearScreen();
        std::cout << "═══════════════════════════════════════════" << std::endl;
        std::cout << "  Controlling: " << joint_name << std::endl;
        std::cout << "  Servo ID: " << servo_id << std::endl;
        std::cout << "═══════════════════════════════════════════" << std::endl;
        std::cout << std::endl;
        
        // Read current position
        int currentPos = sm_st.ReadPos(servo_id);
        if(currentPos != -1) {
            std::cout << "Current Position: " << currentPos << " / 4095" << std::endl;
            float percentage = (currentPos * 100.0) / 4095.0;
            std::cout << "                  (" << std::fixed << std::setprecision(1) 
                      << percentage << "% of range)" << std::endl;
        } else {
            std::cout << "Current Position: [Unable to read]" << std::endl;
        }
        
        std::cout << std::endl;
        std::cout << "OPTIONS:" << std::endl;
        std::cout << "  1. Set Specific Position (0-4095)" << std::endl;
        std::cout << "  2. Move to Center (2048)" << std::endl;
        std::cout << "  3. Move to Min (0)" << std::endl;
        std::cout << "  4. Move to Max (4095)" << std::endl;
        std::cout << "  5. Read Detailed Feedback" << std::endl;
        std::cout << "  6. Incremental Control (+/- adjustment)" << std::endl;
        std::cout << "  0. Back" << std::endl;
        std::cout << std::endl;
        std::cout << "Enter choice: ";
        
        int choice;
        std::cin >> choice;
        
        if(choice == 0) break;
        
        switch(choice) {
            case 1: {
                int position;
                std::cout << "Enter target position (0-4095): ";
                std::cin >> position;
                
                if(position < 0 || position > 4095) {
                    std::cout << "Invalid position! Must be 0-4095" << std::endl;
                } else {
                    std::cout << "Moving to position " << position << "..." << std::endl;
                    sm_st.WritePosEx(servo_id, position, currentSpeed, currentAcc);
                    std::cout << "Command sent!" << std::endl;
                }
                break;
            }
            case 2:
                std::cout << "Moving to center position (2048)..." << std::endl;
                sm_st.WritePosEx(servo_id, CENTER_POSITION, currentSpeed, currentAcc);
                std::cout << "Command sent!" << std::endl;
                break;
            case 3:
                std::cout << "Moving to minimum position (0)..." << std::endl;
                sm_st.WritePosEx(servo_id, MIN_POSITION, currentSpeed, currentAcc);
                std::cout << "Command sent!" << std::endl;
                break;
            case 4:
                std::cout << "Moving to maximum position (4095)..." << std::endl;
                sm_st.WritePosEx(servo_id, MAX_POSITION, currentSpeed, currentAcc);
                std::cout << "Command sent!" << std::endl;
                break;
            case 5: {
                std::cout << std::endl << "Reading detailed feedback..." << std::endl;
                if(sm_st.FeedBack(servo_id) != -1) {
                    int Pos = sm_st.ReadPos(-1);
                    int Speed = sm_st.ReadSpeed(-1);
                    int Load = sm_st.ReadLoad(-1);
                    int Voltage = sm_st.ReadVoltage(-1);
                    int Temper = sm_st.ReadTemper(-1);
                    int Move = sm_st.ReadMove(-1);
                    int Current = sm_st.ReadCurrent(-1);
                    
                    std::cout << "┌─────────────────────────────────┐" << std::endl;
                    std::cout << "│ Servo Feedback Data             │" << std::endl;
                    std::cout << "├─────────────────────────────────┤" << std::endl;
                    std::cout << "│ Position:    " << std::setw(6) << Pos << " (0-4095)  │" << std::endl;
                    std::cout << "│ Speed:       " << std::setw(6) << Speed << " steps/s  │" << std::endl;
                    std::cout << "│ Load:        " << std::setw(6) << Load << " (0-1000)  │" << std::endl;
                    std::cout << "│ Voltage:     " << std::setw(6) << Voltage << " (x0.1V)   │" << std::endl;
                    std::cout << "│              " << std::setw(6) << std::fixed << std::setprecision(1) 
                              << Voltage/10.0 << " V        │" << std::endl;
                    std::cout << "│ Temperature: " << std::setw(6) << Temper << " °C       │" << std::endl;
                    std::cout << "│ Moving:      " << std::setw(6) << (Move ? "Yes" : "No") << "          │" << std::endl;
                    std::cout << "│ Current:     " << std::setw(6) << Current << " mA       │" << std::endl;
                    std::cout << "└─────────────────────────────────┘" << std::endl;
                } else {
                    std::cout << "ERROR: Failed to read feedback!" << std::endl;
                }
                break;
            }
            case 6: {
                if(currentPos == -1) {
                    std::cout << "Cannot read current position!" << std::endl;
                    break;
                }
                
                int adjustment;
                std::cout << "Enter adjustment (+/- steps): ";
                std::cin >> adjustment;
                
                int newPos = currentPos + adjustment;
                if(newPos < 0) newPos = 0;
                if(newPos > 4095) newPos = 4095;
                
                std::cout << "Moving from " << currentPos << " to " << newPos << "..." << std::endl;
                sm_st.WritePosEx(servo_id, newPos, currentSpeed, currentAcc);
                std::cout << "Command sent!" << std::endl;
                break;
            }
            default:
                std::cout << "Invalid choice!" << std::endl;
        }
        
        std::cout << std::endl << "Press Enter to continue...";
        std::cin.ignore();
        std::cin.get();
    }
}

// Read all servo status
void readAllServos() {
    clearScreen();
    std::cout << "═══════════════════════════════════════════════════════════════════════" << std::endl;
    std::cout << "                    ALL SERVO STATUS REPORT                            " << std::endl;
    std::cout << "═══════════════════════════════════════════════════════════════════════" << std::endl;
    std::cout << std::endl;
    
    std::cout << std::left << std::setw(20) << "Joint" 
              << std::setw(6) << "ID" 
              << std::setw(10) << "Position" 
              << std::setw(8) << "Temp°C"
              << std::setw(10) << "Voltage"
              << std::setw(8) << "Moving" << std::endl;
    std::cout << "─────────────────────────────────────────────────────────────────────" << std::endl;
    
    for(int i = 0; i < NUM_SERVOS; i++) {
        int id = SERVO_IDS[i];
        std::cout << std::left << std::setw(20) << JOINT_NAMES[i] 
                  << std::setw(6) << id;
        
        if(sm_st.FeedBack(id) != -1) {
            int Pos = sm_st.ReadPos(-1);
            int Voltage = sm_st.ReadVoltage(-1);
            int Temper = sm_st.ReadTemper(-1);
            int Move = sm_st.ReadMove(-1);
            
            std::cout << std::setw(10) << Pos
                      << std::setw(8) << Temper
                      << std::setw(10) << std::fixed << std::setprecision(1) << Voltage/10.0
                      << std::setw(8) << (Move ? "Yes" : "No") << std::endl;
        } else {
            std::cout << "[ERROR - No response]" << std::endl;
        }
        usleep(50000); // Small delay between reads
    }
    
    std::cout << "─────────────────────────────────────────────────────────────────────" << std::endl;
    std::cout << std::endl << "Press Enter to continue...";
    std::cin.ignore();
    std::cin.get();
}

// Home all servos
void homeAllServos(int speed, int acc) {
    clearScreen();
    std::cout << "Homing all servos to center position (2048)..." << std::endl;
    std::cout << std::endl;
    
    for(int i = 0; i < NUM_SERVOS; i++) {
        std::cout << "Homing " << JOINT_NAMES[i] << " (ID " << SERVO_IDS[i] << ")..." << std::endl;
        sm_st.WritePosEx(SERVO_IDS[i], CENTER_POSITION, speed, acc);
        usleep(50000);
    }
    
    std::cout << std::endl << "All servos homed!" << std::endl;
    std::cout << "Press Enter to continue...";
    std::cin.ignore();
    std::cin.get();
}

// Move all servos to same position
void moveAllServos(int speed, int acc) {
    int position;
    std::cout << std::endl << "Enter target position for all servos (0-4095): ";
    std::cin >> position;
    
    if(position < 0 || position > 4095) {
        std::cout << "Invalid position!" << std::endl;
        std::cout << "Press Enter to continue...";
        std::cin.ignore();
        std::cin.get();
        return;
    }
    
    std::cout << std::endl << "Moving all servos to position " << position << "..." << std::endl;
    
    for(int i = 0; i < NUM_SERVOS; i++) {
        std::cout << "Moving " << JOINT_NAMES[i] << " (ID " << SERVO_IDS[i] << ")..." << std::endl;
        sm_st.WritePosEx(SERVO_IDS[i], position, speed, acc);
        usleep(50000);
    }
    
    std::cout << std::endl << "All servos moved!" << std::endl;
    std::cout << "Press Enter to continue...";
    std::cin.ignore();
    std::cin.get();
}

// Quick presets
void quickPresets(int speed, int acc) {
    clearScreen();
    std::cout << "═══════════════════════════════════════════" << std::endl;
    std::cout << "           QUICK PRESETS                   " << std::endl;
    std::cout << "═══════════════════════════════════════════" << std::endl;
    std::cout << std::endl;
    std::cout << "1. Home Position (All centered)" << std::endl;
    std::cout << "2. Straight Up" << std::endl;
    std::cout << "3. Rest Position" << std::endl;
    std::cout << "4. Custom Preset 1" << std::endl;
    std::cout << "5. Custom Preset 2" << std::endl;
    std::cout << "0. Back" << std::endl;
    std::cout << std::endl;
    std::cout << "Enter choice: ";
    
    int choice;
    std::cin >> choice;
    
    int positions[NUM_SERVOS];
    
    switch(choice) {
        case 1: // Home
            for(int i = 0; i < NUM_SERVOS; i++) positions[i] = 2048;
            break;
        case 2: // Straight up
            positions[0] = 2048;  // Base center
            positions[1] = 2048;  // Shoulder center
            positions[2] = 2048;  // Elbow center
            positions[3] = 2048;  // Wrist 1 center
            positions[4] = 2048;  // Wrist 2 center
            positions[5] = 2048;  // Wrist 3 center
            positions[6] = 2048;  // Gripper center
            break;
        case 3: // Rest position
            positions[0] = 2048;  // Base center
            positions[1] = 1024;  // Shoulder low
            positions[2] = 3072;  // Elbow folded
            positions[3] = 2048;  // Wrist 1 center
            positions[4] = 2048;  // Wrist 2 center
            positions[5] = 2048;  // Wrist 3 center
            positions[6] = 2048;  // Gripper center
            break;
        case 4: // Custom 1 - You can customize this
            positions[0] = 1536;
            positions[1] = 2048;
            positions[2] = 2560;
            positions[3] = 2048;
            positions[4] = 2048;
            positions[5] = 2048;
            positions[6] = 2048;
            break;
        case 5: // Custom 2 - You can customize this
            positions[0] = 2560;
            positions[1] = 2048;
            positions[2] = 1536;
            positions[3] = 2048;
            positions[4] = 2048;
            positions[5] = 2048;
            positions[6] = 2048;
            break;
        default:
            return;
    }
    
    std::cout << std::endl << "Executing preset..." << std::endl;
    for(int i = 0; i < NUM_SERVOS; i++) {
        std::cout << "Moving " << JOINT_NAMES[i] << " to " << positions[i] << "..." << std::endl;
        sm_st.WritePosEx(SERVO_IDS[i], positions[i], speed, acc);
        usleep(50000);
    }
    
    std::cout << std::endl << "Preset executed!" << std::endl;
    std::cout << "Press Enter to continue...";
    std::cin.ignore();
    std::cin.get();
}

// Ping all servos
void pingServos() {
    clearScreen();
    std::cout << "═══════════════════════════════════════════" << std::endl;
    std::cout << "      SERVO CONNECTION TEST (PING)         " << std::endl;
    std::cout << "═══════════════════════════════════════════" << std::endl;
    std::cout << std::endl;
    
    for(int i = 0; i < NUM_SERVOS; i++) {
        int id = SERVO_IDS[i];
        std::cout << std::left << std::setw(25) << JOINT_NAMES[i] 
                  << " (ID " << id << "): ";
        
        int result = sm_st.Ping(id);
        if(result != -1) {
            std::cout << "✓ Connected" << std::endl;
        } else {
            std::cout << "✗ No response" << std::endl;
        }
        usleep(50000);
    }
    
    std::cout << std::endl << "Press Enter to continue...";
    std::cin.ignore();
    std::cin.get();
}

// Set default parameters
void setDefaultParams(int& speed, int& acc) {
    clearScreen();
    std::cout << "═══════════════════════════════════════════" << std::endl;
    std::cout << "     SET DEFAULT SPEED & ACCELERATION      " << std::endl;
    std::cout << "═══════════════════════════════════════════" << std::endl;
    std::cout << std::endl;
    std::cout << "Current Speed: " << speed << " steps/sec (Max: 2400)" << std::endl;
    std::cout << "Current Acceleration: " << acc << " (x100 steps/sec²)" << std::endl;
    std::cout << std::endl;
    
    std::cout << "Enter new speed (0-2400, or -1 to keep current): ";
    int newSpeed;
    std::cin >> newSpeed;
    if(newSpeed >= 0 && newSpeed <= 2400) {
        speed = newSpeed;
        std::cout << "Speed updated to " << speed << std::endl;
    }
    
    std::cout << "Enter new acceleration (0-254, or -1 to keep current): ";
    int newAcc;
    std::cin >> newAcc;
    if(newAcc >= 0 && newAcc <= 254) {
        acc = newAcc;
        std::cout << "Acceleration updated to " << acc << std::endl;
    }
    
    std::cout << std::endl << "Press Enter to continue...";
    std::cin.ignore();
    std::cin.get();
}

// Circle motion in horizontal plane
void traceCircle(int speed, int acc) {
    clearScreen();
    std::cout << "═══════════════════════════════════════════════════════════════" << std::endl;
    std::cout << "           CIRCLE MOTION - HORIZONTAL PLANE                    " << std::endl;
    std::cout << "═══════════════════════════════════════════════════════════════" << std::endl;
    std::cout << std::endl;
    std::cout << "This feature moves servos in coordinated motion to trace a" << std::endl;
    std::cout << "circle in the horizontal plane using joints 1 and 2." << std::endl;
    std::cout << std::endl;
    std::cout << "Joint 1 (Base): Rotates to change angle around circle" << std::endl;
    std::cout << "Joint 2 (Shoulder): Adjusts to maintain circular radius" << std::endl;
    std::cout << "Other joints: Remain at current/specified positions" << std::endl;
    std::cout << std::endl;
    std::cout << "───────────────────────────────────────────────────────────────" << std::endl;
    std::cout << std::endl;
    
    // Get circle parameters
    int centerBase, radius, numPoints, loops;
    bool useOtherJoints;
    
    std::cout << "CIRCLE PARAMETERS:" << std::endl;
    std::cout << std::endl;
    
    std::cout << "Center position for Joint 1/Base (0-4095, default 2048): ";
    std::cin >> centerBase;
    if(centerBase < 0 || centerBase > 4095) centerBase = CENTER_POSITION;
    
    std::cout << "Radius in servo steps (50-1000, default 500): ";
    std::cin >> radius;
    if(radius < 50 || radius > 1000) radius = 500;
    
    std::cout << "Number of points per circle (8-360, default 36): ";
    std::cin >> numPoints;
    if(numPoints < 8 || numPoints > 360) numPoints = 36;
    
    std::cout << "Number of loops/circles to trace (1-100, default 1): ";
    std::cin >> loops;
    if(loops < 1 || loops > 100) loops = 1;
    
    std::cout << std::endl;
    std::cout << "Keep other joints (3-7) at center position? (1=Yes, 0=No): ";
    int keepCenter;
    std::cin >> keepCenter;
    useOtherJoints = (keepCenter == 1);
    
    std::cout << std::endl;
    std::cout << "───────────────────────────────────────────────────────────────" << std::endl;
    std::cout << "Configuration Summary:" << std::endl;
    std::cout << "  Center (Joint 1): " << centerBase << std::endl;
    std::cout << "  Radius: " << radius << " steps" << std::endl;
    std::cout << "  Points per circle: " << numPoints << std::endl;
    std::cout << "  Number of loops: " << loops << std::endl;
    std::cout << "  Speed: " << speed << " steps/sec" << std::endl;
    std::cout << "  Acceleration: " << acc << std::endl;
    std::cout << "  Other joints: " << (useOtherJoints ? "Centered" : "Unchanged") << std::endl;
    std::cout << "───────────────────────────────────────────────────────────────" << std::endl;
    std::cout << std::endl;
    std::cout << "Press Enter to start (Ctrl+C to abort)...";
    std::cin.ignore();
    std::cin.get();
    
    // Position other joints if requested
    if(useOtherJoints) {
        std::cout << std::endl << "Positioning joints 3-7 to center..." << std::endl;
        for(int i = 2; i < NUM_SERVOS; i++) {
            sm_st.WritePosEx(SERVO_IDS[i], CENTER_POSITION, speed, acc);
            usleep(30000);
        }
        sleep(1); // Wait for positioning
    }
    
    std::cout << std::endl << "Starting circular motion..." << std::endl;
    std::cout << "Press Ctrl+C to stop" << std::endl << std::endl;
    
    // Calculate time delay between points (in microseconds)
    // Rough estimation: time = distance / speed
    // Average distance between points on circle = (2 * PI * radius) / numPoints
    double arcLength = (2.0 * M_PI * radius) / numPoints;
    int delayUs = (int)((arcLength / speed) * 1000000.0);
    if(delayUs < 50000) delayUs = 50000; // Minimum 50ms
    if(delayUs > 2000000) delayUs = 2000000; // Maximum 2s
    
    int totalPoints = 0;
    
    // Execute circular motion
    for(int loop = 0; loop < loops; loop++) {
        std::cout << "Loop " << (loop + 1) << "/" << loops << std::endl;
        
        for(int point = 0; point < numPoints; point++) {
            // Calculate angle for this point
            double angle = (2.0 * M_PI * point) / numPoints;
            
            // Calculate positions
            // Joint 1 (Base) rotates around the circle
            int basePos = centerBase + (int)(radius * cos(angle));
            
            // Joint 2 (Shoulder) moves to create circular motion
            // This creates motion in the horizontal plane
            int shoulderPos = CENTER_POSITION + (int)(radius * sin(angle));
            
            // Clamp positions to valid range
            if(basePos < MIN_POSITION) basePos = MIN_POSITION;
            if(basePos > MAX_POSITION) basePos = MAX_POSITION;
            if(shoulderPos < MIN_POSITION) shoulderPos = MIN_POSITION;
            if(shoulderPos > MAX_POSITION) shoulderPos = MAX_POSITION;
            
            // Move servos
            sm_st.WritePosEx(SERVO_IDS[0], basePos, speed, acc);      // Joint 1 (Base)
            sm_st.WritePosEx(SERVO_IDS[1], shoulderPos, speed, acc);  // Joint 2 (Shoulder)
            
            totalPoints++;
            
            // Progress indicator every 10 points
            if(totalPoints % 10 == 0) {
                std::cout << "  Points: " << totalPoints << " | Angle: " 
                          << (int)(angle * 180.0 / M_PI) << "°" << std::endl;
            }
            
            // Wait for movement
            usleep(delayUs);
        }
    }
    
    std::cout << std::endl << "Circle motion completed!" << std::endl;
    std::cout << "Total points traced: " << totalPoints << std::endl;
    std::cout << std::endl;
    
    // Return to center
    std::cout << "Returning to center position..." << std::endl;
    sm_st.WritePosEx(SERVO_IDS[0], centerBase, speed, acc);
    sm_st.WritePosEx(SERVO_IDS[1], CENTER_POSITION, speed, acc);
    sleep(2);
    
    std::cout << std::endl << "Press Enter to continue...";
    std::cin.ignore();
    std::cin.get();
}

int main(int argc, char **argv)
{
    const char* port = "/dev/ttyACM0";  // Default port
    int baudrate = 1000000;  // Default 1M baud
    
    // Allow custom port from command line
    if(argc >= 2) {
        port = argv[1];
    }
    if(argc >= 3) {
        baudrate = atoi(argv[2]);
    }
    
    clearScreen();
    std::cout << "╔═══════════════════════════════════════════════════════╗" << std::endl;
    std::cout << "║       7-AXIS MANIPULATOR MANUAL CONTROL SYSTEM       ║" << std::endl;
    std::cout << "╚═══════════════════════════════════════════════════════╝" << std::endl;
    std::cout << std::endl;
    std::cout << "Initializing..." << std::endl;
    std::cout << "Port: " << port << std::endl;
    std::cout << "Baud Rate: " << baudrate << std::endl;
    std::cout << "Number of Servos: " << NUM_SERVOS << std::endl;
    std::cout << std::endl;
    
    // Initialize serial communication
    if(!sm_st.begin(baudrate, port)) {
        std::cout << "ERROR: Failed to initialize serial port " << port << std::endl;
        std::cout << std::endl;
        std::cout << "Troubleshooting:" << std::endl;
        std::cout << "  1. Check if servos are connected" << std::endl;
        std::cout << "  2. Verify port name (ls /dev/ttyACM* or /dev/ttyUSB*)" << std::endl;
        std::cout << "  3. Check permissions (sudo usermod -a -G dialout $USER)" << std::endl;
        std::cout << "  4. Try running with sudo" << std::endl;
        return 0;
    }
    
    std::cout << "✓ Serial port initialized successfully!" << std::endl;
    std::cout << std::endl;
    std::cout << "Press Enter to start...";
    std::cin.get();
    
    // Control parameters
    int currentSpeed = DEFAULT_SPEED;
    int currentAcc = DEFAULT_ACC;
    
    // Main loop
    while(true) {
        displayMenu();
        
        int choice;
        std::cin >> choice;
        
        if(choice == 0) {
            std::cout << std::endl << "Shutting down..." << std::endl;
            break;
        }
        
        switch(choice) {
            case 1: {
                displayServoMenu();
                int servoChoice;
                std::cin >> servoChoice;
                if(servoChoice > 0 && servoChoice <= NUM_SERVOS) {
                    controlServo(servoChoice - 1, currentSpeed, currentAcc);
                }
                break;
            }
            case 2:
                readAllServos();
                break;
            case 3:
                homeAllServos(currentSpeed, currentAcc);
                break;
            case 4:
                moveAllServos(currentSpeed, currentAcc);
                break;
            case 5:
                quickPresets(currentSpeed, currentAcc);
                break;
            case 6:
                pingServos();
                break;
            case 7:
                setDefaultParams(currentSpeed, currentAcc);
                break;
            case 8:
                traceCircle(currentSpeed, currentAcc);
                break;
            default:
                std::cout << "Invalid choice!" << std::endl;
                usleep(500000);
        }
    }
    
    sm_st.end();
    std::cout << "Program ended." << std::endl;
    return 0;
}
