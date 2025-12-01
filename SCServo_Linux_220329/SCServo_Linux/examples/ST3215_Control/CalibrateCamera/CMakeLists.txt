cmake_minimum_required(VERSION 2.8.3)
project(CalibrateCamera)

# Set C++ standard
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Include directories
include_directories(
    ${CMAKE_SOURCE_DIR}/../../..
)

# Add executable
add_executable(CalibrateCamera CalibrateCamera.cpp)

# Link libraries
target_link_libraries(CalibrateCamera
    ${CMAKE_SOURCE_DIR}/../../../libSCServo.a
)
