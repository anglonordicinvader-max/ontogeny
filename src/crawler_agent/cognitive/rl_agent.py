"""Reinforcement learning agent for action selection.

Learns from successes and failures to improve decision-making
over time. Uses epsilon-greedy with Q-learning.
"""

import random
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog


@dataclass
class State:
    """Current state of the agent."""

    context: dict[str, Any] = field(default_factory=dict)
    recent_actions: list[str] = field(default_factory=list)
    recent_rewards: list[float] = field(default_factory=list)

    def to_key(self) -> str:
        """Convert state to hashable key."""
        context_str = str(sorted(self.context.items()))
        actions_str = str(self.recent_actions[-3:])
        return f"{context_str}:{actions_str}"


@dataclass
class Action:
    """An action the agent can take."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    action_type: str = ""  # crawl, learn, plan, analyze, etc.
    parameters: dict[str, Any] = field(default_factory=dict)
    preconditions: list[str] = field(default_factory=list)


@dataclass
class Experience:
    """A recorded experience for learning."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: str = ""
    action: str = ""
    reward: float = 0.0
    next_state: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


class RLAgent:
    """Reinforcement learning agent for action selection.

    Uses Q-learning with epsilon-greedy exploration.
    Learns from experience to select better actions over time.
    """

    def __init__(
        self,
        learning_rate: float = 0.1,
        discount_factor: float = 0.95,
        epsilon: float = 0.3,
        epsilon_decay: float = 0.995,
        min_epsilon: float = 0.05,
    ):
        self.q_table: dict[tuple[str, str], float] = defaultdict(float)
        self.actions: dict[str, Action] = {}
        self.experiences: list[Experience] = []
        self.state_history: list[str] = []

        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.min_epsilon = min_epsilon

        self.total_reward = 0.0
        self.episode_count = 0
        self.logger = structlog.get_logger()

    def register_action(self, action: Action):
        """Register an available action."""
        self.actions[action.id] = action

    def register_default_actions(self):
        """Register default cognitive actions."""
        defaults = [
            Action(name="crawl", action_type="crawl", parameters={"depth": "shallow"}),
            Action(name="crawl_deep", action_type="crawl", parameters={"depth": "deep"}),
            Action(name="search", action_type="search"),
            Action(name="learn_focused", action_type="learn", parameters={"mode": "focused"}),
            Action(
                name="learn_exploratory", action_type="learn", parameters={"mode": "exploratory"}
            ),
            Action(name="plan", action_type="plan"),
            Action(name="analyze", action_type="analyze"),
            Action(name="synthesize", action_type="synthesize"),
            Action(name="reflect", action_type="reflect"),
            Action(name="rest", action_type="rest"),  # Do nothing, let memory consolidate
        ]
        for action in defaults:
            self.register_action(action)

    async def select_action(self, state: State) -> Action:
        """Select action using epsilon-greedy policy."""
        state_key = state.to_key()
        self.state_history.append(state_key)

        # Epsilon-greedy: explore vs exploit
        if random.random() < self.epsilon:
            action = self._explore()
            self.logger.debug("rl_explore", action=action.name)
        else:
            action = self._exploit(state_key)
            self.logger.debug("rl_exploit", action=action.name)

        return action

    async def record_outcome(
        self,
        state: State,
        action: Action,
        reward: float,
        next_state: State,
    ):
        """Record the outcome of an action for learning."""
        state_key = state.to_key()
        next_state_key = next_state.to_key()

        # Update Q-value
        current_q = self.q_table[(state_key, action.id)]
        max_next_q = max(
            [self.q_table[(next_state_key, a.id)] for a in self.actions.values()],
            default=0.0,
        )

        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * max_next_q - current_q
        )
        self.q_table[(state_key, action.id)] = new_q

        # Record experience
        experience = Experience(
            state=state_key,
            action=action.id,
            reward=reward,
            next_state=next_state_key,
            metadata={"action_name": action.name},
        )
        self.experiences.append(experience)

        # Update stats
        self.total_reward += reward
        self.episode_count += 1

        # Decay epsilon
        self.epsilon = max(self.min_epsilon, self.epsilon * self.epsilon_decay)

        self.logger.info(
            "rl_update",
            action=action.name,
            reward=reward,
            q_value=new_q,
            epsilon=self.epsilon,
        )

    def get_reward(self, success: bool, quality: float = 0.5, novelty: float = 0.5) -> float:
        """Calculate reward from outcome metrics."""
        reward = 0.0
        if success:
            reward += 1.0
        reward += quality * 0.5
        reward += novelty * 0.3
        return reward

    def get_stats(self) -> dict[str, Any]:
        """Get RL agent statistics."""
        action_rewards = defaultdict(list)
        for exp in self.experiences:
            action_rewards[exp.metadata.get("action_name", "unknown")].append(exp.reward)

        avg_rewards = {
            name: sum(rewards) / len(rewards) if rewards else 0
            for name, rewards in action_rewards.items()
        }

        return {
            "total_experiences": len(self.experiences),
            "total_reward": self.total_reward,
            "epsilon": self.epsilon,
            "q_table_size": len(self.q_table),
            "avg_rewards_by_action": avg_rewards,
            "best_action": max(avg_rewards, key=avg_rewards.get) if avg_rewards else None,
        }

    def get_policy(self, state: State) -> list[tuple[Action, float]]:
        """Get action preferences for a state."""
        state_key = state.to_key()
        q_values = [
            (action, self.q_table[(state_key, action.id)]) for action in self.actions.values()
        ]
        q_values.sort(key=lambda x: x[1], reverse=True)
        return q_values

    def _explore(self) -> Action:
        """Randomly select an action."""
        return random.choice(list(self.actions.values()))

    def _exploit(self, state_key: str) -> Action:
        """Select the best known action."""
        q_values = [
            (action, self.q_table[(state_key, action.id)]) for action in self.actions.values()
        ]
        q_values.sort(key=lambda x: x[1], reverse=True)

        # If all Q-values are 0, explore instead
        if q_values[0][1] == 0:
            return self._explore()

        return q_values[0][0]

    def to_context(self) -> str:
        """Convert RL state to context string."""
        stats = self.get_stats()
        lines = [
            "RL Agent State:",
            f"  Experiences: {stats['total_experiences']}",
            f"  Total Reward: {stats['total_reward']:.2f}",
            f"  Exploration Rate: {stats['epsilon']:.2%}",
        ]
        if stats["best_action"]:
            lines.append(f"  Best Action: {stats['best_action']}")
        return "\n".join(lines)
