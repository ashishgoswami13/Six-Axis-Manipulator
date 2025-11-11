#include <iostream>
#include <unistd.h>
#include "SCServo.h"
// Joint limits in degrees (min, max) for J1..J6 + Gripper
static const int JOINT_MIN_DEG[7] = {-165, -125, -140, -140, -140, -175, -180};
static const int JOINT_MAX_DEG[7] = { 165,  125,  140,  140,  140,  175,  180};
