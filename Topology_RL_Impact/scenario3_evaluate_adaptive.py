#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCENARIO 3: Evaluate Pre-Trained Agent on Changed Topology (NO TRAINING)
This script:
1. Loads changed network snapshot from Scenario 2
2. Loads pre-trained Agent A from Scenario 1
3. Evaluates Agent A on changed topology for 100 iterations (epsilon=0, greedy)
4. NO weight updates - pure evaluation
5. Saves evaluation logs
6. Shows how well pre-trained agent adapts without retraining
"""

import os
import sys
import pickle
import torch
import numpy as np
import pandas as pd
from datetime import datetime

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
os.chdir(parent_dir)

from rl_env import CacheEnvironment
from dqn_agent import DQNAgent

# Output directory - already running from inside Topology_RL_Impact folder
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(f"{OUTPUT_DIR}/logs", exist_ok=True)
os.makedirs(f"{OUTPUT_DIR}/models", exist_ok=True)


def load_network_snapshot(label):
    """Load network snapshot"""
    with open(f"{OUTPUT_DIR}/network_snapshot_{label}.pkl", "rb") as f:
        return pickle.load(f)


def load_agent_model(agent, path):
    """Load pre-trained agent"""
    checkpoint = torch.load(path)
    agent.q_network.load_state_dict(checkpoint['model_state'])
    agent.target_network.load_state_dict(checkpoint['target_state'])
    agent.epsilon = checkpoint['epsilon']
    print(f"[AGENT] Loaded: {path}")
    return agent


def evaluate_agent_no_training(agent, environment, iterations=100):
    """
    Evaluate agent WITHOUT training (greedy policy, epsilon=0)
    Returns DataFrame with evaluation metrics
    """
    agent.epsilon = 0.0  # Fully exploitation (no exploration)
    
    state = environment.reset()
    rows = []
    
    print(f"[EVAL] Starting evaluation: {iterations} iterations, epsilon=0.0 (greedy)")
    
    for t in range(1, iterations + 1):
        state_tensor = torch.FloatTensor(state).unsqueeze(0)
        with torch.no_grad():
            q_values = agent.q_network(state_tensor)
            action = q_values.argmax(1).item()
        
        next_state, reward, done, info = environment.step(action)
        
        rows.append({
            "iteration": t,
            "action": action,
            "selected_router_name": info.get("selected_router_name", f"router_{action}"),
            "reward": float(reward),
            "chr": float(info.get("metrics", {}).get("chr", 0.0) or 0.0),
            "latency_ms": float(info.get("metrics", {}).get("latency_ms", 0.0) or 0.0),
            "cache_occupancy": float(info.get("metrics", {}).get("cache_occupancy", 0.0) or 0.0),
            "cmba": float(info.get("metrics", {}).get("cmba", 0.0) or 0.0),
        })
        
        state = next_state
        if done:
            print(f"[EVAL] Episode ended at iteration {t}")
            break
        
        if t % 20 == 0:
            print(f"[EVAL] Progress: {t}/{iterations}")
    
    print(f"[EVAL] Evaluation complete: {len(rows)} iterations collected")
    return pd.DataFrame(rows)


def main():
    print("\n" + "=" * 80)
    print("SCENARIO 3: EVALUATING PRE-TRAINED AGENT ON CHANGED TOPOLOGY (NO TRAINING)")
    print("=" * 80 + "\n")
    
    # ======== STEP 1: Load changed network snapshot ========
    print("[S3] Loading changed network snapshot...")
    routers_changed, publishers, subscribers_changed = load_network_snapshot("changed")
    print(f"[S3] Loaded: {len(routers_changed)} routers, {len(subscribers_changed)} subscribers")
    
    # ======== STEP 2: Create environment ========
    print("[S3] Creating RL environment for changed topology...")
    env_3 = CacheEnvironment(routers=routers_changed, episode_length=100)
    state_size = env_3.reset().shape[0]
    action_size = len(routers_changed)
    print(f"[S3] Environment: state_size={state_size}, action_size={action_size}")
    
    # ======== STEP 3: Create fresh agent shell ========
    print("[S3] Creating empty agent shell...")
    agent_3 = DQNAgent(state_size=state_size, action_size=action_size)
    print(f"[S3] Agent shell created")
    
    # ======== STEP 4: Load pre-trained weights from Scenario 1 ========
    print("[S3] Loading pre-trained weights from SCENARIO 1...")
    agent_1_path = f"{OUTPUT_DIR}/models/agent_scenario1_original_ep10.pt"
    if not os.path.exists(agent_1_path):
        print(f"[ERROR] Pre-trained agent not found: {agent_1_path}")
        print("[ERROR] Please run Scenario 1 first!")
        return None
    
    agent_3 = load_agent_model(agent_3, agent_1_path)
    print(f"[S3] Pre-trained Agent A loaded successfully")
    
    # ======== STEP 5: Evaluate on changed topology (NO training) ========
    print("\n[S3] Evaluating pre-trained Agent A on CHANGED topology...")
    print("[S3] NOTE: NO weight updates during evaluation (epsilon=0, greedy policy)")
    
    eval_df = evaluate_agent_no_training(agent_3, env_3, iterations=100)
    
    # ======== STEP 6: Save evaluation metrics ========
    print("[S3] Saving evaluation results...")
    eval_csv = f"{OUTPUT_DIR}/logs/scenario3_evaluation.csv"
    eval_df.to_csv(eval_csv, index=False)
    print(f"[S3] Evaluation saved: {eval_csv}")
    
    # ======== STEP 7: Print summary statistics ========
    print("\n[S3] Evaluation Summary:")
    print(f"  Mean Reward:        {eval_df['reward'].mean():.6f}")
    print(f"  Mean CHR:           {eval_df['chr'].mean():.6f}")
    print(f"  Mean Latency:       {eval_df['latency_ms'].mean():.2f} ms")
    print(f"  Mean Cache Occupancy: {eval_df['cache_occupancy'].mean():.6f}")
    print(f"  Mean CMBA:          {eval_df['cmba'].mean():.6f}")
    
    # ======== STEP 8: Router selection analysis ========
    print("\n[S3] Router Selection Frequency:")
    router_counts = eval_df['selected_router_name'].value_counts().sort_index()
    for router, count in router_counts.items():
        print(f"  {router}: {count} times ({count/len(eval_df)*100:.1f}%)")
    
    # ======== SUMMARY ========
    print("\n" + "=" * 80)
    print("SCENARIO 3 COMPLETE!")
    print("=" * 80)
    print(f"Pre-trained agent evaluated: {agent_1_path}")
    print(f"Evaluation results: {eval_csv}")
    print(f"Total iterations evaluated: {len(eval_df)}")
    print("[S3] This shows how well pre-trained Agent A adapts to the new topology")
    print("[S3] WITHOUT any retraining (transfer learning capability)")
    
    return {
        'agent': agent_3,
        'routers': routers_changed,
        'publishers': publishers,
        'subscribers': subscribers_changed,
        'evaluation_df': eval_df,
    }


if __name__ == "__main__":
    main()
