#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCENARIO 1: Train RL Agent on Original 10-Router Topology
This script:
1. Loads the network (or creates new one)
2. Reduces to 10 routers
3. Pre-simulates baseline (50 iterations)
4. Computes centrality measures
5. Trains DQN Agent A for 10 episodes x 100 iterations
6. Saves agent and logs
"""

import os
import sys
import pickle
import torch
import numpy as np
import pandas as pd
from datetime import datetime
import shutil

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
os.chdir(parent_dir)

from main import load_network, setup_network, run_simulation, plot_centrality_measures
from rl_env import CacheEnvironment
from dqn_agent import DQNAgent
from trainer import train_agent

# Output directory - already running from inside Topology_RL_Impact folder
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(f"{OUTPUT_DIR}/logs", exist_ok=True)
os.makedirs(f"{OUTPUT_DIR}/models", exist_ok=True)


def reduce_network_to_n_routers(routers, publishers, subscribers, n=10):
    """Keep only first n routers"""
    return routers[:n], publishers, subscribers


def save_network_snapshot(routers, publishers, subscribers, label):
    """Save network snapshot"""
    with open(f"{OUTPUT_DIR}/network_snapshot_{label}.pkl", "wb") as f:
        pickle.dump((routers, publishers, subscribers), f)
    print(f"[SNAPSHOT] Saved: {OUTPUT_DIR}/network_snapshot_{label}.pkl")


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
    print("SCENARIO 1: TRAINING RL ON ORIGINAL 10-ROUTER TOPOLOGY")
    print("=" * 80 + "\n")

    # ======== STEP 1: Load or create network ========
    print("[S1] Loading network...")
    network = load_network()
    if not network:
        print("[S1] Creating new network...")
        routers, publishers, subscribers = setup_network()
    else:
        routers, publishers, subscribers = network
    
    # ======== STEP 2: Reduce to 10 routers ========
    print("[S1] Reducing network to 10 routers...")
    routers, publishers, subscribers = reduce_network_to_n_routers(
        routers, publishers, subscribers, n=10
    )
    print(f"[S1] Network: {len(routers)} routers, {len(publishers)} publishers, "
          f"{len(subscribers)} subscribers")
    
    # ======== STEP 3: Save original snapshot ========
    print("[S1] Saving network snapshot...")
    save_network_snapshot(routers, publishers, subscribers, "original")
    
    # ======== STEP 4: Pre-simulate baseline ========
    print("[S1] Pre-simulating baseline (50 iterations)...")
    try:
        run_simulation(routers, publishers, subscribers, policy="baseline", iterations=50)
        print("[S1] Pre-simulation completed")
    except Exception as e:
        print(f"[S1] Pre-sim warning: {e}")
    
    # ======== STEP 5: Print router metrics before training ========
    print("\n[S1] Router metrics BEFORE training:")
    for i, r in enumerate(routers):
        chr_val = (r.cache_hits / r.total_requests) if r.total_requests > 0 else 0.0
        lat_val = (r.total_cache_access_time / r.total_requests) * 1000 if r.total_requests > 0 else 0.0
        print(f"  Router{i} ({r.name}): CHR={chr_val:.4f}, Latency={lat_val:.2f}ms, "
              f"Cache_Hits={r.cache_hits}, Total_Req={r.total_requests}")
    
    # ======== STEP 6: Compute centrality ========
    print("[S1] Computing centrality scores...")
    try:
        plot_centrality_measures(routers)
        print("[S1] Centrality computed")
    except Exception as e:
        print(f"[S1] Centrality warning: {e}")
    
    # ======== STEP 7: Create environment and agent ========
    print("[S1] Creating RL environment...")
    env = CacheEnvironment(routers=routers, episode_length=100)
    state_size = env.reset().shape[0]
    action_size = len(routers)
    print(f"[S1] Environment: state_size={state_size}, action_size={action_size}")
    
    agent_1 = DQNAgent(state_size=state_size, action_size=action_size)
    print(f"[S1] Agent created")
    
    # ======== STEP 8: Train agent ========
    print("\n[S1] Training RL Agent A (10 episodes x 100 iterations)...")
    results_1 = train_agent(
        environment=env,
        agent=agent_1,
        episodes=10,
        iterations=100,
        out_dir=f"{OUTPUT_DIR}/logs"
    )
    
    # ======== STEP 9: Save agent ========
    print("\n[S1] Saving trained agent...")
    agent_1_path = save_agent_model(agent_1, "scenario1", 10, "original")
    
    # ======== STEP 10: Copy and rename logs ========
    print("[S1] Organizing logs...")
    try:
        # Make sure log files exist
        if os.path.exists(results_1['summary_csv']):
            dest = f"{OUTPUT_DIR}/logs/scenario1_summary.csv"
            shutil.copy(results_1['summary_csv'], dest)
            print(f"[S1] Copied summary: {dest}")
        if os.path.exists(results_1['selections_csv']):
            dest = f"{OUTPUT_DIR}/logs/scenario1_selections.csv"
            shutil.copy(results_1['selections_csv'], dest)
            print(f"[S1] Copied selections: {dest}")
    except Exception as e:
        print(f"[S1] Error organizing logs: {e}")
    
    print(f"[S1] Logs saved")
    
    # ======== SUMMARY ========
    print("\n" + "=" * 80)
    print("SCENARIO 1 COMPLETE!")
    print("=" * 80)
    print(f"Agent saved: {agent_1_path}")
    print(f"Logs: {OUTPUT_DIR}/logs/scenario1_*.csv")
    print(f"Network snapshot: {OUTPUT_DIR}/network_snapshot_original.pkl")
    
    return {
        'agent': agent_1,
        'routers': routers,
        'publishers': publishers,
        'subscribers': subscribers,
        'agent_path': agent_1_path,
    }


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[ERROR] Fatal exception in scenario 1: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
