cmake_minimum_required(VERSION 2.8.3)
project(ContinuousTeach)

# Set C++11 standard
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Include directories - go up to SCServo_Linux root (3 levels up)
set(LIB_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../..")
include_directories(${LIB_DIR})

# Add executable
add_executable(ContinuousTeach ContinuousTeach.cpp)

# Link against the SCServo library
target_link_libraries(ContinuousTeach ${LIB_DIR}/libSCServo.a pthread)
