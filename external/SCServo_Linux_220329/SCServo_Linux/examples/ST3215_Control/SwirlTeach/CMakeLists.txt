cmake_minimum_required(VERSION 3.10)
project(SwirlTeach)

set(CMAKE_CXX_STANDARD 11)

include_directories(${CMAKE_SOURCE_DIR}/../../../)

add_executable(SwirlTeach SwirlTeach.cpp
    ${CMAKE_SOURCE_DIR}/../../../SCSerial.cpp
    ${CMAKE_SOURCE_DIR}/../../../SCS.cpp
    ${CMAKE_SOURCE_DIR}/../../../SMS_STS.cpp)

target_link_libraries(SwirlTeach pthread)
