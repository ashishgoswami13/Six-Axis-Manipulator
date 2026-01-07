/*
 * SwirlTeach.cpp
 * Teach swirling motion and automatically generate perfect circular refinement
 * 
 * Workflow:
 *   1. Record janky circular motion manually (teach mode)
 *   2. Analyze recorded path to detect circular plane & center
 *   3. Generate refined perfect circular motion on same plane
 *   4. Playback original or refined version
 * 
 * Usage:
 *   sudo ./SwirlTeach [port]
 */

#include <iostream>
#include <vector>
#include <cmath>
#include <fstream>
#include <unistd.h>
#include "SCServo.h"

struct Waypoint {
    int positions[7];
    int timestamp_ms;
};

std::vector<Waypoint> recorded_trajectory;
std::vector<Waypoint> refined_trajectory;
SMS_STS sm_st;

bool readAllPositions(Waypoint& wp) {
    for(int i = 0; i < 7; i++) {
        int id = i + 1;
        if(sm_st.FeedBack(id) != -1) {
            wp.positions[i] = sm_st.ReadPos(-1);
        } else {
            std::cerr << "Failed to read servo " << id << std::endl;
            return false;
        }
        usleep(10000);
    }
    return true;
}

void displayPositions(const Waypoint& wp) {
    std::cout << "  [";
    for(int i = 0; i < 6; i++) {
        std::cout << wp.positions[i];
        if(i < 5) std::cout << ", ";
    }
    std::cout << "] G:" << wp.positions[6] << std::endl;
}

void recordSwirl() {
    std::cout << "\n╔═════════════════════════════════════════════════════════╗" << std::endl;
    std::cout << "║           SWIRL TEACH MODE - RECORDING                  ║" << std::endl;
    std::cout << "╚═════════════════════════════════════════════════════════╝\n" << std::endl;
    
    // Disable torque for manual movement
    std::cout << "Disabling torque..." << std::endl;
    for(int i = 1; i <= 7; i++) {
        sm_st.EnableTorque(i, 0);
        usleep(50000);
    }
    
    std::cout << "\n✓ Torque disabled - Move arm freely!\n" << std::endl;
    std::cout << "Instructions:" << std::endl;
    std::cout << "  1. Move to starting position of swirl" << std::endl;
    std::cout << "  2. Press ENTER to begin continuous recording" << std::endl;
    std::cout << "  3. Perform swirling motion slowly" << std::endl;
    std::cout << "  4. Press ENTER again when complete\n" << std::endl;
    
    std::cout << "Press ENTER to start recording: ";
    std::cin.ignore();
    std::cin.get();
    
    recorded_trajectory.clear();
    std::cout << "\n🔴 RECORDING - Perform swirl motion now..." << std::endl;
    std::cout << "Press ENTER when done...\n" << std::endl;
    
    // Continuous recording thread simulation
    int sample_interval_ms = 100; // 10Hz sampling
    int waypoint_count = 0;
    
    // Non-blocking recording
    fd_set readfds;
    struct timeval tv;
    int start_time = 0;
    
    while(true) {
        // Check for ENTER press
        FD_ZERO(&readfds);
        FD_SET(STDIN_FILENO, &readfds);
        tv.tv_sec = 0;
        tv.tv_usec = sample_interval_ms * 1000;
        
        int ret = select(STDIN_FILENO + 1, &readfds, NULL, NULL, &tv);
        
        if(ret > 0 && FD_ISSET(STDIN_FILENO, &readfds)) {
            char c;
            read(STDIN_FILENO, &c, 1);
            if(c == '\n') break;
        }
        
        // Sample current position
        Waypoint wp;
        wp.timestamp_ms = start_time;
        if(readAllPositions(wp)) {
            recorded_trajectory.push_back(wp);
            waypoint_count++;
            std::cout << "\r  Waypoints: " << waypoint_count << std::flush;
        }
        
        start_time += sample_interval_ms;
    }
    
    std::cout << "\n\n✓ Recording complete! " << recorded_trajectory.size() << " waypoints captured." << std::endl;
    
    // Save raw recording
    std::ofstream file("swirl_recorded.txt");
    if(file.is_open()) {
        file << recorded_trajectory.size() << std::endl;
        for(const auto& wp : recorded_trajectory) {
            file << wp.timestamp_ms;
            for(int i = 0; i < 7; i++) {
                file << " " << wp.positions[i];
            }
            file << std::endl;
        }
        file.close();
        std::cout << "✓ Saved to 'swirl_recorded.txt'" << std::endl;
    }
}

void analyzeAndRefine() {
    if(recorded_trajectory.size() < 3) {
        std::cout << "\n⚠ Need at least 3 waypoints to analyze!" << std::endl;
        return;
    }
    
    std::cout << "\n╔═════════════════════════════════════════════════════════╗" << std::endl;
    std::cout << "║           ANALYZING SWIRL MOTION                        ║" << std::endl;
    std::cout << "╚═════════════════════════════════════════════════════════╝\n" << std::endl;
    
    // Analyze which joints moved most (dominant motion axes)
    double variance[7] = {0};
    double mean[7] = {0};
    
    // Calculate mean
    for(const auto& wp : recorded_trajectory) {
        for(int i = 0; i < 7; i++) {
            mean[i] += wp.positions[i];
        }
    }
    for(int i = 0; i < 7; i++) {
        mean[i] /= recorded_trajectory.size();
    }
    
    // Calculate variance
    for(const auto& wp : recorded_trajectory) {
        for(int i = 0; i < 7; i++) {
            double diff = wp.positions[i] - mean[i];
            variance[i] += diff * diff;
        }
    }
    for(int i = 0; i < 7; i++) {
        variance[i] /= recorded_trajectory.size();
    }
    
    std::cout << "Motion Analysis:" << std::endl;
    std::cout << "────────────────────────────────────────────────────────" << std::endl;
    
    // Find dominant motion axes (top 2-3 joints with most variance)
    struct JointVar { int joint; double var; };
    JointVar sorted[7];
    for(int i = 0; i < 7; i++) {
        sorted[i] = {i, variance[i]};
    }
    
    // Simple bubble sort
    for(int i = 0; i < 6; i++) {
        for(int j = 0; j < 6-i; j++) {
            if(sorted[j].var < sorted[j+1].var) {
                JointVar temp = sorted[j];
                sorted[j] = sorted[j+1];
                sorted[j+1] = temp;
            }
        }
    }
    
    std::cout << "Joint Motion (sorted by variance):" << std::endl;
    for(int i = 0; i < 7; i++) {
        int joint = sorted[i].joint;
        std::cout << "  J" << (joint+1) << ": " 
                  << "mean=" << (int)mean[joint] 
                  << ", variance=" << (int)variance[joint];
        if(i < 2) std::cout << " ← PRIMARY SWIRL AXIS";
        std::cout << std::endl;
    }
    
    std::cout << "\nDetected Swirl Characteristics:" << std::endl;
    std::cout << "  • Primary motion joints: J" << (sorted[0].joint+1) 
              << " and J" << (sorted[1].joint+1) << std::endl;
    std::cout << "  • Center position: [";
    for(int i = 0; i < 6; i++) {
        std::cout << (int)mean[i];
        if(i < 5) std::cout << ", ";
    }
    std::cout << "]" << std::endl;
    
    // Calculate approximate radius (average distance from center)
    double total_radius = 0;
    int primary_joint = sorted[0].joint;
    int secondary_joint = sorted[1].joint;
    
    for(const auto& wp : recorded_trajectory) {
        double dx = wp.positions[primary_joint] - mean[primary_joint];
        double dy = wp.positions[secondary_joint] - mean[secondary_joint];
        total_radius += sqrt(dx*dx + dy*dy);
    }
    double avg_radius = total_radius / recorded_trajectory.size();
    
    std::cout << "  • Approximate radius: " << (int)avg_radius << " steps" << std::endl;
    std::cout << "  • Duration: " << recorded_trajectory.back().timestamp_ms << "ms" << std::endl;
}

void generateRefinedCircle() {
    if(recorded_trajectory.size() < 3) {
        std::cout << "\n⚠ Need recorded trajectory first!" << std::endl;
        return;
    }
    
    std::cout << "\n╔═════════════════════════════════════════════════════════╗" << std::endl;
    std::cout << "║        GENERATING REFINED CIRCULAR MOTION               ║" << std::endl;
    std::cout << "╚═════════════════════════════════════════════════════════╝\n" << std::endl;
    
    // Calculate center and variance
    double mean[7] = {0};
    double variance[7] = {0};
    
    for(const auto& wp : recorded_trajectory) {
        for(int i = 0; i < 7; i++) {
            mean[i] += wp.positions[i];
        }
    }
    for(int i = 0; i < 7; i++) {
        mean[i] /= recorded_trajectory.size();
    }
    
    for(const auto& wp : recorded_trajectory) {
        for(int i = 0; i < 7; i++) {
            double diff = wp.positions[i] - mean[i];
            variance[i] += diff * diff;
        }
    }
    for(int i = 0; i < 7; i++) {
        variance[i] /= recorded_trajectory.size();
    }
    
    // Find top 2 motion axes
    int primary = 0, secondary = 1;
    for(int i = 0; i < 7; i++) {
        if(variance[i] > variance[primary]) {
            secondary = primary;
            primary = i;
        } else if(variance[i] > variance[secondary] && i != primary) {
            secondary = i;
        }
    }
    
    // Calculate radius
    double total_radius = 0;
    for(const auto& wp : recorded_trajectory) {
        double dx = wp.positions[primary] - mean[primary];
        double dy = wp.positions[secondary] - mean[secondary];
        total_radius += sqrt(dx*dx + dy*dy);
    }
    double radius = total_radius / recorded_trajectory.size();
    
    std::cout << "Generating perfect circle:" << std::endl;
    std::cout << "  • Center: J" << (primary+1) << "=" << (int)mean[primary] 
              << ", J" << (secondary+1) << "=" << (int)mean[secondary] << std::endl;
    std::cout << "  • Radius: " << (int)radius << " steps" << std::endl;
    std::cout << "  • Resolution: 36 waypoints (10° intervals)" << std::endl;
    
    // Generate perfect circle
    refined_trajectory.clear();
    int num_points = 36; // 36 points = 10° per step
    int duration_ms = recorded_trajectory.back().timestamp_ms;
    int interval_ms = duration_ms / num_points;
    
    for(int i = 0; i < num_points; i++) {
        Waypoint wp;
        double angle = (2.0 * M_PI * i) / num_points;
        
        for(int j = 0; j < 7; j++) {
            if(j == primary) {
                wp.positions[j] = (int)(mean[j] + radius * cos(angle));
            } else if(j == secondary) {
                wp.positions[j] = (int)(mean[j] + radius * sin(angle));
            } else {
                wp.positions[j] = (int)mean[j]; // Keep other joints at center
            }
        }
        
        wp.timestamp_ms = i * interval_ms;
        refined_trajectory.push_back(wp);
    }
    
    std::cout << "✓ Generated " << refined_trajectory.size() << " waypoints for perfect circle" << std::endl;
    
    // Save refined trajectory
    std::ofstream file("swirl_refined.txt");
    if(file.is_open()) {
        file << refined_trajectory.size() << std::endl;
        for(const auto& wp : refined_trajectory) {
            file << wp.timestamp_ms;
            for(int i = 0; i < 7; i++) {
                file << " " << wp.positions[i];
            }
            file << std::endl;
        }
        file.close();
        std::cout << "✓ Saved to 'swirl_refined.txt'" << std::endl;
    }
}

void playback(const std::vector<Waypoint>& trajectory, const std::string& name) {
    if(trajectory.size() == 0) {
        std::cout << "\n⚠ No trajectory to playback!" << std::endl;
        return;
    }
    
    std::cout << "\n╔═════════════════════════════════════════════════════════╗" << std::endl;
    std::cout << "║           PLAYBACK: " << name << std::endl;
    std::cout << "╚═════════════════════════════════════════════════════════╝\n" << std::endl;
    
    // Enable torque
    std::cout << "Enabling torque..." << std::endl;
    for(int i = 1; i <= 7; i++) {
        sm_st.EnableTorque(i, 1);
        usleep(50000);
    }
    
    std::cout << "\n✓ Playing " << trajectory.size() << " waypoints...\n" << std::endl;
    
    for(size_t i = 0; i < trajectory.size(); i++) {
        const Waypoint& wp = trajectory[i];
        
        std::cout << "\rWaypoint " << (i+1) << "/" << trajectory.size() << std::flush;
        
        // Smooth motion parameters
        int speed = 1200;
        int acc = 150;
        
        for(int j = 0; j < 7; j++) {
            sm_st.WritePosEx(j+1, wp.positions[j], speed, acc);
        }
        
        // Wait for next waypoint
        if(i < trajectory.size() - 1) {
            int delay_ms = trajectory[i+1].timestamp_ms - wp.timestamp_ms;
            if(delay_ms > 0) {
                usleep(delay_ms * 1000);
            }
        }
    }
    
    std::cout << "\n\n✓ Playback complete!" << std::endl;
}

int main(int argc, char** argv) {
    const char* port = "/dev/ttyACM0";
    if(argc >= 2) port = argv[1];
    
    std::cout << "╔═════════════════════════════════════════════════════════╗" << std::endl;
    std::cout << "║           SWIRL TEACH & REFINE SYSTEM                   ║" << std::endl;
    std::cout << "╚═════════════════════════════════════════════════════════╝" << std::endl;
    std::cout << "\nPort: " << port << "\n" << std::endl;
    
    if(!sm_st.begin(1000000, port)) {
        std::cerr << "ERROR: Failed to initialize serial on " << port << std::endl;
        return 1;
    }
    
    while(true) {
        std::cout << "\n╔═════════════════════════════════════════════════════════╗" << std::endl;
        std::cout << "║                    MAIN MENU                            ║" << std::endl;
        std::cout << "╚═════════════════════════════════════════════════════════╝" << std::endl;
        std::cout << "  1 - Record swirl motion (teach mode)" << std::endl;
        std::cout << "  2 - Analyze recorded motion" << std::endl;
        std::cout << "  3 - Generate refined circular motion" << std::endl;
        std::cout << "  4 - Playback recorded (original)" << std::endl;
        std::cout << "  5 - Playback refined (perfect circle)" << std::endl;
        std::cout << "  q - Quit" << std::endl;
        std::cout << "\nChoice: ";
        
        std::string choice;
        std::getline(std::cin, choice);
        
        if(choice == "1") {
            recordSwirl();
        }
        else if(choice == "2") {
            analyzeAndRefine();
        }
        else if(choice == "3") {
            generateRefinedCircle();
        }
        else if(choice == "4") {
            playback(recorded_trajectory, "RECORDED (ORIGINAL)");
        }
        else if(choice == "5") {
            playback(refined_trajectory, "REFINED (PERFECT CIRCLE)");
        }
        else if(choice == "q" || choice == "Q") {
            break;
        }
    }
    
    // Re-enable torque before exit
    std::cout << "\nRe-enabling torque..." << std::endl;
    for(int i = 1; i <= 7; i++) {
        sm_st.EnableTorque(i, 1);
        usleep(50000);
    }
    
    sm_st.end();
    std::cout << "\n✓ Goodbye!" << std::endl;
    return 0;
}
