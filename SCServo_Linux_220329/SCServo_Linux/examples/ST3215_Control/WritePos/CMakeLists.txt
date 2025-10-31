cmake_minimum_required(VERSION 2.8.3)
set(project "ST3215_WritePos")
project(${project})

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11 -O3")

# Set the library directory (relative to this CMakeLists.txt)
set(LIB_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../../..)

include_directories(${LIB_DIR})
link_directories(${LIB_DIR})

add_executable(WritePos WritePos.cpp)
target_link_libraries(WritePos ${LIB_DIR}/libSCServo.a)
