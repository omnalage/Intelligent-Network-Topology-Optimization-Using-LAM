# Quick Reference: Running Subscriber Topology Impact Analysis

## One-Liner to Run

```python
python subscriber_topology_impact.py
```

## What Happens

1. ✓ Loads your existing network (or creates new one)
2. ✓ Runs baseline simulation with original subscriber positions
3. ✓ **Randomly moves all subscribers** to different routers
4. ✓ Runs simulation again with new topology
5. ✓ Compares metrics and generates visualizations

## Generated Outputs (in `Path_Iterations/plots/`)

### Network Topology Graphs

- `topology_before.png` - Visual network layout BEFORE changes
- `topology_after.png` - Visual network layout AFTER changes

### Metric Comparison Charts (each metric in separate plot)

- `topology_comparison_chr.png` - Cache Hit Ratio
- `topology_comparison_latency.png` - Latency
- `topology_comparison_hopreduction.png` - Hop Reduction

### Performance Over Time

- `timeseries_comparison_cachehitratio.png` - CHR iteration by iteration
- `timeseries_comparison_latency.png` - Latency iteration by iteration
- `timeseries_comparison_hopreduction.png` - Hop Reduction iteration by iteration

## Expected Performance Degradation

When subscribers move to random (suboptimal) positions:

```
📊 Metric Changes
├── Cache Hit Ratio:    ↓ Should DECREASE (-X%)
├── Latency:            ↑ Should INCREASE (+X%)
└── Hop Reduction:      ↓ Should DECREASE (-X%)
```

## File Structure After Running

```
Path_Iterations/plots/
├── topology_before.png                          ← Network visualization BEFORE
├── topology_after.png                           ← Network visualization AFTER
├── topology_comparison_chr.png                  ← CHR metric comparison
├── topology_comparison_latency.png              ← Latency metric comparison
├── topology_comparison_hopreduction.png         ← Hop Reduction metric comparison
├── timeseries_comparison_cachehitratio.png      ← CHR over iterations
├── timeseries_comparison_latency.png            ← Latency over iterations
└── timeseries_comparison_hopreduction.png       ← Hop Reduction over iterations
```

## Interpreting the Results

### Topology Visualization

- **Blue Squares**: Routers (core network)
- **Green Circles**: Publishers (content sources)
- **Red Triangles**: Subscribers (clients)
- **Connections**: Show how subscribers attach to routers

### Metric Comparison Plots

- **Blue Bar**: Performance before topology change
- **Red Bar**: Performance after topology change
- **Percentage**: Shows % change (negative = worse, positive = better/worse depending on metric)

### Time Series Plots

- **Blue Line**: Original topology performance across iterations
- **Red Dashed Line**: New topology performance across iterations
- **Direction Arrow**: Indicates whether metric going up/down is good

## Customization

To run with different parameters, modify the last line:

```python
# In subscriber_topology_impact.py, main() section:
results = run_subscriber_topology_experiment(
    policy="LRU",        # Change caching policy
    iterations=1000      # Change number of iterations
)
```

## Supported Policies

- FACR (default)
- LRU
- FIFO
- Random
- Others defined in main.py

## Key Functions

| Function                               | Purpose                                            |
| -------------------------------------- | -------------------------------------------------- |
| `move_subscribers_randomly()`          | Randomly reassign subscribers to different routers |
| `visualize_network_topology()`         | Draw network topology graph                        |
| `plot_before_after_metrics()`          | Create separate comparison plots for each metric   |
| `plot_time_series()`                   | Create time-series evolution plots                 |
| `run_subscriber_topology_experiment()` | Run complete experiment pipeline                   |

## Troubleshooting

| Problem               | Solution                                                      |
| --------------------- | ------------------------------------------------------------- |
| No network found      | Run `main.py` first                                           |
| Plots look cluttered  | Network is large; adjust `figsize` in visualization functions |
| Metrics not degrading | Check console output to verify subscribers are moving         |
| Import error          | Ensure `networkx` is installed: `pip install networkx`        |

## Example Console Output

```
================================================================================
SUBSCRIBER TOPOLOGY IMPACT ANALYSIS
================================================================================
[subscriber_topology_impact] Loaded existing network (30 routers, 5 publishers, 10 subscribers)
[subscriber_topology_impact] Original subscriber->router mapping:
  Subscriber1 -> Router5
  Subscriber2 -> Router12
  ...

[subscriber_topology_impact] Creating network topology visualization (BEFORE)...
[subscriber_topology_impact] Saved topology visualization to: Path_Iterations/plots/topology_before.png

[subscriber_topology_impact] Running baseline simulation (original topology)...
[subscriber_topology_impact] Baseline averages (policy=FACR): CHR=0.7234, Latency=0.001234, HopReduction=0.6789

[subscriber_topology_impact] Randomly moving ALL subscribers to new router positions...
[subscriber_topology_impact] New subscriber->router mapping:
  Subscriber1: Router5 -> Router18
  Subscriber2: Router12 -> Router8
  ...

[subscriber_topology_impact] Creating network topology visualization (AFTER)...
[subscriber_topology_impact] Saved topology visualization to: Path_Iterations/plots/topology_after.png

[subscriber_topology_impact] Running simulation AFTER subscriber-topology change...
[subscriber_topology_impact] After-change averages (policy=FACR): CHR=0.6102, Latency=0.001987, HopReduction=0.5521

[subscriber_topology_impact] Metric Changes:
  CHR Change: -15.62% (should be negative for worse performance)
  Latency Change: +60.93% (should be positive for worse performance)
  Hop Reduction Change: -18.54% (should be negative for worse performance)

[subscriber_topology_impact] Creating metric comparison plots...
[subscriber_topology_impact] Saved Cache Hit Ratio comparison plot to: Path_Iterations/plots/topology_comparison_chr.png
[subscriber_topology_impact] Saved Latency comparison plot to: Path_Iterations/plots/topology_comparison_latency.png
[subscriber_topology_impact] Saved Hop Reduction comparison plot to: Path_Iterations/plots/topology_comparison_hopreduction.png

[subscriber_topology_impact] Experiment complete.
Check 'Path_Iterations/plots/' for comparison figures.
```

## Next Steps

1. ✅ Run the script
2. 📊 View generated plots in `Path_Iterations/plots/`
3. 📈 Analyze topology changes and metric impacts
4. 🔄 Compare different policies by changing `policy` parameter
5. 📝 Document findings in your project report
