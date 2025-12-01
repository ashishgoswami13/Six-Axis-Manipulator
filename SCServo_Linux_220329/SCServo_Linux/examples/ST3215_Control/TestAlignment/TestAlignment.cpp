/*
 * TestAlignment.cpp - CAMERA ALIGNMENT TEST
 * ==========================================
 * 
 * PURPOSE: Move robot in specific directions to verify camera alignment
 * 
 * MOVEMENT SEQUENCE:
 * 1. HOME - All joints at 0°
 * 2. FRONT - Extend arm forward (J2 and J3)
 * 3. LEFT - Rotate base left (J1 positive)
 * 4. RIGHT - Rotate base right (J1 negative)
 * 5. HOME - Return to start
 * 
 * USE WITH: camera_arm_sync_test.py running in another terminal
 */

#include <iostream>
#include <unistd.h>
#include "SCServo.h"

// Joint limits
static const int JOINT_MIN_DEG[7] = {-165, -125, -140, -140, -140, -175, -180};
static const int JOINT_MAX_DEG[7] = { 165,  125,  140,  140,  140,  175,  180};

// COORDINATE TRANSFORM: Physical robot is rotated 90° clockwise from zero
// To align with camera/code coordinates, we add 90° to J1 commands
static const double J1_OFFSET = 90.0;  // Compensate for clockwise physical rotation

// Convert degrees to servo steps
static int degreesToSteps(double deg){
    double steps = 2048.0 + (deg / 360.0) * 4096.0;
    while(steps < 0) steps += 4096.0;
    while(steps >= 4096.0) steps -= 4096.0;
    return (int)(steps + 0.5);
}

// Move multiple joints to target positions
void moveJoints(SMS_STS& sm_st, const double* target_deg, int speed = 800, int acc = 50){
    // Send commands to all joints
    for(int i = 0; i < 7; i++){
        int id = i + 1;
        double deg = target_deg[i];
        
        // Apply coordinate transform for J1 (base rotation)
        // Physical robot is rotated 90° clockwise, so we compensate
        if(i == 0){  // J1 (base joint)
            deg += J1_OFFSET;
            std::cout << "  J1 transform: " << target_deg[i] << "° → " << deg << "° (offset: " << J1_OFFSET << "°)" << std::endl;
        }
        
        // Clamp to limits
        if(deg < JOINT_MIN_DEG[i]) deg = JOINT_MIN_DEG[i];
        if(deg > JOINT_MAX_DEG[i]) deg = JOINT_MAX_DEG[i];
        
        int steps = degreesToSteps(deg);
        sm_st.EnableTorque(id, 1);
        sm_st.WritePosEx(id, steps, speed, acc);
        usleep(50000); // 50ms between commands
    }
}

// Print current movement
void printMovement(const char* name, const char* description, const char* camera_note){
    std::cout << "\n" << std::string(70, '=') << std::endl;
    std::cout << name << std::endl;
    std::cout << std::string(70, '=') << std::endl;
    std::cout << description << std::endl;
    std::cout << "📹 " << camera_note << std::endl;
    std::cout << std::string(70, '=') << std::endl;
}

int main(int argc, char** argv){
    const char* port = "/dev/ttyACM0";
    if(argc >= 2) port = argv[1];
    
    std::cout << "\n" << std::string(70, '=') << std::endl;
    std::cout << "ROBOT MOVEMENT TEST - Camera Alignment Verification" << std::endl;
    std::cout << std::string(70, '=') << std::endl;
    std::cout << "\nThis will move the robot to test camera alignment:" << std::endl;
    std::cout << "  1. HOME position" << std::endl;
    std::cout << "  2. FRONT - Extend forward" << std::endl;
    std::cout << "  3. LEFT - Rotate base left" << std::endl;
    std::cout << "  4. RIGHT - Rotate base right" << std::endl;
    std::cout << "  5. HOME - Return" << std::endl;
    std::cout << "\n🔄 COORDINATE TRANSFORM ACTIVE:" << std::endl;
    std::cout << "  Physical robot rotated 90° clockwise from zero" << std::endl;
    std::cout << "  J1 offset: " << J1_OFFSET << "° (compensates for physical rotation)" << std::endl;
    std::cout << "\n⚠️  SAFETY: Ensure workspace is clear!" << std::endl;
    std::cout << "\nPort: " << port << std::endl;
    std::cout << std::string(70, '=') << std::endl;
    
    std::cout << "\nPress ENTER to start, or Ctrl+C to cancel...";
    std::cin.get();
    
    // Initialize servo controller
    SMS_STS sm_st;
    if(!sm_st.begin(1000000, port)){
        std::cerr << "❌ Failed to initialize serial on " << port << std::endl;
        return 1;
    }
    
    std::cout << "\n✅ Connected to robot\n" << std::endl;
    
    // Define positions for each test
    // Format: {J1, J2, J3, J4, J5, J6, Gripper}
    
    double home[7]  = {0, 0, 0, 0, 0, 0, 0};
    double front[7] = {0, 35, 35, 0, 0, 0, 0};  // Extend J2 and J3 forward
    double left[7]  = {-45, 35, 35, 0, 0, 0, 0}; // J1 rotate left (negative after transform)
    double right[7] = {45, 35, 35, 0, 0, 0, 0}; // J1 rotate right (positive after transform)
    
    int wait_time = 4; // seconds between movements
    
    // ========================================================================
    // STEP 1: HOME
    // ========================================================================
    printMovement(
        "STEP 1: HOME POSITION",
        "Moving all joints to 0°...",
        "Watch: Robot should return to neutral position"
    );
    
    moveJoints(sm_st, home);
    std::cout << "⏱️  Waiting " << wait_time << " seconds...\n" << std::endl;
    sleep(wait_time);
    
    // ========================================================================
    // STEP 2: FRONT
    // ========================================================================
    printMovement(
        "STEP 2: EXTEND FRONT",
        "Moving J2=35°, J3=35° (extending arm forward)...",
        "Watch camera: Arm should extend FORWARD/AWAY from base"
    );
    
    moveJoints(sm_st, front);
    std::cout << "⏱️  Waiting " << wait_time << " seconds...\n" << std::endl;
    sleep(wait_time);
    
    // ========================================================================
    // STEP 3: LEFT
    // ========================================================================
    printMovement(
        "STEP 3: ROTATE LEFT",
        "Moving J1=45° (rotating base counterclockwise)...",
        "Watch camera: Arm should swing to the LEFT"
    );
    
    moveJoints(sm_st, left);
    std::cout << "⏱️  Waiting " << wait_time << " seconds...\n" << std::endl;
    sleep(wait_time);
    
    // ========================================================================
    // STEP 4: RIGHT
    // ========================================================================
    printMovement(
        "STEP 4: ROTATE RIGHT",
        "Moving J1=-45° (rotating base clockwise)...",
        "Watch camera: Arm should swing to the RIGHT"
    );
    
    moveJoints(sm_st, right);
    std::cout << "⏱️  Waiting " << wait_time << " seconds...\n" << std::endl;
    sleep(wait_time);
    
    // ========================================================================
    // STEP 5: RETURN HOME
    // ========================================================================
    printMovement(
        "STEP 5: RETURN HOME",
        "Moving all joints back to 0°...",
        "Watch: Robot returns to start position"
    );
    
    moveJoints(sm_st, home);
    std::cout << "⏱️  Waiting " << wait_time << " seconds...\n" << std::endl;
    sleep(wait_time);
    
    // Cleanup
    sm_st.end();
    
    std::cout << "\n" << std::string(70, '=') << std::endl;
    std::cout << "✅ MOVEMENT TEST COMPLETE!" << std::endl;
    std::cout << std::string(70, '=') << std::endl;
    std::cout << "\nVERIFICATION CHECKLIST:" << std::endl;
    std::cout << "  □ FRONT: Did arm extend forward in camera view?" << std::endl;
    std::cout << "  □ LEFT:  Did arm move left in camera view?" << std::endl;
    std::cout << "  □ RIGHT: Did arm move right in camera view?" << std::endl;
    std::cout << "\nIf all matched → Camera alignment is CORRECT! ✅" << std::endl;
    std::cout << "If not → Camera needs repositioning or coordinate transform" << std::endl;
    std::cout << std::string(70, '=') << std::endl;
    
    return 0;
}
