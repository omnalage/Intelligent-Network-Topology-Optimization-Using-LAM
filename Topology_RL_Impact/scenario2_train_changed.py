#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCENARIO 2: Apply Topology Change & Train Fresh RL Agent
This script:
1. Loads original network snapshot from Scenario 1
2. Applies topology change (move subscribers randomly)
3. Saves changed network snapshot
4. Visualizes before/after topologies
5. Pre-simulates on changed topology (50 iterations)
6. Computes centrality on changed topology
7. Trains fresh DQN Agent B for 10 episodes x 100 iterations
8. Saves agent and logs
"""

import os
import sys
import pickle
import torch
import numpy as np
import pandas as pd
import copy
from datetime import datetime
import shutil

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
os.chdir(parent_dir)

from main import load_network, setup_network, run_simulation, plot_centrality_measures, plot_network_graph
from rl_env import CacheEnvironment
from dqn_agent import DQNAgent
from trainer import train_agent

# Output directory - already running from inside Topology_RL_Impact folder
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(f"{OUTPUT_DIR}/logs", exist_ok=True)
os.makedirs(f"{OUTPUT_DIR}/models", exist_ok=True)
os.makedirs(f"{OUTPUT_DIR}/plots", exist_ok=True)


def load_network_snapshot(label):
    """Load network snapshot"""
    with open(f"{OUTPUT_DIR}/network_snapshot_{label}.pkl", "rb") as f:
        return pickle.load(f)


def save_network_snapshot(routers, publishers, subscribers, label):
    """Save network snapshot"""
    with open(f"{OUTPUT_DIR}/network_snapshot_{label}.pkl", "wb") as f:
        pickle.dump((routers, publishers, subscribers), f)
    print(f"[SNAPSHOT] Saved: {OUTPUT_DIR}/network_snapshot_{label}.pkl")


def move_subscribers_randomly(subscribers, routers, seed=42):
    """Move subscribers to different routers randomly"""
    np.random.seed(seed)
    for subscriber in subscribers:
        new_router_idx = np.random.randint(0, len(routers))
        subscriber.attached_router = routers[new_router_idx]
    print(f"[TOPOLOGY] Moved {len(subscribers)} subscribers to random routers (seed={seed})")


def visualize_topologies(routers_before, routers_after, publishers, subscribers_before, subscribers_after):
    """Generate before/after topology plots"""
    try:
        plot_network_graph(routers_before, publishers, subscribers_before,
                          out_path=f"{OUTPUT_DIR}/plots/topology_before_change.png")
        print(f"[VIZ] Saved: {OUTPUT_DIR}/plots/topology_before_change.png")
    except Exception as e:
        print(f"[VIZ] Warning (before): {e}")
    
    try:
        plot_network_graph(routers_after, publishers, subscribers_after,
                          out_path=f"{OUTPUT_DIR}/plots/topology_after_change.png")
        print(f"[VIZ] Saved: {OUTPUT_DIR}/plots/topology_after_change.png")
    except Exception as e:
        print(f"[VIZ] Warning (after): {e}")


def save_agent_model(agent, scenario, episode, topology_name):
    """Save trained agent"""
    path = f"{OUTPUT_DIR}/models/agent_{scenario}_{topology_name}_ep{episode}.pt"
    torch.save({
        'model_state': agent.q_network.state_dict(),
        'target_state': agent.target_network.state_dict(),
        'epsilon': agent.epsilon,
    }, path)
    print(f"[AGENT] Saved: {path}")
    return path


def main():
    print("\n" + "=" * 80)
    print("SCENARIO 2: APPLYING TOPOLOGY CHANGE AND TRAINING FRESH AGENT")
    print("=" * 80 + "\n")
    
    # ======== STEP 1: Load original network snapshot ========
    print("[S2] Loading original network snapshot...")
    routers_original, publishers, subscribers_original = load_network_snapshot("original")
    print(f"[S2] Loaded: {len(routers_original)} routers, {len(subscribers_original)} subscribers")
    
    # ======== STEP 2: Deep copy for changed topology ========
    print("[S2] Creating changed topology (deep copy)...")
    routers_changed = copy.deepcopy(routers_original)
    subscribers_changed = copy.deepcopy(subscribers_original)
    print(f"[S2] Deep copied for modification")
    
    # ======== STEP 3: Apply topology change ========
    print("[S2] Applying topology change...")
    move_subscribers_randomly(subscribers_changed, routers_changed, seed=123)
    
    # ======== STEP 4: Save changed snapshot ========
    print("[S2] Saving changed network snapshot...")
    save_network_snapshot(routers_changed, publishers, subscribers_changed, "changed")
    
    # ======== STEP 5: Visualize before/after ========
    print("[S2] Visualizing topologies...")
    visualize_topologies(routers_original, routers_changed, publishers,
                        subscribers_original, subscribers_changed)
    
    # ======== STEP 6: Pre-simulate changed topology ========
    print("[S2] Pre-simulating on changed topology (50 iterations)...")
    try:
        run_simulation(routers_changed, publishers, subscribers_changed, policy="baseline", iterations=50)
        print("[S2] Pre-simulation completed")
    except Exception as e:
        print(f"[S2] Pre-sim warning: {e}")
    
    # ======== STEP 7: Print router metrics after topology change ========
    print("\n[S2] Router metrics AFTER topology change:")
    for i, r in enumerate(routers_changed):
        chr_val = (r.cache_hits / r.total_requests) if r.total_requests > 0 else 0.0
        lat_val = (r.total_cache_access_time / r.total_requests) * 1000 if r.total_requests > 0 else 0.0
        print(f"  Router{i} ({r.name}): CHR={chr_val:.4f}, Latency={lat_val:.2f}ms, "
              f"Cache_Hits={r.cache_hits}, Total_Req={r.total_requests}")
    
    # ======== STEP 8: Compute centrality on changed topology ========
    print("[S2] Computing centrality on changed topology...")
    try:
        plot_centrality_measures(routers_changed)
        print("[S2] Centrality computed")
    except Exception as e:
        print(f"[S2] Centrality warning: {e}")
    
    # ======== STEP 9: Create environment and fresh agent ========
    print("[S2] Creating RL environment for changed topology...")
    env_2 = CacheEnvironment(routers=routers_changed, episode_length=100)
    state_size = env_2.reset().shape[0]
    action_size = len(routers_changed)
    print(f"[S2] Environment: state_size={state_size}, action_size={action_size}")
    
    agent_2 = DQNAgent(state_size=state_size, action_size=action_size)
    print(f"[S2] Fresh Agent B created")
    
    # ======== STEP 10: Train fresh agent ========
    print("\n[S2] Training FRESH Agent B (10 episodes x 100 iterations)...")
    results_2 = train_agent(
        environment=env_2,
        agent=agent_2,
        episodes=10,
        iterations=100,
        out_dir=f"{OUTPUT_DIR}/logs"
    )
    
    # ======== STEP 11: Save agent ========
    print("\n[S2] Saving fresh agent...")
    agent_2_path = save_agent_model(agent_2, "scenario2", 10, "changed")
    
    # ======== STEP 12: Copy and rename logs ========
    print("[S2] Organizing logs...")
    try:
        # Make sure log files exist
        if os.path.exists(results_2['summary_csv']):
            dest = f"{OUTPUT_DIR}/logs/scenario2_summary.csv"
            shutil.copy(results_2['summary_csv'], dest)
            print(f"[S2] Copied summary: {dest}")
        if os.path.exists(results_2['selections_csv']):
            dest = f"{OUTPUT_DIR}/logs/scenario2_selections.csv"
            shutil.copy(results_2['selections_csv'], dest)
            print(f"[S2] Copied selections: {dest}")
    except Exception as e:
        print(f"[S2] Error organizing logs: {e}")
    
    print(f"[S2] Logs saved")
    
    # ======== SUMMARY ========
    print("\n" + "=" * 80)
    print("SCENARIO 2 COMPLETE!")
    print("=" * 80)
    print(f"Fresh agent saved: {agent_2_path}")
    print(f"Logs: {OUTPUT_DIR}/logs/scenario2_*.csv")
    print(f"Changed network snapshot: {OUTPUT_DIR}/network_snapshot_changed.pkl")
    
    return {
        'agent': agent_2,
        'routers': routers_changed,
        'publishers': publishers,
        'subscribers': subscribers_changed,
        'agent_path': agent_2_path,
    }


if __name__ == "__main__":
    main()
