cmake_minimum_required(VERSION 3.5)
project(ManualControl)

# Set C++ standard
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Include directories - go up to SCServo_Linux root
include_directories(${CMAKE_SOURCE_DIR}/../../..)

# Source files
set(SOURCES
    ManualControl.cpp
    ${CMAKE_SOURCE_DIR}/../../../SCSerial.cpp
    ${CMAKE_SOURCE_DIR}/../../../SCS.cpp
    ${CMAKE_SOURCE_DIR}/../../../SMS_STS.cpp
)

# Create executable
add_executable(ManualControl ${SOURCES})

# Link pthread library (required for serial communication)
target_link_libraries(ManualControl pthread)
