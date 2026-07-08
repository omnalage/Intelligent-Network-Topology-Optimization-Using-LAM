"""
INTEGRATION CODE PATTERNS
Practical examples for connecting simulator and RL system
"""

# ============================================================
# PATTERN 1: BASIC INTEGRATION (Recommended Starting Point)
# ============================================================

def integration_basic():
    """
    Simple integration: Load network → Setup RL env → Train
    No simulation during training, but metrics are pre-populated.
    """
    from main import load_network, plot_centrality_measures
    from rl_env import CacheEnvironment
    from dqn_agent import DQNAgent
    from trainer import train_agent
    
    # Step 1: Load network
    print("[Integration] Loading network...")
    routers, publishers, subscribers = load_network()
    num_routers = len(routers)
    print(f"  Network loaded: {num_routers} routers")
    
    # Step 2: Compute centrality (enriches routers with CMBA)
    print("[Integration] Computing centrality measures...")
    plot_centrality_measures(routers, show_plot=False)
    print(f"  Centrality saved to: Graphs/Centrality/results.csv")
    
    # Step 3: Create RL environment
    print("[Integration] Creating RL environment...")
    env = CacheEnvironment(
        routers=routers,
        episode_length=100,
        w1=0.25,  # CHR weight
        w2=0.25,  # CMBA weight
        w3=0.25,  # Latency weight
        w4=0.25   # Occupancy weight
    )
    
    # Step 4: Create agent
    print("[Integration] Creating DQN agent...")
    state_size = num_routers * 6
    action_size = num_routers
    agent = DQNAgent(
        state_size=state_size,
        action_size=action_size,
        lr=1e-3,
        gamma=0.99,
        epsilon_start=1.0,
        epsilon_end=0.05,
        epsilon_decay=0.995,
        batch_size=64,
        target_update_freq=100
    )
    print(f"  Agent created: state_size={state_size}, action_size={action_size}")
    
    # Step 5: Train
    print("[Integration] Starting RL training...")
    results = train_agent(
        environment=env,
        agent=agent,
        episodes=10,
        iterations=100,
        out_dir="Path_Iterations"
    )
    
    print(f"[Integration] Training complete!")
    print(f"  Results CSV: {results['summary_csv']}")
    return results


# ============================================================
# PATTERN 2: WITH PRE-SIMULATION (Better Metrics)
# ============================================================

def integration_with_presimulation(policy='LRU', pre_sim_iterations=500):
    """
    Integration with pre-simulation:
    1. Run simulation to populate router metrics
    2. Then train RL agent on those metrics
    
    This ensures routers have realistic cache_hits, total_requests, etc.
    """
    from main import load_network, run_simulation, plot_centrality_measures
    from rl_env import CacheEnvironment
    from dqn_agent import DQNAgent
    from trainer import train_agent
    import time
    
    print("[IntegrationWithPreSim] Starting workflow...")
    
    # Step 1: Load network
    print("\n[1/5] Loading network...")
    routers, publishers, subscribers = load_network()
    num_routers = len(routers)
    print(f"  ✓ Network loaded: {num_routers} routers, {len(publishers)} publishers, {len(subscribers)} subscribers")
    
    # Step 2: Pre-simulate to populate metrics
    print(f"\n[2/5] Pre-simulating {pre_sim_iterations} iterations with {policy} policy...")
    start_time = time.time()
    simulation_data = run_simulation(
        routers=routers,
        publishers=publishers,
        subscribers=subscribers,
        policy=policy,
        iterations=pre_sim_iterations
    )
    elapsed = time.time() - start_time
    print(f"  ✓ Simulation complete ({elapsed:.2f}s)")
    print(f"    Metrics collected:")
    
    # Inspect router metrics
    for i, router in enumerate(routers[:3]):  # Show first 3
        print(f"    Router{i}: cache_hits={router.cache_hits}, "
              f"total_requests={router.total_requests}, "
              f"cache_occ={len(router.cs)}/{router.CACHE_LIMIT}")
    
    # Step 3: Compute centrality
    print("\n[3/5] Computing centrality measures...")
    plot_centrality_measures(routers, show_plot=False)
    print(f"  ✓ Centrality saved to: Graphs/Centrality/results.csv")
    
    # Step 4: Create RL environment
    print("\n[4/5] Creating RL environment...")
    env = CacheEnvironment(routers=routers, episode_length=100)
    print(f"  ✓ Environment created with {num_routers} routers")
    
    # Step 5: Train RL agent
    print("\n[5/5] Training DQN agent...")
    state_size = num_routers * 6
    action_size = num_routers
    
    agent = DQNAgent(
        state_size=state_size,
        action_size=action_size,
        gamma=0.99,
        epsilon_start=1.0,
        epsilon_end=0.05
    )
    
    results = train_agent(
        environment=env,
        agent=agent,
        episodes=5,
        iterations=100,
        out_dir="Path_Iterations"
    )
    
    print(f"\n[IntegrationWithPreSim] ✓ Complete!")
    print(f"  Results: {results['summary_csv']}")
    return {
        'simulation_data': simulation_data,
        'agent': agent,
        'env': env,
        'training_results': results
    }


# ============================================================
# PATTERN 3: PERIODIC METRIC REFRESH (Advanced)
# ============================================================

def integration_with_periodic_refresh(
    pre_sim_iterations=500,
    episodes=10,
    iterations_per_episode=100,
    refresh_interval=2  # Refresh metrics every N episodes
):
    """
    Integration with periodic simulation refresh:
    1. Pre-simulate
    2. During RL training, every N episodes, run mini simulation
    3. This refreshes router metrics between training phases
    
    Useful for:
    - Adapting to changing network conditions
    - Avoiding overfitting to static metrics
    - Exploring different policy states
    """
    from main import load_network, run_simulation, plot_centrality_measures
    from rl_env import CacheEnvironment
    from dqn_agent import DQNAgent
    import pandas as pd
    import os
    
    print("[IntegrationWithRefresh] Starting workflow...")
    
    # Initial setup
    routers, publishers, subscribers = load_network()
    num_routers = len(routers)
    
    print(f"\n[Setup] Network: {num_routers} routers")
    print(f"[Setup] Pre-simulating {pre_sim_iterations} iterations...")
    run_simulation(routers, publishers, subscribers, policy='LRU', iterations=pre_sim_iterations)
    plot_centrality_measures(routers, show_plot=False)
    
    # Create environment and agent
    env = CacheEnvironment(routers=routers, episode_length=iterations_per_episode)
    agent = DQNAgent(
        state_size=num_routers * 6,
        action_size=num_routers,
        gamma=0.99,
        epsilon_start=1.0,
        epsilon_end=0.05
    )
    
    # Training loop with periodic refresh
    os.makedirs("Path_Iterations/refresh_logs", exist_ok=True)
    episode_rewards = []
    episode_policies_used = []
    
    for episode in range(1, episodes + 1):
        # Periodic metric refresh
        if episode > 1 and (episode - 1) % refresh_interval == 0:
            policy = 'FACR' if episode % 2 == 0 else 'LRU'
            print(f"\n[Episode {episode}] Refreshing metrics with {policy} policy...")
            
            # Run mini-simulation (fewer iterations than pre-sim)
            run_simulation(
                routers=routers,
                publishers=publishers,
                subscribers=subscribers,
                policy=policy,
                iterations=100  # Smaller refresh
            )
            
            # Log refresh
            episode_policies_used.append(({
                'episode': episode,
                'policy': policy,
                'action': 'refresh'
            }))
            
            print(f"  Metrics refreshed. Sample router metrics:")
            r = routers[0]
            print(f"    {r.name}: CHR={r.cache_hits/max(1,r.total_requests):.3f}, "
                  f"Cache={len(r.cs)}/{r.CACHE_LIMIT}")
        
        # Train one episode
        state = env.reset()
        episode_reward_sum = 0.0
        
        for iteration in range(1, iterations_per_episode + 1):
            action = int(agent.select_action(state, training=True))
            next_state, reward, done, info = env.step(action)
            
            agent.store_transition(state, action, reward, next_state, done)
            loss = float(agent.train_step())
            
            episode_reward_sum += reward
            state = next_state
            
            if done:
                break
        
        avg_reward = episode_reward_sum / iteration
        episode_rewards.append({
            'episode': episode,
            'total_reward': episode_reward_sum,
            'avg_reward': avg_reward,
            'epsilon': agent.epsilon
        })
        
        print(f"[Episode {episode:3d}] "
              f"Total={episode_reward_sum:7.4f}, "
              f"Avg={avg_reward:7.4f}, "
              f"ε={agent.epsilon:.4f}")
    
    # Save logs
    rewards_df = pd.DataFrame(episode_rewards)
    rewards_df.to_csv("Path_Iterations/refresh_logs/episode_rewards.csv", index=False)
    
    print(f"\n[IntegrationWithRefresh] ✓ Complete!")
    print(f"  Rewards log: Path_Iterations/refresh_logs/episode_rewards.csv")
    
    return {
        'agent': agent,
        'env': env,
        'episode_rewards': rewards_df,
        'routers': routers
    }


# ============================================================
# PATTERN 4: EVALUATION AGAINST BASELINES
# ============================================================

def evaluate_trained_agent(agent, env, routers, publishers, subscribers, baseline_policy='LRU'):
    """
    Evaluate trained agent against baseline policies.
    
    Returns comparison metrics:
    - RL agent average reward
    - Baseline policy average reward
    - Improvement percentage
    """
    from main import run_simulation
    import numpy as np
    
    print("[Evaluation] Comparing trained agent vs baselines...")
    
    # Test trained agent (deterministic policy)
    print("\n[Eval] Testing trained RL agent (no exploration)...")
    state = env.reset()
    rl_rewards = []
    rl_selected_routers = []
    
    for step in range(100):
        # Agent acts deterministically (training=False)
        action = int(agent.select_action(state, training=False))
        next_state, reward, done, info = env.step(action)
        
        rl_rewards.append(float(reward))
        rl_selected_routers.append(info['selected_router_name'])
        
        state = next_state
        if done:
            break
    
    rl_avg_reward = np.mean(rl_rewards)
    print(f"  RL Agent: avg_reward={rl_avg_reward:.4f}, std={np.std(rl_rewards):.4f}")
    
    # Test baseline policies
    baseline_results = {}
    for policy in [baseline_policy, 'LFU', 'FIFO']:
        print(f"\n[Eval] Testing {policy} baseline...")
        
        # Reload network and run simulation
        from main import load_network
        routers_baseline, _, _ = load_network()
        
        # Run simulation with this policy
        sim_data = run_simulation(
            routers=routers_baseline,
            publishers=publishers,
            subscribers=subscribers,
            policy=policy,
            iterations=500
        )
        
        # Convert simulation data to rewards
        # (Simple metric: cache hit ratio from final iteration)
        final_chr = sim_data[-1][4]  # Cache hit ratio is index 4
        baseline_results[policy] = final_chr
        print(f"  {policy}: final_CHR={final_chr:.4f}")
    
    # Compute comparison
    comparison = {
        'RL_avg_reward': rl_avg_reward,
        'Baselines': baseline_results,
        'RL_vs_LRU_improvement': (rl_avg_reward - baseline_results['LRU']) / abs(baseline_results['LRU']) if baseline_results['LRU'] != 0 else 0
    }
    
    print(f"\n[Evaluation Summary]")
    print(f"  RL Agent: {rl_avg_reward:.4f}")
    print(f"  LRU Baseline: {baseline_results['LRU']:.4f}")
    print(f"  Improvement: {comparison['RL_vs_LRU_improvement']*100:.2f}%")
    
    return comparison


# ============================================================
# PATTERN 5: CUSTOM REWARD FUNCTION
# ============================================================

def custom_reward_based_on_simulation_metrics(selected_router, all_routers, weights=None):
    """
    Compute reward based on simulator metrics rather than normalized features.
    
    This allows for domain-specific reward shaping.
    """
    if weights is None:
        weights = {
            'chr': 0.3,
            'occupancy': -0.25,
            'latency': -0.3,
            'cmba': 0.15
        }
    
    # Extract raw simulator metrics
    cache_hits = float(getattr(selected_router, 'cache_hits', 0))
    total_requests = float(getattr(selected_router, 'total_requests', 1))
    chr_value = cache_hits / total_requests if total_requests > 0 else 0.0
    
    cache_occupancy = len(selected_router.cs)
    cache_limit = selected_router.__class__.CACHE_LIMIT
    occupancy_norm = cache_occupancy / cache_limit if cache_limit > 0 else 0.0
    
    total_cache_access_time = float(getattr(selected_router, 'total_cache_access_time', 0))
    latency_ms = (total_cache_access_time / total_requests * 1000) if total_requests > 0 else 0.0
    latency_norm = min(1.0, latency_ms / 200.0)  # Normalize to typical range (0-200ms)
    
    cmba = float(getattr(selected_router, 'CMBA', 0.5))
    
    # Compute weighted reward
    reward = (
        weights['chr'] * min(1.0, chr_value) +
        weights['occupancy'] * occupancy_norm +
        weights['latency'] * latency_norm +
        weights['cmba'] * min(1.0, cmba)
    )
    
    return reward, {
        'chr': chr_value,
        'occupancy': occupancy_norm,
        'latency': latency_ms,
        'cmba': cmba
    }


# ============================================================
# PATTERN 6: MULTI-EPISODE TRACKING
# ============================================================

def integration_with_tracking(episodes=5, iterations=100):
    """
    Integration with detailed tracking of:
    - Per-episode rewards
    - Per-episode router selections
    - Router selection statistics
    - Reward components breakdown
    """
    from main import load_network, plot_centrality_measures
    from rl_env import CacheEnvironment
    from dqn_agent import DQNAgent
    import pandas as pd
    import os
    from collections import Counter
    
    print("[IntegrationWithTracking] Starting...")
    
    # Setup
    routers, _, _ = load_network()
    plot_centrality_measures(routers, show_plot=False)
    
    env = CacheEnvironment(routers=routers, episode_length=iterations)
    agent = DQNAgent(
        state_size=len(routers)*6,
        action_size=len(routers),
        gamma=0.99,
        epsilon_start=1.0,
        epsilon_end=0.05
    )
    
    # Tracking structures
    os.makedirs("Path_Iterations/tracking", exist_ok=True)
    
    episode_log = []
    iteration_log = []
    router_selections = Counter()
    
    # Training loop with tracking
    for ep in range(1, episodes + 1):
        state = env.reset()
        ep_reward_sum = 0.0
        ep_selected_routers = []
        
        for it in range(1, iterations + 1):
            action = int(agent.select_action(state, training=True))
            next_state, reward, done, info = env.step(action)
            
            agent.store_transition(state, action, reward, next_state, done)
            agent.train_step()
            
            ep_reward_sum += reward
            router_name = info['selected_router_name']
            ep_selected_routers.append(router_name)
            router_selections[router_name] += 1
            
            # Log per-iteration
            iteration_log.append({
                'episode': ep,
                'iteration': it,
                'reward': float(reward),
                'selected_router': router_name,
                'epsilon': agent.epsilon,
                'chr': info['metrics']['chr'],
                'latency_ms': info['metrics']['latency_ms'],
                'cache_occupancy': info['metrics']['cache_occupancy'],
                'cmba': info['metrics']['cmba']
            })
            
            state = next_state
            if done:
                break
        
        # Log per-episode
        ep_reward_avg = ep_reward_sum / it
        episode_log.append({
            'episode': ep,
            'total_reward': ep_reward_sum,
            'avg_reward': ep_reward_avg,
            'num_iterations': it,
            'epsilon': agent.epsilon,
            'unique_routers_selected': len(set(ep_selected_routers))
        })
        
        print(f"[Ep {ep:2d}] Total={ep_reward_sum:7.4f}, "
              f"Avg={ep_reward_avg:7.4f}, "
              f"Unique={len(set(ep_selected_routers))}, "
              f"ε={agent.epsilon:.4f}")
    
    # Save tracking logs
    episode_df = pd.DataFrame(episode_log)
    iteration_df = pd.DataFrame(iteration_log)
    
    episode_df.to_csv("Path_Iterations/tracking/episodes.csv", index=False)
    iteration_df.to_csv("Path_Iterations/tracking/iterations.csv", index=False)
    
    # Router selection statistics
    selection_stats = pd.DataFrame([
        {'router': r, 'selections': c}
        for r, c in router_selections.most_common()
    ])
    selection_stats.to_csv("Path_Iterations/tracking/router_selections.csv", index=False)
    
    print(f"\n[IntegrationWithTracking] ✓ Complete!")
    print(f"  Episodes: Path_Iterations/tracking/episodes.csv")
    print(f"  Iterations: Path_Iterations/tracking/iterations.csv")
    print(f"  Router stats: Path_Iterations/tracking/router_selections.csv")
    
    print(f"\nRouter Selection Distribution:")
    for _, row in selection_stats.iterrows():
        pct = (row['selections'] / iteration_df.shape[0] * 100)
        print(f"  {row['router']}: {row['selections']:3d} times ({pct:5.1f}%)")
    
    return {
        'episodes_df': episode_df,
        'iterations_df': iteration_df,
        'selections_df': selection_stats,
        'agent': agent,
        'env': env
    }


# ============================================================
# MAIN EXECUTION
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("RL System & Simulator Integration Patterns")
    print("=" * 70)
    
    import sys
    
    if len(sys.argv) > 1:
        pattern = sys.argv[1]
    else:
        pattern = "1"
    
    if pattern == "1":
        print("\n[Running PATTERN 1: Basic Integration]")
        integration_basic()
    
    elif pattern == "2":
        print("\n[Running PATTERN 2: With Pre-Simulation]")
        integration_with_presimulation(policy='LRU', pre_sim_iterations=500)
    
    elif pattern == "3":
        print("\n[Running PATTERN 3: With Periodic Refresh]")
        integration_with_periodic_refresh(
            pre_sim_iterations=500,
            episodes=10,
            iterations_per_episode=100,
            refresh_interval=2
        )
    
    elif pattern == "6":
        print("\n[Running PATTERN 6: With Detailed Tracking]")
        integration_with_tracking(episodes=5, iterations=100)
    
    else:
        print(f"\nUnknown pattern: {pattern}")
        print("Available patterns: 1, 2, 3, 6")
        print("\nUsage: python integration_patterns.py [pattern_number]")
