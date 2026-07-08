#!/usr/bin/env python3
"""
Generate presentation-focused plots from Topology_RL_Impact logs.
"""

from __future__ import annotations

import os
from typing import Dict, Tuple

import matplotlib.pyplot as plt
import pandas as pd


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
PLOT_DIR = os.path.join(BASE_DIR, "plots")

os.makedirs(PLOT_DIR, exist_ok=True)


SCENARIO_META: Dict[str, Dict[str, str]] = {
    "scenario1": {
        "label": "Scenario 1: Original Train",
        "color": "#1f77b4",
        "marker": "o",
        "linestyle": "-",
    },
    "scenario2": {
        "label": "Scenario 2: Changed Fresh",
        "color": "#ff7f0e",
        "marker": "s",
        "linestyle": "--",
    },
    "scenario3": {
        "label": "Scenario 3: Adaptive Eval",
        "color": "#2ca02c",
        "marker": "^",
        "linestyle": "-.",
    },
    "scenario4": {
        "label": "Scenario 4: Fine-tuned",
        "color": "#d62728",
        "marker": "D",
        "linestyle": ":",
    },
}


def _load_training_rewards(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.copy()
    df["global_step"] = range(1, len(df) + 1)
    df["reward_smooth"] = df["reward"].rolling(window=10, min_periods=1).mean()
    return df


def _load_eval_rewards(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.copy()
    df["global_step"] = df["iteration"]
    df["reward_smooth"] = df["reward"].rolling(window=10, min_periods=1).mean()
    return df


def _load_training_metric(path: str, metric: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.copy()
    df["global_step"] = range(1, len(df) + 1)
    df[metric] = pd.to_numeric(df[metric], errors="coerce").fillna(0.0)
    df[f"{metric}_smooth"] = df[metric].rolling(window=10, min_periods=1).mean()
    return df


def _load_eval_metric(path: str, metric: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.copy()
    df["global_step"] = df["iteration"]
    df[metric] = pd.to_numeric(df[metric], errors="coerce").fillna(0.0)
    df[f"{metric}_smooth"] = df[metric].rolling(window=10, min_periods=1).mean()
    return df


def plot_reward_vs_iteration() -> None:
    scenario_paths: Dict[str, Tuple[str, bool]] = {
        "scenario1": (os.path.join(LOG_DIR, "scenario1_rewards.csv"), True),
        "scenario2": (os.path.join(LOG_DIR, "scenario2_rewards.csv"), True),
        "scenario3": (os.path.join(LOG_DIR, "scenario3_evaluation.csv"), False),
        "scenario4": (os.path.join(LOG_DIR, "scenario4_finetune_rewards.csv"), True),
    }

    plt.figure(figsize=(12, 7))
    for key, (path, is_training) in scenario_paths.items():
        if not os.path.exists(path):
            continue
        df = _load_training_rewards(path) if is_training else _load_eval_rewards(path)
        meta = SCENARIO_META[key]
        plt.plot(
            df["global_step"],
            df["reward_smooth"],
            label=meta["label"],
            color=meta["color"],
            linewidth=2.2,
            linestyle=meta["linestyle"],
            marker=meta["marker"],
            markevery=max(1, len(df) // 12),
            markersize=6,
        )

    plt.title("Reward vs Iteration Across Scenarios")
    plt.xlabel("Iteration / Global Step")
    plt.ylabel("Reward (10-step rolling average)")
    plt.grid(True, linestyle="--", alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "06_reward_vs_iteration_all_scenarios.png"), dpi=150)
    plt.close()


def plot_episode_avg_reward() -> None:
    summary_paths = {
        "scenario1": os.path.join(LOG_DIR, "scenario1_summary.csv"),
        "scenario2": os.path.join(LOG_DIR, "scenario2_summary.csv"),
        "scenario4": os.path.join(LOG_DIR, "scenario4_finetune_summary.csv"),
    }

    plt.figure(figsize=(12, 7))
    for key, path in summary_paths.items():
        if not os.path.exists(path):
            continue
        df = pd.read_csv(path)
        meta = SCENARIO_META[key]
        plt.plot(
            df["episode"],
            df["episode_reward_avg"],
            linewidth=2.2,
            label=meta["label"],
            color=meta["color"],
            linestyle=meta["linestyle"],
            marker=meta["marker"],
            markersize=7,
        )

    plt.title("Average Reward per Episode")
    plt.xlabel("Episode")
    plt.ylabel("Episode Average Reward")
    plt.grid(True, linestyle="--", alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "07_episode_avg_reward_comparison.png"), dpi=150)
    plt.close()


def plot_latency_vs_iteration() -> None:
    scenario_paths: Dict[str, Tuple[str, bool]] = {
        "scenario1": (os.path.join(LOG_DIR, "scenario1_selections.csv"), True),
        "scenario2": (os.path.join(LOG_DIR, "scenario2_selections.csv"), True),
        "scenario3": (os.path.join(LOG_DIR, "scenario3_evaluation.csv"), False),
        "scenario4": (os.path.join(LOG_DIR, "scenario4_finetune_selections.csv"), True),
    }

    plt.figure(figsize=(12, 7))
    for key, (path, is_training) in scenario_paths.items():
        if not os.path.exists(path):
            continue
        df = _load_training_metric(path, "latency_ms") if is_training else _load_eval_metric(path, "latency_ms")
        meta = SCENARIO_META[key]
        plt.plot(
            df["global_step"],
            df["latency_ms_smooth"],
            label=meta["label"],
            color=meta["color"],
            linewidth=2.2,
            linestyle=meta["linestyle"],
            marker=meta["marker"],
            markevery=max(1, len(df) // 12),
            markersize=6,
        )

    plt.title("Latency vs Iteration Across Scenarios")
    plt.xlabel("Iteration / Global Step")
    plt.ylabel("Latency (ms, 10-step rolling average)")
    plt.grid(True, linestyle="--", alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "08_latency_vs_iteration_all_scenarios.png"), dpi=150)
    plt.close()


def plot_router_selection_bars() -> None:
    scenario_paths = {
        "scenario1": os.path.join(LOG_DIR, "scenario1_selections.csv"),
        "scenario2": os.path.join(LOG_DIR, "scenario2_selections.csv"),
        "scenario3": os.path.join(LOG_DIR, "scenario3_evaluation.csv"),
        "scenario4": os.path.join(LOG_DIR, "scenario4_finetune_selections.csv"),
    }

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    for ax, (key, path) in zip(axes, scenario_paths.items()):
        if not os.path.exists(path):
            ax.axis("off")
            continue
        df = pd.read_csv(path)
        counts = df["selected_router_name"].value_counts().sort_index()
        meta = SCENARIO_META[key]
        ax.bar(counts.index, counts.values, color=meta["color"], alpha=0.85)
        ax.set_title(meta["label"])
        ax.set_xlabel("Router")
        ax.set_ylabel("Selections")
        ax.tick_params(axis="x", rotation=45)
        ax.grid(axis="y", linestyle="--", alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "09_router_selection_per_scenario.png"), dpi=150)
    plt.close()


def main() -> None:
    plot_reward_vs_iteration()
    plot_episode_avg_reward()
    plot_latency_vs_iteration()
    plot_router_selection_bars()
    print("Presentation plots generated in Topology_RL_Impact/plots/")


if __name__ == "__main__":
    main()
