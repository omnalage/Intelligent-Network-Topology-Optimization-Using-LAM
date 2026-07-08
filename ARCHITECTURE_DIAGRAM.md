# Visual Architecture & Data Flow Diagram

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│              SUBSCRIBER TOPOLOGY IMPACT ANALYSIS                │
│                         System Flow                             │
└─────────────────────────────────────────────────────────────────┘

    ┌──────────────────────────────────────────┐
    │    Load/Create Network                   │
    │  (routers, publishers, subscribers)      │
    │                                          │
    │  _ensure_network()                       │
    └────────────────┬─────────────────────────┘
                     │
                     ▼
    ┌──────────────────────────────────────────┐
    │ Visualize Original Topology              │
    │                                          │
    │ visualize_network_topology()             │
    │ └─> build_network_graph()                │
    │     - Nodes: Routers, Publishers, Subs  │
    │     - Edges: Connections & Routing      │
    │                                          │
    │ Output: topology_before.png              │
    └────────────────┬─────────────────────────┘
                     │
                     ▼
    ┌──────────────────────────────────────────┐
    │ Run Baseline Simulation (Original)       │
    │                                          │
    │ run_simulation()                         │
    │ Iterations: 500 (default)                │
    │ Policy: FACR (default)                   │
    │                                          │
    │ Output: Baseline metrics                 │
    └────────────────┬─────────────────────────┘
                     │
                     ▼
    ┌──────────────────────────────────────────┐
    │ Calculate Baseline Metrics               │
    │                                          │
    │ compute_average_metrics()                │
    │ - CHR (Cache Hit Ratio)                  │
    │ - Latency (ms)                           │
    │ - HopReduction                           │
    └────────────────┬─────────────────────────┘
                     │
                     ▼
    ┌──────────────────────────────────────────┐
    │ Randomly Move Subscribers                │
    │                                          │
    │ move_subscribers_randomly()              │
    │ - Random router selection                │
    │ - Update connections                    │
    │ - Log mappings                          │
    │                                          │
    │ Output: Movement mapping                │
    └────────────────┬─────────────────────────┘
                     │
                     ▼
    ┌──────────────────────────────────────────┐
    │ Visualize New Topology                   │
    │                                          │
    │ visualize_network_topology()             │
    │ └─> build_network_graph()                │
    │                                          │
    │ Output: topology_after.png               │
    └────────────────┬─────────────────────────┘
                     │
                     ▼
    ┌──────────────────────────────────────────┐
    │ Run New Simulation (After Movement)      │
    │                                          │
    │ run_simulation()                         │
    │ Same parameters as baseline              │
    │                                          │
    │ Output: After-movement metrics           │
    └────────────────┬─────────────────────────┘
                     │
                     ▼
    ┌──────────────────────────────────────────┐
    │ Calculate After-Movement Metrics         │
    │                                          │
    │ compute_average_metrics()                │
    │ - CHR (should be lower)                  │
    │ - Latency (should be higher)             │
    │ - HopReduction (should be lower)         │
    └────────────────┬─────────────────────────┘
                     │
                     ▼
    ┌──────────────────────────────────────────┐
    │ Calculate & Display Changes              │
    │                                          │
    │ Percentage changes:                      │
    │ - CHR Change: -15.62% (negative ✓)      │
    │ - Latency Change: +60.93% (positive ✓)  │
    │ - HopReduction: -18.54% (negative ✓)    │
    └────────────────┬─────────────────────────┘
                     │
                     ▼
    ┌──────────────────────────────────────────┐
    │ Generate Metric Comparison Plots         │
    │                                          │
    │ plot_before_after_metrics()              │
    │ - Separate plot per metric               │
    │ - Side-by-side bars                      │
    │ - Percentage display                    │
    │                                          │
    │ Output:                                  │
    │ ✓ topology_comparison_chr.png            │
    │ ✓ topology_comparison_latency.png        │
    │ ✓ topology_comparison_hopreduction.png   │
    └────────────────┬─────────────────────────┘
                     │
                     ▼
    ┌──────────────────────────────────────────┐
    │ Generate Time Series Plots               │
    │                                          │
    │ plot_time_series()                       │
    │ - Separate plot per metric               │
    │ - Before & After lines                   │
    │ - Iteration tracking                    │
    │                                          │
    │ Output:                                  │
    │ ✓ timeseries_comparison_cachehitratio.png│
    │ ✓ timeseries_comparison_latency.png      │
    │ ✓ timeseries_comparison_hopreduction.png │
    └────────────────┬─────────────────────────┘
                     │
                     ▼
    ┌──────────────────────────────────────────┐
    │         Analysis Complete ✅             │
    │                                          │
    │ All outputs saved to:                    │
    │ Path_Iterations/plots/                   │
    │                                          │
    │ Total Files Generated: 8                 │
    └──────────────────────────────────────────┘
```

## Data Flow Diagram

```
┌─────────────────────┐
│  Network Objects    │
│ ┌───────────────┐   │
│ │ Routers: 30   │   │
│ │ Publishers: 5 │   │
│ │ Subs: 10      │   │
│ └───────────────┘   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────────────────────┐
│        Original Topology State                   │
│                                                 │
│  Sub1 → Router5        build_network_graph()   │
│  Sub2 → Router12       ─────────────────────>   │
│  Sub3 → Router8                                │
│  ...                                           │
│                                                 │
│  Simulation: baseline_sim_data → baseline_df    │
│  ┌────────────────────────────────────────┐    │
│  │ CHR:        0.7234                     │    │
│  │ Latency:    0.001234                   │    │
│  │ HopReduction: 0.6789                   │    │
│  └────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────┐
│    Random Movement Applied                      │
│                                                 │
│  Sub1: Router5 → Router27                      │
│  Sub2: Router12 → Router4                      │
│  Sub3: Router8 → Router19                      │
│  ...                                           │
│                                                 │
│  mapping = {                                   │
│    'Sub1': ('Router5', 'Router27'),            │
│    ...                                         │
│  }                                             │
└─────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────┐
│        New Topology State                       │
│                                                 │
│  Sub1 → Router27       build_network_graph()   │
│  Sub2 → Router4        ─────────────────────>   │
│  Sub3 → Router19                               │
│  ...                                           │
│                                                 │
│  Simulation: after_sim_data → after_df         │
│  ┌────────────────────────────────────────┐    │
│  │ CHR:        0.6102                     │    │
│  │ Latency:    0.001987                   │    │
│  │ HopReduction: 0.5521                   │    │
│  └────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────┐
│     Comparison & Analysis                       │
│                                                 │
│  CHR:        0.7234 → 0.6102 (-15.62%) ✓       │
│  Latency:    0.001234 → 0.001987 (+60.93%) ✓   │
│  HopReduction: 0.6789 → 0.5521 (-18.54%) ✓     │
│                                                 │
│  All metrics degraded as expected!             │
└─────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────┐
│     Visualization Output                        │
│                                                 │
│  ✓ topology_before.png (8 nodes connected)     │
│  ✓ topology_after.png (8 nodes, different)     │
│  ✓ topology_comparison_chr.png (bar chart)     │
│  ✓ topology_comparison_latency.png             │
│  ✓ topology_comparison_hopreduction.png        │
│  ✓ timeseries_comparison_cachehitratio.png     │
│  ✓ timeseries_comparison_latency.png           │
│  ✓ timeseries_comparison_hopreduction.png      │
└─────────────────────────────────────────────────┘
```

## Class & Function Relationships

```
┌──────────────────────────────────────┐
│      Main Entry Point                │
├──────────────────────────────────────┤
│ run_subscriber_topology_experiment() │
│                                      │
│  ├─ _ensure_network()               │
│  │                                  │
│  ├─ visualize_network_topology()    │
│  │  └─ build_network_graph()        │
│  │     └─ NetworkX Graph            │
│  │                                  │
│  ├─ run_simulation()                │
│  │                                  │
│  ├─ _simulation_to_df()             │
│  │  └─ Pandas DataFrame             │
│  │                                  │
│  ├─ compute_average_metrics()       │
│  │                                  │
│  ├─ move_subscribers_randomly()     │
│  │                                  │
│  ├─ visualize_network_topology()    │
│  │  └─ build_network_graph()        │
│  │                                  │
│  ├─ run_simulation()                │
│  │                                  │
│  ├─ compute_average_metrics()       │
│  │                                  │
│  ├─ plot_before_after_metrics()     │
│  │  └─ Matplotlib Figures (3x)      │
│  │                                  │
│  └─ plot_time_series()              │
│     └─ Matplotlib Figures (3x)      │
└──────────────────────────────────────┘
```

## Plot Dependency Graph

```
Simulation Data (Before)
        │
        ├─ _simulation_to_df() ──────────> Baseline DataFrame
        │                                         │
        ├─ compute_average_metrics() ───────────>│ Before Metrics
        │                                        │
        └──────────────────────────┐             │
                                   │             │
                                   ▼             ▼
                          plot_before_after_metrics()
                              │
                    ┌─────────┼─────────┐
                    ▼         ▼         ▼
               CHR Plot  Latency Plot  HopReduction Plot

Simulation Data (After)
        │
        ├─ _simulation_to_df() ──────────> After DataFrame
        │                                      │
        ├─ compute_average_metrics() ────────>│ After Metrics
        │                                     │
        └──────────────────────┐              │
                               │              │
                               ▼              ▼
                      plot_time_series()
                           │
                ┌──────────┼──────────┐
                ▼          ▼          ▼
          CHR TimeSeries  Latency     HopReduction
          Plot            TimeSeries  TimeSeries Plot
                          Plot
```

## File I/O Structure

```
Python Script Execution
        │
        ├─ Read: Saved_Network/network_setup.pkl
        │
        ├─ Write: Path_Iterations/plots/topology_before.png
        │
        ├─ Write: Path_Iterations/plots/topology_after.png
        │
        ├─ Write: Path_Iterations/plots/topology_comparison_chr.png
        │
        ├─ Write: Path_Iterations/plots/topology_comparison_latency.png
        │
        ├─ Write: Path_Iterations/plots/topology_comparison_hopreduction.png
        │
        ├─ Write: Path_Iterations/plots/timeseries_comparison_cachehitratio.png
        │
        ├─ Write: Path_Iterations/plots/timeseries_comparison_latency.png
        │
        └─ Write: Path_Iterations/plots/timeseries_comparison_hopreduction.png
```

## Component Interaction

```
┌──────────────────────┐
│   NetworkX Library   │
│  (Graph Building)    │
└────────┬─────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│    build_network_graph()               │
│  - Add Router Nodes                    │
│  - Add Publisher Nodes                 │
│  - Add Subscriber Nodes                │
│  - Add Routing Edges                   │
│  - Add Connection Edges                │
│                                        │
│  Returns: nx.Graph object              │
└────────┬─────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│    visualize_network_topology()        │
│  - Spring Layout Algorithm             │
│  - Separate nodes by type              │
│  - Color nodes by type                 │
│  - Draw edges by type                  │
│  - Add labels                          │
│  - Save to PNG                         │
└────────┬─────────────────────────────┘
         │
         ▼
   PNG Image Files
(topology_before.png, etc)
```

## Memory & Performance

```
Network Size: 30 routers, 5 publishers, 10 subscribers

Memory Allocation:
├─ Network Objects: ~5-10MB
├─ Simulation Data: ~20-30MB
├─ NetworkX Graphs: ~2-5MB (per graph)
├─ DataFrames: ~10-15MB (per iteration)
├─ PNG Files: ~100-200KB each
│
└─ Total: ~100-250MB

Execution Timeline:
├─ Network Load: 1-2 seconds
├─ Baseline Simulation: 60-90 seconds
├─ Subscriber Movement: 0.1 seconds
├─ After Simulation: 60-90 seconds
├─ Topology Visualization: 5-10 seconds each
├─ Metric Plots: 2-3 seconds each
│
└─ Total Runtime: 3-5 minutes
```

## Error Handling Flow

```
run_subscriber_topology_experiment()
        │
        ├─ _ensure_network()
        │  └─ If no saved network, call setup_network()
        │
        ├─ move_subscribers_randomly()
        │  ├─ Check empty lists
        │  ├─ Handle missing router attribute
        │  └─ Return mapping
        │
        ├─ build_network_graph()
        │  ├─ Handle missing FIB
        │  ├─ Handle missing attributes
        │  └─ Create edges safely
        │
        ├─ visualize_network_topology()
        │  ├─ Create output directory
        │  ├─ Generate layout
        │  └─ Save PNG
        │
        └─ plot_before_after_metrics()
           ├─ Create output directory
           ├─ Validate dataframes
           └─ Generate and save plots
```

This architecture ensures:
✅ Modularity
✅ Reusability
✅ Extensibility
✅ Error Handling
✅ Clear Data Flow
