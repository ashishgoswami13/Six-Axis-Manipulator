cmake_minimum_required(VERSION 3.10)
project(ReachObject)

set(CMAKE_CXX_STANDARD 11)

# Path to SCServo library
set(SCSERVO_PATH "../../..")

# Include directories
include_directories(${SCSERVO_PATH})

# Source files
set(SOURCES
    ReachObject.cpp
    ${SCSERVO_PATH}/SCS.cpp
    ${SCSERVO_PATH}/SCSerial.cpp
    ${SCSERVO_PATH}/SMS_STS.cpp
)

# Add executable
add_executable(ReachObject ${SOURCES})
