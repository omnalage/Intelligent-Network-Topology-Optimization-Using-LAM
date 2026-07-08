#!/usr/bin/env python3
"""
Presentation-safe topology RL impact analysis.

This version keeps the reduced-router setup for faster training while fixing:
- invalid subscriber movement (`connected_router` is used consistently)
- inconsistent reduced topology/FIB wiring
- zero-metric scenarios caused by stale or missing simulator refreshes
- unsupported claims in the final report

Scenarios:
1. Train Agent A on original reduced topology
2. Train Agent B from scratch on changed topology
3. Evaluate Agent A on changed topology without retraining
4. Fine-tune Agent A briefly on changed topology
"""

from __future__ import annotations

import copy
import os
import pickle
import random
import shutil
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch

from main import load_network, plot_centrality_measures, plot_network_graph, run_simulation, setup_network
from dqn_agent import DQNAgent
from rl_env import CacheEnvironment
from trainer import train_agent


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = SCRIPT_DIR
LOG_DIR = os.path.join(OUTPUT_DIR, "logs")
MODEL_DIR = os.path.join(OUTPUT_DIR, "models")
PLOT_DIR = os.path.join(OUTPUT_DIR, "plots")

for path in (LOG_DIR, MODEL_DIR, PLOT_DIR):
    os.makedirs(path, exist_ok=True)


def load_or_create_network() -> Tuple[List[Any], List[Any], List[Any]]:
    network = load_network()
    if network:
        return copy.deepcopy(network)
    return setup_network()


def reduce_network_to_n_routers(
    routers: List[Any],
    publishers: List[Any],
    subscribers: List[Any],
    n: int = 10,
) -> Tuple[List[Any], List[Any], List[Any]]:
    """
    Build a self-consistent reduced network instead of only slicing routers.

    The original implementation kept the first N routers but left subscribers and
    FIB paths pointing outside the reduced topology, which made scenario results
    unreliable. Here we rebuild a valid smaller topology while preserving speed.
    """
    if not routers:
        raise ValueError("Cannot reduce an empty router list")

    keep_n = min(n, len(routers))
    routers = routers[:keep_n]
    publishers = publishers[:]
    subscribers = subscribers[:]

    # Reattach all subscribers inside the reduced topology.
    for idx, subscriber in enumerate(subscribers):
        subscriber.connected_router = routers[idx % keep_n]

    # Optional publisher attachment is useful for graph plotting consistency.
    for publisher in publishers:
        publisher.connected_router = routers[-1]

    # Rebuild the reduced FIB so requests stay inside the smaller topology.
    for i, router in enumerate(routers):
        router.fib = {}
        if i < keep_n - 1:
            router.fib.update({f"cat_image{j}.jpg": routers[i + 1] for j in range(1, 51)})
            router.fib.update({f"dog_image{j}.jpg": routers[i + 1] for j in range(1, 51)})

        for j in range(i + 2, min(i + 4, keep_n)):
            router.fib.update({f"cat_image{k}.jpg": routers[j] for k in range(1, 51)})
            router.fib.update({f"dog_image{k}.jpg": routers[j] for k in range(1, 51)})

    if publishers:
        routers[-1].fib.update({f"cat_image{j}.jpg": publishers[0] for j in range(1, 51)})
    if len(publishers) > 1:
        routers[-1].fib.update({f"dog_image{j}.jpg": publishers[1] for j in range(1, 51)})

    return routers, publishers, subscribers


def save_network_snapshot(routers: List[Any], publishers: List[Any], subscribers: List[Any], label: str) -> str:
    path = os.path.join(OUTPUT_DIR, f"network_snapshot_{label}.pkl")
    with open(path, "wb") as handle:
        pickle.dump((routers, publishers, subscribers), handle)
    return path


def save_agent_model(agent: Any, scenario: str, episode: int, topology_name: str) -> str:
    path = os.path.join(MODEL_DIR, f"agent_{scenario}_{topology_name}_ep{episode}.pt")
    torch.save(
        {
            "model_state": agent.q_network.state_dict(),
            "target_state": agent.target_network.state_dict(),
            "epsilon": agent.epsilon,
        },
        path,
    )
    return path


def load_agent_model(agent: Any, path: str) -> Any:
    checkpoint = torch.load(path, map_location=agent.device)
    agent.q_network.load_state_dict(checkpoint["model_state"])
    agent.target_network.load_state_dict(checkpoint["target_state"])
    agent.epsilon = checkpoint.get("epsilon", agent.epsilon)
    return agent


def reset_router_metrics(routers: List[Any]) -> None:
    for router in routers:
        router.reset()
        router.CMBA = 0.0
        router.cmba = 0.0
        router.avg_cache_latency_ms = 0.0


def simulation_df(simulation_rows: List[List[Any]]) -> pd.DataFrame:
    columns = [
        "simulation_time",
        "num_clients",
        "total_requests",
        "hop_reduction",
        "chr_percent",
        "latency",
    ]
    return pd.DataFrame(simulation_rows, columns=columns)


def refresh_topology_metrics(
    routers: List[Any],
    publishers: List[Any],
    subscribers: List[Any],
    iterations: int = 20,
) -> Dict[str, float]:
    """
    Refresh router statistics using the simulator and recompute centrality.

    Keeping this explicit avoids stale all-zero metrics in changed-topology runs.
    """
    rows = run_simulation(
        routers=routers,
        publishers=publishers,
        subscribers=subscribers,
        policy="baseline",
        iterations=iterations,
    )
    try:
        plot_centrality_measures(routers, save_path=None, show_plot=False)
    except Exception:
        pass

    df = simulation_df(rows)
    return {
        "chr_percent": float(df["chr_percent"].mean()) if not df.empty else 0.0,
        "latency": float(df["latency"].mean()) if not df.empty else 0.0,
        "hop_reduction": float(df["hop_reduction"].mean()) if not df.empty else 0.0,
    }


def build_environment(
    routers: List[Any],
    publishers: List[Any],
    subscribers: List[Any],
    episode_length: int = 100,
    refresh_iterations: int = 5,
) -> CacheEnvironment:
    def refresh_metrics(action: int | None = None) -> None:
        # The simulator remains the source of truth for topology-sensitive metrics.
        refresh_topology_metrics(
            routers=routers,
            publishers=publishers,
            subscribers=subscribers,
            iterations=refresh_iterations,
        )

    return CacheEnvironment(
        routers=routers,
        publishers=publishers,
        subscribers=subscribers,
        episode_length=episode_length,
        refresh_metrics_fn=refresh_metrics,
        auto_refresh_on_reset=True,
        auto_refresh_on_step=True,
    )


def move_subscribers_randomly(
    subscribers: List[Any],
    routers: List[Any],
    seed: int = 42,
) -> Dict[str, Tuple[str, str]]:
    rng = random.Random(seed)
    mapping: Dict[str, Tuple[str, str]] = {}

    for subscriber in subscribers:
        old_router = getattr(subscriber, "connected_router", None)
        available = [router for router in routers if router is not old_router] or routers
        new_router = rng.choice(available)
        subscriber.connected_router = new_router
        mapping[subscriber.name] = (
            getattr(old_router, "name", "None"),
            getattr(new_router, "name", "None"),
        )

    return mapping


def copy_training_logs(results: Dict[str, Any], prefix: str) -> None:
    shutil.copyfile(results["summary_csv"], os.path.join(LOG_DIR, f"{prefix}_summary.csv"))
    shutil.copyfile(results["selections_csv"], os.path.join(LOG_DIR, f"{prefix}_selections.csv"))
    shutil.copyfile(results["rewards_csv"], os.path.join(LOG_DIR, f"{prefix}_rewards.csv"))


def evaluate_agent_no_training(agent: Any, environment: CacheEnvironment, iterations: int = 100) -> pd.DataFrame:
    agent.epsilon = 0.0
    state = environment.reset()
    rows: List[Dict[str, Any]] = []

    for step_idx in range(1, iterations + 1):
        action = int(agent.select_action(state, training=False))
        next_state, reward, done, info = environment.step(action)
        metrics = info.get("metrics", {})
        rows.append(
            {
                "iteration": step_idx,
                "action": action,
                "selected_router_name": info.get("selected_router_name", f"router_{action}"),
                "reward": float(reward),
                "chr": float(metrics.get("chr", 0.0) or 0.0),
                "latency_ms": float(metrics.get("latency_ms", 0.0) or 0.0),
                "cache_occupancy": float(metrics.get("cache_occupancy", 0.0) or 0.0),
                "cmba": float(metrics.get("cmba", 0.0) or 0.0),
            }
        )
        state = next_state
        if done:
            state = environment.reset()

    return pd.DataFrame(rows)


def visualize_topologies(
    routers_before: List[Any],
    routers_after: List[Any],
    publishers: List[Any],
    subscribers_before: List[Any],
    subscribers_after: List[Any],
) -> None:
    try:
        plot_network_graph(
            routers_before,
            publishers,
            subscribers_before,
            out_path=os.path.join(PLOT_DIR, "topology_before_rl.png"),
        )
    except Exception:
        pass

    try:
        plot_network_graph(
            routers_after,
            publishers,
            subscribers_after,
            out_path=os.path.join(PLOT_DIR, "topology_after_rl.png"),
        )
    except Exception:
        pass


def scenario_1_original_topology() -> Dict[str, Any]:
    routers, publishers, subscribers = load_or_create_network()
    routers, publishers, subscribers = reduce_network_to_n_routers(routers, publishers, subscribers, n=10)
    save_network_snapshot(routers, publishers, subscribers, "original")

    baseline_metrics = refresh_topology_metrics(routers, publishers, subscribers, iterations=50)
    env = build_environment(routers, publishers, subscribers, episode_length=100, refresh_iterations=5)
    state_size = env.reset().shape[0]
    agent = DQNAgent(state_size=state_size, action_size=len(routers))
    results = train_agent(environment=env, agent=agent, episodes=10, iterations=100, out_dir=LOG_DIR)
    copy_training_logs(results, "scenario1")
    model_path = save_agent_model(agent, "scenario1", 10, "original")

    return {
        "agent": agent,
        "agent_path": model_path,
        "routers": routers,
        "publishers": publishers,
        "subscribers": subscribers,
        "baseline_metrics": baseline_metrics,
    }


def scenario_2_changed_topology(
    routers_original: List[Any],
    publishers: List[Any],
    subscribers_original: List[Any],
) -> Dict[str, Any]:
    routers_changed = copy.deepcopy(routers_original)
    publishers_changed = copy.deepcopy(publishers)
    subscribers_changed = copy.deepcopy(subscribers_original)
    mapping = move_subscribers_randomly(subscribers_changed, routers_changed, seed=123)

    save_network_snapshot(routers_changed, publishers_changed, subscribers_changed, "changed")
    visualize_topologies(
        routers_original,
        routers_changed,
        publishers_changed,
        subscribers_original,
        subscribers_changed,
    )

    baseline_metrics = refresh_topology_metrics(routers_changed, publishers_changed, subscribers_changed, iterations=50)
    env = build_environment(routers_changed, publishers_changed, subscribers_changed, episode_length=100, refresh_iterations=5)
    state_size = env.reset().shape[0]
    agent = DQNAgent(state_size=state_size, action_size=len(routers_changed))
    results = train_agent(environment=env, agent=agent, episodes=10, iterations=100, out_dir=LOG_DIR)
    copy_training_logs(results, "scenario2")
    model_path = save_agent_model(agent, "scenario2", 10, "changed")

    return {
        "agent": agent,
        "agent_path": model_path,
        "routers": routers_changed,
        "publishers": publishers_changed,
        "subscribers": subscribers_changed,
        "baseline_metrics": baseline_metrics,
        "mapping": mapping,
    }


def scenario_3_adaptive_evaluation(
    pretrained_agent_path: str,
    routers_changed: List[Any],
    publishers_changed: List[Any],
    subscribers_changed: List[Any],
) -> pd.DataFrame:
    env = build_environment(routers_changed, publishers_changed, subscribers_changed, episode_length=100, refresh_iterations=5)
    state_size = env.reset().shape[0]
    agent = DQNAgent(state_size=state_size, action_size=len(routers_changed))
    load_agent_model(agent, pretrained_agent_path)
    eval_df = evaluate_agent_no_training(agent, env, iterations=100)
    eval_df.to_csv(os.path.join(LOG_DIR, "scenario3_evaluation.csv"), index=False)
    return eval_df


def scenario_4_finetune(
    pretrained_agent_path: str,
    routers_changed: List[Any],
    publishers_changed: List[Any],
    subscribers_changed: List[Any],
) -> Dict[str, Any]:
    env = build_environment(routers_changed, publishers_changed, subscribers_changed, episode_length=100, refresh_iterations=5)
    state_size = env.reset().shape[0]
    agent = DQNAgent(state_size=state_size, action_size=len(routers_changed))
    load_agent_model(agent, pretrained_agent_path)
    agent.epsilon = max(agent.epsilon, 0.10)

    results = train_agent(environment=env, agent=agent, episodes=3, iterations=100, out_dir=LOG_DIR)
    copy_training_logs(results, "scenario4_finetune")
    model_path = save_agent_model(agent, "scenario4", 3, "changed_finetuned")

    return {
        "agent": agent,
        "agent_path": model_path,
    }


def scenario_metric_row(label: str, reward: float, chr_value: float, latency_ms: float, occupancy: float) -> Dict[str, Any]:
    return {
        "Scenario": label,
        "final_reward": float(reward),
        "avg_chr": float(chr_value),
        "avg_latency_ms": float(latency_ms),
        "avg_occupancy": float(occupancy),
    }


def compare_scenarios() -> pd.DataFrame:
    s1_summary = pd.read_csv(os.path.join(LOG_DIR, "scenario1_summary.csv"))
    s1_selections = pd.read_csv(os.path.join(LOG_DIR, "scenario1_selections.csv"))
    s2_summary = pd.read_csv(os.path.join(LOG_DIR, "scenario2_summary.csv"))
    s2_selections = pd.read_csv(os.path.join(LOG_DIR, "scenario2_selections.csv"))
    s3_eval = pd.read_csv(os.path.join(LOG_DIR, "scenario3_evaluation.csv"))
    s4_summary = pd.read_csv(os.path.join(LOG_DIR, "scenario4_finetune_summary.csv"))
    s4_selections = pd.read_csv(os.path.join(LOG_DIR, "scenario4_finetune_selections.csv"))

    rows = [
        scenario_metric_row(
            "1_Original_Train",
            s1_summary["episode_reward_avg"].iloc[-1],
            s1_selections["chr"].mean(),
            s1_selections["latency_ms"].mean(),
            s1_selections["cache_occupancy"].mean(),
        ),
        scenario_metric_row(
            "2_Changed_Fresh",
            s2_summary["episode_reward_avg"].iloc[-1],
            s2_selections["chr"].mean(),
            s2_selections["latency_ms"].mean(),
            s2_selections["cache_occupancy"].mean(),
        ),
        scenario_metric_row(
            "3_Changed_Adaptive",
            s3_eval["reward"].mean(),
            s3_eval["chr"].mean(),
            s3_eval["latency_ms"].mean(),
            s3_eval["cache_occupancy"].mean(),
        ),
        scenario_metric_row(
            "4_Changed_Finetuned",
            s4_summary["episode_reward_avg"].iloc[-1],
            s4_selections["chr"].mean(),
            s4_selections["latency_ms"].mean(),
            s4_selections["cache_occupancy"].mean(),
        ),
    ]

    comparison_df = pd.DataFrame(rows)
    comparison_df.to_csv(os.path.join(LOG_DIR, "comparison_summary.csv"), index=False)
    return comparison_df


def plot_scenario_comparison(comparison_df: pd.DataFrame) -> None:
    scenarios = comparison_df["Scenario"].tolist()
    metrics = [
        ("final_reward", "Final Reward", "01_reward_comparison.png"),
        ("avg_chr", "Average CHR", "02_chr_comparison.png"),
        ("avg_latency_ms", "Average Latency (ms)", "03_latency_comparison.png"),
        ("avg_occupancy", "Average Cache Occupancy", "04_occupancy_comparison.png"),
    ]

    for col, title, filename in metrics:
        plt.figure(figsize=(11, 6))
        bars = plt.bar(scenarios, comparison_df[col], color=["#3A7CA5", "#F18F01", "#6A994E", "#8E5A9B"])
        plt.title(title)
        plt.ylabel(title)
        plt.xticks(rotation=20, ha="right")
        plt.grid(axis="y", alpha=0.3)
        for bar, value in zip(bars, comparison_df[col]):
            plt.text(bar.get_x() + bar.get_width() / 2, value, f"{value:.4f}", ha="center", va="bottom", fontsize=9)
        plt.tight_layout()
        plt.savefig(os.path.join(PLOT_DIR, filename), dpi=150)
        plt.close()


def plot_router_selection_heatmap() -> None:
    scenario_frames = {
        "Scenario 1": pd.read_csv(os.path.join(LOG_DIR, "scenario1_selections.csv")),
        "Scenario 2": pd.read_csv(os.path.join(LOG_DIR, "scenario2_selections.csv")),
        "Scenario 3": pd.read_csv(os.path.join(LOG_DIR, "scenario3_evaluation.csv")),
        "Scenario 4": pd.read_csv(os.path.join(LOG_DIR, "scenario4_finetune_selections.csv")),
    }

    counters = {label: Counter(frame["selected_router_name"]) for label, frame in scenario_frames.items()}
    all_routers = sorted({router for counter in counters.values() for router in counter.keys()})
    data = np.array([[counter.get(router, 0) for router in all_routers] for counter in counters.values()])

    fig, ax = plt.subplots(figsize=(12, 6))
    image = ax.imshow(data, cmap="YlOrRd", aspect="auto")
    ax.set_xticks(range(len(all_routers)))
    ax.set_xticklabels(all_routers, rotation=45, ha="right")
    ax.set_yticks(range(len(counters)))
    ax.set_yticklabels(list(counters.keys()))
    ax.set_title("Router Selection Frequency Heatmap")
    ax.set_xlabel("Router")
    plt.colorbar(image, ax=ax, label="Selection Count")
    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "05_router_selection_heatmap.png"), dpi=150)
    plt.close()


def percent_change(new_value: float, old_value: float) -> str:
    if abs(old_value) < 1e-12:
        return "N/A"
    return f"{((new_value - old_value) / old_value) * 100:.2f}%"


def generate_report(comparison_df: pd.DataFrame) -> None:
    comparison_df = comparison_df.set_index("Scenario")
    s1 = comparison_df.loc["1_Original_Train"]
    s2 = comparison_df.loc["2_Changed_Fresh"]
    s3 = comparison_df.loc["3_Changed_Adaptive"]
    s4 = comparison_df.loc["4_Changed_Finetuned"]

    report = f"""
TOPOLOGY RL IMPACT ANALYSIS
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Network Scope:
- Reduced topology used for speed: 10 routers
- Subscriber movement changes only attachment points

Scenario 1: Original topology, Agent A trained
- Final reward: {s1['final_reward']:.6f}
- Average CHR: {s1['avg_chr']:.6f}
- Average latency: {s1['avg_latency_ms']:.4f} ms

Scenario 2: Changed topology, Agent B trained from scratch
- Final reward: {s2['final_reward']:.6f}
- Average CHR: {s2['avg_chr']:.6f}
- Average latency: {s2['avg_latency_ms']:.4f} ms
- Reward change vs Scenario 1: {percent_change(s2['final_reward'], s1['final_reward'])}

Scenario 3: Changed topology, Agent A reused without retraining
- Final reward: {s3['final_reward']:.6f}
- Average CHR: {s3['avg_chr']:.6f}
- Average latency: {s3['avg_latency_ms']:.4f} ms
- Reward change vs Scenario 1: {percent_change(s3['final_reward'], s1['final_reward'])}

Scenario 4: Changed topology, Agent A fine-tuned briefly
- Final reward: {s4['final_reward']:.6f}
- Average CHR: {s4['avg_chr']:.6f}
- Average latency: {s4['avg_latency_ms']:.4f} ms
- Reward change vs Scenario 2: {percent_change(s4['final_reward'], s2['final_reward'])}

Interpretation Guidance:
- Scenario 2 shows the cost of relearning on the changed topology.
- Scenario 3 shows transfer without adaptation.
- Scenario 4 shows whether quick fine-tuning is enough for recovery.

Presentation-safe claim:
- Use the results to compare adaptation behavior across the same reduced 10-router setting.
- Avoid claiming universal improvement; topology change can legitimately reduce performance.
"""

    with open(os.path.join(OUTPUT_DIR, "ANALYSIS_REPORT.txt"), "w", encoding="utf-8") as handle:
        handle.write(report.strip() + "\n")


def main() -> None:
    print("=" * 70)
    print("TOPOLOGY RL IMPACT ANALYSIS (REDUCED 10-ROUTER SETUP)")
    print("=" * 70)

    scenario1 = scenario_1_original_topology()
    scenario2 = scenario_2_changed_topology(
        scenario1["routers"],
        scenario1["publishers"],
        scenario1["subscribers"],
    )
    scenario_3_adaptive_evaluation(
        scenario1["agent_path"],
        scenario2["routers"],
        scenario2["publishers"],
        scenario2["subscribers"],
    )
    scenario_4_finetune(
        scenario1["agent_path"],
        scenario2["routers"],
        scenario2["publishers"],
        scenario2["subscribers"],
    )

    comparison_df = compare_scenarios()
    plot_scenario_comparison(comparison_df)
    plot_router_selection_heatmap()
    generate_report(comparison_df)

    print("Completed. Results are saved in Topology_RL_Impact/.")


if __name__ == "__main__":
    main()
