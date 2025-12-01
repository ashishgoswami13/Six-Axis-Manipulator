#!/bin/bash
# Fine-tune OpenVLA on collected demonstrations

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║          OpenVLA Fine-tuning Pipeline                         ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "This will:"
echo "  1. Prepare collected data for training"
echo "  2. Fine-tune OpenVLA-7B with LoRA adapters"
echo "  3. Save fine-tuned model"
echo ""

cd "/home/dev/Six Axis Manipulator"

# Step 1: Prepare data
echo "Step 1: Preparing training data..."
echo "=" | awk '{for(i=1;i<=70;i++)printf"=";printf"\n"}'
python3 prepare_training_data.py

if [ $? -ne 0 ]; then
    echo "✗ Data preparation failed!"
    exit 1
fi

echo ""
echo "Step 2: Training action adapter (this will take ~5 minutes)..."
echo "=" | awk '{for(i=1;i<=70;i++)printf"=";printf"\n"}'
python3 train_action_adapter.py

if [ $? -ne 0 ]; then
    echo "✗ Fine-tuning failed!"
    exit 1
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                  Fine-tuning Complete!                        ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "Fine-tuned model saved to: ~/vla_finetuned/"
echo ""
echo "Next steps:"
echo "  1. Test with: python3 test_finetuned_model.py"
echo "  2. Try 'go to home' command"
echo "  3. Compare with base model performance"
