# Topology-Aware Reinforcement Learning for Adaptive Cooperative Caching in Content-Centric Networks

> A Thesis Project implementing a Topology-Aware Deep Reinforcement Learning framework for adaptive cooperative caching in Content-Centric Networks (CCN).

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![PyTorch](https://img.shields.io/badge/PyTorch-Deep%20Learning-red)
![NetworkX](https://img.shields.io/badge/NetworkX-Graph%20Analytics-green)
![Status](https://img.shields.io/badge/Status-Research-orange)
![License](https://img.shields.io/badge/License-MIT-blue)

---

## Overview

Content-Centric Networking (CCN) improves content delivery by allowing routers to cache frequently requested data. Traditional caching strategies are either:

- Static (Centrality-Based)
- Adaptive (Reinforcement Learning)

However, most existing approaches fail when network topology changes due to subscriber migration or changing traffic patterns.

This project proposes a **Topology-Aware Deep Q-Network (DQN)** that combines:

- Graph Centrality (CMBA)
- Reinforcement Learning
- Adaptive Fine-Tuning
- Cooperative Caching

to dynamically optimize cache placement under evolving network conditions.

---

## Key Features

- Graph-based CCN simulation
- Deep Q-Network (DQN) agent
- CMBA (Centrality Measures Based Algorithm)
- Topology-aware state representation
- Adaptive cache placement
- Experience Replay
- Target Network
- Fine-tuning after topology migration
- Performance visualization
- Comparative scenario evaluation

---

## Research Motivation

Most reinforcement learning based caching algorithms assume a fixed network topology.

In practical deployments:

- Users move
- Traffic changes
- Subscribers migrate
- Router importance changes

As a result, previously trained policies become inefficient.

This work introduces topology awareness into the RL state and evaluates how policies adapt after structural changes.

---

# Project Architecture

```
                +------------------------+
                |   Network Topology     |
                +-----------+------------+
                            |
                            |
                  Compute Graph Centrality
                            |
          +-----------------+-----------------+
          |                                   |
          |          CMBA Features            |
          |                                   |
          +-----------------+-----------------+
                            |
                            |
                 Environment State
                            |
      Cache Hit Ratio + Latency + Occupancy
                            |
                            |
                     Deep Q Network
                            |
                    Cache Placement
                            |
                     Reward Function
                            |
                   Experience Replay
                            |
                     Policy Update
```

---

# System Workflow

```
Original Topology

        ↓

Train DQN Agent

        ↓

Save Model

        ↓

Topology Changes

        ↓

Scenario 1
Original Training

Scenario 2
Train from Scratch

Scenario 3
Direct Transfer

Scenario 4
Fine-Tuning

        ↓

Performance Comparison

```

---

# Repository Structure

```
Topology-Aware-RL-CCN/
│
├── data/
│   ├── topology/
│   ├── cache_logs/
│   └── csv/
│
├── graphs/
│   ├── reward/
│   ├── latency/
│   ├── router_selection/
│   ├── heatmaps/
│   └── centrality/
│
├── models/
│   ├── original_model.pth
│   ├── changed_model.pth
│   └── finetuned_model.pth
│
├── environment/
│   ├── network.py
│   ├── cache.py
│   ├── topology.py
│   └── simulator.py
│
├── agents/
│   ├── dqn.py
│   ├── replay_buffer.py
│   └── trainer.py
│
├── utils/
│   ├── centrality.py
│   ├── metrics.py
│   ├── plotting.py
│   └── helper.py
│
├── notebooks/
│
├── results/
│
├── requirements.txt
│
└── README.md
```

---

# State Representation

Each state consists of:

- Cache Hit Ratio (CHR)
- Cache Occupancy
- Average Latency
- CMBA Centrality Score

```
State =

[
 Cache Hit Ratio,
 Cache Occupancy,
 Latency,
 CMBA Score
]
```

---

# Action Space

Each action decides whether content should be cached at a router.

```
Action =

0 → Do Not Cache

1 → Cache Content
```

---

# Reward Function

The reward combines multiple objectives.

```
Reward =

+ Cache Hit Ratio
+ CMBA Score
- Latency
- Cache Occupancy
```

This encourages:

- High cache hits
- Low latency
- Better router selection
- Efficient cache utilization

---

# CMBA (Centrality Measures)

The project combines four graph centrality metrics.

- Degree Centrality
- Closeness Centrality
- Betweenness Centrality
- Reach Centrality

```
CMBA

=

Average(
Degree,
Closeness,
Betweenness,
Reach
)
```

These features help the RL agent identify structurally important routers.

---

# Experimental Scenarios

## Scenario 1

Original topology training.

✔ Baseline model

---

## Scenario 2

Topology changes.

Train a completely new DQN agent.

---

## Scenario 3

Directly evaluate the old model on the changed topology.

Shows policy mismatch.

---

## Scenario 4

Fine-tune the pretrained model.

Fast adaptation with minimal retraining.

---

# Performance Metrics

The following metrics are evaluated:

- Average Reward
- Reward per Iteration
- Cache Hit Ratio
- Latency
- Router Selection Frequency
- Router Selection Heatmap
- Learning Stability
- Adaptation Speed

---

# Results

The proposed Topology-Aware DQN demonstrates:

- Faster convergence after topology migration
- Lower latency
- Improved cache efficiency
- Stable router selection
- Better reward than retraining from scratch
- Improved adaptation using fine-tuning

---

# Technologies Used

- Python
- PyTorch
- NumPy
- NetworkX
- Matplotlib
- Pandas
- OpenAI Gym Style Environment

---

# Installation

Clone the repository

```bash
git clone https://github.com/yourusername/Topology-Aware-RL-CCN.git

cd Topology-Aware-RL-CCN
```

Install dependencies

```bash
pip install -r requirements.txt
```

Run training

```bash
python train.py
```

Run evaluation

```bash
python evaluate.py
```

---

# Sample Outputs

The repository includes:

- Reward Curves
- Latency Curves
- Router Selection Graphs
- Heatmaps
- Centrality Visualizations
- CSV Logs

---

# Future Work

- Graph Neural Networks (GNN)
- Multi-Agent Reinforcement Learning (MARL)
- Dynamic Content Popularity Prediction
- Real CCNx / NDN Integration
- Large Scale Internet Topologies
- Distributed Cooperative Learning

---

# Citation

If you use this work, please cite:

```
Om Ashok Nalage,
Yash,
Aman Raj,
Karan Khotre,

Topology-Aware Reinforcement Learning for Adaptive Cooperative
Caching in Content-Centric Networks.

Visvesvaraya National Institute of Technology (VNIT), Nagpur.
```

---

# Authors

**Om Ashok Nalage**

Department of Computer Science and Engineering

Visvesvaraya National Institute of Technology (VNIT), Nagpur

---

**Yash**

Department of Computer Science and Engineering

Visvesvaraya National Institute of Technology (VNIT), Nagpur
---

**Aman Raj**

Department of Computer Science and Engineering

Visvesvaraya National Institute of Technology (VNIT), Nagpur

---

**Karan Khotre**

Department of Computer Science and Engineering

Visvesvaraya National Institute of Technology (VNIT), Nagpur

---

# Acknowledgements

Special thanks to **Dr. Nidhi Lal** for her continuous guidance, technical insights, and support throughout this research work.

---

# License

This project is released under the MIT License.

