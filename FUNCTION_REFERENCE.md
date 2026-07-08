# Quick Reference: Exact Function Signatures & Locations

## File Locations & Key Functions

### 1. Simulator Functions (main.py)

#### Setup Network

```python
Location: main.py:L398-L437
Function: setup_network()
Signature: () -> Tuple[List[Router], List[Publisher], List[Subscriber]]
Returns: (routers, publishers, subscribers)
User prompt: Interactive - asks for num_routers, num_subscribers
Output file: Saved_Network/network_setup.pkl
```

#### Load Saved Network

```python
Location: main.py:L379-L388
Function: load_network()
Signature: () -> Tuple[List[Router], List[Publisher], List[Subscriber]]
Returns: (routers, publishers, subscribers)
Reads: Saved_Network/network_setup.pkl
```

#### Run Main Simulation Loop

```python
Location: main.py:L501-L599
Function: run_simulation(routers, publishers, subscribers, policy, iterations, model=None)

Parameters:
  routers: List[Router]
  publishers: List[Publisher]
  subscribers: List[Subscriber]
  policy: str in {'LRU', 'LFU', 'FIFO', 'MRU', 'FACR', 'Rdm', 'RandomForest'}
  iterations: int (number of simulation steps)
  model: Optional RandomForestClassifier

Returns: List[List]
  Each row: [timestamp_str, num_active_subscribers, total_requests,
             hop_reduction_ratio, avg_cache_hit_ratio, avg_latency]

Router metrics updated:
  - router.cache_hits (int)
  - router.total_requests (int)
  - router.total_cache_access_time (float)
  - router.cache_frequency (defaultdict)
  - router.cache_access_times (dict)
  - router.cs (list of cached content)
  - router.popularity_table (DataFrame)
  - router.pit (interest table)
```

#### Compute Centrality Measures

```python
Location: main.py:L920-L1010
Function: plot_centrality_measures(routers, save_path=None, show_plot=True)

Parameters:
  routers: List[Router]
  save_path: Optional[str] (currently unused, always saves to Graphs/Centrality/)
  show_plot: bool (whether to display plots)

Returns: None (saves CSVs and PNGs)

Output files:
  - Graphs/Centrality/results.csv (main: Router, Closeness, Reach_raw, Reach_norm, Degree, Betweenness, CMBA)
  - Graphs/Centrality/closeness.csv
  - Graphs/Centrality/reach.csv
  - Graphs/Centrality/degree.csv
  - Graphs/Centrality/betweenness.csv
  - Graphs/Centrality/cmba.csv
  - Graphs/Centrality/*.png (bar charts for each measure)

Key: Sets router.CMBA (if accessible) or adds to external tracking
```

#### Save Iteration Router Metrics

```python
Location: main.py:L1615-L1682
Function: save_iteration_router_metrics(routers, iteration: int, path_label: str = "default_path")

Parameters:
  routers: List[Router]
  iteration: int (episode/iteration number)
  path_label: str (used for CSV filename)

Returns: str (output filename)

Output file:
  Path_Iterations/{path_label.replace(' ','_')}_router_iteration_metrics.csv
  Columns: [iteration, Router, CacheOccupancy, CacheOccupancyPct, CHR, Latency_ms]
```

#### Plot Network Topology

```python
Location: main.py:L1000-L1030
Function: plot_network_graph(routers, publishers, subscribers, out_path: str = None)

Parameters:
  routers: List[Router]
  publishers: List[Publisher]
  subscribers: List[Subscriber]
  out_path: Optional[str] (where to save PNG)

Returns: None (displays and saves plot)

Output: PNG file (if out_path provided)
Uses: NetworkX spring layout, colors nodes by type
```

#### Main Entry Function

```python
Location: main.py:L1647-L1682
Function: main()

Parameters: None (interactive)

Behavior:
  1. Calls setup_network() or loads existing
  2. Plots topology
  3. Asks for number of iterations
  4. Loads RandomForest model
  5. Runs run_simulation() for each policy
  6. Saves all results
  7. Computes centrality measures
```

---

### 2. RL Environment Functions (rl_env.py)

#### Create RL Environment

```python
Location: rl_env.py:L20-L34
Class: CacheEnvironment

Constructor: __init__(self, routers: List[Any], episode_length: int = 100,
                     w1: float = 0.25, w2: float = 0.25,
                     w3: float = 0.25, w4: float = 0.25)

Parameters:
  routers: List of Router objects (must have: name, cs, cache_hits, total_requests, ttl, CMBA)
  episode_length: Max steps per episode before done=True
  w1, w2, w3, w4: Reward weights (CHR, CMBA, -latency, -occupancy)

Key attributes:
  - self.routers: reference to router list
  - self._step_count: tracks steps in current episode
```

#### Reset Environment

```python
Location: rl_env.py:L36-L39
Method: CacheEnvironment.reset()

Returns: np.ndarray (initial state)
  Shape: (num_routers * 6,)
  Contents: Normalized metrics for all routers

Side effects:
  - Resets _step_count to 0
  - Calls _get_state() to compute initial state
```

#### Step Environment

```python
Location: rl_env.py:L41-L85
Method: CacheEnvironment.step(action: int)

Parameters:
  action: int (router index 0 to len(routers)-1)

Returns: Tuple[np.ndarray, float, bool, Dict]
  next_state: np.ndarray (normalized metrics)
  reward: float (computed from formula)
  done: bool (whether episode finished)
  info: Dict containing:
    - selected_router_index: int
    - selected_router_name: str
    - metrics: Dict with chr, latency_ms, cache_occupancy, cmba
    - reward_components: Dict with component breakdown
    - formula: str (reward calculation formula)

Reward formula:
  reward = w1 * CHR_norm + w2 * CMBA_norm - w3 * latency_norm - w4 * occ_norm
  (all components clipped to [0, 1])
```

#### Collect Router Metrics

```python
Location: rl_env.py:L139-L187 (called from step)
Method: CacheEnvironment._collect_router_metrics()

Returns: List[RouterMetrics]
  @dataclass RouterMetrics:
    - name: str
    - cache_occupancy: float (len(router.cs))
    - chr_value: float (cache_hits / total_requests)
    - latency_ms: float ((total_cache_access_time / total_requests) * 1000)
    - cmba: float
    - global_avg_chr: float (network average)
    - global_avg_latency: float (network average)

Computation:
  1. For each router, read: cs, cache_hits, total_requests, total_cache_access_time
  2. Compute CHR and latency from raw metrics
  3. Compute global averages
  4. Return all metrics
```

#### Get State Vector

```python
Location: rl_env.py:L87-L136
Method: CacheEnvironment._get_state()

Returns: np.ndarray of shape (num_routers * 6,)

State vector format (per router):
  [occ_norm, chr_norm, lat_norm, cmba_norm, global_chr_norm, global_lat_norm, ...]

Normalization:
  - Each feature normalized to [0, 1] min-max across all routers
  - If max == min (all same), return 0.0 for all
```

---

### 3. DQN Agent Functions (dqn_agent.py)

#### Create DQN Agent

```python
Location: dqn_agent.py:L95-L145
Class: DQNAgent

Constructor: __init__(self, state_size: int, action_size: int,
                     lr: float = 1e-3, gamma: float = 0.99,
                     epsilon_start: float = 1.0, epsilon_end: float = 0.05,
                     epsilon_decay: float = 0.995, buffer_capacity: int = 10000,
                     batch_size: int = 64, target_update_freq: int = 100,
                     device: str | None = None)

Parameters:
  state_size: int (total features = num_routers * 6 for our environment)
  action_size: int (number of routers, i.e., num_routers)
  lr: float (learning rate for Adam optimizer)
  gamma: float (discount factor)
  epsilon_start: float (initial exploration rate)
  epsilon_end: float (final exploration rate)
  epsilon_decay: float (decay per step)
  buffer_capacity: int (replay buffer size)
  batch_size: int (batch for training)
  target_update_freq: int (steps between copying Q to target Q)
  device: str (cuda/cpu, auto-detected if None)

Key attributes:
  - self.q_network: Main Q-network (PyTorch nn.Module)
  - self.target_network: Target Q-network (for stability)
  - self.replay_buffer: Experience replay buffer
  - self.epsilon: Current exploration rate
  - self.device: torch device
```

#### Select Action

```python
Location: dqn_agent.py:L147-xxx (see full file)
Method: DQNAgent.select_action(state: np.ndarray, training: bool = True)

Parameters:
  state: np.ndarray (output from env._get_state())
  training: bool (if False, acts deterministically; if True, epsilon-greedy)

Returns: int (action/router index)

Behavior:
  if training:
    - With probability epsilon: random action
    - Else: greedy action (argmax Q-value)
  else:
    - Always greedy action
```

#### Store Transition

```python
Location: dqn_agent.py:xxx
Method: DQNAgent.store_transition(state, action, reward, next_state, done)

Parameters:
  state: np.ndarray
  action: int
  reward: float
  next_state: np.ndarray
  done: bool

Returns: None

Side effects:
  - Appends to self.replay_buffer
```

#### Train Step

```python
Location: dqn_agent.py:xxx
Method: DQNAgent.train_step()

Returns: float (loss value, or 0.0 if buffer not ready)

Behavior:
  1. If buffer size < batch_size: return 0.0 (wait for data)
  2. Sample batch from replay_buffer
  3. Compute Q-targets using target_network
  4. Compute loss vs Q-network
  5. Backprop and update Q-network
  6. Every target_update_freq steps: copy Q-network to target_network
  7. Decay epsilon
  8. Return loss
```

---

### 4. Training Loop Functions (trainer.py)

#### Train Agent

```python
Location: trainer.py:L31-L150+
Function: train_agent(environment, agent, episodes, iterations, out_dir="Path_Iterations")

Parameters:
  environment: CacheEnvironment instance
  agent: DQNAgent instance
  episodes: int (number of episodes)
  iterations: int (max iterations per episode)
  out_dir: str (output directory for logs)

Returns: Dict[str, str/pd.DataFrame]
  - 'rewards_df': DataFrame of all rewards
  - 'selections_df': DataFrame of router selections
  - 'episode_summary_df': DataFrame of episode summaries
  - 'rewards_csv': path to rewards CSV
  - 'selections_csv': path to selections CSV
  - 'summary_csv': path to summary CSV

Behavior:
  1. For each episode:
     a. Reset environment
     b. For each iteration:
        i. Agent selects action
        ii. Environment steps and returns reward
        iii. Agent stores experience and trains
        iv. Log metrics
     c. Save episode summary
  2. Generate plots and statistics
  3. Save all logs to CSVs

Output files (in Path_Iterations/):
  - training_reward_log_*.csv
  - training_selection_log_*.csv
  - training_summary_log_*.csv
```

---

### 5. Data Flow Summary

```
main.setup_network()
        ↓
    routers, publishers, subscribers
        ↓
main.run_simulation()  [updates router metrics]
        ↓
    simulation_data (list of iterations)
        ↓
main.plot_centrality_measures()
        ↓
    CMBA scores computed
        ↓
CacheEnvironment(routers=routers)
        ↓
    env.reset() → initial_state
        ↓
    for iteration:
        agent.select_action(state) → action
            ↓
        env.step(action)
            ↓
        env._collect_router_metrics()  [reads current router state]
            ↓
        computes reward from selected router metrics
            ↓
        agent.store_transition() and agent.train_step()

(repeat)
```

---

## Critical Metric Definitions

### Cache Hit Ratio (CHR)

```
CHR = cache_hits / total_requests
Location computed: rl_env.py:L174
Value range: [0, 1]
Higher is better
```

### Latency

```
latency_ms = (total_cache_access_time / total_requests) * 1000
Location computed: rl_env.py:L179
Unit: milliseconds
Lower is better
```

### Cache Occupancy

```
cache_occupancy = len(router.cs)
Location computed: rl_env.py:L166
Value range: [0, CACHE_LIMIT]
Lower is better (frees space)
```

### Composite Metric (CMBA)

```
CMBA = (Closeness + Reach_norm + Degree + Betweenness) / 4
Location computed: main.py:L955
Value range: [0, 1]
Higher is better (more central routers)
```

---

## Quick Integration Checklist

```
[ ] 1. Load network: routers, pubs, subs = load_network()
[ ] 2. (Optional) Pre-simulate: run_simulation(routers, pubs, subs, policy='LRU', iterations=500)
[ ] 3. Compute centrality: plot_centrality_measures(routers)
[ ] 4. Create environment: env = CacheEnvironment(routers=routers)
[ ] 5. Create agent: agent = DQNAgent(state_size=len(routers)*6, action_size=len(routers))
[ ] 6. Train: results = train_agent(env, agent, episodes=10, iterations=100)
[ ] 7. Evaluate: agent.select_action(state, training=False) for testing
[ ] 8. Save agent checkpoint: torch.save(agent.q_network.state_dict(), 'agent.pth')
```

---

## Common Router Attributes Accessed by RL

```python
router.name              # str: "Router1", "Router2", etc.
router.cs               # list: content store (cache)
router.cache_hits       # int: cumulative cache hits
router.publisher_hits   # int: cumulative publisher hits
router.total_requests   # int: total requests processed
router.total_cache_access_time  # float: sum of access times (seconds)
router.pit              # dict: pending interest table
router.fib              # dict: forwarding information base
router.popularity_table # DataFrame: content popularity rankings
router.CACHE_LIMIT      # class int: max cache size (default 15)
router.caching_policy   # str: current policy (LRU, LFU, etc.)
```

---

## File Locations Summary

| Component    | File                                                | Key Functions                                                                 |
| ------------ | --------------------------------------------------- | ----------------------------------------------------------------------------- |
| Simulator    | main.py                                             | setup_network(), load_network(), run_simulation(), plot_centrality_measures() |
| RL Env       | rl_env.py                                           | CacheEnvironment.reset(), step(), \_get_state()                               |
| DQN Agent    | dqn_agent.py                                        | DQNAgent.**init**(), select_action(), train_step()                            |
| Training     | trainer.py                                          | train_agent()                                                                 |
| Entry        | run_rl.py                                           | main()                                                                        |
| Network Data | Saved_Network/network_setup.pkl                     | Pickled (routers, publishers, subscribers)                                    |
| Logs         | Logs/log_Router\*.txt                               | Per-router event logs                                                         |
| Metrics      | Policy_Stats/, Graphs/Centrality/, Path_Iterations/ | CSV outputs                                                                   |
