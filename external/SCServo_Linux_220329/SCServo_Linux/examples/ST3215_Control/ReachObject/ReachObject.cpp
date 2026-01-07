/*
 * ReachObject.cpp - MOVE ARM TO DETECTED OBJECT WITH VERIFICATION
 * ================================================================
 * 
 * PURPOSE: Move robot arm to reach a detected object with multiple attempts
 *          and verification steps
 * 
 * USAGE:
 *   ./ReachObject <j1> <j2> <j3> [attempts]
 * 
 * Example:
 *   ./ReachObject 15.5 35.0 35.0 3
 * 
 * This makes up to 3 attempts to reach and pick up the object.
 */

#include <iostream>
#include <unistd.h>
#include <cstdlib>
#include "SCServo.h"

// Joint limits
static const int JOINT_MIN_DEG[7] = {-165, -125, -140, -140, -140, -175, -180};
static const int JOINT_MAX_DEG[7] = { 165,  125,  140,  140,  140,  175,  180};

// Coordinate transform offset
static const double J1_OFFSET = 90.0;

// Convert degrees to servo steps
static int degreesToSteps(double deg){
    double steps = 2048.0 + (deg / 360.0) * 4096.0;
    while(steps < 0) steps += 4096.0;
    while(steps >= 4096.0) steps -= 4096.0;
    return (int)(steps + 0.5);
}

// Move single joint and verify
bool moveJoint(SMS_STS& sm_st, int id, double target_deg, int speed = 600){
    const char* joint_names[] = {"J1", "J2", "J3", "J4", "J5", "J6", "Gripper"};
    
    // Apply coordinate transform for J1
    double adjusted_deg = target_deg;
    if(id == 1){
        adjusted_deg += J1_OFFSET;
    }
    
    // Clamp to limits
    int idx = id - 1;
    if(adjusted_deg < JOINT_MIN_DEG[idx]){
        std::cout << "⚠️  " << joint_names[idx] << " clamped: " << adjusted_deg << "° → " << JOINT_MIN_DEG[idx] << "°" << std::endl;
        adjusted_deg = JOINT_MIN_DEG[idx];
    }
    if(adjusted_deg > JOINT_MAX_DEG[idx]){
        std::cout << "⚠️  " << joint_names[idx] << " clamped: " << adjusted_deg << "° → " << JOINT_MAX_DEG[idx] << "°" << std::endl;
        adjusted_deg = JOINT_MAX_DEG[idx];
    }
    
    int steps = degreesToSteps(adjusted_deg);
    
    sm_st.EnableTorque(id, 1);
    int result = sm_st.WritePosEx(id, steps, speed, 50);
    
    if(result == -1){
        std::cerr << "❌ Failed to send command to " << joint_names[idx] << std::endl;
        return false;
    }
    
    std::cout << "  " << joint_names[idx] << ": " << target_deg << "° → " << adjusted_deg << "° (steps: " << steps << ")" << std::endl;
    return true;
}

// Move to home position
void moveHome(SMS_STS& sm_st){
    std::cout << "\n🏠 Returning to HOME position..." << std::endl;
    for(int i = 0; i < 7; i++){
        moveJoint(sm_st, i + 1, 0.0);
        usleep(50000);
    }
    sleep(2);
}

// Approach sequence with multiple steps
bool approachObject(SMS_STS& sm_st, double j1, double j2, double j3, int attempt){
    std::cout << "\n" << std::string(70, '=') << std::endl;
    std::cout << "ATTEMPT " << attempt << " - APPROACHING OBJECT" << std::endl;
    std::cout << std::string(70, '=') << std::endl;
    
    // Step 1: Position base (J1) first
    std::cout << "\nStep 1: Rotating base to align with object..." << std::endl;
    if(!moveJoint(sm_st, 1, j1, 400)){
        return false;
    }
    sleep(2);
    
    // Step 2: Extend arm partially (70% of target)
    std::cout << "\nStep 2: Extending arm partially..." << std::endl;
    double j2_partial = j2 * 0.7;
    double j3_partial = j3 * 0.7;
    
    moveJoint(sm_st, 2, j2_partial, 400);
    usleep(100000);
    moveJoint(sm_st, 3, j3_partial, 400);
    sleep(2);
    
    // Step 3: Full extension to target
    std::cout << "\nStep 3: Extending to full target position..." << std::endl;
    moveJoint(sm_st, 2, j2, 300);
    usleep(100000);
    moveJoint(sm_st, 3, j3, 300);
    sleep(2);
    
    // Step 4: Fine adjustment - try slight variations
    if(attempt > 1){
        std::cout << "\nStep 4: Fine adjustment (attempt " << attempt << ")..." << std::endl;
        double offset = (attempt - 1) * 3.0;  // ±3° per attempt
        moveJoint(sm_st, 2, j2 + offset, 200);
        usleep(100000);
        moveJoint(sm_st, 3, j3 + offset, 200);
        sleep(2);
    }
    
    // Step 5: Close gripper to attempt pickup
    std::cout << "\nStep 5: Closing gripper to grasp object..." << std::endl;
    moveJoint(sm_st, 7, -30, 300);  // Close gripper (negative angle)
    sleep(2);
    
    // Step 6: Lift slightly to test if object is held
    std::cout << "\nStep 6: Lifting to verify grasp..." << std::endl;
    moveJoint(sm_st, 2, j2 - 10, 200);  // Lift shoulder
    sleep(2);
    
    // Read gripper position to check if it closed fully (object in grip)
    std::cout << "\nVerifying gripper state..." << std::endl;
    if(sm_st.FeedBack(7) != -1){
        int gripper_pos = sm_st.ReadPos(-1);
        double gripper_angle = (gripper_pos / 4096.0) * 360.0;
        if(gripper_angle > 180.0) gripper_angle -= 360.0;
        
        std::cout << "Gripper position: " << gripper_angle << "°" << std::endl;
        
        // If gripper didn't close completely, object might be in grip
        // (gripper stops when it hits resistance)
        if(gripper_angle > -25){  // Didn't reach full -30°
            std::cout << "✅ Object appears to be grasped! (gripper stopped early)" << std::endl;
            return true;
        } else {
            std::cout << "❌ Gripper closed fully - likely missed object" << std::endl;
            
            // Open gripper and retry
            std::cout << "Opening gripper..." << std::endl;
            moveJoint(sm_st, 7, 0, 300);
            sleep(1);
            return false;
        }
    }
    
    return false;
}

int main(int argc, char** argv){
    if(argc < 4){
        std::cerr << "Usage: " << argv[0] << " <j1_angle> <j2_angle> <j3_angle> [max_attempts]" << std::endl;
        std::cerr << "\nExample:" << std::endl;
        std::cerr << "  " << argv[0] << " 15.5 35.0 35.0 3" << std::endl;
        std::cerr << "\nThis tries up to 3 times to reach and grasp the object." << std::endl;
        return 1;
    }
    
    // Parse arguments
    double j1 = atof(argv[1]);
    double j2 = atof(argv[2]);
    double j3 = atof(argv[3]);
    int max_attempts = (argc >= 5) ? atoi(argv[4]) : 3;  // Default 3 attempts
    
    const char* port = "/dev/ttyACM0";
    if(argc >= 6) port = argv[5];
    
    std::cout << "\n" << std::string(70, '=') << std::endl;
    std::cout << "REACH AND GRASP OBJECT - Multi-Attempt System" << std::endl;
    std::cout << std::string(70, '=') << std::endl;
    std::cout << "Target angles:" << std::endl;
    std::cout << "  J1 (base): " << j1 << "°" << std::endl;
    std::cout << "  J2 (shoulder): " << j2 << "°" << std::endl;
    std::cout << "  J3 (elbow): " << j3 << "°" << std::endl;
    std::cout << "Max attempts: " << max_attempts << std::endl;
    std::cout << "Port: " << port << std::endl;
    std::cout << std::string(70, '=') << std::endl;
    
    // Initialize servo controller
    SMS_STS sm_st;
    if(!sm_st.begin(1000000, port)){
        std::cerr << "❌ Failed to initialize serial on " << port << std::endl;
        return 1;
    }
    
    std::cout << "✅ Connected to robot\n" << std::endl;
    
    // Start from home
    moveHome(sm_st);
    
    // Try multiple attempts
    bool success = false;
    for(int attempt = 1; attempt <= max_attempts; attempt++){
        success = approachObject(sm_st, j1, j2, j3, attempt);
        
        if(success){
            std::cout << "\n" << std::string(70, '=') << std::endl;
            std::cout << "✅ SUCCESS! Object grasped on attempt " << attempt << std::endl;
            std::cout << std::string(70, '=') << std::endl;
            
            // Move to a safe position with object
            std::cout << "\nMoving to safe position with object..." << std::endl;
            moveJoint(sm_st, 2, 0, 300);
            usleep(100000);
            moveJoint(sm_st, 3, 0, 300);
            sleep(2);
            
            break;
        } else if(attempt < max_attempts){
            std::cout << "\n⚠️  Attempt " << attempt << " failed. Retrying..." << std::endl;
            // Return to home before next attempt
            moveHome(sm_st);
        }
    }
    
    if(!success){
        std::cout << "\n" << std::string(70, '=') << std::endl;
        std::cout << "❌ Failed to grasp object after " << max_attempts << " attempts" << std::endl;
        std::cout << std::string(70, '=') << std::endl;
        std::cout << "\nSuggestions:" << std::endl;
        std::cout << "  - Verify object position with camera" << std::endl;
        std::cout << "  - Adjust target angles manually" << std::endl;
        std::cout << "  - Check if object is graspable" << std::endl;
        
        // Return to home
        moveHome(sm_st);
    }
    
    sm_st.end();
    
    return success ? 0 : 1;
}
