"""
Step 4: Training loop for RL agent.

Creates:
    train_agent(environment, agent, episodes, iterations)

Behavior:
- Reset environment each episode
- For each iteration:
    - choose action
    - apply action
    - get reward
    - store experience
    - train model
- Log:
    - rewards per iteration
    - selected router per iteration
- Save logs to CSV
"""

from __future__ import annotations

import os
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
import pandas as pd


def train_agent(
    environment: Any,
    agent: Any,
    episodes: int,
    iterations: int,
    out_dir: str = "Path_Iterations",
) -> Dict[str, Any]:
    """
    Train an RL agent using a simple episodic loop.

    Args:
        environment: object with reset() and step(action)
        agent: object with methods:
               - select_action(state, training=True)
               - store_transition(state, action, reward, next_state, done)
               - train_step() -> loss
        episodes: number of episodes
        iterations: max iterations (steps) per episode
        out_dir: directory where CSV logs are saved

    Returns:
        dict with:
            - rewards_df
            - selections_df
            - episode_summary_df
            - rewards_csv
            - selections_csv
            - summary_csv
    """
    if episodes <= 0:
        raise ValueError("episodes must be > 0")
    if iterations <= 0:
        raise ValueError("iterations must be > 0")

    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    reward_rows: List[Dict[str, Any]] = []
    selection_rows: List[Dict[str, Any]] = []
    summary_rows: List[Dict[str, Any]] = []

    for ep in range(1, episodes + 1):
        state = environment.reset()
        ep_reward_sum = 0.0
        ep_losses: List[float] = []

        for it in range(1, iterations + 1):
            # 1) choose action
            action = int(agent.select_action(state, training=True))

            # 2) apply action / 3) get reward
            next_state, reward, done, info = environment.step(action)
            reward = float(reward)
            ep_reward_sum += reward

            # 4) store experience
            agent.store_transition(state, action, reward, next_state, done)

            # 5) train model
            loss = float(agent.train_step())
            ep_losses.append(loss)

            # Log reward per iteration
            reward_rows.append(
                {
                    "episode": ep,
                    "iteration": it,
                    "reward": reward,
                    "loss": loss,
                    "done": bool(done),
                }
            )

            # Log selected router per iteration
            selection_rows.append(
                {
                    "episode": ep,
                    "iteration": it,
                    "selected_router_index": info.get("selected_router_index", action),
                    "selected_router_name": info.get("selected_router_name", f"router_{action}"),
                    "chr": info.get("metrics", {}).get("chr", None),
                    "latency_ms": info.get("metrics", {}).get("latency_ms", None),
                    "cache_occupancy": info.get("metrics", {}).get("cache_occupancy", None),
                    "cmba": info.get("metrics", {}).get("cmba", None),
                }
            )

            state = next_state
            if done:
                break

        # Episode summary
        steps_in_ep = min(iterations, it)
        summary_rows.append(
            {
                "episode": ep,
                "steps": steps_in_ep,
                "episode_reward_sum": ep_reward_sum,
                "episode_reward_avg": ep_reward_sum / steps_in_ep if steps_in_ep > 0 else 0.0,
                "episode_loss_avg": sum(ep_losses) / len(ep_losses) if ep_losses else 0.0,
                "epsilon": getattr(agent, "epsilon", None),
            }
        )

        print(
            f"[trainer] episode={ep:03d} "
            f"steps={steps_in_ep:03d} "
            f"reward_sum={ep_reward_sum:.4f} "
            f"reward_avg={(ep_reward_sum / steps_in_ep):.4f}"
        )

    # Build DataFrames
    rewards_df = pd.DataFrame(reward_rows)
    selections_df = pd.DataFrame(selection_rows)
    summary_df = pd.DataFrame(summary_rows)

    # Compute router selection counts
    router_counts = Counter(selections_df['selected_router_name'])
    selection_counts_df = pd.DataFrame(list(router_counts.items()), columns=['router', 'selections'])

    # Save selection counts CSV
    selection_counts_csv = os.path.join(out_dir, f"rl_router_selection_counts_{ts}.csv")
    selection_counts_df.to_csv(selection_counts_csv, index=False)
    print(f"[trainer] Saved router selection counts: {selection_counts_csv}")

    # Plot router selection bar graph
    plt.figure(figsize=(10, 6))
    routers = list(router_counts.keys())
    counts = list(router_counts.values())
    plt.bar(routers, counts)
    plt.xlabel('Router')
    plt.ylabel('Selection Count')
    plt.title('Router Selection Frequency')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plot_path = os.path.join(out_dir, "plots", f"router_selection_counts_{ts}.png")
    os.makedirs(os.path.dirname(plot_path), exist_ok=True)
    plt.savefig(plot_path)
    plt.close()
    print(f"[trainer] Saved router selection plot: {plot_path}")

    # Save CSV logs
    rewards_csv = os.path.join(out_dir, f"rl_rewards_log_{ts}.csv")
    selections_csv = os.path.join(out_dir, f"rl_selected_router_log_{ts}.csv")
    summary_csv = os.path.join(out_dir, f"rl_episode_summary_{ts}.csv")

    rewards_df.to_csv(rewards_csv, index=False)
    selections_df.to_csv(selections_csv, index=False)
    summary_df.to_csv(summary_csv, index=False)

    print(f"[trainer] Saved rewards log: {rewards_csv}")
    print(f"[trainer] Saved selection log: {selections_csv}")
    print(f"[trainer] Saved episode summary: {summary_csv}")

    return {
        "rewards_df": rewards_df,
        "selections_df": selections_df,
        "episode_summary_df": summary_df,
        "selection_counts_df": selection_counts_df,
        "rewards_csv": rewards_csv,
        "selections_csv": selections_csv,
        "summary_csv": summary_csv,
        "selection_counts_csv": selection_counts_csv,
    }


if __name__ == "__main__":
    # Minimal usage hint only (no hard execution to avoid dependency assumptions)
    print("trainer.py loaded. Use train_agent(environment, agent, episodes, iterations).")
