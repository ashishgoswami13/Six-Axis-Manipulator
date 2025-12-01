#!/bin/bash

# Package VLA Training Data for Transfer
# Run this on the robot system after data collection is complete

set -e

echo "=============================================="
echo "VLA Training Data Package Creator"
echo "=============================================="
echo ""

# Paths
DATASET_DIR=~/vla_dataset
TRAINING_DATA_DIR=~/vla_training_data
WORKSPACE_DIR=~/Six\ Axis\ Manipulator
OUTPUT_FILE=~/vla_training_package.tar.gz

# Step 1: Check if dataset exists
echo "[1/5] Checking dataset..."
if [ ! -d "$DATASET_DIR" ]; then
    echo "❌ Error: Dataset not found at $DATASET_DIR"
    exit 1
fi

EPISODE_COUNT=$(ls -d "$DATASET_DIR"/episode_* 2>/dev/null | wc -l)
echo "✓ Found $EPISODE_COUNT episodes"

if [ "$EPISODE_COUNT" -lt 50 ]; then
    echo "⚠️  Warning: Only $EPISODE_COUNT episodes found. Recommend at least 100 for good training."
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Step 2: Prepare training data
echo ""
echo "[2/5] Preparing training data..."
cd "$WORKSPACE_DIR"

python3 prepare_training_data.py \
    --dataset_dir "$DATASET_DIR" \
    --output_dir "$TRAINING_DATA_DIR" \
    --action_horizon 1

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to prepare training data"
    exit 1
fi

# Step 3: Verify training data
echo ""
echo "[3/5] Verifying training data..."
if [ ! -f "$TRAINING_DATA_DIR/training_data.pkl" ]; then
    echo "❌ Error: training_data.pkl not created"
    exit 1
fi

PKL_SIZE=$(du -h "$TRAINING_DATA_DIR/training_data.pkl" | cut -f1)
echo "✓ Training data size: $PKL_SIZE"

# Step 4: Create package
echo ""
echo "[4/5] Creating transfer package..."

cd ~
rm -f "$OUTPUT_FILE"

tar -czf "$OUTPUT_FILE" \
    vla_training_data/ \
    "Six Axis Manipulator/train_openvla.py" \
    "Six Axis Manipulator/servo_limits_config.py" \
    "Six Axis Manipulator/TRAINING_GUIDE.md"

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to create package"
    exit 1
fi

# Step 5: Summary
echo ""
echo "[5/5] Package complete!"
echo ""
echo "=============================================="
echo "Summary"
echo "=============================================="
echo "Episodes: $EPISODE_COUNT"
echo "Training data: $PKL_SIZE"
echo "Package: $(du -h "$OUTPUT_FILE" | cut -f1)"
echo ""
echo "Package location: $OUTPUT_FILE"
echo ""
echo "=============================================="
echo "Next Steps"
echo "=============================================="
echo "1. Transfer package to training machine:"
echo "   - USB: cp $OUTPUT_FILE /media/usb/"
echo "   - SCP: scp $OUTPUT_FILE user@machine:~/"
echo ""
echo "2. On training machine:"
echo "   tar -xzf vla_training_package.tar.gz"
echo "   Follow instructions in TRAINING_GUIDE.md"
echo ""
echo "=============================================="
