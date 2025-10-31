/*
 * ContinuousTeach.cpp
 * Continuous trajectory recording for 7-DOF robot (6 joints + gripper)
 * 
 * Unlike TeachMode which uses discrete waypoints, this mode:
 *   - Continuously samples servo positions at high frequency (default 100ms)
 *   - Records smooth, fluid trajectories as you move the arm
 *   - Replays with smooth acceleration/deceleration
 * 
 * RECORD MODE:
 *   - Disables torque on all servos for manual movement
 *   - Auto-records positions every 100ms
 *   - Press 'q' to stop recording
 * 
 * PLAYBACK MODE:
 *   - Enables torque and smoothly replays the trajectory
 *   - Smooth interpolation between recorded positions
 * 
 * Usage:
 *   sudo ./ContinuousTeach [port] [sample_interval_ms]
 *   
 * Default sample interval: 100ms (10 samples per second)
 */

#include <iostream>
#include <vector>
#include <string>
#include <fstream>
#include <unistd.h>
#include <termios.h>
#include <fcntl.h>
#include <sys/time.h>
#include <cmath>
#include "SCServo.h"

// Trajectory point structure
struct TrajectoryPoint {
    int positions[7];  // positions for servos 1-7
    long long timestamp_us;  // microsecond timestamp for precise timing
};

// Global trajectory storage
std::vector<TrajectoryPoint> trajectory;
SMS_STS sm_st;

// Get current time in microseconds
long long getCurrentTimeMicros() {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (long long)tv.tv_sec * 1000000LL + (long long)tv.tv_usec;
}

// Set terminal to non-blocking mode for input
struct termios orig_termios;

void disableRawMode() {
    tcsetattr(STDIN_FILENO, TCSAFLUSH, &orig_termios);
}

void enableRawMode() {
    tcgetattr(STDIN_FILENO, &orig_termios);
    atexit(disableRawMode);
    
    struct termios raw = orig_termios;
    raw.c_lflag &= ~(ECHO | ICANON);
    raw.c_cc[VMIN] = 0;
    raw.c_cc[VTIME] = 0;
    
    tcsetattr(STDIN_FILENO, TCSAFLUSH, &raw);
}

// Check if key was pressed (non-blocking)
char getKeyPress() {
    char c = 0;
    if(read(STDIN_FILENO, &c, 1) == 1) {
        return c;
    }
    return 0;
}

// Read current positions of all 7 servos
bool readAllPositions(TrajectoryPoint& tp) {
    for(int i = 0; i < 7; i++) {
        int id = i + 1;
        if(sm_st.FeedBack(id) != -1) {
            tp.positions[i] = sm_st.ReadPos(-1);
        } else {
            std::cerr << "Failed to read servo " << id << std::endl;
            return false;
        }
        usleep(2000); // 2ms between reads (faster than waypoint mode)
    }
    return true;
}

// Display current positions
void displayPositions(const TrajectoryPoint& tp, int sample_num) {
    std::cout << "\r[Sample " << sample_num << "] ";
    for(int i = 0; i < 6; i++) {
        std::cout << "J" << (i+1) << ":" << tp.positions[i] << " ";
    }
    std::cout << "G:" << tp.positions[6] << "  " << std::flush;
}

// Continuous recording mode
void recordContinuous(int sample_interval_ms) {
    std::cout << "\n╔═══════════════════════════════════════════════════════════════╗" << std::endl;
    std::cout << "║          CONTINUOUS TEACH MODE - RECORDING                    ║" << std::endl;
    std::cout << "╚═══════════════════════════════════════════════════════════════╝\n" << std::endl;
    
    // Disable torque on all servos for manual movement
    std::cout << "Disabling torque on all servos..." << std::endl;
    for(int i = 1; i <= 7; i++) {
        sm_st.EnableTorque(i, 0);
        usleep(50000);
    }
    
    std::cout << "\n✓ Torque disabled - Move the arm to start position!\n" << std::endl;
    std::cout << "Press ENTER when ready to start recording..." << std::endl;
    std::cin.get();
    
    trajectory.clear();
    enableRawMode();
    
    std::cout << "\n🔴 RECORDING... (Press 'q' to stop)\n" << std::endl;
    
    long long start_time = getCurrentTimeMicros();
    int sample_count = 0;
    char key = 0;
    
    while(key != 'q' && key != 'Q') {
        TrajectoryPoint tp;
        tp.timestamp_us = getCurrentTimeMicros() - start_time;
        
        if(readAllPositions(tp)) {
            trajectory.push_back(tp);
            sample_count++;
            displayPositions(tp, sample_count);
        }
        
        // Check for quit key
        key = getKeyPress();
        
        // Wait for next sample
        usleep(sample_interval_ms * 1000);
    }
    
    disableRawMode();
    
    std::cout << "\n\n✓ Recording stopped!" << std::endl;
    std::cout << "Captured " << trajectory.size() << " samples over " 
              << (trajectory.back().timestamp_us / 1000000.0) << " seconds" << std::endl;
    std::cout << "Sample rate: " << (trajectory.size() / (trajectory.back().timestamp_us / 1000000.0)) 
              << " Hz" << std::endl;
}

// Smooth playback mode with interpolation
void playbackContinuous(bool loop = false) {
    if(trajectory.size() == 0) {
        std::cout << "\n⚠ No trajectory to playback!" << std::endl;
        return;
    }
    
    std::cout << "\n╔═══════════════════════════════════════════════════════════════╗" << std::endl;
    std::cout << "║          CONTINUOUS TEACH MODE - PLAYBACK                     ║" << std::endl;
    std::cout << "╚═══════════════════════════════════════════════════════════════╝\n" << std::endl;
    
    // Enable torque on all servos
    std::cout << "Enabling torque on all servos..." << std::endl;
    for(int i = 1; i <= 7; i++) {
        sm_st.EnableTorque(i, 1);
        usleep(50000);
    }
    
    float duration = trajectory.back().timestamp_us / 1000000.0;
    std::cout << "\n✓ Starting playback of " << trajectory.size() 
              << " samples (" << duration << "s)...\n" << std::endl;
    
    int iteration = 0;
    do {
        if(loop) std::cout << "\n--- Loop " << (++iteration) << " ---" << std::endl;
        
        long long playback_start = getCurrentTimeMicros();
        size_t next_idx = 0;
        
        // Smooth playback with acceleration control
        while(next_idx < trajectory.size()) {
            long long elapsed_us = getCurrentTimeMicros() - playback_start;
            
            // Find the trajectory point(s) for current time
            while(next_idx < trajectory.size() && 
                  trajectory[next_idx].timestamp_us <= elapsed_us) {
                
                const TrajectoryPoint& tp = trajectory[next_idx];
                
                // Calculate speed based on time to next point
                int speed, acc;
                if(next_idx < trajectory.size() - 1) {
                    long long time_to_next_us = trajectory[next_idx + 1].timestamp_us - tp.timestamp_us;
                    
                    // Adaptive speed: faster for longer intervals, slower for short intervals
                    if(time_to_next_us > 200000) {  // > 200ms
                        speed = 1200;  // Medium speed
                        acc = 80;      // Medium acceleration
                    } else if(time_to_next_us > 100000) {  // > 100ms
                        speed = 800;   // Slower speed
                        acc = 120;     // Higher acceleration for smoothness
                    } else {
                        speed = 600;   // Very slow for fine movements
                        acc = 150;     // Very smooth acceleration
                    }
                } else {
                    speed = 400;   // Very slow for final position
                    acc = 150;     // Very smooth
                }
                
                // Send positions to all servos with smooth motion
                for(int j = 0; j < 7; j++) {
                    int id = j + 1;
                    sm_st.WritePosEx(id, tp.positions[j], speed, acc);
                }
                
                // Progress indicator
                if(next_idx % 10 == 0) {
                    float progress = (float)next_idx / trajectory.size() * 100.0;
                    std::cout << "\rProgress: " << (int)progress << "% " 
                              << "[" << (next_idx+1) << "/" << trajectory.size() << "]   " << std::flush;
                }
                
                next_idx++;
            }
            
            usleep(1000);  // 1ms update rate for smooth playback
        }
        
        std::cout << "\rProgress: 100% ✓                          " << std::endl;
        
        if(loop) {
            std::cout << "\nPress ENTER to continue loop, or 'q' to stop: ";
            std::string input;
            std::getline(std::cin, input);
            if(input == "q" || input == "Q") break;
        }
        
    } while(loop);
    
    std::cout << "\n✓ Playback finished!" << std::endl;
}

// Save trajectory to file
void saveTrajectory(const std::string& filename) {
    std::ofstream file(filename);
    if(!file.is_open()) {
        std::cerr << "Failed to open file for writing!" << std::endl;
        return;
    }
    
    file << trajectory.size() << std::endl;
    for(const auto& tp : trajectory) {
        file << tp.timestamp_us;
        for(int i = 0; i < 7; i++) {
            file << " " << tp.positions[i];
        }
        file << std::endl;
    }
    
    file.close();
    std::cout << "✓ Saved " << trajectory.size() << " samples to '" << filename << "'" << std::endl;
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
        TrajectoryPoint tp;
        file >> tp.timestamp_us;
        for(int j = 0; j < 7; j++) {
            file >> tp.positions[j];
        }
        trajectory.push_back(tp);
    }
    
    file.close();
    std::cout << "✓ Loaded " << trajectory.size() << " samples from '" << filename << "'" << std::endl;
    return true;
}

int main(int argc, char** argv) {
    const char* port = "/dev/ttyACM0";
    int sample_interval_ms = 100; // 100ms = 10Hz sampling by default
    
    if(argc >= 2) port = argv[1];
    if(argc >= 3) sample_interval_ms = atoi(argv[2]);
    
    std::cout << "╔═══════════════════════════════════════════════════════════════╗" << std::endl;
    std::cout << "║      CONTINUOUS TEACH MODE - Fluid Trajectory Recording       ║" << std::endl;
    std::cout << "╚═══════════════════════════════════════════════════════════════╝" << std::endl;
    std::cout << "\nPort: " << port << std::endl;
    std::cout << "Sample interval: " << sample_interval_ms << "ms (" 
              << (1000.0/sample_interval_ms) << " Hz)" << std::endl;
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
        std::cout << "  r - Record continuous trajectory" << std::endl;
        std::cout << "  p - Playback recorded trajectory (once)" << std::endl;
        std::cout << "  l - Playback in loop mode" << std::endl;
        std::cout << "  s - Save trajectory to file" << std::endl;
        std::cout << "  o - Open (load) trajectory from file" << std::endl;
        std::cout << "  i - Show trajectory info" << std::endl;
        std::cout << "  q - Quit" << std::endl;
        std::cout << "\nChoice: ";
        
        std::string choice;
        std::getline(std::cin, choice);
        
        if(choice.empty()) continue;
        
        switch(choice[0]) {
            case 'r':
            case 'R':
                recordContinuous(sample_interval_ms);
                break;
                
            case 'p':
            case 'P':
                playbackContinuous(false);
                break;
                
            case 'l':
            case 'L':
                playbackContinuous(true);
                break;
                
            case 's':
            case 'S': {
                if(trajectory.size() == 0) {
                    std::cout << "⚠ No trajectory to save!" << std::endl;
                    break;
                }
                std::cout << "Enter filename (default: continuous_trajectory.txt): ";
                std::string filename;
                std::getline(std::cin, filename);
                if(filename.empty()) filename = "continuous_trajectory.txt";
                saveTrajectory(filename);
                break;
            }
                
            case 'o':
            case 'O': {
                std::cout << "Enter filename to load (default: continuous_trajectory.txt): ";
                std::string filename;
                std::getline(std::cin, filename);
                if(filename.empty()) filename = "continuous_trajectory.txt";
                if(!loadTrajectory(filename)) {
                    std::cout << "⚠ Failed to load file '" << filename << "'" << std::endl;
                }
                break;
            }
                
            case 'i':
            case 'I':
                if(trajectory.size() == 0) {
                    std::cout << "\n⚠ No trajectory loaded" << std::endl;
                } else {
                    float duration = trajectory.back().timestamp_us / 1000000.0;
                    float sample_rate = trajectory.size() / duration;
                    std::cout << "\n╔═══════════════════════════════════════════════════════════════╗" << std::endl;
                    std::cout << "║                  TRAJECTORY INFORMATION                       ║" << std::endl;
                    std::cout << "╚═══════════════════════════════════════════════════════════════╝" << std::endl;
                    std::cout << "  Samples: " << trajectory.size() << std::endl;
                    std::cout << "  Duration: " << duration << " seconds" << std::endl;
                    std::cout << "  Sample rate: " << sample_rate << " Hz" << std::endl;
                    std::cout << "  Memory: " << (trajectory.size() * sizeof(TrajectoryPoint) / 1024) << " KB" << std::endl;
                }
                break;
                
            case 'q':
            case 'Q':
                std::cout << "\nExiting...\n" << std::endl;
                sm_st.end();
                return 0;
                
            default:
                std::cout << "⚠ Invalid choice!" << std::endl;
        }
    }
    
    sm_st.end();
    return 0;
}
