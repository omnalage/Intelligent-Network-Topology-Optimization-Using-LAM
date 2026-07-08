"""
STEP 5: Comparison with baseline

Compares:
- Baseline scoring policy (select_best_router_by_score)
- RL policy (DQN agent greedy inference)

Metrics compared:
- average reward
- average latency
- average CHR

Outputs:
- CSV logs (per-iteration and summary)
- PNG plots
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt
import pandas as pd

from ai_agent import select_best_router_by_score
from rl_env import CacheEnvironment
from main import load_network


def evaluate_baseline_policy(environment: CacheEnvironment, iterations: int) -> pd.DataFrame:
    """Run baseline policy for fixed iterations and return per-step DataFrame."""
    state = environment.reset()
    rows: List[Dict[str, Any]] = []

    for t in range(1, iterations + 1):
        action = select_best_router_by_score(state)
        next_state, reward, done, info = environment.step(action)
        rows.append(
            {
                "iteration": t,
                "policy": "Baseline",
                "selected_router_index": info.get("selected_router_index", action),
                "selected_router_name": info.get("selected_router_name", f"router_{action}"),
                "reward": float(reward),
                "latency_ms": float(info.get("metrics", {}).get("latency_ms", 0.0) or 0.0),
                "chr": float(info.get("metrics", {}).get("chr", 0.0) or 0.0),
            }
        )
        state = next_state
        if done:
            break
    return pd.DataFrame(rows)


def evaluate_rl_policy(environment: CacheEnvironment, agent: Any, iterations: int) -> pd.DataFrame:
    """
    Run RL policy in inference mode (greedy action; no epsilon exploration)
    and return per-step DataFrame.
    """
    state = environment.reset()
    rows: List[Dict[str, Any]] = []

    for t in range(1, iterations + 1):
        action = int(agent.select_action(state, training=False))
        next_state, reward, done, info = environment.step(action)
        rows.append(
            {
                "iteration": t,
                "policy": "RL",
                "selected_router_index": info.get("selected_router_index", action),
                "selected_router_name": info.get("selected_router_name", f"router_{action}"),
                "reward": float(reward),
                "latency_ms": float(info.get("metrics", {}).get("latency_ms", 0.0) or 0.0),
                "chr": float(info.get("metrics", {}).get("chr", 0.0) or 0.0),
            }
        )
        state = next_state
        if done:
            break
    return pd.DataFrame(rows)


def _summary(df: pd.DataFrame) -> pd.DataFrame:
    """Compute policy-level summary metrics."""
    if df.empty:
        return pd.DataFrame(columns=["policy", "avg_reward", "avg_latency_ms", "avg_chr"])
    out = (
        df.groupby("policy", as_index=False)
        .agg(
            avg_reward=("reward", "mean"),
            avg_latency_ms=("latency_ms", "mean"),
            avg_chr=("chr", "mean"),
        )
        .sort_values("policy")
        .reset_index(drop=True)
    )
    return out


def _plot_metric_lines(df_baseline: pd.DataFrame, df_rl: pd.DataFrame, out_dir: str) -> None:
    """Plot reward, latency, CHR over iterations (baseline vs RL)."""
    os.makedirs(out_dir, exist_ok=True)

    # Align iteration axis
    merged = {
        "reward": ("Reward", "reward"),
        "latency": ("Latency (ms)", "latency_ms"),
        "chr": ("CHR", "chr"),
    }

    fig, axes = plt.subplots(3, 1, figsize=(12, 10))
    for ax, (key, (title, col)) in zip(axes, merged.items()):
        ax.plot(df_baseline["iteration"], df_baseline[col], marker="o", linestyle="-", label="Baseline")
        ax.plot(df_rl["iteration"], df_rl[col], marker="s", linestyle="--", label="RL")
        ax.set_title(f"{title} over Iterations")
        ax.set_xlabel("Iteration")
        ax.set_ylabel(title)
        ax.grid(True, linestyle="--", alpha=0.35)
        ax.legend(loc="best")

    plt.tight_layout()
    out_path = os.path.join(out_dir, "baseline_vs_rl_timeseries.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[compare_baseline_rl] Saved: {out_path}")


def _plot_summary_bars(summary_df: pd.DataFrame, out_dir: str) -> None:
    """Plot bar comparison for average reward, latency, CHR."""
    os.makedirs(out_dir, exist_ok=True)
    if summary_df.empty:
        return

    metrics = [
        ("avg_reward", "Average Reward"),
        ("avg_latency_ms", "Average Latency (ms)"),
        ("avg_chr", "Average CHR"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    for ax, (col, title) in zip(axes, metrics):
        vals = summary_df[col].tolist()
        labels = summary_df["policy"].tolist()
        bars = ax.bar(labels, vals, alpha=0.75)
        ax.set_title(title)
        ax.grid(axis="y", linestyle="--", alpha=0.35)
        for b in bars:
            h = b.get_height()
            ax.text(b.get_x() + b.get_width() / 2, h, f"{h:.4f}", ha="center", va="bottom", fontsize=9)

    plt.tight_layout()
    out_path = os.path.join(out_dir, "baseline_vs_rl_summary.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[compare_baseline_rl] Saved: {out_path}")


def compare_baseline_vs_rl(
    episodes: int = 1,
    iterations: int = 100,
    out_dir: str = "Path_Iterations",
    trained_agent: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Run and compare baseline vs RL policies.

    Notes:
    - Expects `trained_agent` to be a trained DQNAgent instance.
    - If not provided, function will try to instantiate DQNAgent if torch is available.
      (Untrained RL is still comparable structurally but not meaningful performance-wise.)
    """
    network = load_network()
    if not network:
        raise RuntimeError("No saved network found. Create/load network first.")
    routers, publishers, subscribers = network

    # Environments kept separate so each policy starts clean.
    env_baseline = CacheEnvironment(routers=routers, episode_length=iterations)
    env_rl = CacheEnvironment(routers=routers, episode_length=iterations)

    # Prepare RL agent
    agent = trained_agent
    if agent is None:
        try:
            from dqn_agent import DQNAgent  # lazy import to handle missing torch gracefully

            state_size = env_rl.reset().shape[0]
            action_size = len(routers)
            agent = DQNAgent(state_size=state_size, action_size=action_size)
            print("[compare_baseline_rl] Warning: using UNTRAINED DQN agent for comparison.")
        except Exception as e:
            raise RuntimeError(
                "RL comparison requires dqn_agent (PyTorch). "
                "Install torch and/or pass a trained_agent."
            ) from e

    # Evaluate per episode and concatenate
    baseline_all = []
    rl_all = []
    for ep in range(1, episodes + 1):
        bdf = evaluate_baseline_policy(env_baseline, iterations)
        rdf = evaluate_rl_policy(env_rl, agent, iterations)
        bdf["episode"] = ep
        rdf["episode"] = ep
        baseline_all.append(bdf)
        rl_all.append(rdf)

    df_baseline = pd.concat(baseline_all, ignore_index=True) if baseline_all else pd.DataFrame()
    df_rl = pd.concat(rl_all, ignore_index=True) if rl_all else pd.DataFrame()
    combined = pd.concat([df_baseline, df_rl], ignore_index=True)

    summary_df = _summary(combined)

    # Save logs
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    per_iter_csv = os.path.join(out_dir, f"baseline_vs_rl_per_iteration_{ts}.csv")
    summary_csv = os.path.join(out_dir, f"baseline_vs_rl_summary_{ts}.csv")

    combined.to_csv(per_iter_csv, index=False)
    summary_df.to_csv(summary_csv, index=False)

    # Plots
    plot_dir = os.path.join(out_dir, "plots")
    _plot_metric_lines(df_baseline, df_rl, plot_dir)
    _plot_summary_bars(summary_df, plot_dir)

    print("\n[compare_baseline_rl] Summary:")
    print(summary_df.to_string(index=False))
    print(f"[compare_baseline_rl] Saved CSV: {per_iter_csv}")
    print(f"[compare_baseline_rl] Saved CSV: {summary_csv}")

    return {
        "per_iteration_df": combined,
        "summary_df": summary_df,
        "per_iteration_csv": per_iter_csv,
        "summary_csv": summary_csv,
    }


if __name__ == "__main__":
    # Default run (uses untrained RL if no trained agent passed).
    # For meaningful results, train DQN first and pass trained agent from your training script.
    compare_baseline_vs_rl(episodes=1, iterations=50, out_dir="Path_Iterations", trained_agent=None)
