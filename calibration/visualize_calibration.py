#!/usr/bin/env python3
"""
Calibration Visualization Tool
===============================

Visualizes calibration errors and helps analyze calibration quality.
"""

import numpy as np
import json
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import sys


def load_calibration_data(filename='calibration_data.json'):
    """Load calibration data from JSON file"""
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"✗ File not found: {filename}")
        return None
    except json.JSONDecodeError:
        print(f"✗ Invalid JSON in {filename}")
        return None


def plot_errors_3d(data):
    """Plot actual vs predicted positions in 3D"""
    points = data['calibration_points']
    
    predicted = np.array([p['predicted_position'] for p in points])
    actual = np.array([p['actual_position'] for p in points])
    
    fig = plt.figure(figsize=(14, 6))
    
    # 3D scatter plot
    ax1 = fig.add_subplot(121, projection='3d')
    
    # Plot predicted positions
    ax1.scatter(predicted[:, 0], predicted[:, 1], predicted[:, 2], 
                c='blue', marker='o', s=100, label='Predicted', alpha=0.6)
    
    # Plot actual positions  
    ax1.scatter(actual[:, 0], actual[:, 1], actual[:, 2],
                c='red', marker='^', s=100, label='Actual', alpha=0.6)
    
    # Draw error vectors
    for i in range(len(points)):
        ax1.plot([predicted[i, 0], actual[i, 0]],
                [predicted[i, 1], actual[i, 1]],
                [predicted[i, 2], actual[i, 2]],
                'gray', linestyle='--', alpha=0.3)
    
    ax1.set_xlabel('X (mm)')
    ax1.set_ylabel('Y (mm)')
    ax1.set_zlabel('Z (mm)')
    ax1.set_title('Predicted vs Actual Positions')
    ax1.legend()
    ax1.grid(True)
    
    # Error magnitude plot
    ax2 = fig.add_subplot(122)
    
    errors = [p['error'] for p in points]
    positions_names = [p['position_name'] for p in points]
    
    colors = ['red' if e > 10 else 'orange' if e > 5 else 'green' for e in errors]
    bars = ax2.bar(range(len(errors)), errors, color=colors, alpha=0.7)
    
    ax2.set_xlabel('Calibration Point')
    ax2.set_ylabel('Position Error (mm)')
    ax2.set_title('Error Magnitude by Position')
    ax2.axhline(y=5, color='orange', linestyle='--', label='5mm threshold')
    ax2.axhline(y=10, color='red', linestyle='--', label='10mm threshold')
    ax2.set_xticks(range(len(errors)))
    ax2.set_xticklabels([f"{i+1}" for i in range(len(errors))], rotation=45)
    ax2.legend()
    ax2.grid(True, axis='y')
    
    plt.tight_layout()
    plt.savefig('calibration_errors.png', dpi=150)
    print("✓ Saved calibration_errors.png")
    plt.show()


def plot_error_components(data):
    """Plot error components (X, Y, Z)"""
    points = data['calibration_points']
    
    predicted = np.array([p['predicted_position'] for p in points])
    actual = np.array([p['actual_position'] for p in points])
    
    errors = actual - predicted
    
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # X error
    axes[0, 0].bar(range(len(errors)), errors[:, 0], color='red', alpha=0.7)
    axes[0, 0].set_title('X-axis Error')
    axes[0, 0].set_ylabel('Error (mm)')
    axes[0, 0].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    axes[0, 0].grid(True, axis='y')
    
    # Y error
    axes[0, 1].bar(range(len(errors)), errors[:, 1], color='green', alpha=0.7)
    axes[0, 1].set_title('Y-axis Error')
    axes[0, 1].set_ylabel('Error (mm)')
    axes[0, 1].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    axes[0, 1].grid(True, axis='y')
    
    # Z error
    axes[1, 0].bar(range(len(errors)), errors[:, 2], color='blue', alpha=0.7)
    axes[1, 0].set_title('Z-axis Error')
    axes[1, 0].set_ylabel('Error (mm)')
    axes[1, 0].set_xlabel('Calibration Point')
    axes[1, 0].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    axes[1, 0].grid(True, axis='y')
    
    # Error distribution
    axes[1, 1].hist([errors[:, 0], errors[:, 1], errors[:, 2]], 
                    bins=10, label=['X', 'Y', 'Z'], alpha=0.7)
    axes[1, 1].set_title('Error Distribution')
    axes[1, 1].set_xlabel('Error (mm)')
    axes[1, 1].set_ylabel('Frequency')
    axes[1, 1].legend()
    axes[1, 1].grid(True, axis='y')
    
    plt.tight_layout()
    plt.savefig('calibration_error_components.png', dpi=150)
    print("✓ Saved calibration_error_components.png")
    plt.show()


def plot_workspace_coverage(data):
    """Plot calibration point coverage in workspace"""
    points = data['calibration_points']
    actual = np.array([p['actual_position'] for p in points])
    
    fig = plt.figure(figsize=(15, 5))
    
    # XY plane (top view)
    ax1 = fig.add_subplot(131)
    ax1.scatter(actual[:, 0], actual[:, 1], c='blue', s=100, alpha=0.6)
    ax1.scatter(0, 0, c='red', marker='x', s=200, label='Robot Base')
    for i, pos in enumerate(actual):
        ax1.annotate(f"{i+1}", (pos[0], pos[1]), fontsize=8)
    ax1.set_xlabel('X (mm)')
    ax1.set_ylabel('Y (mm)')
    ax1.set_title('Top View (XY Plane)')
    ax1.grid(True)
    ax1.axis('equal')
    ax1.legend()
    
    # XZ plane (side view)
    ax2 = fig.add_subplot(132)
    ax2.scatter(actual[:, 0], actual[:, 2], c='blue', s=100, alpha=0.6)
    ax2.scatter(0, 0, c='red', marker='x', s=200, label='Robot Base')
    for i, pos in enumerate(actual):
        ax2.annotate(f"{i+1}", (pos[0], pos[2]), fontsize=8)
    ax2.set_xlabel('X (mm)')
    ax2.set_ylabel('Z (mm)')
    ax2.set_title('Side View (XZ Plane)')
    ax2.grid(True)
    ax2.axis('equal')
    ax2.legend()
    
    # YZ plane (front view)
    ax3 = fig.add_subplot(133)
    ax3.scatter(actual[:, 1], actual[:, 2], c='blue', s=100, alpha=0.6)
    ax3.scatter(0, 0, c='red', marker='x', s=200, label='Robot Base')
    for i, pos in enumerate(actual):
        ax3.annotate(f"{i+1}", (pos[1], pos[2]), fontsize=8)
    ax3.set_xlabel('Y (mm)')
    ax3.set_ylabel('Z (mm)')
    ax3.set_title('Front View (YZ Plane)')
    ax3.grid(True)
    ax3.axis('equal')
    ax3.legend()
    
    plt.tight_layout()
    plt.savefig('calibration_workspace_coverage.png', dpi=150)
    print("✓ Saved calibration_workspace_coverage.png")
    plt.show()


def print_statistics(data):
    """Print detailed calibration statistics"""
    print("\n" + "="*70)
    print("CALIBRATION STATISTICS")
    print("="*70)
    
    stats = data.get('statistics', {})
    points = data['calibration_points']
    
    print(f"\nNumber of calibration points: {stats.get('num_points', len(points))}")
    print(f"Calibration timestamp:        {data.get('timestamp', 'Unknown')}")
    
    print("\nPosition Error (mm):")
    print(f"  Mean:  {stats.get('mean_error', 0):.2f}")
    print(f"  Max:   {stats.get('max_error', 0):.2f}")
    print(f"  Min:   {stats.get('min_error', 0):.2f}")
    
    # Calculate component errors
    predicted = np.array([p['predicted_position'] for p in points])
    actual = np.array([p['actual_position'] for p in points])
    errors = actual - predicted
    
    print("\nError by Axis (mm):")
    print(f"  X-axis: mean={np.mean(errors[:, 0]):.2f}, std={np.std(errors[:, 0]):.2f}")
    print(f"  Y-axis: mean={np.mean(errors[:, 1]):.2f}, std={np.std(errors[:, 1]):.2f}")
    print(f"  Z-axis: mean={np.mean(errors[:, 2]):.2f}, std={np.std(errors[:, 2]):.2f}")
    
    # Workspace coverage
    print("\nWorkspace Coverage:")
    print(f"  X range: [{np.min(actual[:, 0]):.1f}, {np.max(actual[:, 0]):.1f}] mm")
    print(f"  Y range: [{np.min(actual[:, 1]):.1f}, {np.max(actual[:, 1]):.1f}] mm")
    print(f"  Z range: [{np.min(actual[:, 2]):.1f}, {np.max(actual[:, 2]):.1f}] mm")
    
    # Quality assessment
    print("\nCalibration Quality:")
    mean_error = stats.get('mean_error', 0)
    if mean_error < 3:
        quality = "EXCELLENT"
        color = "✓"
    elif mean_error < 5:
        quality = "GOOD"
        color = "✓"
    elif mean_error < 10:
        quality = "FAIR"
        color = "!"
    else:
        quality = "POOR"
        color = "✗"
    
    print(f"  {color} {quality} (mean error: {mean_error:.1f} mm)")
    
    if mean_error > 10:
        print("\nRecommendations:")
        print("  • Check measurement accuracy")
        print("  • Collect more calibration points")
        print("  • Verify robot mechanical assembly")
    elif mean_error > 5:
        print("\nRecommendations:")
        print("  • Consider collecting more points in high-error regions")
        print("  • Run parameter optimization")
    else:
        print("\nRecommendations:")
        print("  • ✓ Ready for parameter optimization")
        print("  • ✓ Calibration data quality is good")
    
    print("\n" + "="*70 + "\n")


def main():
    """Main visualization function"""
    print("="*70)
    print("  CALIBRATION DATA VISUALIZATION")
    print("="*70 + "\n")
    
    # Load data
    filename = 'calibration_data.json'
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    
    print(f"Loading: {filename}")
    data = load_calibration_data(filename)
    
    if data is None:
        return
    
    print(f"✓ Loaded {len(data['calibration_points'])} calibration points\n")
    
    # Print statistics
    print_statistics(data)
    
    # Generate plots
    print("Generating visualizations...")
    print()
    
    try:
        plot_errors_3d(data)
        plot_error_components(data)
        plot_workspace_coverage(data)
        
        print("\n✓ All visualizations complete!")
        print("\nGenerated files:")
        print("  • calibration_errors.png")
        print("  • calibration_error_components.png")
        print("  • calibration_workspace_coverage.png")
        
    except Exception as e:
        print(f"\n✗ Error generating plots: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
