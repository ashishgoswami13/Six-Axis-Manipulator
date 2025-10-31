/*
 * HomeAll.cpp
 * Move all 7 servos to their home (0°) position while respecting joint limits.
 * - Assumes servo IDs 1..6 map to joints J1..J6, ID 7 is gripper
 * - ST3215 uses 0..4095 steps => 360° range; center (0°) is at 2048 steps
 * - Limits are applied in degrees (see spec)
 * - Uses 1M baud (1000000) as ST3215 default
 */

#include <iostream>
#include <unistd.h>
#include "SCServo.h"

// Joint limits in degrees (min, max) for J1..J6 + Gripper
static const int JOINT_MIN_DEG[7] = {-165, -125, -140, -140, -140, -175, -180};
static const int JOINT_MAX_DEG[7] = { 165,  125,  140,  140,  140,  175,  180};

// Convert degrees (where 0° is center) to servo steps (0..4095)
static int degreesToSteps(double deg){
    // 0° -> 2048, +360° -> 2048+4096 -> wrap to steps
    double steps = 2048.0 + (deg / 360.0) * 4096.0;
    // Normalize to 0..4095
    while(steps < 0) steps += 4096.0;
    while(steps >= 4096.0) steps -= 4096.0;
    return (int)(steps + 0.5);
}

int main(int argc, char** argv){
    const char* port = "/dev/ttyACM0";
    if(argc >= 2) port = argv[1];

    std::cout << "HomeAll - Move joints 1..6 + gripper (7) to home (0°) respecting joint limits" << std::endl;
    std::cout << "Port: " << port << std::endl;
    std::cout << "Baud: 1000000 (1M)" << std::endl;

    SMS_STS sm_st;
    if(!sm_st.begin(1000000, port)){
        std::cerr << "ERROR: Failed to initialize serial on " << port << std::endl;
        return 1;
    }

    // Safety speed: limit to max joint speed 150°/s -> convert to steps/sec
    const double max_deg_per_sec = 150.0;
    int max_steps_per_sec = (int)((max_deg_per_sec / 360.0) * 4096.0 + 0.5); // ~1707
    int travel_speed = std::min(1000, max_steps_per_sec); // choose safe 1000 steps/sec
    int acc = 50; // default acceleration

    std::cout << "Using speed (steps/s): " << travel_speed << " (capped to 150 deg/s)" << std::endl;

    // Enable torque and move each joint to 0 deg (clamped)
    for(int i=0;i<7;i++){
        int id = i+1; // servo IDs 1..7
        double want_deg = 0.0; // home = 0°
        // Clamp to joint limits
        if(want_deg < JOINT_MIN_DEG[i]) want_deg = JOINT_MIN_DEG[i];
        if(want_deg > JOINT_MAX_DEG[i]) want_deg = JOINT_MAX_DEG[i];
        int steps = degreesToSteps(want_deg);

        const char* label = (i < 6) ? "Joint" : "Gripper";
        std::cout << label << " "<< id << ": target "<< want_deg << "° -> "<< steps << " steps" << std::endl;
        sm_st.EnableTorque(id, 1); // enable torque
        int res = sm_st.WritePosEx(id, steps, travel_speed, acc);
        if(res == -1){
            std::cerr << "Failed to send position to servo "<< id << std::endl;
        }
        usleep(100000); // short delay between commands
    }

    // Wait a bit for motion to complete
    std::cout << "Waiting for motion to complete..." << std::endl;
    sleep(2);

    // Read back positions
    for(int i=0;i<7;i++){
        int id = i+1;
        const char* label = (i < 6) ? "Joint" : "Gripper";
        if(sm_st.FeedBack(id) != -1){
            int pos = sm_st.ReadPos(-1); // from cache
            double angle = (pos / 4096.0) * 360.0;
            // Convert angle to -180..+180 centered around 0
            double centered = angle;
            if(centered >= 360.0) centered -= 360.0;
            if(centered > 180.0) centered -= 360.0;
            std::cout << label <<" "<<id<<" current steps="<<pos<<" angle="<<centered<<"°"<<std::endl;
        }else{
            std::cout << "Failed to read feedback for servo "<<id<<std::endl;
        }
    }

    sm_st.end();
    std::cout << "Done." << std::endl;
    return 0;
}
