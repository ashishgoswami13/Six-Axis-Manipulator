/*
 * WritePos.cpp
 * Control ST3215 servo position
 * For Waveshare ST3215 servo motor on /dev/ttyACM0
 * 
 * ST3215 Position Range: 0-4095 (approximately 0-360 degrees)
 * Center position: ~2048
 */

#include <iostream>
#include <unistd.h>
#include "SCServo.h"

SMS_STS sm_st;

int main(int argc, char **argv)
{
    const char* port = "/dev/ttyACM0";  // Default port
    int servo_id = 1;  // Default servo ID
    
    // Allow custom port and ID from command line
    if(argc >= 2){
        port = argv[1];
    }
    if(argc >= 3){
        servo_id = atoi(argv[2]);
    }
    
    std::cout << "=== ST3215 Servo Position Control ===" << std::endl;
    std::cout << "Port: " << port << std::endl;
    std::cout << "Servo ID: " << servo_id << std::endl;
    std::cout << "Baud Rate: 1000000 (1M)" << std::endl;
    std::cout << "=====================================" << std::endl;
    
    // Initialize serial communication at 1M baud (ST3215 factory default)
    if(!sm_st.begin(1000000, port)){
        std::cout << "ERROR: Failed to initialize serial port " << port << std::endl;
        return 0;
    }
    
    std::cout << "Serial port initialized successfully!" << std::endl;
    std::cout << "Moving servo between positions..." << std::endl;
    std::cout << "Press Ctrl+C to stop" << std::endl << std::endl;
    
    // Main control loop - oscillate between two positions
    while(1){
        // Move to position 4095 (max position)
        // Parameters: ID, Position (0-4095), Speed (0-2400 steps/sec), Acceleration (50*100 steps/sec²)
        sm_st.WritePosEx(servo_id, 4095, 2400, 50);
        std::cout << "Position: 4095 (Max)" << std::endl;
        usleep(2187 * 1000);  // Wait for movement to complete: [(4095-0)/2400]*1000 + [2400/(50*100)]*1000
        
        // Move to position 0 (min position)
        sm_st.WritePosEx(servo_id, 0, 2400, 50);
        std::cout << "Position: 0 (Min)" << std::endl;
        usleep(2187 * 1000);  // Wait for movement to complete
    }
    
    sm_st.end();
    return 1;
}
