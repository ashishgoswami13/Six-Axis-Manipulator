/*
 * TeachMode.cpp
 * Teach and replay mode for 7-DOF robot (6 joints + gripper)
 * 
 * RECORD MODE:
 *   - Disables torque on all servos so you can manually move the arm
 *   - Records positions at specified intervals
 *   - Press Enter to save waypoint, 'q' to finish recording
 * 
 * PLAYBACK MODE:
 *   - Enables torque and replays the recorded trajectory
 *   - Can loop the trajectory or play once
 * 
 * Usage:
 *   sudo ./TeachMode [port] [interval_ms]
 *   
 * Controls during recording:
 *   - Move arm manually to desired position
 *   - Press ENTER to save current position as waypoint
 *   - Type 'q' and press ENTER to finish recording
 *   - Type 'p' to start playback
 */

#include <iostream>
#include <vector>
#include <string>
#include <fstream>
#include <unistd.h>
#include <termios.h>
#include <fcntl.h>
#include "SCServo.h"

// Waypoint structure - stores all 7 servo positions
struct Waypoint {
    int positions[7];  // positions for servos 1-7
    int timestamp_ms;  // time offset from start
};

// Global trajectory storage
std::vector<Waypoint> trajectory;
SMS_STS sm_st;

// Set terminal to non-blocking mode for input
void setNonBlocking(bool enable) {
    static struct termios oldt, newt;
    if(enable) {
        tcgetattr(STDIN_FILENO, &oldt);
        newt = oldt;
        newt.c_lflag &= ~(ICANON | ECHO);
        tcsetattr(STDIN_FILENO, TCSANOW, &newt);
        fcntl(STDIN_FILENO, F_SETFL, O_NONBLOCK);
    } else {
        tcsetattr(STDIN_FILENO, TCSANOW, &oldt);
        fcntl(STDIN_FILENO, F_SETFL, 0);
    }
}

// Read current positions of all 7 servos
bool readAllPositions(Waypoint& wp) {
    for(int i = 0; i < 7; i++) {
        int id = i + 1;
        if(sm_st.FeedBack(id) != -1) {
            wp.positions[i] = sm_st.ReadPos(-1);
        } else {
            std::cerr << "Failed to read servo " << id << std::endl;
            return false;
        }
        usleep(10000); // 10ms between reads
    }
    return true;
}

// Display current positions
void displayPositions(const Waypoint& wp) {
    std::cout << "Positions: ";
    for(int i = 0; i < 6; i++) {
        std::cout << "J" << (i+1) << ":" << wp.positions[i] << " ";
    }
    std::cout << "Gripper:" << wp.positions[6] << std::endl;
}

// Record mode - manual movement and waypoint capture
void recordMode(int interval_ms) {
    std::cout << "\n╔═══════════════════════════════════════════════════════════════╗" << std::endl;
    std::cout << "║              TEACH MODE - RECORDING                           ║" << std::endl;
    std::cout << "╚═══════════════════════════════════════════════════════════════╝\n" << std::endl;
    
    // Disable torque on all servos for manual movement
    std::cout << "Disabling torque on all servos..." << std::endl;
    for(int i = 1; i <= 7; i++) {
        sm_st.EnableTorque(i, 0);
        usleep(50000);
    }
    
    std::cout << "\n✓ Torque disabled - You can now move the arm manually!\n" << std::endl;
    std::cout << "Instructions:" << std::endl;
    std::cout << "  1. Move the arm to a position" << std::endl;
    std::cout << "  2. Press ENTER to save waypoint" << std::endl;
    std::cout << "  3. Type 'q' and press ENTER when done" << std::endl;
    std::cout << "  4. Type 'p' and press ENTER to playback\n" << std::endl;
    
    trajectory.clear();
    int start_time = 0;
    bool first = true;
    std::string input;
    
    while(true) {
        std::cout << "\n[Waypoint " << (trajectory.size() + 1) << "] Move arm and press ENTER (or 'q' to finish, 'p' to play): ";
        std::getline(std::cin, input);
        
        if(input == "q" || input == "Q") {
            std::cout << "\n✓ Recording finished! " << trajectory.size() << " waypoints saved." << std::endl;
            break;
        }
        
        if(input == "p" || input == "P") {
            if(trajectory.size() == 0) {
                std::cout << "⚠ No waypoints recorded yet!" << std::endl;
                continue;
            }
            std::cout << "\n✓ Recording finished! " << trajectory.size() << " waypoints saved." << std::endl;
            break;
        }
        
        // Read current positions
        Waypoint wp;
        if(first) {
            start_time = 0;
            first = false;
        } else {
            start_time += interval_ms;
        }
        wp.timestamp_ms = start_time;
        
        if(readAllPositions(wp)) {
            trajectory.push_back(wp);
            std::cout << "  ✓ Waypoint " << trajectory.size() << " saved at t=" << start_time << "ms" << std::endl;
            std::cout << "    ";
            displayPositions(wp);
        } else {
            std::cerr << "  ✗ Failed to read positions!" << std::endl;
        }
    }
    
    // Save to file
    if(trajectory.size() > 0) {
        std::ofstream file("trajectory.txt");
        if(file.is_open()) {
            file << trajectory.size() << std::endl;
            for(const auto& wp : trajectory) {
                file << wp.timestamp_ms;
                for(int i = 0; i < 7; i++) {
                    file << " " << wp.positions[i];
                }
                file << std::endl;
            }
            file.close();
            std::cout << "\n✓ Trajectory saved to 'trajectory.txt'" << std::endl;
        }
    }
}

// Playback mode - replay recorded trajectory
void playbackMode(bool loop = false) {
    if(trajectory.size() == 0) {
        std::cout << "\n⚠ No trajectory to playback!" << std::endl;
        return;
    }
    
    std::cout << "\n╔═══════════════════════════════════════════════════════════════╗" << std::endl;
    std::cout << "║              TEACH MODE - PLAYBACK                            ║" << std::endl;
    std::cout << "╚═══════════════════════════════════════════════════════════════╝\n" << std::endl;
    
    // Enable torque on all servos
    std::cout << "Enabling torque on all servos..." << std::endl;
    for(int i = 1; i <= 7; i++) {
        sm_st.EnableTorque(i, 1);
        usleep(50000);
    }
    
    std::cout << "\n✓ Starting playback of " << trajectory.size() << " waypoints...\n" << std::endl;
    
    int iteration = 0;
    do {
        if(loop) std::cout << "\n--- Loop " << (++iteration) << " ---" << std::endl;
        
        for(size_t i = 0; i < trajectory.size(); i++) {
            const Waypoint& wp = trajectory[i];
            
            std::cout << "Waypoint " << (i+1) << "/" << trajectory.size() 
                      << " (t=" << wp.timestamp_ms << "ms)" << std::endl;
            
            // Calculate smooth motion parameters
            // For smoother motion: lower speed, higher acceleration value
            int speed = 1200;   // Slower speed for smoother motion (was 1500)
            int acc = 150;     // Higher acceleration for smoother curves (was 50)
            
            for(int j = 0; j < 7; j++) {
                int id = j + 1;
                sm_st.WritePosEx(id, wp.positions[j], speed, acc);
            }
            
            displayPositions(wp);
            
            // Wait for next waypoint
            if(i < trajectory.size() - 1) {
                int delay_ms = trajectory[i+1].timestamp_ms - wp.timestamp_ms;
                if(delay_ms > 0) {
                    usleep(delay_ms * 1000);
                }
            } else {
                sleep(1); // pause at end
            }
        }
        
        if(loop) {
            std::cout << "\nPress ENTER to continue loop, or 'q' to stop: ";
            std::string input;
            std::getline(std::cin, input);
            if(input == "q" || input == "Q") break;
        }
        
    } while(loop);
    
    std::cout << "\n✓ Playback finished!" << std::endl;
}

// Load trajectory from file
bool loadTrajectory(const std::string& filename) {
    std::ifstream file(filename);
    if(!file.is_open()) {
        return false;
    }
    
    trajectory.clear();
    int count;
    file >> count;
    
    for(int i = 0; i < count; i++) {
        Waypoint wp;
        file >> wp.timestamp_ms;
        for(int j = 0; j < 7; j++) {
            file >> wp.positions[j];
        }
        trajectory.push_back(wp);
    }
    
    file.close();
    std::cout << "✓ Loaded " << trajectory.size() << " waypoints from '" << filename << "'" << std::endl;
    return true;
}

int main(int argc, char** argv) {
    const char* port = "/dev/ttyACM0";
    int interval_ms = 1000; // 1 second between waypoints by default
    
    if(argc >= 2) port = argv[1];
    if(argc >= 3) interval_ms = atoi(argv[2]);
    
    std::cout << "╔═══════════════════════════════════════════════════════════════╗" << std::endl;
    std::cout << "║         TEACH MODE - Robot Trajectory Recording              ║" << std::endl;
    std::cout << "╚═══════════════════════════════════════════════════════════════╝" << std::endl;
    std::cout << "\nPort: " << port << std::endl;
    std::cout << "Waypoint interval: " << interval_ms << "ms" << std::endl;
    std::cout << "Controlling: 7 servos (6 joints + gripper)\n" << std::endl;
    
    // Initialize serial
    if(!sm_st.begin(1000000, port)) {
        std::cerr << "ERROR: Failed to initialize serial on " << port << std::endl;
        return 1;
    }
    
    // Main menu
    while(true) {
        std::cout << "\n╔═══════════════════════════════════════════════════════════════╗" << std::endl;
        std::cout << "║                      MAIN MENU                                ║" << std::endl;
        std::cout << "╚═══════════════════════════════════════════════════════════════╝" << std::endl;
        std::cout << "  r - Record new trajectory" << std::endl;
        std::cout << "  p - Playback recorded trajectory (once)" << std::endl;
        std::cout << "  l - Playback in loop mode" << std::endl;
        std::cout << "  s - Save trajectory to file" << std::endl;
        std::cout << "  o - Load trajectory from file" << std::endl;
        std::cout << "  q - Quit" << std::endl;
        std::cout << "\nChoice: ";
        
        std::string choice;
        std::getline(std::cin, choice);
        
        if(choice == "r" || choice == "R") {
            recordMode(interval_ms);
        }
        else if(choice == "p" || choice == "P") {
            playbackMode(false);
        }
        else if(choice == "l" || choice == "L") {
            playbackMode(true);
        }
        else if(choice == "s" || choice == "S") {
            if(trajectory.size() > 0) {
                std::cout << "Filename (default: trajectory.txt): ";
                std::string filename;
                std::getline(std::cin, filename);
                if(filename.empty()) filename = "trajectory.txt";
                
                std::ofstream file(filename);
                if(file.is_open()) {
                    file << trajectory.size() << std::endl;
                    for(const auto& wp : trajectory) {
                        file << wp.timestamp_ms;
                        for(int i = 0; i < 7; i++) {
                            file << " " << wp.positions[i];
                        }
                        file << std::endl;
                    }
                    file.close();
                    std::cout << "✓ Saved to '" << filename << "'" << std::endl;
                } else {
                    std::cerr << "✗ Failed to save!" << std::endl;
                }
            } else {
                std::cout << "⚠ No trajectory to save!" << std::endl;
            }
        }
        else if(choice == "o" || choice == "O") {
            std::cout << "Filename to load (default: trajectory.txt): ";
            std::string filename;
            std::getline(std::cin, filename);
            if(filename.empty()) filename = "trajectory.txt";
            
            if(!loadTrajectory(filename)) {
                std::cerr << "✗ Failed to load '" << filename << "'" << std::endl;
            }
        }
        else if(choice == "q" || choice == "Q") {
            break;
        }
    }
    
    // Re-enable torque before exit
    std::cout << "\nRe-enabling torque on all servos..." << std::endl;
    for(int i = 1; i <= 7; i++) {
        sm_st.EnableTorque(i, 1);
        usleep(50000);
    }
    
    sm_st.end();
    std::cout << "\n✓ Exiting teach mode. Goodbye!" << std::endl;
    return 0;
}
