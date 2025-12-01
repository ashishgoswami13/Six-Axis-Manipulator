# OpenVLA Fine-Tuning Guide

Complete guide for fine-tuning OpenVLA on your robot arm data.

## Overview

You've collected data on the robot system, now you'll fine-tune OpenVLA on a different (more powerful) machine.

**Dataset Info:**
- Episodes: 100+
- Frames per episode: 30-60
- Total training samples: ~3,000-6,000
- Task: "go to home" from random positions
- Action space: 7 DOF (6 joints + gripper)

## Transfer to Training Machine

### 1. Prepare Dataset Package

On the **robot system** (where you collected data):

```bash
# Navigate to workspace
cd ~/Six\ Axis\ Manipulator/

# Prepare training data (converts episodes to training format)
python3 prepare_training_data.py \
    --dataset_dir ~/vla_dataset \
    --output_dir ~/vla_training_data \
    --action_horizon 1

# This creates:
# ~/vla_training_data/training_data.pkl (all processed samples)
# ~/vla_training_data/dataset_stats.json (statistics)
```

### 2. Create Transfer Package

```bash
# Create tarball
cd ~
tar -czf vla_training_package.tar.gz \
    vla_training_data/ \
    "Six Axis Manipulator/train_openvla.py" \
    "Six Axis Manipulator/servo_limits_config.py"

# Check size
ls -lh vla_training_package.tar.gz
```

### 3. Transfer to Training Machine

Choose one method:

**Option A: USB Drive**
```bash
# Copy to USB
cp vla_training_package.tar.gz /media/usb/
```

**Option B: SCP (if networked)**
```bash
# Replace with your training machine details
scp vla_training_package.tar.gz user@training-machine:~/
```

**Option C: Cloud Storage**
```bash
# Upload to cloud (Google Drive, Dropbox, etc.)
# Or use rclone, aws s3, etc.
```

## Setup on Training Machine

### 1. System Requirements

**Minimum:**
- GPU: NVIDIA GPU with 16GB+ VRAM (RTX 4090, A5000, etc.)
- RAM: 32GB+
- Disk: 50GB free
- CUDA: 11.8+
- Python: 3.8+

**Recommended:**
- GPU: NVIDIA A100 (40GB/80GB) or H100
- RAM: 64GB+
- Disk: 100GB+ SSD

### 2. Extract Package

```bash
cd ~
tar -xzf vla_training_package.tar.gz

# You should now have:
# ~/vla_training_data/training_data.pkl
# ~/vla_training_data/dataset_stats.json
# ~/train_openvla.py
# ~/servo_limits_config.py
```

### 3. Install Dependencies

```bash
# Create conda environment (recommended)
conda create -n openvla python=3.10
conda activate openvla

# Install PyTorch with CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install transformers and dependencies
pip install transformers>=4.40.0
pip install accelerate>=0.30.0
pip install peft>=0.10.0  # For LoRA
pip install datasets
pip install Pillow
pip install opencv-python
pip install numpy
pip install tqdm

# Install OpenVLA (if using official repo)
git clone https://github.com/openvla/openvla.git
cd openvla
pip install -e .
cd ~
```

### 4. Download Base Model

```bash
# Download OpenVLA-7B base model (one-time, ~15GB)
python3 -c "
from transformers import AutoModelForVision2Seq, AutoProcessor
model_name = 'openvla/openvla-7b'
print('Downloading model...')
processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
model = AutoModelForVision2Seq.from_pretrained(model_name, trust_remote_code=True)
print('Model downloaded successfully!')
"
```

## Training

### 1. Verify Setup

```bash
# Check dataset
python3 -c "
import pickle
with open('vla_training_data/training_data.pkl', 'rb') as f:
    data = pickle.load(f)
print(f'Loaded {len(data)} samples')
print(f'Image shape: {data[0][\"image\"].shape}')
print(f'Action dim: {len(data[0][\"action\"])}')
"

# Check GPU
python3 -c "
import torch
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU: {torch.cuda.get_device_name(0)}')
    print(f'VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB')
"
```

### 2. Start Training

```bash
# Full training (50k steps, ~8-12 hours on A100)
python3 train_openvla.py \
    --data_path ~/vla_training_data/training_data.pkl \
    --output_dir ~/vla_finetuned_model \
    --batch_size 4 \
    --learning_rate 5e-5 \
    --max_steps 50000 \
    --use_lora

# Quick test run (1000 steps, ~30 mins)
python3 train_openvla.py \
    --data_path ~/vla_training_data/training_data.pkl \
    --output_dir ~/vla_test_model \
    --batch_size 4 \
    --max_steps 1000 \
    --use_lora
```

### 3. Monitor Training

```bash
# Training will show progress:
# Epoch 1: 100%|██████████| 750/750 [12:34<00:00, loss=0.0234, lr=4.8e-05, step=3000]
# ✓ Saved checkpoint to ~/vla_checkpoints/checkpoint_step_3000.pt

# Watch GPU usage in another terminal
watch -n 1 nvidia-smi
```

### 4. Training Parameters

**Default settings:**
- Batch size: 4 (adjust based on GPU VRAM)
- Learning rate: 5e-5 (with cosine schedule)
- Max steps: 50,000 (OpenVLA recommendation)
- LoRA: rank=32, alpha=16
- Mixed precision: FP16 (faster training)
- Checkpoints: Every 1000 steps
- Warmup: 500 steps

**Adjust for your GPU:**
- 16GB VRAM: batch_size=2, gradient_accumulation=2
- 24GB VRAM: batch_size=4 (default)
- 40GB+ VRAM: batch_size=8

## After Training

### 1. Model Files

Training produces:
```
~/vla_finetuned_model/
├── final_model/              # Fine-tuned VLA model
│   ├── config.json
│   ├── pytorch_model.bin
│   └── ...
└── action_head.pt            # Action prediction head
```

### 2. Transfer Back to Robot

```bash
# On training machine, create package
cd ~
tar -czf vla_finetuned_package.tar.gz vla_finetuned_model/

# Transfer back (USB/SCP/Cloud)
scp vla_finetuned_package.tar.gz user@robot-machine:~/
```

### 3. On Robot System

```bash
# Extract model
cd ~
tar -xzf vla_finetuned_package.tar.gz

# Test model (create test script)
python3 test_model.py
```

## Troubleshooting

### Out of Memory (OOM)

```bash
# Reduce batch size
python3 train_openvla.py --batch_size 2 --max_steps 50000

# Or use gradient accumulation
# (Modify train_openvla.py to add gradient accumulation)
```

### Slow Training

- Ensure CUDA is working: `torch.cuda.is_available()`
- Check GPU utilization: `nvidia-smi`
- Enable mixed precision (already default)
- Use smaller model if needed

### Data Loading Issues

```bash
# Regenerate training data
python3 prepare_training_data.py \
    --dataset_dir ~/vla_dataset \
    --output_dir ~/vla_training_data
```

## Expected Training Time

| GPU | Batch Size | Steps | Time |
|-----|------------|-------|------|
| RTX 4090 | 4 | 50k | 10-14 hrs |
| A100 40GB | 4 | 50k | 8-10 hrs |
| A100 80GB | 8 | 50k | 5-7 hrs |

## Next Steps

1. **Prepare data**: Run `prepare_training_data.py`
2. **Transfer**: Move package to training machine
3. **Setup**: Install dependencies, download base model
4. **Train**: Run `train_openvla.py` for 50k steps
5. **Transfer back**: Move trained model to robot
6. **Deploy**: Create inference script for robot control

## Questions?

Common issues:
- **CUDA errors**: Update NVIDIA drivers, reinstall PyTorch with correct CUDA version
- **Import errors**: Install missing packages with pip
- **Model download fails**: Check internet, use HuggingFace token if needed
- **Training diverges**: Reduce learning rate (--learning_rate 1e-5)

Good luck with training! 🚀
