#!/usr/bin/env python3
"""
Data Preparation for OpenVLA Fine-Tuning
Converts raw episodes to training format for OpenVLA-OFT.
"""

import json
import pickle
import numpy as np
from pathlib import Path
from PIL import Image
import cv2
from tqdm import tqdm

def load_episodes(dataset_dir):
    """Load all episodes from dataset directory"""
    dataset_path = Path(dataset_dir)
    episodes = []
    
    episode_dirs = sorted(dataset_path.glob("episode_*"))
    print(f"Found {len(episode_dirs)} episodes")
    
    for ep_dir in tqdm(episode_dirs, desc="Loading episodes"):
        # Load trajectory metadata
        traj_file = ep_dir / "trajectory.json"
        if not traj_file.exists():
            print(f"Warning: No trajectory.json in {ep_dir}")
            continue
            
        with open(traj_file, 'r') as f:
            trajectory = json.load(f)
        
        episode_data = {
            'episode_id': trajectory['episode_id'],
            'task': trajectory['task'],
            'frames': []
        }
        
        # Load each frame
        for frame in trajectory['frames']:
            img_path = ep_dir / frame['image_path']
            if not img_path.exists():
                print(f"Warning: Missing image {img_path}")
                continue
            
            # Load and resize image to 224x224 (OpenVLA input size)
            img = cv2.imread(str(img_path))
            img = cv2.resize(img, (224, 224))
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            episode_data['frames'].append({
                'image': img,
                'joint_positions': np.array(frame['joint_positions'], dtype=np.float32),
                'joint_positions_steps': np.array(frame['joint_positions_steps'], dtype=np.int32),
                'timestamp': frame['timestamp']
            })
        
        if len(episode_data['frames']) > 0:
            episodes.append(episode_data)
    
    return episodes

def compute_action_deltas(episodes, action_horizon=1):
    """
    Compute action deltas (next N joint positions - current)
    action_horizon: how many steps ahead to predict (1 = next frame)
    """
    training_samples = []
    
    for episode in tqdm(episodes, desc="Computing actions"):
        frames = episode['frames']
        
        for i in range(len(frames) - action_horizon):
            current_frame = frames[i]
            future_frame = frames[i + action_horizon]
            
            # Action = delta in joint positions (degrees)
            action = future_frame['joint_positions'] - current_frame['joint_positions']
            
            # Normalize actions to [-1, 1] range
            # Assume max movement is 10 degrees per step
            max_delta = 10.0
            action_normalized = np.clip(action / max_delta, -1.0, 1.0)
            
            training_samples.append({
                'image': current_frame['image'],
                'joint_positions': current_frame['joint_positions'],
                'action': action_normalized,
                'action_raw': action,
                'instruction': episode['task'],
                'episode_id': episode['episode_id']
            })
    
    return training_samples

def save_training_data(samples, output_dir):
    """Save processed training data"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Save as pickle file
    output_file = output_path / "training_data.pkl"
    with open(output_file, 'wb') as f:
        pickle.dump(samples, f)
    
    print(f"\n✓ Saved {len(samples)} training samples to {output_file}")
    
    # Save statistics
    stats = {
        'num_samples': len(samples),
        'image_shape': samples[0]['image'].shape,
        'action_dim': len(samples[0]['action']),
        'unique_episodes': len(set(s['episode_id'] for s in samples)),
        'instruction': samples[0]['instruction']
    }
    
    stats_file = output_path / "dataset_stats.json"
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    
    print(f"✓ Dataset statistics saved to {stats_file}")
    
    # Print summary
    print("\n" + "="*70)
    print("Dataset Summary:")
    print("="*70)
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print("="*70)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Prepare OpenVLA training data")
    parser.add_argument('--dataset_dir', type=str, default='~/vla_dataset',
                        help='Directory containing episode_XXXX folders')
    parser.add_argument('--output_dir', type=str, default='~/vla_training_data',
                        help='Output directory for processed data')
    parser.add_argument('--action_horizon', type=int, default=1,
                        help='Frames ahead to predict (1=next frame)')
    args = parser.parse_args()
    
    dataset_dir = Path(args.dataset_dir).expanduser()
    output_dir = Path(args.output_dir).expanduser()
    
    print("\n" + "="*70)
    print("OpenVLA Data Preparation")
    print("="*70)
    print(f"Dataset: {dataset_dir}")
    print(f"Output: {output_dir}")
    print(f"Action horizon: {args.action_horizon} frames")
    print("="*70 + "\n")
    
    # Load episodes
    episodes = load_episodes(dataset_dir)
    print(f"\n✓ Loaded {len(episodes)} episodes")
    
    # Compute actions
    samples = compute_action_deltas(episodes, args.action_horizon)
    print(f"✓ Created {len(samples)} training samples")
    
    # Save
    save_training_data(samples, output_dir)
    
    print("\n" + "="*70)
    print("Data preparation complete!")
    print("="*70)
    print(f"\nNext steps:")
    print(f"  1. Copy {output_dir} to your training machine")
    print(f"  2. Run training script with this data")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
