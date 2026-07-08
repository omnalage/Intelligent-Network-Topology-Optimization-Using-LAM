"""
Subscriber Topology Impact Analysis
-----------------------------------

Goal:
- Keep Routers and Publishers fixed.
- Change ONLY Subscriber -> Router attachment (topology of subscribers).
- Measure system performance (CHR, Latency, Hop Reduction) BEFORE and AFTER
  changing subscriber positions.
- Compare and visualize the impact.

This script:
1. Loads the existing network (routers, publishers, subscribers) from
   Saved_Network/network_setup.pkl (created by main.setup_network()).
2. Runs a baseline simulation with the original subscriber attachments.
3. Randomly moves subscribers to different routers to create a worse topology.
4. Runs the simulation again for the modified subscriber topology.
5. Computes average metrics and generates comparison plots with topology visualization.
"""

import os
import copy
import random
from typing import List, Tuple, Dict, Any

import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx

from main import load_network, setup_network, run_simulation, plot_network_graph


# -------------------------
# Helper functions
# -------------------------

def _ensure_network() -> Tuple[List[Any], List[Any], List[Any]]:
    """
    Load an existing network if available; otherwise call setup_network().
    Returns:
        (routers, publishers, subscribers)
    """
    network = load_network()
    if network is not None and isinstance(network, tuple) and len(network) == 3:
        routers, publishers, subscribers = network
        print(f"[subscriber_topology_impact] Loaded existing network "
              f"({len(routers)} routers, {len(publishers)} publishers, {len(subscribers)} subscribers)")
        return routers, publishers, subscribers

    print("[subscriber_topology_impact] No saved network found, running setup_network()...")
    routers, publishers, subscribers = setup_network()
    return routers, publishers, subscribers


def _simulation_to_df(simulation_data) -> pd.DataFrame:
    """
    Convert run_simulation() output to a DataFrame with standard columns.
    run_simulation() returns rows of:
        [Simulation Time, No of Clients, Total Requests,
         Hop Reduction, Cache Hit Ratio, Latency]
    """
    columns = [
        "SimulationTime",
        "NumClients",
        "TotalRequests",
        "HopReduction",
        "CacheHitRatio",
        "Latency",
    ]
    return pd.DataFrame(simulation_data, columns=columns)


def compute_average_metrics(df: pd.DataFrame) -> Dict[str, float]:
    """
    Compute average CHR, Latency, and HopReduction from a simulation DataFrame.
    Returns:
        dict with keys: 'CHR', 'Latency', 'HopReduction'
    """
    if df.empty:
        return {"CHR": 0.0, "Latency": 0.0, "HopReduction": 0.0}

    chr_avg = float(df["CacheHitRatio"].mean())
    latency_avg = float(df["Latency"].mean())
    hop_avg = float(df["HopReduction"].mean())
    return {"CHR": chr_avg, "Latency": latency_avg, "HopReduction": hop_avg}


def move_subscribers_randomly(subscribers: List[Any],
                              routers: List[Any],
                              seed: int = None) -> Tuple[Dict[str, Tuple[str, str]], List[Any], List[Any]]:
    """
    Randomly move subscribers to different routers, creating a suboptimal topology
    that will degrade performance metrics.

    Args:
        subscribers: list of Subscriber objects (must have .connected_router)
        routers: list of Router objects
        seed: random seed for reproducibility

    Returns:
        Tuple of:
            - mapping dict: {subscriber_name: (old_router_name, new_router_name)}
            - original_routers: list of original router connections before change
            - new_routers: list of new router connections after change
    """
    if seed is not None:
        random.seed(seed)
    
    if not routers or not subscribers:
        return {}, [], []

    mapping = {}
    original_routers = []
    new_routers = []
    
    for sub in subscribers:
        old_router = getattr(sub, "connected_router", None)
        original_routers.append(old_router)
        
        # Randomly select a different router
        new_router = random.choice(routers)
        new_routers.append(new_router)
        
        # Update subscriber's connection
        setattr(sub, "connected_router", new_router)
        
        old_name = getattr(old_router, 'name', 'None')
        new_name = new_router.name
        mapping[str(sub.name)] = (old_name, new_name)
    
    return mapping, original_routers, new_routers


def build_network_graph(routers: List[Any],
                       publishers: List[Any],
                       subscribers: List[Any],
                       subscriber_connections: List[Any]) -> nx.Graph:
    """
    Build a NetworkX graph representation of the network topology.
    
    Args:
        routers: list of Router objects
        publishers: list of Publisher objects
        subscribers: list of Subscriber objects
        subscriber_connections: list of router objects that subscribers are connected to
    
    Returns:
        nx.Graph: network topology graph
    """
    G = nx.Graph()
    
    # Add routers (nodes)
    for router in routers:
        G.add_node(router.name, node_type='router')
    
    # Add publishers (nodes)
    for pub in publishers:
        pub_name = getattr(pub, 'name', f'pub_{id(pub)}')
        G.add_node(pub_name, node_type='publisher')
        # Connect publisher to its router
        pub_router = getattr(pub, 'connected_router', None)
        if pub_router:
            G.add_edge(pub_name, pub_router.name, edge_type='publisher_connection')
    
    # Add subscribers (nodes) and their connections
    for sub, connected_router in zip(subscribers, subscriber_connections):
        sub_name = getattr(sub, 'name', f'sub_{id(sub)}')
        G.add_node(sub_name, node_type='subscriber')
        if connected_router:
            G.add_edge(sub_name, connected_router.name, edge_type='subscriber_connection')
    
    # Add router interconnections from FIB
    for router in routers:
        fib = getattr(router, 'FIB', {})
        for prefix, next_hop_router in fib.items():
            if isinstance(next_hop_router, str):
                G.add_edge(router.name, next_hop_router, edge_type='routing')
            else:
                next_router_name = getattr(next_hop_router, 'name', str(next_hop_router))
                G.add_edge(router.name, next_router_name, edge_type='routing')
    
    return G


def visualize_network_topology(routers: List[Any],
                               publishers: List[Any],
                               subscribers: List[Any],
                               subscriber_connections: List[Any],
                               title: str = "Network Topology",
                               out_path: str = None):
    """
    Visualize network topology with routers, publishers, and subscribers.
    
    Args:
        routers: list of Router objects
        publishers: list of Publisher objects
        subscribers: list of Subscriber objects
        subscriber_connections: list of router objects that subscribers are connected to
        title: title for the plot
        out_path: path to save the figure (optional)
    """
    G = build_network_graph(routers, publishers, subscribers, subscriber_connections)
    
    plt.figure(figsize=(14, 10))
    
    # Layout algorithm - spring layout for better visualization
    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
    
    # Separate nodes by type
    routers_nodes = [node for node, attr in G.nodes(data=True) if attr.get('node_type') == 'router']
    publishers_nodes = [node for node, attr in G.nodes(data=True) if attr.get('node_type') == 'publisher']
    subscribers_nodes = [node for node, attr in G.nodes(data=True) if attr.get('node_type') == 'subscriber']
    
    # Draw edges by type
    routing_edges = [(u, v) for u, v, attr in G.edges(data=True) if attr.get('edge_type') == 'routing']
    publisher_edges = [(u, v) for u, v, attr in G.edges(data=True) if attr.get('edge_type') == 'publisher_connection']
    subscriber_edges = [(u, v) for u, v, attr in G.edges(data=True) if attr.get('edge_type') == 'subscriber_connection']
    
    # Draw different edge types
    nx.draw_networkx_edges(G, pos, edgelist=routing_edges, edge_color='gray', width=1.5, alpha=0.6, style='solid')
    nx.draw_networkx_edges(G, pos, edgelist=publisher_edges, edge_color='green', width=2.5, alpha=0.8, style='dashed')
    nx.draw_networkx_edges(G, pos, edgelist=subscriber_edges, edge_color='red', width=2.5, alpha=0.8, style='dashed')
    
    # Draw nodes by type
    nx.draw_networkx_nodes(G, pos, nodelist=routers_nodes, node_color='#3498db', 
                          node_size=1500, node_shape='s', label='Routers')
    nx.draw_networkx_nodes(G, pos, nodelist=publishers_nodes, node_color='#2ecc71', 
                          node_size=1000, node_shape='o', label='Publishers')
    nx.draw_networkx_nodes(G, pos, nodelist=subscribers_nodes, node_color='#e74c3c', 
                          node_size=1000, node_shape='^', label='Subscribers')
    
    # Draw labels
    nx.draw_networkx_labels(G, pos, font_size=8, font_weight='bold')
    
    plt.title(title, fontsize=14, fontweight='bold')
    plt.legend(loc='upper left', fontsize=10)
    plt.axis('off')
    plt.tight_layout()
    
    if out_path:
        os.makedirs(os.path.dirname(out_path) if os.path.dirname(out_path) else '.', exist_ok=True)
        plt.savefig(out_path, dpi=150, bbox_inches='tight')
        print(f"[subscriber_topology_impact] Saved topology visualization to: {out_path}")
    
    plt.show()
    plt.close()


def plot_before_after_metrics(before: Dict[str, float],
                              after: Dict[str, float],
                              out_dir: str = "Path_Iterations/plots",
                              title_suffix: str = ""):
    """
    Create separate bar chart comparisons for each metric (CHR, Latency, HopReduction)
    between 'Before' and 'After' subscriber-topology change.
    """
    os.makedirs(out_dir, exist_ok=True)

    metrics = [
        ("CHR", "Cache Hit Ratio (CHR)", "Higher is Better"),
        ("Latency", "Latency (ms)", "Lower is Better"),
        ("HopReduction", "Hop Reduction Ratio", "Higher is Better")
    ]

    for metric_key, metric_label, direction in metrics:
        before_val = before.get(metric_key, 0.0)
        after_val = after.get(metric_key, 0.0)

        fig, ax = plt.subplots(figsize=(8, 6))
        
        x_pos = [0, 1]
        values = [before_val, after_val]
        colors = ['#3498db', '#e74c3c']
        labels = ['Before\n(Original)', 'After\n(Subscriber Moved)']

        bars = ax.bar(x_pos, values, color=colors, alpha=0.8, edgecolor='black', linewidth=2)
        
        # Add value labels on bars
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{value:.4f}',
                   ha='center', va='bottom', fontweight='bold', fontsize=11)

        ax.set_xticks(x_pos)
        ax.set_xticklabels(labels, fontsize=11)
        ax.set_ylabel(metric_label, fontsize=12, fontweight='bold')
        ax.set_title(f"{metric_label} Comparison\n({direction})" + 
                    (f" - {title_suffix}" if title_suffix else ""),
                    fontsize=13, fontweight='bold')
        ax.grid(axis='y', linestyle='--', alpha=0.3)
        ax.set_axisbelow(True)
        
        # Calculate percentage change
        if before_val != 0:
            pct_change = ((after_val - before_val) / before_val) * 100
            change_text = f"Change: {pct_change:+.2f}%"
            ax.text(0.5, 0.95, change_text, transform=ax.transAxes,
                   ha='center', va='top', fontsize=10, 
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        
        # Save with metric-specific filename
        metric_filename = metric_key.lower().replace(' ', '_')
        out_path = os.path.join(out_dir, f"topology_comparison_{metric_filename}.png")
        plt.savefig(out_path, dpi=150, bbox_inches='tight')
        print(f"[subscriber_topology_impact] Saved {metric_key} comparison plot to: {out_path}")
        plt.close()


def plot_time_series(before_df: pd.DataFrame,
                     after_df: pd.DataFrame,
                     out_dir: str = "Path_Iterations/plots"):
    """
    Plot CHR, Latency, HopReduction over iterations for
    before vs after subscriber-topology change with separate plots for each metric.
    """
    os.makedirs(out_dir, exist_ok=True)

    # Ensure both dataframes have an 'iteration' index
    before_df = before_df.reset_index(drop=True)
    after_df = after_df.reset_index(drop=True)
    
    before_df['iteration'] = range(len(before_df))
    after_df['iteration'] = range(len(after_df))

    metrics = [
        ("CacheHitRatio", "Cache Hit Ratio (CHR)", True),  # higher is better
        ("Latency", "Latency (ms)", False),                # lower is better
        ("HopReduction", "Hop Reduction Ratio", True),     # higher is better
    ]

    for col, label, higher_better in metrics:
        fig, ax = plt.subplots(figsize=(12, 6))
        
        ax.plot(before_df["iteration"], before_df[col], marker='o', linestyle='-',
                label="Before (original)", color="#3498db", linewidth=2.5, markersize=4, alpha=0.8)
        ax.plot(after_df["iteration"], after_df[col], marker='s', linestyle='--',
                label="After (subscriber moved)", color="#e74c3c", linewidth=2.5, markersize=4, alpha=0.8)
        
        ax.set_xlabel("Iteration", fontsize=12, fontweight='bold')
        ax.set_ylabel(label, fontsize=12, fontweight='bold')
        
        better_dir = "↑ Higher is Better" if higher_better else "↓ Lower is Better"
        ax.set_title(f"{label} over Iterations\n({better_dir})", fontsize=13, fontweight='bold')
        
        ax.grid(True, linestyle='--', alpha=0.3)
        ax.legend(loc='best', fontsize=11)
        ax.set_axisbelow(True)
        
        plt.tight_layout()
        
        metric_filename = col.lower()
        out_path = os.path.join(out_dir, f"timeseries_comparison_{metric_filename}.png")
        plt.savefig(out_path, dpi=150, bbox_inches='tight')
        print(f"[subscriber_topology_impact] Saved {label} time-series plot to: {out_path}")
        plt.close()


# -------------------------
# Main experiment pipeline
# -------------------------

def run_subscriber_topology_experiment(policy: str = "FACR",
                                       iterations: int = 500) -> Dict[str, Any]:
    """
    Run the subscriber-topology impact experiment:
      1) Baseline with original subscriber attachments.
      2) After randomly moving subscribers to new routers.
      3) Generate network topology visualizations before and after.
      4) Generate separate metric comparison plots.

    Args:
        policy: caching policy string to use in run_simulation()
        iterations: number of iterations per simulation

    Returns:
        dict with:
            'before_metrics', 'after_metrics',
            'before_df', 'after_df',
            'topology_mapping',
            'original_connections'
    """
    routers, publishers, subscribers = _ensure_network()
    
    # Store original connections
    original_connections = [getattr(s, "connected_router", None) for s in subscribers]

    # Deep-copy subscriber->router mapping for logging
    original_mapping = {s.name: getattr(s, "connected_router", None).name
                        for s in subscribers if getattr(s, "connected_router", None) is not None}
    print("[subscriber_topology_impact] Original subscriber->router mapping:")
    for s_name, r_name in original_mapping.items():
        print(f"  {s_name} -> {r_name}")

    # --- Visualize original topology ---
    print("\n[subscriber_topology_impact] Creating network topology visualization (BEFORE)...")
    os.makedirs("Path_Iterations/plots", exist_ok=True)
    try:
        plot_network_graph(routers, publishers, subscribers, out_path="Path_Iterations/plots/topology_before.png")
    except Exception:
        # Fallback to local visualization if main.plot_network_graph fails
        visualize_network_topology(routers, publishers, subscribers, original_connections,
                                   title="Network Topology - BEFORE Subscriber Movement",
                                   out_path="Path_Iterations/plots/topology_before.png")

    # --- Baseline simulation ---
    print("\n[subscriber_topology_impact] Running baseline simulation (original topology)...")
    baseline_sim_data = run_simulation(routers, publishers, subscribers, policy, iterations, model=None)
    baseline_df = _simulation_to_df(baseline_sim_data)
    before_metrics = compute_average_metrics(baseline_df)
    print(f"[subscriber_topology_impact] Baseline averages (policy={policy}): "
          f"CHR={before_metrics['CHR']:.4f}, "
          f"Latency={before_metrics['Latency']:.6f}, "
          f"HopReduction={before_metrics['HopReduction']:.4f}")

    # --- Move subscribers randomly ---
    print("\n[subscriber_topology_impact] Randomly moving ALL subscribers to new router positions...")
    mapping, orig_routers, new_routers = move_subscribers_randomly(subscribers, routers, seed=42)
    print("[subscriber_topology_impact] New subscriber->router mapping:")
    for s_name, (old_r, new_r) in mapping.items():
        print(f"  {s_name}: {old_r} -> {new_r}")

    # --- Visualize new topology ---
    print("\n[subscriber_topology_impact] Creating network topology visualization (AFTER)...")
    try:
        plot_network_graph(routers, publishers, subscribers, out_path="Path_Iterations/plots/topology_after.png")
    except Exception:
        visualize_network_topology(routers, publishers, subscribers, new_routers,
                                   title="Network Topology - AFTER Subscriber Movement",
                                   out_path="Path_Iterations/plots/topology_after.png")

    # --- Simulation after topology change ---
    print("\n[subscriber_topology_impact] Running simulation AFTER subscriber-topology change...")
    after_sim_data = run_simulation(routers, publishers, subscribers, policy, iterations, model=None)
    after_df = _simulation_to_df(after_sim_data)
    after_metrics = compute_average_metrics(after_df)
    print(f"[subscriber_topology_impact] After-change averages (policy={policy}): "
          f"CHR={after_metrics['CHR']:.4f}, "
          f"Latency={after_metrics['Latency']:.6f}, "
          f"HopReduction={after_metrics['HopReduction']:.4f}")

    # --- Calculate metric changes ---
    print("\n[subscriber_topology_impact] Metric Changes:")
    chr_change = ((after_metrics['CHR'] - before_metrics['CHR']) / before_metrics['CHR'] * 100) if before_metrics['CHR'] != 0 else 0
    lat_change = ((after_metrics['Latency'] - before_metrics['Latency']) / before_metrics['Latency'] * 100) if before_metrics['Latency'] != 0 else 0
    hop_change = ((after_metrics['HopReduction'] - before_metrics['HopReduction']) / before_metrics['HopReduction'] * 100) if before_metrics['HopReduction'] != 0 else 0
    
    print(f"  CHR Change: {chr_change:+.2f}% (should be negative for worse performance)")
    print(f"  Latency Change: {lat_change:+.2f}% (should be positive for worse performance)")
    print(f"  Hop Reduction Change: {hop_change:+.2f}% (should be negative for worse performance)")

    # --- Create separate metric plots ---
    print("\n[subscriber_topology_impact] Creating metric comparison plots...")
    # Do not include policy string in the plot titles
    plot_before_after_metrics(before_metrics, after_metrics, out_dir="Path_Iterations/plots", 
                             title_suffix="")
    
    # --- Plot time series comparison ---
    plot_time_series(baseline_df, after_df, out_dir="Path_Iterations/plots")

    return {
        "before_metrics": before_metrics,
        "after_metrics": after_metrics,
        "before_df": baseline_df,
        "after_df": after_df,
        "topology_mapping": mapping,
        "original_connections": original_connections,
    }


if __name__ == "__main__":
    print("=" * 80)
    print("SUBSCRIBER TOPOLOGY IMPACT ANALYSIS")
    print("=" * 80)
    results = run_subscriber_topology_experiment(policy="FACR", iterations=500)
    print("\n[subscriber_topology_impact] Experiment complete.")
    print("[subscriber_topology_impact] Before metrics:", results["before_metrics"])
    print("[subscriber_topology_impact] After metrics:", results["after_metrics"])
    print("Check 'Path_Iterations/plots/' for comparison figures.")

