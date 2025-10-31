/*
 * Ping.cpp
 * Test if ST3215 servo motor is connected and responsive
 * For Waveshare ST3215 servo motor on /dev/ttyACM0
 */

#include <iostream>
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
    
    std::cout << "=== ST3215 Servo Ping Test ===" << std::endl;
    std::cout << "Port: " << port << std::endl;
    std::cout << "Servo ID: " << servo_id << std::endl;
    std::cout << "Baud Rate: 1000000 (1M)" << std::endl;
    std::cout << "===============================" << std::endl;
    
    // Initialize serial communication at 1M baud (ST3215 factory default)
    if(!sm_st.begin(1000000, port)){
        std::cout << "ERROR: Failed to initialize serial port " << port << std::endl;
        std::cout << "Make sure:" << std::endl;
        std::cout << "  1. The servo is connected" << std::endl;
        std::cout << "  2. You have permissions (run with sudo or add user to dialout group)" << std::endl;
        std::cout << "  3. The port name is correct" << std::endl;
        return 0;
    }
    
    std::cout << "Serial port initialized successfully!" << std::endl;
    
    // Ping the servo
    int ID = sm_st.Ping(servo_id);
    if(ID != -1){
        std::cout << "SUCCESS: Servo responded!" << std::endl;
        std::cout << "Servo ID: " << ID << std::endl;
    }else{
        std::cout << "ERROR: No response from servo ID " << servo_id << std::endl;
        std::cout << "Check:" << std::endl;
        std::cout << "  1. Servo is powered on" << std::endl;
        std::cout << "  2. Servo ID matches (default is usually 1)" << std::endl;
        std::cout << "  3. Baud rate is correct (115200)" << std::endl;
    }
    
    sm_st.end();
    return (ID != -1) ? 1 : 0;
}
