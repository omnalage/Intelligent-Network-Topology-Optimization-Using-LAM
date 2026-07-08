# Expected Output & Visual Guide

## Console Output Example

When you run `python subscriber_topology_impact.py`, you should see:

```
================================================================================
SUBSCRIBER TOPOLOGY IMPACT ANALYSIS
================================================================================
[subscriber_topology_impact] Loaded existing network (30 routers, 5 publishers, 10 subscribers)
[subscriber_topology_impact] Original subscriber->router mapping:
  Subscriber1 -> Router5
  Subscriber2 -> Router12
  Subscriber3 -> Router8
  Subscriber4 -> Router3
  Subscriber5 -> Router15
  Subscriber6 -> Router22
  Subscriber7 -> Router18
  Subscriber8 -> Router9
  Subscriber9 -> Router25
  Subscriber10 -> Router2

[subscriber_topology_impact] Creating network topology visualization (BEFORE)...
[subscriber_topology_impact] Saved topology visualization to: Path_Iterations/plots/topology_before.png

[subscriber_topology_impact] Running baseline simulation (original topology)...
[subscriber_topology_impact] Baseline averages (policy=FACR): CHR=0.7234, Latency=0.001234, HopReduction=0.6789

[subscriber_topology_impact] Randomly moving ALL subscribers to new router positions...
[subscriber_topology_impact] New subscriber->router mapping:
  Subscriber1: Router5 -> Router27
  Subscriber2: Router12 -> Router4
  Subscriber3: Router8 -> Router19
  Subscriber4: Router3 -> Router11
  Subscriber5: Router15 -> Router28
  Subscriber6: Router22 -> Router6
  Subscriber7: Router18 -> Router14
  Subscriber8: Router9 -> Router26
  Subscriber9: Router25 -> Router1
  Subscriber10: Router2 -> Router23

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
[subscriber_topology_impact] Saved Cache Hit Ratio time-series plot to: Path_Iterations/plots/timeseries_comparison_cachehitratio.png
[subscriber_topology_impact] Saved Latency time-series plot to: Path_Iterations/plots/timeseries_comparison_latency.png
[subscriber_topology_impact] Saved Hop Reduction time-series plot to: Path_Iterations/plots/timeseries_comparison_hopreduction.png

[subscriber_topology_impact] Experiment complete.
[subscriber_topology_impact] Before metrics: {'CHR': 0.7234, 'Latency': 0.001234, 'HopReduction': 0.6789}
[subscriber_topology_impact] After metrics: {'CHR': 0.6102, 'Latency': 0.001987, 'HopReduction': 0.5521}
Check 'Path_Iterations/plots/' for comparison figures.
```

## Generated Visualizations

### 1. Topology Visualization - BEFORE

**File**: `topology_before.png`

```
Visual representation showing:
  • Blue Squares: 30 Routers (core network)
  • Green Circles: 5 Publishers (content sources)
  • Red Triangles: 10 Subscribers (clients)

Network Layout:
- Publishers connected to specific routers (green dashed lines)
- Subscribers attached to their current routers (red dashed lines)
- Router-to-router connections visible (gray solid lines)
- Spring layout creates logical clustering

This is the OPTIMAL topology where subscribers are close to content.
```

### 2. Topology Visualization - AFTER

**File**: `topology_after.png`

```
Same network structure but:
  • Subscribers are now connected to DIFFERENT routers
  • Overall network layout may appear more scattered
  • Subscriber connections (red dashed lines) point to different routers

This creates a SUBOPTIMAL topology where subscribers are farther from content.
```

### 3. Cache Hit Ratio Comparison

**File**: `topology_comparison_chr.png`

```
┌─────────────────────────────────────────────┐
│  Cache Hit Ratio (CHR) Comparison           │
│  (↑ Higher is Better)                       │
├─────────────────────────────────────────────┤
│                                             │
│  0.75 │     ┌─────┐                        │
│       │     │0.7234                        │
│  0.70 │     ├─────┤                        │
│       │     │     │  ┌─────┐               │
│  0.65 │     │     │  │0.6102              │
│       │     │     │  ├─────┤               │
│  0.60 │     │     │  │     │               │
│       │     │     │  │     │               │
│       ├─────┼─────┼──┼─────┼────────────   │
│     Before After                           │
│   (Original) (Subscriber Moved)            │
│                                             │
│              Change: -15.62%               │
│              (Performance Degraded)        │
└─────────────────────────────────────────────┘
```

**What This Shows**:

- Before: 72.34% cache hit ratio (good performance)
- After: 61.02% cache hit ratio (worse performance)
- Change: -15.62% (11.32 percentage points decrease)

### 4. Latency Comparison

**File**: `topology_comparison_latency.png`

```
┌──────────────────────────────────────┐
│  Latency (ms) Comparison             │
│  (↓ Lower is Better)                 │
├──────────────────────────────────────┤
│                                      │
│  0.0025 │              ┌─────┐      │
│         │              │0.001987    │
│  0.0020 │     ┌─────┐  ├─────┤      │
│         │     │0.001234 │     │      │
│  0.0015 │     ├─────┤  │     │      │
│         │     │     │  │     │      │
│  0.0010 │     │     │  │     │      │
│         │     │     │  │     │      │
│       ├─┼─────┼─────┼──┼─────┼──    │
│     Before After                    │
│   (Original) (Subscriber Moved)     │
│                                      │
│              Change: +60.93%        │
│              (Performance Worsened) │
└──────────────────────────────────────┘
```

**What This Shows**:

- Before: 0.001234 ms latency (good)
- After: 0.001987 ms latency (worse)
- Change: +60.93% (0.000753 ms increase)

### 5. Hop Reduction Comparison

**File**: `topology_comparison_hopreduction.png`

```
┌──────────────────────────────────────┐
│  Hop Reduction Ratio Comparison      │
│  (↑ Higher is Better)                │
├──────────────────────────────────────┤
│                                      │
│  0.70 │     ┌─────┐                 │
│       │     │0.6789                 │
│  0.65 │     ├─────┤                 │
│       │     │     │  ┌─────┐        │
│  0.60 │     │     │  │0.5521       │
│       │     │     │  ├─────┤        │
│  0.55 │     │     │  │     │        │
│       │     │     │  │     │        │
│       ├─────┼─────┼──┼─────┼────    │
│     Before After                    │
│   (Original) (Subscriber Moved)     │
│                                      │
│              Change: -18.54%        │
│              (Performance Degraded) │
└──────────────────────────────────────┘
```

**What This Shows**:

- Before: 67.89% hop reduction (good)
- After: 55.21% hop reduction (worse)
- Change: -18.54% decrease

### 6. Time Series - Cache Hit Ratio Over Iterations

**File**: `timeseries_comparison_cachehitratio.png`

```
CHR: 0.75│                ┌──────────  ← After (new topology)
        │               ╱
        │              ╱
     0.70│            ╱  ┌────────── ← Before (original)
        │           ╱   ╱
        │          ╱   ╱
     0.65│        ╱   ╱
        │       ╱   ╱
        │      ╱───╱
     0.60│    ╱   ╱
        │   ╱   ╱
     0.55│──────
        └─────────────────────────────→ Iteration
          0    100    200   300   400  500
```

**What This Shows**:

- Blue line: Original topology (CHR ~0.72)
- Red dashed line: New topology (CHR ~0.61)
- Both stabilize after ~50-100 iterations
- Consistent degradation maintained throughout

### 7. Time Series - Latency Over Iterations

**File**: `timeseries_comparison_latency.png`

```
Latency │ After (new)  ┌──────────
(ms)    │            ╱╱
        │          ╱╱
 0.002  │────╱────╱   ← Higher latency
        │  ╱    ╱
        │╱╱    ╱   ┌─────── ← Before (original)
 0.001  │    ╱    ╱
        │   ╱    ╱
        │  ╱    ╱
 0.000  │─────────
        └──────────────────→ Iteration
          0    100   200  300  400  500
```

**What This Shows**:

- Blue line: Original topology (lower latency ~0.0012 ms)
- Red dashed line: New topology (higher latency ~0.002 ms)
- Latency increases and stabilizes at higher level
- Consistent degradation throughout simulation

### 8. Time Series - Hop Reduction Over Iterations

**File**: `timeseries_comparison_hopreduction.png`

```
Hop     │     Before (original) ─────
Reduction│  ╱                    0.68
        │╱
     0.7│───
        │
        │  After (new topology)
     0.6│ ╱╱╱╱────────────────
        │╱                   0.55
     0.5│
        │
        │
     0.4│
        └──────────────────────→ Iteration
          0    100   200  300  400  500
```

**What This Shows**:

- Blue line: Original topology (hop reduction ~0.68)
- Red dashed line: New topology (hop reduction ~0.55)
- Both reach steady state quickly
- New topology maintains lower hop reduction

## Key Observations

### Metric Degradation Pattern

```
BEFORE (Original Topology):
├── CHR: 72.34% ✓ Good
├── Latency: 0.001234 ms ✓ Good
└── HopReduction: 67.89% ✓ Good

AFTER (Random Subscriber Movement):
├── CHR: 61.02% ✗ Worse (-15.62%)
├── Latency: 0.001987 ms ✗ Worse (+60.93%)
└── HopReduction: 55.21% ✗ Worse (-18.54%)
```

### Why Metrics Degraded

1. **Lower CHR**: Subscribers moved away from caches → fewer cache hits
2. **Higher Latency**: Longer paths to content → increased latency
3. **Lower HopReduction**: Less optimal routing due to new topology

### Performance Impact Summary

The random subscriber movement created a **demonstrably worse topology**:

- Network performance declined across all metrics
- Percentage changes are consistent with expectations
- Visual topology changes clearly show subscriber repositioning

## Success Criteria

✅ All of these should be TRUE:

- [ ] `topology_before.png` shows original subscriber positions
- [ ] `topology_after.png` shows different subscriber positions
- [ ] CHR decreased (negative change %)
- [ ] Latency increased (positive change %)
- [ ] Hop Reduction decreased (negative change %)
- [ ] All 3 metric comparison plots generated
- [ ] All 3 time-series plots generated
- [ ] Console shows metric changes with calculations

## Troubleshooting Output

### Issue: Metrics Not Degrading

**Check Console Output**:

```
Should see something like:
✗ CHR Change: -15.62% (should be negative for worse performance)
✗ Latency Change: +60.93% (should be positive for worse performance)
✗ Hop Reduction Change: -18.54% (should be negative for worse performance)
```

If metrics aren't degrading, verify:

1. Subscribers were actually moved (check mapping in console)
2. Simulation ran correctly (check CHR/Latency/HopReduction values)
3. Network has sufficient routers for random movement

### Issue: No Visualization Differences

Check if:

1. Network is large enough (30+ routers recommended)
2. Spring layout parameters are appropriate
3. Figure size is adequate (14x10 default)

### Issue: Empty Plots

Make sure:

1. Simulations completed successfully
2. Data frames have values (check console for averages)
3. Output directory `Path_Iterations/plots/` was created
