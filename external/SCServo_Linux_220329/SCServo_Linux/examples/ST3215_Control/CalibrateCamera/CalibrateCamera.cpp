/*
 * CalibrateCamera.cpp - CAMERA-ROBOT COORDINATE CALIBRATION
 * ===========================================================
 * 
 * PURPOSE: Collect calibration data by moving robot to known positions
 *          while capturing corresponding camera frames.
 * 
 * PROCESS:
 *   1. Move robot to home position
 *   2. Move to a grid of calibration points in workspace
 *   3. At each point, capture frame and record robot joint angles
 *   4. Save calibration data for processing
 * 
 * OUTPUT: calibration_data.txt with format:
 *   <timestamp> <J1> <J2> <J3> <J4> <J5> <J6> <gripper> <frame_file>
 * 
 * USAGE:
 *   ./CalibrateCamera [port]
 */

#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <unistd.h>
#include <sys/time.h>
#include "SCServo.h"

// Joint limits
static const int JOINT_MIN_DEG[7] = {-165, -125, -140, -140, -140, -175, -180};
static const int JOINT_MAX_DEG[7] = { 165,  125,  140,  140,  140,  175,  180};

// Coordinate transform
static const double J1_OFFSET = 90.0;

// Convert degrees to servo steps
static int degreesToSteps(double deg){
    double steps = 2048.0 + (deg / 360.0) * 4096.0;
    while(steps < 0) steps += 4096.0;
    while(steps >= 4096.0) steps -= 4096.0;
    return (int)(steps + 0.5);
}

// Get current time in microseconds
long long getCurrentTimeMicros() {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (long long)tv.tv_sec * 1000000LL + (long long)tv.tv_usec;
}

// Move single joint with coordinate transform
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
        adjusted_deg = JOINT_MIN_DEG[idx];
    }
    if(adjusted_deg > JOINT_MAX_DEG[idx]){
        adjusted_deg = JOINT_MAX_DEG[idx];
    }
    
    int steps = degreesToSteps(adjusted_deg);
    
    sm_st.EnableTorque(id, 1);
    int result = sm_st.WritePosEx(id, steps, speed, 50);
    
    if(result == -1){
        std::cerr << "❌ Failed to send command to " << joint_names[idx] << std::endl;
        return false;
    }
    
    return true;
}

// Move to specific position
void moveToPosition(SMS_STS& sm_st, double j1, double j2, double j3, double j4, double j5, double j6){
    std::cout << "  Moving to: J1=" << j1 << "° J2=" << j2 << "° J3=" << j3 
              << "° J4=" << j4 << "° J5=" << j5 << "° J6=" << j6 << "°" << std::endl;
    
    moveJoint(sm_st, 1, j1, 400);
    usleep(100000);
    moveJoint(sm_st, 2, j2, 400);
    usleep(100000);
    moveJoint(sm_st, 3, j3, 400);
    usleep(100000);
    moveJoint(sm_st, 4, j4, 300);
    usleep(100000);
    moveJoint(sm_st, 5, j5, 300);
    usleep(100000);
    moveJoint(sm_st, 6, j6, 300);
    
    // Wait for movement to complete
    sleep(3);
}

// Calibration point structure
struct CalibrationPoint {
    double j1, j2, j3, j4, j5, j6;
    std::string description;
};

int main(int argc, char** argv){
    const char* port = "/dev/ttyACM0";
    if(argc >= 2) port = argv[1];
    
    std::cout << "\n" << std::string(70, '=') << std::endl;
    std::cout << "CAMERA-ROBOT CALIBRATION DATA COLLECTION" << std::endl;
    std::cout << std::string(70, '=') << std::endl;
    std::cout << "\nThis program will move the robot through a series of" << std::endl;
    std::cout << "calibration positions while Python captures camera frames." << std::endl;
    std::cout << "\nPort: " << port << std::endl;
    std::cout << std::string(70, '=') << std::endl;
    
    // Initialize servo controller
    SMS_STS sm_st;
    if(!sm_st.begin(1000000, port)){
        std::cerr << "❌ Failed to initialize serial on " << port << std::endl;
        return 1;
    }
    
    std::cout << "\n✅ Connected to robot\n" << std::endl;
    
    // Define calibration grid points
    // We'll create a grid in the robot's workspace
    std::vector<CalibrationPoint> calibration_points;
    
    // Home position
    calibration_points.push_back({0, 0, 0, 0, 0, 0, "Home - Center"});
    
    // Grid points in horizontal plane (varying J1 and J2/J3)
    // J1 (base rotation): -60, -30, 0, 30, 60 degrees
    // J2/J3 (reach): combinations for different distances
    
    double j1_values[] = {-60, -30, 0, 30, 60};
    double reach_configs[][2] = {
        {20, 20},   // Close
        {35, 35},   // Medium
        {50, 50}    // Far
    };
    
    for(double j1 : j1_values){
        for(auto& reach : reach_configs){
            double j2 = reach[0];
            double j3 = reach[1];
            
            std::stringstream ss;
            ss << "J1=" << j1 << " Reach=" << j2 << "/" << j3;
            
            calibration_points.push_back({j1, j2, j3, 0, 0, 0, ss.str()});
        }
    }
    
    // Add some elevated points
    calibration_points.push_back({0, -20, -20, 0, 0, 0, "Elevated center"});
    calibration_points.push_back({-45, -20, -20, 0, 0, 0, "Elevated left"});
    calibration_points.push_back({45, -20, -20, 0, 0, 0, "Elevated right"});
    
    std::cout << "Total calibration points: " << calibration_points.size() << std::endl;
    std::cout << "\n⚠️  SAFETY: Ensure workspace is clear!" << std::endl;
    std::cout << "\nPress ENTER to start calibration sequence...";
    std::cin.get();
    
    // Open output file
    std::ofstream outfile("/home/dev/Six Axis Manipulator/VLM/calibration_data.txt");
    if(!outfile.is_open()){
        std::cerr << "❌ Failed to open calibration_data.txt" << std::endl;
        return 1;
    }
    
    std::cout << "\n" << std::string(70, '=') << std::endl;
    std::cout << "STARTING CALIBRATION SEQUENCE" << std::endl;
    std::cout << std::string(70, '=') << std::endl;
    
    // Move through each calibration point
    for(size_t i = 0; i < calibration_points.size(); i++){
        CalibrationPoint& cp = calibration_points[i];
        
        std::cout << "\n[" << (i+1) << "/" << calibration_points.size() << "] " 
                  << cp.description << std::endl;
        
        // Move to position
        moveToPosition(sm_st, cp.j1, cp.j2, cp.j3, cp.j4, cp.j5, cp.j6);
        
        // Get timestamp
        long long timestamp = getCurrentTimeMicros();
        
        // Write to file (Python will capture frame based on this)
        outfile << timestamp << " "
                << cp.j1 << " " << cp.j2 << " " << cp.j3 << " "
                << cp.j4 << " " << cp.j5 << " " << cp.j6 << " "
                << "0 "  // gripper position
                << "frame_" << i << ".jpg" << std::endl;
        outfile.flush();
        
        std::cout << "  ✓ Position reached" << std::endl;
        std::cout << "  ⏸️  Waiting for camera capture..." << std::endl;
        
        // Wait for camera to capture
        sleep(2);
        
        std::cout << "  ✓ Point " << (i+1) << " complete" << std::endl;
    }
    
    outfile.close();
    
    // Return to home
    std::cout << "\n" << std::string(70, '=') << std::endl;
    std::cout << "CALIBRATION COMPLETE - Returning to home" << std::endl;
    std::cout << std::string(70, '=') << std::endl;
    
    moveToPosition(sm_st, 0, 0, 0, 0, 0, 0);
    
    sm_st.end();
    
    std::cout << "\n✅ Calibration data collection complete!" << std::endl;
    std::cout << "Data saved to: /home/dev/Six Axis Manipulator/VLM/calibration_data.txt" << std::endl;
    std::cout << "\nNext step: Run Python script to process calibration data" << std::endl;
    
    return 0;
}
