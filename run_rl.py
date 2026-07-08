#!/usr/bin/env python3
"""
Run RL training for cache placement optimization.
"""

from main import load_network
from rl_env import CacheEnvironment
from dqn_agent import DQNAgent
from trainer import train_agent

def main():
    # Load network
    network = load_network()
    if not network:
        raise RuntimeError("No saved network found. Create one first.")

    routers, publishers, subscribers = network
    print(f"Loaded network with {len(routers)} routers, {len(publishers)} publishers, {len(subscribers)} subscribers")

    # Create environment
    env = CacheEnvironment(routers=routers, episode_length=100)

    # Create agent
    state_size = len(routers) * 6  # 6 metrics per router: occ, chr, lat, cmba, global_chr, global_lat
    action_size = len(routers)
    agent = DQNAgent(state_size=state_size, action_size=action_size)

    # Train
    print("Starting RL training...")
    results = train_agent(
        environment=env,
        agent=agent,
        episodes=5,  # Small for testing
        iterations=50
    )

    print("Training complete!")
    print(f"Results saved to: {results['summary_csv']}")

if __name__ == "__main__":
    main()