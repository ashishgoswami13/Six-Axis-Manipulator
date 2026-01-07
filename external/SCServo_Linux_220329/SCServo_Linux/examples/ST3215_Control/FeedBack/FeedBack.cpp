/*
 * FeedBack.cpp
 * Read ST3215 servo status and feedback data
 * For Waveshare ST3215 servo motor on /dev/ttyACM0
 * 
 * Reads: Position, Speed, Load, Voltage, Temperature, Movement status, Current
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
    
    std::cout << "=== ST3215 Servo Feedback Reader ===" << std::endl;
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
    std::cout << "Reading servo feedback data..." << std::endl;
    std::cout << "Press Ctrl+C to stop" << std::endl << std::endl;
    
    int readCount = 0;
    
    // Main feedback loop
    while(1){
        int Pos, Speed, Load, Voltage, Temper, Move, Current;
        
        // Method 1: Single feedback instruction to read all parameters efficiently
        if(sm_st.FeedBack(servo_id) != -1){
            Pos = sm_st.ReadPos(-1);        // -1 means read from cached data
            Speed = sm_st.ReadSpeed(-1);
            Load = sm_st.ReadLoad(-1);
            Voltage = sm_st.ReadVoltage(-1);
            Temper = sm_st.ReadTemper(-1);
            Move = sm_st.ReadMove(-1);
            Current = sm_st.ReadCurrent(-1);
            
            std::cout << "=== Read #" << ++readCount << " ===" << std::endl;
            std::cout << "  Position:    " << Pos << " (0-4095)" << std::endl;
            std::cout << "  Speed:       " << Speed << " steps/sec" << std::endl;
            std::cout << "  Load:        " << Load << " (0-1000)" << std::endl;
            std::cout << "  Voltage:     " << Voltage << " (×0.1V = " << Voltage/10.0 << "V)" << std::endl;
            std::cout << "  Temperature: " << Temper << " °C" << std::endl;
            std::cout << "  Moving:      " << (Move ? "Yes" : "No") << std::endl;
            std::cout << "  Current:     " << Current << " mA" << std::endl;
            std::cout << std::endl;
            
            usleep(100 * 1000);  // 100ms delay
        }else{
            std::cout << "ERROR: Failed to read feedback from servo" << std::endl;
            sleep(1);
        }
        
        // Optional: Method 2 - Read individual parameters (commented out, slower)
        /*
        Pos = sm_st.ReadPos(servo_id);
        if(Pos != -1){
            std::cout << "Position: " << Pos << std::endl;
        }
        usleep(10 * 1000);
        
        Voltage = sm_st.ReadVoltage(servo_id);
        if(Voltage != -1){
            std::cout << "Voltage: " << Voltage/10.0 << "V" << std::endl;
        }
        usleep(10 * 1000);
        */
    }
    
    sm_st.end();
    return 1;
}
