# Subscriber Topology Impact Analysis - Updated Implementation

## Overview

The updated `subscriber_topology_impact.py` script performs a comprehensive analysis of how randomly moving subscribers to different routers impacts network performance metrics.

## Key Features

### 1. **Random Subscriber Movement**

- **Function**: `move_subscribers_randomly()`
- Randomly reassigns subscribers to different routers (instead of deterministic round-robin)
- Creates a more realistic "suboptimal" topology that naturally degrades performance
- Returns mapping of old → new router assignments

### 2. **Network Topology Visualization**

- **Function**: `visualize_network_topology()`
- Visualizes complete network topology with:
  - **Routers** (blue squares)
  - **Publishers** (green circles)
  - **Subscribers** (red triangles)
- Different edge types shown:
  - Gray solid lines: Router-to-router connections
  - Green dashed lines: Publisher connections
  - Red dashed lines: Subscriber connections
- Uses spring layout algorithm for optimal node positioning
- Creates two visualizations:
  - `topology_before.png`: Original network topology
  - `topology_after.png`: Network topology after subscriber movement

### 3. **Separate Metric Comparison Plots**

Each metric gets its own dedicated comparison chart:

#### **Cache Hit Ratio (CHR) Comparison**

- `topology_comparison_chr.png`
- Shows before/after CHR values as side-by-side bars
- Includes percentage change annotation
- Direction: Higher is Better ↑

#### **Latency Comparison**

- `topology_comparison_latency.png`
- Shows before/after latency values
- Includes percentage change annotation
- Direction: Lower is Better ↓

#### **Hop Reduction Ratio Comparison**

- `topology_comparison_hopreduction.png`
- Shows before/after hop reduction values
- Includes percentage change annotation
- Direction: Higher is Better ↑

### 4. **Time Series Analysis**

Separate time-series plots for each metric showing performance evolution:

- `timeseries_comparison_cachehitratio.png`
- `timeseries_comparison_latency.png`
- `timeseries_comparison_hopreduction.png`

Each plot displays:

- Before (original topology) line in blue
- After (subscriber moved) line in red
- Iteration-by-iteration performance tracking
- Direction indicator (higher/lower is better)

## Expected Results

When subscribers are randomly moved to suboptimal positions:

| Metric                    | Expected Change | Reason                                     |
| ------------------------- | --------------- | ------------------------------------------ |
| **Cache Hit Ratio (CHR)** | ↓ Decrease      | Subscribers farther from content caches    |
| **Latency**               | ↑ Increase      | Longer paths to reach content              |
| **Hop Reduction**         | ↓ Decrease      | Less efficient routing due to new topology |

## Usage

### Basic Usage

```python
python subscriber_topology_impact.py
```

### Custom Configuration

```python
# In the main() function or modify the file:
results = run_subscriber_topology_experiment(policy="FACR", iterations=500)
```

### Parameters

- **policy**: Caching policy to use (e.g., "FACR", "LRU", "FIFO")
- **iterations**: Number of simulation iterations (default: 500)

## Output Files

All outputs are saved to `Path_Iterations/plots/`:

### Topology Visualizations

- `topology_before.png` - Network topology before subscriber movement
- `topology_after.png` - Network topology after subscriber movement

### Metric Comparisons

- `topology_comparison_chr.png` - Cache Hit Ratio before/after
- `topology_comparison_latency.png` - Latency before/after
- `topology_comparison_hopreduction.png` - Hop Reduction before/after

### Time Series Analysis

- `timeseries_comparison_cachehitratio.png` - CHR over iterations
- `timeseries_comparison_latency.png` - Latency over iterations
- `timeseries_comparison_hopreduction.png` - Hop Reduction over iterations

## Console Output

The script provides detailed logging:

```
[subscriber_topology_impact] Loaded existing network (30 routers, 5 publishers, 10 subscribers)
[subscriber_topology_impact] Original subscriber->router mapping:
  Subscriber1 -> Router5
  ...
[subscriber_topology_impact] Running baseline simulation (original topology)...
[subscriber_topology_impact] Baseline averages (policy=FACR): CHR=0.7234, Latency=0.001234, HopReduction=0.6789
[subscriber_topology_impact] Randomly moving ALL subscribers to new router positions...
[subscriber_topology_impact] Metric Changes:
  CHR Change: -15.43% (should be negative for worse performance)
  Latency Change: +22.15% (should be positive for worse performance)
  Hop Reduction Change: -18.76% (should be negative for worse performance)
```

## Technical Details

### Network Graph Structure

- Built using NetworkX library
- Nodes: Routers, Publishers, Subscribers
- Edges: Connections and routing paths
- Attributes: Node types and edge types for visualization

### Metrics Calculation

- **CHR**: Average Cache Hit Ratio from all iterations
- **Latency**: Average latency (milliseconds) from all iterations
- **Hop Reduction**: Average hop reduction ratio from all iterations

### Visualization Libraries

- **matplotlib**: Plotting and chart generation
- **networkx**: Network topology representation and visualization
- **pandas**: Data manipulation and analysis

## Integration with Main Project

The script integrates with the main project:

- Uses `load_network()` to load existing network topology
- Uses `setup_network()` if no saved network exists
- Uses `run_simulation()` to execute simulations
- Compatible with all caching policies defined in `main.py`

## Advantages Over Previous Implementation

1. **Random Movement**: More realistic topology changes vs. deterministic round-robin
2. **Separate Metric Plots**: Easier to analyze individual metric impacts
3. **Network Visualization**: Visual representation of topology changes
4. **Better Logging**: Detailed console output with percentage changes
5. **Improved Time Series**: Individual plots per metric with clearer presentation
6. **NetworkX Integration**: Proper graph-based topology representation

## Troubleshooting

### Issue: No saved network found

- Run `main.py` first to create the network
- The script will automatically call `setup_network()` if needed

### Issue: Metrics not showing expected degradation

- Ensure subscribers are actually being moved (check console output)
- Check that the simulation is using the correct policy
- Verify network has sufficient routers and subscribers

### Issue: Visualization not showing all connections

- Spring layout may need adjustment (modify `k` and `iterations` parameters in `visualize_network_topology()`)
- Increase figure size for better clarity
