#!/bin/bash
mkdir -p build
cd build
cmake ..
make
cd ..
echo "Build complete! Run with: sudo ./build/SwirlTeach"
