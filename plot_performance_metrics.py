# plot_performance_metrics.py
"""
Comprehensive plotting functions for AI-based router selection performance metrics.
Plots: CHR, Latency, Hop Reduction, Detection Cost, Prediction Time, Accuracy
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Optional, Dict, List

CSV_DIR = "Path_Iterations"
PLOT_DIR = os.path.join(CSV_DIR, "plots")
os.makedirs(PLOT_DIR, exist_ok=True)


def plot_all_performance_metrics(metrics_csv: str = "Path_Iterations/performance_metrics.csv",
                                 save_plots: bool = True,
                                 show_plots: bool = False) -> Dict[str, str]:
    """
    Plot all 6 performance metrics as line charts with different markers.
    
    Metrics:
    1. CHR (Cache Hit Ratio)
    2. Latency
    3. Hop Reduction
    4. Detection Cost
    5. Prediction Time
    6. Accuracy
    
    Returns dictionary with paths to saved plots.
    """
    if not os.path.exists(metrics_csv):
        raise FileNotFoundError(f"Performance metrics CSV not found: {metrics_csv}")
    
    df = pd.read_csv(metrics_csv)
    
    if df.empty:
        raise ValueError("Performance metrics DataFrame is empty")
    
    # Ensure iteration column exists
    if 'iteration' not in df.columns:
        raise ValueError("CSV must contain 'iteration' column")
    
    # Sort by iteration
    df = df.sort_values('iteration').reset_index(drop=True)
    
    plot_paths = {}
    
    # Define markers for different metrics
    markers = {
        'CHR': 'o',           # circle
        'Latency': 's',        # square
        'HopReduction': '^',    # triangle up
        'DetectionCost': 'v',  # triangle down
        'PredictionTime': 'D',  # diamond
        'Accuracy': 'x'        # x marker
    }
    
    # Define colors
    colors = {
        'CHR': '#2E86AB',           # Blue
        'Latency': '#A23B72',       # Purple
        'HopReduction': '#F18F01',  # Orange
        'DetectionCost': '#C73E1D', # Red
        'PredictionTime': '#6A994E', # Green
        'Accuracy': '#D62828'       # Dark Red
    }
    
    # Define labels and units
    labels = {
        'CHR': 'Cache Hit Ratio (CHR)',
        'Latency': 'Latency (ms)',
        'HopReduction': 'Hop Reduction',
        'DetectionCost': 'Detection Cost (ms)',
        'PredictionTime': 'Prediction Time (ms)',
        'Accuracy': 'Accuracy'
    }
    
    # Plot 1: Individual metric plots (6 separate plots)
    for metric in ['CHR', 'Latency', 'HopReduction', 'DetectionCost', 'PredictionTime', 'Accuracy']:
        if metric not in df.columns:
            print(f"[plot_all_performance_metrics] Warning: {metric} not found in CSV, skipping")
            continue
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        iterations = df['iteration'].values
        values = df[metric].values
        
        ax.plot(iterations, values, 
                marker=markers[metric], 
                color=colors[metric],
                linestyle='-',
                linewidth=2,
                markersize=6,
                label=labels[metric],
                alpha=0.8)
        
        # Add trend line
        z = np.polyfit(iterations, values, 1)
        p = np.poly1d(z)
        ax.plot(iterations, p(iterations), 
                linestyle='--', 
                color=colors[metric], 
                alpha=0.5,
                linewidth=1,
                label=f'Trend ({labels[metric]})')
        
        ax.set_xlabel('Iteration', fontsize=12, fontweight='bold')
        ax.set_ylabel(labels[metric], fontsize=12, fontweight='bold')
        ax.set_title(f'{labels[metric]} Over Iterations', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='best')
        ax.set_xlim(left=min(iterations), right=max(iterations))
        
        plt.tight_layout()
        
        if save_plots:
            plot_path = os.path.join(PLOT_DIR, f'{metric.lower()}_over_iterations.png')
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            plot_paths[f'{metric}_individual'] = plot_path
            print(f"[plot_all_performance_metrics] Saved {metric} plot: {plot_path}")
        
        if show_plots:
            plt.show()
        else:
            plt.close()
    
    # Plot 2: Combined plot (all metrics on one chart with normalized y-axis)
    fig, ax = plt.subplots(figsize=(14, 8))
    
    iterations = df['iteration'].values
    
    for metric in ['CHR', 'Latency', 'HopReduction', 'DetectionCost', 'PredictionTime', 'Accuracy']:
        if metric not in df.columns:
            continue
        
        values = df[metric].values
        
        # Normalize values to 0-1 for comparison
        if values.max() > values.min():
            normalized = (values - values.min()) / (values.max() - values.min())
        else:
            normalized = values
        
        ax.plot(iterations, normalized,
                marker=markers[metric],
                color=colors[metric],
                linestyle='-',
                linewidth=2,
                markersize=5,
                label=labels[metric],
                alpha=0.8)
    
    ax.set_xlabel('Iteration', fontsize=12, fontweight='bold')
    ax.set_ylabel('Normalized Value (0-1)', fontsize=12, fontweight='bold')
    ax.set_title('All Performance Metrics Over Iterations (Normalized)', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(loc='best', ncol=2, fontsize=10)
    ax.set_xlim(left=min(iterations), right=max(iterations))
    
    plt.tight_layout()
    
    if save_plots:
        plot_path = os.path.join(PLOT_DIR, 'all_metrics_combined_normalized.png')
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plot_paths['all_metrics_combined'] = plot_path
        print(f"[plot_all_performance_metrics] Saved combined plot: {plot_path}")
    
    if show_plots:
        plt.show()
    else:
        plt.close()
    
    # Plot 3: Subplot grid (2x3 layout)
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    axes = axes.flatten()
    
    metric_list = ['CHR', 'Latency', 'HopReduction', 'DetectionCost', 'PredictionTime', 'Accuracy']
    
    for idx, metric in enumerate(metric_list):
        if metric not in df.columns:
            axes[idx].text(0.5, 0.5, f'{metric}\nNot Available', 
                          ha='center', va='center', transform=axes[idx].transAxes)
            axes[idx].set_title(labels.get(metric, metric), fontsize=11, fontweight='bold')
            continue
        
        iterations = df['iteration'].values
        values = df[metric].values
        
        axes[idx].plot(iterations, values,
                      marker=markers[metric],
                      color=colors[metric],
                      linestyle='-',
                      linewidth=2,
                      markersize=4,
                      alpha=0.8)
        
        axes[idx].set_xlabel('Iteration', fontsize=10)
        axes[idx].set_ylabel(labels[metric], fontsize=10)
        axes[idx].set_title(labels[metric], fontsize=11, fontweight='bold')
        axes[idx].grid(True, alpha=0.3, linestyle='--')
        axes[idx].set_xlim(left=min(iterations), right=max(iterations))
    
    plt.tight_layout()
    
    if save_plots:
        plot_path = os.path.join(PLOT_DIR, 'all_metrics_subplots.png')
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plot_paths['all_metrics_subplots'] = plot_path
        print(f"[plot_all_performance_metrics] Saved subplot grid: {plot_path}")
    
    if show_plots:
        plt.show()
    else:
        plt.close()
    
    # Plot 4: Statistical summary (box plots and statistics)
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    axes = axes.flatten()
    
    for idx, metric in enumerate(metric_list):
        if metric not in df.columns:
            axes[idx].text(0.5, 0.5, f'{metric}\nNot Available',
                          ha='center', va='center', transform=axes[idx].transAxes)
            axes[idx].set_title(labels.get(metric, metric), fontsize=11, fontweight='bold')
            continue
        
        values = df[metric].values
        
        # Box plot
        bp = axes[idx].boxplot([values], patch_artist=True, labels=[labels[metric]])
        bp['boxes'][0].set_facecolor(colors[metric])
        bp['boxes'][0].set_alpha(0.7)
        
        # Add statistics text
        mean_val = np.mean(values)
        std_val = np.std(values)
        median_val = np.median(values)
        
        stats_text = f'Mean: {mean_val:.4f}\nStd: {std_val:.4f}\nMedian: {median_val:.4f}'
        axes[idx].text(0.02, 0.98, stats_text,
                      transform=axes[idx].transAxes,
                      verticalalignment='top',
                      bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
                      fontsize=9)
        
        axes[idx].set_ylabel('Value', fontsize=10)
        axes[idx].set_title(f'{labels[metric]} - Distribution', fontsize=11, fontweight='bold')
        axes[idx].grid(True, alpha=0.3, linestyle='--', axis='y')
    
    plt.tight_layout()
    
    if save_plots:
        plot_path = os.path.join(PLOT_DIR, 'all_metrics_statistics.png')
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plot_paths['all_metrics_statistics'] = plot_path
        print(f"[plot_all_performance_metrics] Saved statistics plot: {plot_path}")
    
    if show_plots:
        plt.show()
    else:
        plt.close()
    
    return plot_paths


def plot_metric_comparison(metrics_csv: str = "Path_Iterations/performance_metrics.csv",
                          baseline_csv: Optional[str] = None,
                          save_plots: bool = True,
                          show_plots: bool = False) -> Dict[str, str]:
    """
    Compare AI metrics against baseline (ICN) if provided.
    """
    if not os.path.exists(metrics_csv):
        raise FileNotFoundError(f"Performance metrics CSV not found: {metrics_csv}")
    
    df_ai = pd.read_csv(metrics_csv)
    df_ai = df_ai.sort_values('iteration').reset_index(drop=True)
    
    plot_paths = {}
    
    # If baseline provided, create comparison plots
    if baseline_csv and os.path.exists(baseline_csv):
        df_baseline = pd.read_csv(baseline_csv)
        df_baseline = df_baseline.sort_values('iteration').reset_index(drop=True)
        
        # Comparison plot for key metrics
        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        axes = axes.flatten()
        
        comparison_metrics = ['CHR', 'Latency', 'HopReduction', 'Accuracy']
        
        for idx, metric in enumerate(comparison_metrics):
            if metric not in df_ai.columns or metric not in df_baseline.columns:
                continue
            
            iterations = df_ai['iteration'].values
            ai_values = df_ai[metric].values
            baseline_values = df_baseline[metric].values
            
            axes[idx].plot(iterations, ai_values, 
                          marker='o', color='#2E86AB', linewidth=2, 
                          markersize=5, label='AI-Based', alpha=0.8)
            axes[idx].plot(iterations, baseline_values,
                          marker='s', color='#A23B72', linewidth=2,
                          markersize=5, label='ICN-Based', alpha=0.8)
            
            axes[idx].set_xlabel('Iteration', fontsize=11)
            axes[idx].set_ylabel(metric, fontsize=11)
            axes[idx].set_title(f'{metric} Comparison: AI vs ICN', fontsize=12, fontweight='bold')
            axes[idx].legend(loc='best')
            axes[idx].grid(True, alpha=0.3, linestyle='--')
        
        plt.tight_layout()
        
        if save_plots:
            plot_path = os.path.join(PLOT_DIR, 'ai_vs_icn_metrics_comparison.png')
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            plot_paths['comparison'] = plot_path
            print(f"[plot_metric_comparison] Saved comparison plot: {plot_path}")
        
        if show_plots:
            plt.show()
        else:
            plt.close()
    
    return plot_paths


if __name__ == "__main__":
    # Test plotting
    try:
        plot_paths = plot_all_performance_metrics()
        print("\n[+] All performance metric plots generated successfully!")
        print("Plot paths:")
        for key, path in plot_paths.items():
            print(f"  - {key}: {path}")
    except Exception as e:
        print(f"[-] Error generating plots: {e}")
        import traceback
        traceback.print_exc()

