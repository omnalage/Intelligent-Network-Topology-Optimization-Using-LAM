#!/usr/bin/env python3
"""
Integrated RL training with simulator.

Flow:
1. Load/setup network
2. Pre-simulate to populate router metrics
3. Compute centrality scores (CMBA)
4. Create RL environment with populated routers
5. Train DQN agent on simulator data
6. Evaluate baseline vs RL policies
7. Generate comparison plots
"""

import os
from main import load_network, setup_network, run_simulation, plot_centrality_measures
from rl_env import CacheEnvironment
from dqn_agent import DQNAgent
from trainer import train_agent
from compare_baseline_rl import compare_baseline_vs_rl

def main():
    print("=" * 60)
    print("INTEGRATED RL TRAINING WITH SIMULATOR")
    print("=" * 60)

    # Step 1: Load or setup network
    print("\n[Step 1] Loading/setting up network...")
    network = load_network()
    if not network:
        print("[Step 1] No network found. Creating new network...")
        routers, publishers, subscribers = setup_network()
    else:
        routers, publishers, subscribers = network
        print(f"[Step 1] Network loaded: {len(routers)} routers, {len(publishers)} publishers, {len(subscribers)} subscribers")

    # Step 2: Pre-simulate to populate router metrics
    print("\n[Step 2] Pre-simulating to populate router metrics...")
    print("[Step 2] Running baseline policy simulation (50 iterations)...")
    try:
        baseline_results = run_simulation(
            routers=routers,
            publishers=publishers,
            subscribers=subscribers,
            policy="baseline",
            iterations=50
        )
        print(f"[Step 2] Pre-simulation complete. Generated {len(baseline_results)} metrics")
    except Exception as e:
        print(f"[Step 2] Pre-simulation warning: {e}")
        print("[Step 2] Continuing without pre-sim (RL will work with minimal metrics)")

    # Step 3: Compute centrality scores
    print("\n[Step 3] Computing centrality scores (CMBA)...")
    try:
        plot_centrality_measures(routers)
        print("[Step 3] Centrality scores computed and stored in routers")
    except Exception as e:
        print(f"[Step 3] Centrality computation warning: {e}")

    # Step 4: Create RL environment
    print("\n[Step 4] Creating RL environment...")
    env = CacheEnvironment(routers=routers, episode_length=100)
    state = env.reset()
    print(f"[Step 4] Environment created. State shape: {state.shape}")

    # Step 5: Create DQN agent
    print("\n[Step 5] Creating DQN agent...")
    state_size = state.shape[0]
    action_size = len(routers)
    agent = DQNAgent(state_size=state_size, action_size=action_size)
    print(f"[Step 5] DQN agent created. State size: {state_size}, Action size: {action_size}")

    # Step 6: Train RL agent
    print("\n[Step 6] Training RL agent...")
    print("[Step 6] Training for 10 episodes × 100 iterations...")
    results = train_agent(
        environment=env,
        agent=agent,
        episodes=10,
        iterations=100,
        out_dir="Path_Iterations"
    )
    print(f"[Step 6] Training complete!")
    print(f"[Step 6] Results saved to: {results['summary_csv']}")

    # Step 6b: Re-simulate to refresh metrics for fair comparison
    print("\n[Step 6b] Refreshing metrics for evaluation (50 iterations)...")
    try:
        refresh_results = run_simulation(
            routers=routers,
            publishers=publishers,
            subscribers=subscribers,
            policy="baseline",
            iterations=50
        )
        print(f"[Step 6b] Metrics refreshed. Routers now have fresh metrics for comparison.")
    except Exception as e:
        print(f"[Step 6b] Metrics refresh warning: {e}")

    # Step 7: Compare baseline vs trained RL
    print("\n[Step 7] Evaluating trained RL vs baseline policy...")
    comparison = compare_baseline_vs_rl(
        episodes=3,
        iterations=100,
        out_dir="Path_Iterations",
        trained_agent=agent
    )
    print(f"[Step 7] Comparison saved to: {comparison['summary_csv']}")

    # Step 8: Generate analysis plots
    print("\n[Step 8] Generating analysis plots...")
    try:
        import generate_plots
        generate_plots.plot_reward_vs_iteration()
        generate_plots.plot_router_selection_frequency()
        generate_plots.plot_latency_comparison()
        generate_plots.plot_chr_comparison()
        print("[Step 8] All plots generated in Path_Iterations/plots/")
    except Exception as e:
        print(f"[Step 8] Plot generation warning: {e}")

    print("\n" + "=" * 60)
    print("TRAINING COMPLETE!")
    print("=" * 60)
    print("\nGenerated files:")
    print("  - RL training logs: Path_Iterations/rl_*")
    print("  - Comparison logs: Path_Iterations/baseline_vs_rl_*")
    print("  - Plots: Path_Iterations/plots/")
    print("\nKey metrics to check:")
    print("  1. Router selection counts (preference analysis)")
    print("  2. Reward vs iteration (learning curve)")
    print("  3. Latency/CHR comparison (policy performance)")
    print("\nReady for viva explanation!")

if __name__ == "__main__":
    main()
