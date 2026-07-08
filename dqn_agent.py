"""
Step 3: Simple DQN agent (PyTorch)

Provides:
- DQNAgent class
- ReplayBuffer class

Features:
- epsilon-greedy action selection
- experience replay buffer
- target network
"""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass
from typing import Deque, List, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim


class QNetwork(nn.Module):
    """Simple MLP for Q-value approximation."""

    def __init__(self, state_size: int, action_size: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_size, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Linear(128, action_size),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


@dataclass
class Transition:
    state: np.ndarray
    action: int
    reward: float
    next_state: np.ndarray
    done: float


class ReplayBuffer:
    """Fixed-size replay buffer for storing transitions."""

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be > 0")
        self.buffer: Deque[Transition] = deque(maxlen=capacity)

    def push(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool,
    ) -> None:
        self.buffer.append(
            Transition(
                state=np.asarray(state, dtype=np.float32),
                action=int(action),
                reward=float(reward),
                next_state=np.asarray(next_state, dtype=np.float32),
                done=float(done),
            )
        )

    def sample(
        self, batch_size: int
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        if batch_size <= 0:
            raise ValueError("batch_size must be > 0")
        transitions = random.sample(self.buffer, batch_size)

        states = np.stack([t.state for t in transitions])
        actions = np.asarray([t.action for t in transitions], dtype=np.int64)
        rewards = np.asarray([t.reward for t in transitions], dtype=np.float32)
        next_states = np.stack([t.next_state for t in transitions])
        dones = np.asarray([t.done for t in transitions], dtype=np.float32)
        return states, actions, rewards, next_states, dones

    def __len__(self) -> int:
        return len(self.buffer)


class DQNAgent:
    """
    Simple DQN Agent.

    Args:
        state_size: flattened state vector length
        action_size: number of actions (routers)
    """

    def __init__(
        self,
        state_size: int,
        action_size: int,
        lr: float = 1e-3,
        gamma: float = 0.99,
        epsilon_start: float = 1.0,
        epsilon_end: float = 0.05,
        epsilon_decay: float = 0.995,
        buffer_capacity: int = 10000,
        batch_size: int = 64,
        target_update_freq: int = 100,
        device: str | None = None,
    ) -> None:
        if state_size <= 0:
            raise ValueError("state_size must be > 0")
        if action_size <= 0:
            raise ValueError("action_size must be > 0")

        self.state_size = state_size
        self.action_size = action_size
        self.gamma = float(gamma)
        self.epsilon = float(epsilon_start)
        self.epsilon_end = float(epsilon_end)
        self.epsilon_decay = float(epsilon_decay)
        self.batch_size = int(batch_size)
        self.target_update_freq = int(target_update_freq)
        self.train_step_count = 0

        self.device = (
            torch.device(device)
            if device is not None
            else torch.device("cuda" if torch.cuda.is_available() else "cpu")
        )

        self.q_network = QNetwork(state_size, action_size).to(self.device)
        self.target_network = QNetwork(state_size, action_size).to(self.device)
        self.target_network.load_state_dict(self.q_network.state_dict())
        self.target_network.eval()

        self.optimizer = optim.Adam(self.q_network.parameters(), lr=lr)
        self.loss_fn = nn.MSELoss()

        self.replay_buffer = ReplayBuffer(capacity=buffer_capacity)

    def select_action(self, state: np.ndarray, training: bool = True) -> int:
        """
        Epsilon-greedy action selection.
        """
        if training and random.random() < self.epsilon:
            return random.randrange(self.action_size)

        state_t = torch.as_tensor(
            np.asarray(state, dtype=np.float32), device=self.device
        ).unsqueeze(0)
        with torch.no_grad():
            q_values = self.q_network(state_t)
        action = int(torch.argmax(q_values, dim=1).item())
        return action

    def store_transition(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool,
    ) -> None:
        self.replay_buffer.push(state, action, reward, next_state, done)

    def train_step(self) -> float:
        """
        One optimization step using a mini-batch from replay buffer.
        Returns training loss (0.0 if not enough samples).
        """
        if len(self.replay_buffer) < self.batch_size:
            return 0.0

        states, actions, rewards, next_states, dones = self.replay_buffer.sample(
            self.batch_size
        )

        states_t = torch.as_tensor(states, dtype=torch.float32, device=self.device)
        actions_t = torch.as_tensor(actions, dtype=torch.int64, device=self.device).unsqueeze(1)
        rewards_t = torch.as_tensor(rewards, dtype=torch.float32, device=self.device).unsqueeze(1)
        next_states_t = torch.as_tensor(next_states, dtype=torch.float32, device=self.device)
        dones_t = torch.as_tensor(dones, dtype=torch.float32, device=self.device).unsqueeze(1)

        # Q(s, a)
        q_values = self.q_network(states_t).gather(1, actions_t)

        # target = r + gamma * max_a' Q_target(s', a') * (1-done)
        with torch.no_grad():
            max_next_q = self.target_network(next_states_t).max(dim=1, keepdim=True)[0]
            target_q = rewards_t + self.gamma * max_next_q * (1.0 - dones_t)

        loss = self.loss_fn(q_values, target_q)

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        self.train_step_count += 1
        if self.train_step_count % self.target_update_freq == 0:
            self.update_target_network()

        if self.epsilon > self.epsilon_end:
            self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)

        return float(loss.item())

    def update_target_network(self) -> None:
        """Hard update target network."""
        self.target_network.load_state_dict(self.q_network.state_dict())


if __name__ == "__main__":
    # Smoke test
    state_size = 16
    action_size = 4
    agent = DQNAgent(state_size=state_size, action_size=action_size, batch_size=8)

    for _ in range(20):
        s = np.random.randn(state_size).astype(np.float32)
        a = agent.select_action(s, training=True)
        r = float(np.random.randn())
        ns = np.random.randn(state_size).astype(np.float32)
        d = bool(np.random.rand() > 0.8)
        agent.store_transition(s, a, r, ns, d)
        loss = agent.train_step()
    print("DQNAgent smoke test complete. epsilon=", round(agent.epsilon, 4))
