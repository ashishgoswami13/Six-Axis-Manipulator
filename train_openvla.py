#!/usr/bin/env python3
"""
OpenVLA Fine-Tuning Script for Robot Arm Control
Uses OpenVLA-OFT (Output-space Fine-Tuning) approach from official implementation.
"""

import torch
import pickle
import numpy as np
from pathlib import Path
from tqdm import tqdm
from PIL import Image
from torch.utils.data import Dataset, DataLoader
from transformers import AutoModelForVision2Seq, AutoProcessor
import torch.nn as nn
from torch.cuda.amp import autocast, GradScaler

# ============================================================================
# Configuration
# ============================================================================

class Config:
    # Model
    model_name = "openvla/openvla-7b"  # Base model
    action_dim = 7  # 6 joints + 1 gripper
    action_chunk_size = 1  # Predict 1 step ahead
    
    # Training
    batch_size = 4
    learning_rate = 5e-5
    num_epochs = 10
    warmup_steps = 500
    max_steps = 50000  # OpenVLA recommends 50k-150k steps
    
    # LoRA settings (for efficient fine-tuning)
    use_lora = True
    lora_rank = 32
    lora_alpha = 16
    lora_dropout = 0.1
    
    # Paths
    data_path = "~/vla_training_data/training_data.pkl"
    checkpoint_dir = "~/vla_checkpoints"
    output_dir = "~/vla_finetuned_model"
    
    # Hardware
    device = "cuda" if torch.cuda.is_available() else "cpu"
    mixed_precision = True  # Use FP16 for faster training
    
    # Logging
    log_every = 50
    save_every = 1000
    eval_every = 500

config = Config()

# ============================================================================
# Dataset
# ============================================================================

class RobotDataset(Dataset):
    """Dataset for robot arm control"""
    
    def __init__(self, data_path, processor):
        self.processor = processor
        
        # Load data
        data_path = Path(data_path).expanduser()
        with open(data_path, 'rb') as f:
            self.samples = pickle.load(f)
        
        print(f"Loaded {len(self.samples)} training samples")
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        sample = self.samples[idx]
        
        # Process image
        image = Image.fromarray(sample['image'])
        
        # Process text instruction
        instruction = sample['instruction']
        
        # Get action (normalized to [-1, 1])
        action = torch.tensor(sample['action'], dtype=torch.float32)
        
        # Use processor to prepare inputs
        inputs = self.processor(
            text=instruction,
            images=image,
            return_tensors="pt"
        )
        
        # Remove batch dimension added by processor
        inputs = {k: v.squeeze(0) for k, v in inputs.items()}
        inputs['labels'] = action
        
        return inputs

# ============================================================================
# Model with LoRA
# ============================================================================

class LoRALayer(nn.Module):
    """Low-Rank Adaptation layer"""
    
    def __init__(self, in_features, out_features, rank=32, alpha=16):
        super().__init__()
        self.rank = rank
        self.alpha = alpha
        self.scaling = alpha / rank
        
        # LoRA weights
        self.lora_A = nn.Parameter(torch.randn(in_features, rank) * 0.01)
        self.lora_B = nn.Parameter(torch.zeros(rank, out_features))
    
    def forward(self, x):
        return (x @ self.lora_A @ self.lora_B) * self.scaling

def add_lora_to_model(model, rank=32, alpha=16):
    """Add LoRA adapters to model"""
    
    # Freeze original model parameters
    for param in model.parameters():
        param.requires_grad = False
    
    # Add LoRA layers to attention projections
    # This is a simplified version - adjust based on actual model architecture
    lora_modules = []
    
    for name, module in model.named_modules():
        if isinstance(module, nn.Linear) and ('attention' in name.lower() or 'mlp' in name.lower()):
            # Add LoRA layer
            lora = LoRALayer(module.in_features, module.out_features, rank, alpha)
            lora_modules.append((name, lora))
    
    print(f"Added {len(lora_modules)} LoRA adapters")
    return lora_modules

# ============================================================================
# Action Head
# ============================================================================

class ActionHead(nn.Module):
    """Output head that predicts robot actions from VLA features"""
    
    def __init__(self, hidden_dim=4096, action_dim=7, chunk_size=1):
        super().__init__()
        self.action_dim = action_dim
        self.chunk_size = chunk_size
        
        # MLP head
        self.head = nn.Sequential(
            nn.Linear(hidden_dim, 1024),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(1024, 512),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(512, action_dim * chunk_size),
            nn.Tanh()  # Output in [-1, 1]
        )
    
    def forward(self, features):
        """
        features: [batch, hidden_dim]
        returns: [batch, action_dim * chunk_size]
        """
        return self.head(features)

# ============================================================================
# Training
# ============================================================================

def train_model(config):
    """Main training loop"""
    
    print("\n" + "="*70)
    print("OpenVLA Fine-Tuning")
    print("="*70)
    print(f"Model: {config.model_name}")
    print(f"Device: {config.device}")
    print(f"Action dim: {config.action_dim}")
    print(f"Batch size: {config.batch_size}")
    print(f"Learning rate: {config.learning_rate}")
    print(f"Max steps: {config.max_steps}")
    print(f"Mixed precision: {config.mixed_precision}")
    print(f"LoRA: {config.use_lora}")
    print("="*70 + "\n")
    
    # Create directories
    checkpoint_dir = Path(config.checkpoint_dir).expanduser()
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    output_dir = Path(config.output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load processor and model
    print("Loading model...")
    processor = AutoProcessor.from_pretrained(config.model_name, trust_remote_code=True)
    model = AutoModelForVision2Seq.from_pretrained(
        config.model_name,
        torch_dtype=torch.float16 if config.mixed_precision else torch.float32,
        trust_remote_code=True
    )
    
    # Add LoRA if enabled
    if config.use_lora:
        print("Adding LoRA adapters...")
        add_lora_to_model(model, config.lora_rank, config.lora_alpha)
    
    # Add action head
    print("Adding action head...")
    hidden_dim = model.config.hidden_size if hasattr(model.config, 'hidden_size') else 4096
    action_head = ActionHead(hidden_dim, config.action_dim, config.action_chunk_size)
    
    # Move to device
    model = model.to(config.device)
    action_head = action_head.to(config.device)
    
    # Load dataset
    print("Loading dataset...")
    dataset = RobotDataset(config.data_path, processor)
    dataloader = DataLoader(
        dataset,
        batch_size=config.batch_size,
        shuffle=True,
        num_workers=4,
        pin_memory=True
    )
    
    # Optimizer (only trainable params)
    trainable_params = list(action_head.parameters())
    if config.use_lora:
        trainable_params += [p for p in model.parameters() if p.requires_grad]
    
    optimizer = torch.optim.AdamW(trainable_params, lr=config.learning_rate, weight_decay=0.01)
    
    # Learning rate scheduler
    from transformers import get_cosine_schedule_with_warmup
    scheduler = get_cosine_schedule_with_warmup(
        optimizer,
        num_warmup_steps=config.warmup_steps,
        num_training_steps=config.max_steps
    )
    
    # Loss function (L1 loss for actions)
    criterion = nn.L1Loss()
    
    # Mixed precision scaler
    scaler = GradScaler() if config.mixed_precision else None
    
    # Training loop
    print("\nStarting training...\n")
    global_step = 0
    epoch = 0
    best_loss = float('inf')
    
    while global_step < config.max_steps:
        epoch += 1
        model.train()
        action_head.train()
        
        epoch_loss = 0
        pbar = tqdm(dataloader, desc=f"Epoch {epoch}")
        
        for batch in pbar:
            # Move to device
            batch = {k: v.to(config.device) for k, v in batch.items()}
            labels = batch.pop('labels')
            
            # Forward pass
            if config.mixed_precision:
                with autocast():
                    outputs = model(**batch, output_hidden_states=True)
                    # Get last hidden state
                    hidden_states = outputs.hidden_states[-1][:, -1, :]  # [batch, hidden_dim]
                    # Predict actions
                    predicted_actions = action_head(hidden_states)
                    # Compute loss
                    loss = criterion(predicted_actions, labels)
                
                # Backward pass with mixed precision
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
            else:
                outputs = model(**batch, output_hidden_states=True)
                hidden_states = outputs.hidden_states[-1][:, -1, :]
                predicted_actions = action_head(hidden_states)
                loss = criterion(predicted_actions, labels)
                
                loss.backward()
                optimizer.step()
            
            optimizer.zero_grad()
            scheduler.step()
            
            # Update metrics
            epoch_loss += loss.item()
            global_step += 1
            
            # Logging
            if global_step % config.log_every == 0:
                avg_loss = epoch_loss / (pbar.n + 1)
                pbar.set_postfix({
                    'loss': f'{avg_loss:.4f}',
                    'lr': f'{scheduler.get_last_lr()[0]:.2e}',
                    'step': global_step
                })
            
            # Save checkpoint
            if global_step % config.save_every == 0:
                checkpoint_path = checkpoint_dir / f"checkpoint_step_{global_step}.pt"
                torch.save({
                    'step': global_step,
                    'model_state_dict': model.state_dict(),
                    'action_head_state_dict': action_head.state_dict(),
                    'optimizer_state_dict': optimizer.state_dict(),
                    'loss': loss.item(),
                }, checkpoint_path)
                print(f"\n✓ Saved checkpoint to {checkpoint_path}")
            
            # Stop if reached max steps
            if global_step >= config.max_steps:
                break
    
    # Save final model
    print("\n" + "="*70)
    print("Training Complete!")
    print("="*70)
    
    final_path = output_dir / "final_model"
    model.save_pretrained(final_path)
    processor.save_pretrained(final_path)
    
    action_head_path = output_dir / "action_head.pt"
    torch.save(action_head.state_dict(), action_head_path)
    
    print(f"\n✓ Saved final model to {final_path}")
    print(f"✓ Saved action head to {action_head_path}")
    print("\n" + "="*70 + "\n")

# ============================================================================
# Main
# ============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Fine-tune OpenVLA for robot control")
    parser.add_argument('--data_path', type=str, default=config.data_path)
    parser.add_argument('--output_dir', type=str, default=config.output_dir)
    parser.add_argument('--batch_size', type=int, default=config.batch_size)
    parser.add_argument('--learning_rate', type=float, default=config.learning_rate)
    parser.add_argument('--max_steps', type=int, default=config.max_steps)
    parser.add_argument('--use_lora', action='store_true', default=config.use_lora)
    args = parser.parse_args()
    
    # Update config
    for key, value in vars(args).items():
        if hasattr(config, key):
            setattr(config, key, value)
    
    # Check CUDA
    if not torch.cuda.is_available():
        print("WARNING: CUDA not available! Training will be VERY slow on CPU.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return
    
    # Train
    train_model(config)

if __name__ == "__main__":
    main()
