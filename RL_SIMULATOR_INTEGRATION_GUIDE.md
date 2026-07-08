# RL System & Simulator Integration Research

## Executive Summary

The project has two separate but complementary paths: **simulator-based metrics collection** (main.py) and **RL training** (run_rl.py). Integration requires feeding simulation metrics into the RL environment for training.

---

## 1. How main.py Runs Simulations

### Main Simulation Loop Function

**Location:** [main.py](main.py#L500-L599)  
**Function:** `run_simulation(routers, publishers, subscribers, policy, iterations, model=None)`

```python
def run_simulation(routers, publishers, subscribers, policy, iterations, model=None):
    # Reset routers (lines 501-503)
    for router in routers:
        router.caching_policy = policy
        router.reset()

    contents = [...]  # Content list
    simulation_data = []  # Output list

    # MAIN LOOP (lines 510-573)
    for _ in range(iterations):
        # 1. Select active subscriber
        if active_subscribers:
            subscriber = random.choice(active_subscribers)

        # 2. Create interest packet
            interest_packet = InterestPacket(name=content_to_request)

        # 3. Route through network
            subscriber.send_interest(interest_packet, subscriber.connected_router)

        # 4. Calculate metrics (lines 538-550)
        latency = random.uniform(0.01, 0.1)
        total_requests = sum(router.cache_hits + router.publisher_hits for router in routers)
        total_cache_hits = sum(router.cache_hits for router in routers)
        avg_cache_hit = (total_cache_hits / total_requests) * 100 if total_requests > 0 else 0
        avg_latency = latency / total_requests if total_requests > 0 else 0

        # 5. Compute hop reduction
        hop_reduction_ratios = []
        for subscriber in subscribers:
            if hasattr(subscriber, 'last_interest_packet'):
                pkt = subscriber.last_interest_packet
                if pkt.original_hop_count > 0:
                    reduction = (pkt.original_hop_count - pkt.actual_hop_count) / pkt.original_hop_count
                    hop_reduction_ratios.append(reduction)
        total_hop_reduction = sum(hop_reduction_ratios) / len(hop_reduction_ratios) if hop_reduction_ratios else 0

        # 6. Append iteration data
        simulation_data.append([
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            len(active_subscribers),
            total_requests,
            total_hop_reduction,
            avg_cache_hit,
            avg_latency
        ])

    return simulation_data
```

### Main Entry Point

**Location:** [main.py](main.py#L1630-L1682)  
**Function:** `main()`

```python
def main():
    # 1. Setup network (user interactive)
    routers, publishers, subscribers = setup_network()

    # 2. Plot topology
    plot_network_graph(routers, publishers, subscribers)

    # 3. Get iterations from user
    iterations = int(input("Enter the number of content requests in the simulation: "))

    # 4. Load RF model
    random_forest_model = load_model('models/random_forest_model.pkl')

    # 5. Run simulation for all policies
    for policy in policies:  # LRU, LFU, FIFO, MRU, FACR, Rdm, RandomForest
        routers, publishers, subscribers = load_network()
        stats = run_simulation(routers, publishers, subscribers, policy, iterations)
        policy_stats.extend([...])

    # 6. Save results
    save_results(policy_stats)

    # 7. Generate centrality measures
    plot_centrality_measures(_routers)
```

---

## 2. Simulator Output Data (Metrics)

### Per-Iteration Metrics (returned by run_simulation)

Each iteration appends a row to `simulation_data`:

```python
[
    "Timestamp",           # DateTime string
    Active_Subscribers,    # Integer count
    Total_Requests,        # Integer count
    Hop_Reduction_Ratio,   # Float (0-1)
    Avg_Cache_Hit_Ratio,   # Float percentage
    Avg_Latency            # Float seconds
]
```

### Per-Router Metrics (collected internally)

Each router accumulates during simulation:

| Metric                    | Source                     | Type        | Notes                         |
| ------------------------- | -------------------------- | ----------- | ----------------------------- |
| `cache_hits`              | Router.receive_data()      | int         | Cache hit count               |
| `publisher_hits`          | Router.receive_interest()  | int         | Content source hits           |
| `total_requests`          | Router.receive_interest()  | int         | Total request count           |
| `total_cache_access_time` | Router.receive_interest()  | float       | Sum of access times (seconds) |
| `cs`                      | Router.receive_data()      | list        | Content store (cache)         |
| `cache_frequency`         | Router.receive_data()      | defaultdict | LFU counts                    |
| `cache_access_times`      | Router.receive_data()      | dict        | LRU/MRU timestamps            |
| `popularity_table`        | Router.update_popularity() | DataFrame   | Per-content popularity        |

**Format for RouterMetrics (used by RL environment):**

```python
@dataclass
class RouterMetrics:
    name: str
    cache_occupancy: float          # len(router.cs)
    chr_value: float                # cache_hits / total_requests
    latency_ms: float               # (total_cache_access_time / total_requests) * 1000
    cmba: float                     # Composite Metric (centrality-based)
    global_avg_chr: float           # Network-wide average CHR
    global_avg_latency: float       # Network-wide average latency
```

### Output Files Generated

| File                | Location                               | Description                          |
| ------------------- | -------------------------------------- | ------------------------------------ |
| Policy statistics   | `Policy_Stats/{policy}_stats.csv`      | Per-policy metrics per iteration     |
| Network logs        | `Logs/log_Router{i}.txt`               | Event logs per router                |
| FIB entries         | `Output/FIB/Router{i}/fib.csv`         | Forwarding rules                     |
| Cache state         | `Output/CS/Router{i}/cs.csv`           | Cached content at each router        |
| Popularity table    | `Popularity_Table/{policy}/Ptable.csv` | Content popularity rankings          |
| Centrality measures | `Graphs/Centrality/results.csv`        | CMBA, degree, closeness, betweenness |

---

## 3. Feeding Simulator Output into RL Environment

### Current RL Environment Flow

**Location:** [rl_env.py](rl_env.py#L20-L80)

```python
class CacheEnvironment:
    def __init__(self, routers: List[Any], episode_length: int = 100):
        self.routers = routers
        self.episode_length = episode_length

    def reset(self) -> np.ndarray:
        """Reset environment and return initial state"""
        self._step_count = 0
        return self._get_state()

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        Args:
            action: router index to optimize (0 to len(routers)-1)

        Returns:
            next_state: np.ndarray of normalized metrics
            reward: float computed from formula
            done: bool (episode finished)
            info: dict with selected router and metrics
        """
        metrics = self._collect_router_metrics()
        selected = metrics[action]

        # Reward formula (lines 42-44):
        reward = w1 * CHR + w2 * CMBA - w3 * latency - w4 * cache_occupancy

        return next_state, reward, done, info
```

### Integration Pattern: Simulator → Environment → Agent

```
┌─────────────────────────────────────────────────────────────┐
│ 1. INITIALIZE: Create routers & load network                │
│    routers, publishers, subscribers = setup_network()       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. SIMULATE: Run one simulation iteration                   │
│    - Send interest packets through network                  │
│    - Routers cache/forward content                          │
│    - Metrics accumulate in router objects                   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. COLLECT: RL env reads current router metrics             │
│    metrics = _collect_router_metrics()                      │
│    - Reads: cs, cache_hits, total_requests, latency, etc.   │
│    - Returns: RouterMetrics objects with computed CHR, etc. │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. COMPUTE STATE: Normalize and flatten metrics             │
│    state = _get_state()                                     │
│    - Returns: np.ndarray(len_routers * 6 features)          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. AGENT ACTS: DQN selects router index                     │
│    action = agent.select_action(state)                      │
│    - Router index (0 to len(routers)-1)                     │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. REWARD & TRAIN: Compute reward based on metrics          │
│    reward, done, info = env.step(action)                    │
│    - Reward from selected router's metrics                  │
│    - Agent stores experience and trains                     │
└─────────────────────────────────────────────────────────────┘
```

### Key Integration Point: Linking Simulation to Metrics

**Router state is continuously updated during simulation:**

```python
# In main.py run_simulation():
for _ in range(iterations):
    # ... simulation runs, routers accumulate metrics
    # At ANY POINT, RL env can read:
    for router in routers:
        router.total_requests      # ← Updated by receive_interest()
        router.cache_hits          # ← Updated by receive_interest()
        router.cs                  # ← Updated by receive_data()
        router.total_cache_access_time  # ← Tracking latency
```

**RL environment reads these directly (no copying needed):**

```python
# In rl_env.py _collect_router_metrics():
for r in self.routers:
    cache_hits = float(getattr(r, "cache_hits", 0.0))
    total_requests = float(getattr(r, "total_requests", 0.0))
    chr_value = (cache_hits / total_requests) if total_requests > 0 else 0.0
    # ... and so on
```

---

## 4. Existing Simulation Functions to Call

### Functions Available for RL Training

| Function                          | File          | Purpose                | Returns                            |
| --------------------------------- | ------------- | ---------------------- | ---------------------------------- |
| `setup_network()`                 | main.py:L398  | Create/load network    | (routers, publishers, subscribers) |
| `load_network()`                  | main.py:L379  | Load saved network     | (routers, publishers, subscribers) |
| `run_simulation()`                | main.py:L501  | Run sim iterations     | list of metrics per iteration      |
| `plot_centrality_measures()`      | main.py:L920  | Compute centrality     | None (saves CSVs)                  |
| `save_iteration_router_metrics()` | main.py:L1615 | Log per-router metrics | CSV filename                       |

### Direct Usage in RL Training

```python
# From run_rl.py (current)
from main import load_network
from rl_env import CacheEnvironment
from dqn_agent import DQNAgent
from trainer import train_agent

def main():
    # 1. Load pre-built network
    network = load_network()
    routers, publishers, subscribers = network

    # 2. Create RL environment (wraps routers)
    env = CacheEnvironment(routers=routers, episode_length=100)

    # 3. Create RL agent
    state_size = len(routers) * 6  # 6 metrics per router
    agent = DQNAgent(state_size=state_size, action_size=len(routers))

    # 4. Train
    results = train_agent(env, agent, episodes=5, iterations=50)
```

---

## 5. Expected Flow: Simulation → Metrics → RL Training → Evaluation

### Complete End-to-End Flow

```python
# ============================================================
# PHASE 1: SETUP (One-time)
# ============================================================
routers, publishers, subscribers = setup_network()
# Output: Network saved to 'Saved_Network/network_setup.pkl'

plot_network_graph(routers, publishers, subscribers)
# Output: Topology visualization

# ============================================================
# PHASE 2: PRETRAINING (Optional - establish baseline)
# ============================================================
# Run baseline simulation with different policies
for policy in ['LRU', 'LFU', 'FIFO', 'MRU', 'FACR']:
    routers, _, _ = load_network()
    simulation_data = run_simulation(routers, publishers, subscribers, policy, iterations=1000)
    save_policy_stats(policy, simulation_data)
    # Routers now have accumulated metrics:
    # - cache_hits: 0-1000 per router
    # - total_requests: 0-5000
    # - popular_table: content popularity rankings

# Compute centrality for each router
plot_centrality_measures(routers)
# Output: 'Graphs/Centrality/results.csv' with CMBA scores

# ============================================================
# PHASE 3: RL TRAINING (Main)
# ============================================================
routers, _, _ = load_network()
env = CacheEnvironment(routers=routers, episode_length=100)
agent = DQNAgent(state_size=len(routers)*6, action_size=len(routers))

# Episode loop (from trainer.py):
for episode in range(num_episodes):
    state = env.reset()  # Reset step counter to 0

    for iteration in range(max_iterations_per_episode):
        # 1. COLLECT CURRENT METRICS FROM ROUTERS
        #    via env._collect_router_metrics()
        metrics = env._collect_router_metrics()
        # Returns: [RouterMetrics(...), RouterMetrics(...), ...]
        #   - Each has: name, cache_occupancy, chr_value, latency_ms, cmba

        # 2. GET STATE (normalized feature vector)
        state = env._get_state()
        # Returns: np.ndarray shape (len(routers) * 6,)
        #   - Features per router: occupancy, chr, latency, cmba, global_chr, global_lat

        # 3. AGENT SELECTS ACTION
        action = agent.select_action(state, training=True)
        # Returns: router index (0 to len(routers)-1)

        # 4. STEP ENVIRONMENT (compute reward from selected router)
        next_state, reward, done, info = env.step(action)
        # Reward formula: w1*CHR + w2*CMBA - w3*latency - w4*occupancy
        # info contains: selected router name and its current metrics

        # 5. SIMULATE: Run traffic through network (OPTIONAL)
        # For continuous training, you might run simulation iterations
        # This updates router metrics incrementally
        # (Currently, env.step() doesn't do this - just reads current state)

        # 6. STORE EXPERIENCE & TRAIN DQN
        agent.store_transition(state, action, reward, next_state, done)
        loss = agent.train_step()

        state = next_state
        if done:
            break

# ============================================================
# PHASE 4: EVALUATION
# ============================================================
# Test trained agent on held-out scenario
env_eval = CacheEnvironment(routers=routers_eval, episode_length=100)
state = env_eval.reset()

total_reward = 0
for step in range(100):
    action = agent.select_action(state, training=False)  # Deterministic
    next_state, reward, done, info = env_eval.step(action)
    total_reward += reward
    state = next_state
    if done:
        break

print(f"Evaluation total reward: {total_reward}")

# Compare against baseline (random or LRU policy)
results_comparison = {
    'RL_trained': total_reward,
    'baseline_LRU': baseline_lru_reward,
    'improvement': (total_reward - baseline_lru_reward) / abs(baseline_lru_reward)
}
```

---

## 6. Integration Code Patterns

### Pattern 1: Basic RL Training Loop

```python
from main import load_network, plot_centrality_measures
from rl_env import CacheEnvironment
from dqn_agent import DQNAgent
from trainer import train_agent

# Step 1: Load network
routers, publishers, subscribers = load_network()
num_routers = len(routers)

# Step 2: Create environment
env = CacheEnvironment(
    routers=routers,
    episode_length=100,
    w1=0.25,  # CHR weight
    w2=0.25,  # CMBA weight
    w3=0.25,  # Latency weight (negative)
    w4=0.25   # Occupancy weight (negative)
)

# Step 3: Create agent
state_size = num_routers * 6
action_size = num_routers
agent = DQNAgent(
    state_size=state_size,
    action_size=action_size,
    gamma=0.99,
    epsilon_start=1.0,
    epsilon_end=0.05
)

# Step 4: Train
results = train_agent(
    environment=env,
    agent=agent,
    episodes=10,
    iterations=100
)

# Results contain: rewards_csv, selections_csv, summary_csv
print(f"Training results saved to: {results['summary_csv']}")
```

### Pattern 2: Adding Simulation-Based Metric Updating

```python
from main import load_network, run_simulation
from rl_env import CacheEnvironment

routers, publishers, subscribers = load_network()

# Option A: Pre-simulate to build initial metrics
print("Pre-simulating to establish baseline metrics...")
baseline_data = run_simulation(routers, publishers, subscribers, policy='LRU', iterations=500)
# Now routers have: cache_hits, total_requests, total_cache_access_time populated

# Option B: Create environment and train
env = CacheEnvironment(routers=routers, episode_length=100)

# Option C: In training loop, you could periodically re-simulate
for episode in range(num_episodes):
    state = env.reset()

    # Every N episodes, run mini simulation to refresh metrics
    if episode % 5 == 0:
        print(f"Refreshing simulation metrics at episode {episode}...")
        run_simulation(routers, publishers, subscribers, policy='FACR', iterations=50)

    # Continue training with updated metrics
    for iteration in range(max_iterations):
        action = agent.select_action(state, training=True)
        next_state, reward, done, info = env.step(action)
        agent.store_transition(state, action, reward, next_state, done)
        agent.train_step()
        state = next_state
```

### Pattern 3: Custom Reward Based on Simulation Output

```python
def custom_reward_from_simulation(routers, selected_router_index):
    """
    Compute reward based directly on simulation metrics.
    """
    selected = routers[selected_router_index]

    # Get metrics from accumulated simulation
    cache_hits = float(selected.cache_hits)
    total_requests = float(selected.total_requests)
    chr_value = cache_hits / total_requests if total_requests > 0 else 0.0

    total_cache_access_time = float(selected.total_cache_access_time)
    latency_ms = (total_cache_access_time / total_requests * 1000) if total_requests > 0 else 0.0

    cache_occupancy = len(selected.cs)
    cache_limit = selected.__class__.CACHE_LIMIT
    occupancy_norm = cache_occupancy / cache_limit if cache_limit > 0 else 0.0

    # Custom formula
    reward = (
        0.3 * chr_value +
        0.3 * (1 - occupancy_norm) +
        -0.4 * (latency_ms / 1000)  # Negative reward for high latency
    )

    return reward
```

---

## 7. Critical Design Notes

### State Representation in RL Environment

```python
# From rl_env.py _get_state():
# State = [
#   R1_occupancy_norm, R1_chr_norm, R1_latency_norm, R1_cmba_norm, R1_global_chr, R1_global_lat,
#   R2_occupancy_norm, R2_chr_norm, ...,
#   ...
#   Rn_occupancy_norm, ..., Rn_global_lat
# ]
# Total length: num_routers * 6
```

### Router Metric Collection Flow

```python
Router.receive_interest()  → increments total_requests, cache_hits
                           → updates PIT
                           → logs to Logs/log_Router*.txt

Router.receive_data()      → adds to cs (content store)
                           → increments total_cache_access_time
                           → updates popularity_table
                           → updates cache_access_times (LRU/MRU)

RL_Environment._collect_router_metrics()  → reads all above values
                                          → computes CHR, latency
                                          → returns RouterMetrics objects
```

### Reward Normalization

```python
# All reward components are clipped to [0, 1]
chr_norm = max(0.0, min(1.0, chr_value))
lat_norm = max(0.0, min(1.0, latency_normalized))
occ_norm = max(0.0, min(1.0, occupancy / cache_limit))
cmba_norm = max(0.0, min(1.0, cmba_value))

# Final reward (weighted sum):
reward = w1 * chr_norm + w2 * cmba_norm - w3 * lat_norm - w4 * occ_norm
```

---

## 8. Files to Modify/Create for Full Integration

| File                         | Purpose                          | Status           |
| ---------------------------- | -------------------------------- | ---------------- |
| `run_rl.py`                  | RL training entry point          | ✓ Exists (basic) |
| `trainer.py`                 | Training loop logic              | ✓ Exists         |
| `rl_env.py`                  | RL environment wrapper           | ✓ Exists         |
| `dqn_agent.py`               | DQN agent implementation         | ✓ Exists         |
| `simulator_rl_integrated.py` | **NEW**: Combined simulator + RL | ❌ Create        |
| `eval_rl_agent.py`           | **NEW**: Evaluation script       | ❌ Create        |

### Minimal Required Additions

1. **Modify `run_rl.py`**: Add pre-simulation step
2. **Create `simulator_rl_integrated.py`**: Unified training with periodic sim updates
3. **Create `eval_rl_agent.py`**: Compare RL vs. baseline policies

---

## 9. Summary Table: Data Flow

| Step | Function                                     | Input                                                  | Output                           | Metrics Updated                                     |
| ---- | -------------------------------------------- | ------------------------------------------------------ | -------------------------------- | --------------------------------------------------- |
| 1    | `setup_network()`                            | User input                                             | Network objects                  | None                                                |
| 2    | `save_network()`                             | (routers, publishers, subscribers)                     | PKL file                         | None                                                |
| 3    | `load_network()`                             | PKL file                                               | Network objects                  | None                                                |
| 4    | `run_simulation()`                           | (routers, publishers, subscribers, policy, iterations) | simulation_data list             | cache_hits, total_requests, total_cache_access_time |
| 5    | `plot_centrality_measures()`                 | routers                                                | results.csv                      | CMBA scores                                         |
| 6    | `CacheEnvironment.reset()`                   | -                                                      | initial_state                    | step_count=0                                        |
| 7    | `CacheEnvironment._collect_router_metrics()` | -                                                      | RouterMetrics[]                  | None (reads only)                                   |
| 8    | `CacheEnvironment._get_state()`              | -                                                      | normalized_state_vector          | None (normalized copy)                              |
| 9    | `CacheEnvironment.step(action)`              | action (router_index)                                  | (next_state, reward, done, info) | None (reward computed)                              |
| 10   | `DQNAgent.select_action()`                   | state                                                  | action                           | None (policy)                                       |
| 11   | `DQNAgent.store_transition()`                | (s, a, r, s', done)                                    | -                                | replay_buffer                                       |
| 12   | `DQNAgent.train_step()`                      | -                                                      | loss                             | q_network weights                                   |

---

## Recommendations for Integration

### Short-term (Immediate)

1. ✅ Modify `run_rl.py` to call `plot_centrality_measures()` before training
2. ✅ Add pre-simulation phase to generate initial metrics
3. ✅ Verify agent can read router metrics correctly

### Medium-term (Optional)

1. Create simulation updater that runs mini-simulations every N episodes
2. Compare learned policy vs. baseline (LRU, FACR)
3. Save agent checkpoint at best performance

### Long-term (Enhancement)

1. Multi-objective optimization (Pareto frontier)
2. Transfer learning across different network topologies
3. Online learning with live traffic simulation
