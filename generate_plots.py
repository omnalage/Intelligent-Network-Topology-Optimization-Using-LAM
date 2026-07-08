#!/usr/bin/env python3
"""
Generate specific plots from RL training logs.
"""

import os
import glob
import pandas as pd
import matplotlib.pyplot as plt

def plot_reward_vs_iteration():
    """Plot reward vs iteration from RL training."""
    # Find latest rewards log
    pattern = "Path_Iterations/rl_rewards_log_*.csv"
    files = glob.glob(pattern)
    if not files:
        print("No rewards log found.")
        return
    
    latest = max(files, key=os.path.getctime)
    df = pd.read_csv(latest)
    
    plt.figure(figsize=(10, 6))
    for ep in df['episode'].unique():
        ep_data = df[df['episode'] == ep]
        plt.plot(ep_data['iteration'], ep_data['reward'], label=f'Episode {ep}', alpha=0.7)
    
    plt.xlabel('Iteration')
    plt.ylabel('Reward')
    plt.title('Reward vs Iteration (RL Training)')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    
    out_path = "Path_Iterations/plots/reward_vs_iteration.png"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.savefig(out_path)
    plt.close()
    print(f"Saved: {out_path}")

def plot_router_selection_frequency():
    """Plot router selection frequency (already done in trainer, but recreate if needed)."""
    pattern = "Path_Iterations/rl_router_selection_counts_*.csv"
    files = glob.glob(pattern)
    if not files:
        print("No selection counts found.")
        return
    
    latest = max(files, key=os.path.getctime)
    df = pd.read_csv(latest)
    
    plt.figure(figsize=(12, 6))
    plt.bar(df['router'], df['selections'])
    plt.xlabel('Router')
    plt.ylabel('Selection Count')
    plt.title('Router Selection Frequency')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    out_path = "Path_Iterations/plots/router_selection_frequency.png"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.savefig(out_path)
    plt.close()
    print(f"Saved: {out_path}")

def plot_latency_comparison():
    """Plot latency comparison from RL training logs (first 100 iterations)."""
    pattern = "Path_Iterations/rl_selected_router_log_*.csv"
    files = glob.glob(pattern)
    if not files:
        print("No RL selection log found.")
        return
    
    latest = max(files, key=os.path.getctime)
    sel_df = pd.read_csv(latest)
    
    if len(sel_df) == 0:
        print("No data in selection logs.")
        return
    
    # Take first 100 iterations from first and last episodes for comparison
    episodes = sorted(sel_df['episode'].unique())
    
    # First episode as baseline, last episode as RL
    baseline_data = sel_df[sel_df['episode'] == episodes[0]].head(100).reset_index(drop=True)
    rl_data = sel_df[sel_df['episode'] == episodes[-1]].head(100).reset_index(drop=True)
    
    plt.figure(figsize=(10, 6))
    plt.plot(range(len(baseline_data)), baseline_data['latency_ms'].fillna(0), label='Baseline', marker='o', alpha=0.7, linewidth=2)
    plt.plot(range(len(rl_data)), rl_data['latency_ms'].fillna(0), label='RL (Trained)', marker='s', alpha=0.7, linewidth=2)
    
    plt.xlabel('Iteration')
    plt.ylabel('Latency (ms)')
    plt.title('Latency Comparison: Baseline vs RL (100 iterations)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    out_path = "Path_Iterations/plots/latency_comparison.png"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved: {out_path}")

def plot_chr_comparison():
    """Plot CHR comparison from RL training logs (first 100 iterations)."""
    pattern = "Path_Iterations/rl_selected_router_log_*.csv"
    files = glob.glob(pattern)
    if not files:
        print("No RL selection log found.")
        return
    
    latest = max(files, key=os.path.getctime)
    sel_df = pd.read_csv(latest)
    
    if len(sel_df) == 0:
        print("No data in selection logs.")
        return
    
    # Take first 100 iterations from first and last episodes for comparison
    episodes = sorted(sel_df['episode'].unique())
    
    # First episode as baseline, last episode as RL
    baseline_data = sel_df[sel_df['episode'] == episodes[0]].head(100).reset_index(drop=True)
    rl_data = sel_df[sel_df['episode'] == episodes[-1]].head(100).reset_index(drop=True)
    
    plt.figure(figsize=(10, 6))
    plt.plot(range(len(baseline_data)), baseline_data['chr'].fillna(0), label='Baseline', marker='o', alpha=0.7, linewidth=2)
    plt.plot(range(len(rl_data)), rl_data['chr'].fillna(0), label='RL (Trained)', marker='s', alpha=0.7, linewidth=2)
    
    plt.xlabel('Iteration')
    plt.ylabel('Cache Hit Ratio (CHR)')
    plt.title('CHR Comparison: Baseline vs RL (100 iterations)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    out_path = "Path_Iterations/plots/chr_comparison.png"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved: {out_path}")

if __name__ == "__main__":
    plot_reward_vs_iteration()
    plot_router_selection_frequency()
    plot_latency_comparison()
    plot_chr_comparison()
    print("All plots generated!")