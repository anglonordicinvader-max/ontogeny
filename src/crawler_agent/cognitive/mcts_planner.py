"""MCTS Planner - Monte Carlo Tree Search for long-horizon planning with learned world model."""

import asyncio
import math
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import structlog

from .backend import CognitiveBackend, CognitiveResponse
from .planning import Plan, PlanStatus, PlanStep, StepStatus
from .world_model import BayesianWorldModel

logger = structlog.get_logger()


@dataclass
class MCTSConfig:
    """Configuration for MCTS planner."""

    iterations: int = 100
    exploration_constant: float = 1.414
    max_depth: int = 10
    discount_factor: float = 0.95
    rollout_policy: str = "random"  # random, heuristic, learned
    parallel_rollouts: int = 1
    time_limit_ms: int | None = None
    progressive_widening: bool = True
    widening_constant: float = 1.0
    widening_exponent: float = 0.5


@dataclass
class MCTSNode:
    """Node in the MCTS tree."""

    state: Any
    parent: Optional["MCTSNode"] = None
    action: Any = None
    children: list["MCTSNode"] = field(default_factory=list)
    visits: int = 0
    total_reward: float = 0.0
    untried_actions: list[Any] = field(default_factory=list)
    depth: int = 0
    is_terminal: bool = False
    terminal_reward: float = 0.0

    @property
    def q_value(self) -> float:
        return self.total_reward / self.visits if self.visits > 0 else 0.0

    @property
    def uct_value(self) -> float:
        if self.visits == 0:
            return float("inf")
        return (
            self.q_value
            + self.exploration_constant * math.sqrt(math.log(self.parent.visits) / self.visits)
            if self.parent
            else 0.0
        )

    exploration_constant: float = 1.414


class WorldModelInterface(ABC):
    """Interface for world model used in MCTS."""

    @abstractmethod
    async def predict(self, state: Any, action: Any) -> tuple[Any, float, bool]:
        """Predict next state, reward, and done from state-action pair."""
        ...

    @abstractmethod
    async def is_terminal(self, state: Any) -> tuple[bool, float]:
        """Check if state is terminal, return (done, reward)."""
        ...

    @abstractmethod
    async def get_valid_actions(self, state: Any) -> list[Any]:
        """Get valid actions for a state."""
        ...


class LearnedWorldModel(WorldModelInterface):
    """World model using LLM + BayesianWorldModel."""

    def __init__(
        self,
        backend: CognitiveBackend,
        bayesian_model: BayesianWorldModel,
        available_actions: list[str],
    ):
        self.backend = backend
        self.bayesian_model = bayesian_model
        self.available_actions = available_actions

    async def predict(self, state: dict, action: str) -> tuple[dict, float, bool]:
        """Use LLM to predict next state."""
        prompt = f"""Predict the result of this action in the current state.

State: {json.dumps(state)[:3000]}
Action: {action}

Return JSON: {{"next_state": {{...}}, "reward": 0.0-1.0, "done": true/false}}"""

        response = await self.backend.complete(prompt, temperature=0.3, max_tokens=1000)
        try:
            result = json.loads(response.content)
            return (
                result.get("next_state", state),
                result.get("reward", 0.0),
                result.get("done", False),
            )
        except Exception:
            return state, 0.0, False

    async def is_terminal(self, state: dict) -> tuple[bool, float]:
        """Check if state represents goal completion."""
        # Could use LLM or check goal conditions
        return False, 0.0

    async def get_valid_actions(self, state: dict) -> list[str]:
        return self.available_actions


class MCTSPlanner:
    """Monte Carlo Tree Search planner with learned world model."""

    def __init__(
        self,
        world_model: WorldModelInterface,
        config: MCTSConfig | None = None,
        backend: CognitiveBackend | None = None,
    ):
        self.world_model = world_model
        self.config = config or MCTSConfig()
        self.backend = backend
        self.logger = logger.bind(component="mcts_planner")
        self.root: MCTSNode | None = None
        self.stats = {"iterations": 0, "nodes_created": 0, "rollouts": 0, "best_reward": 0.0}

    async def plan(self, initial_state: Any, goal: str, max_time_ms: int | None = None) -> Plan:
        """Run MCTS and return best plan."""
        self.logger.info("mcts_start", goal=goal, iterations=self.config.iterations)
        start_time = time.perf_counter()

        # Initialize root
        valid_actions = await self.world_model.get_valid_actions(initial_state)
        self.root = MCTSNode(state=initial_state, untried_actions=valid_actions.copy(), depth=0)

        time_limit = max_time_ms or self.config.time_limit_ms
        deadline = start_time + (time_limit / 1000) if time_limit else None

        # Run iterations
        for i in range(self.config.iterations):
            if deadline and time.perf_counter() > deadline:
                break

            await self._mcts_iteration(self.root)
            self.stats["iterations"] = i + 1

            if i % 20 == 0:
                best = self._get_best_child(self.root)
                self.stats["best_reward"] = best.q_value if best else 0.0
                self.logger.debug(
                    "mcts_progress", iteration=i, best_reward=self.stats["best_reward"]
                )

        # Extract best plan
        plan = await self._extract_plan(self.root, goal)
        elapsed = (time.perf_counter() - start_time) * 1000
        self.logger.info("mcts_complete", elapsed_ms=elapsed, **self.stats)

        return plan

    async def _mcts_iteration(self, root: MCTSNode):
        """Single MCTS iteration: selection -> expansion -> simulation -> backpropagation."""
        # Selection
        node = self._select(root)

        # Expansion
        if not node.is_terminal and node.untried_actions:
            node = await self._expand(node)

        # Simulation (rollout)
        reward = await self._simulate(node)

        # Backpropagation
        self._backpropagate(node, reward)

    def _select(self, node: MCTSNode) -> MCTSNode:
        """Select node using UCT."""
        while node.children and not node.is_terminal:
            # Progressive widening
            if self.config.progressive_widening and len(
                node.children
            ) < self.config.widening_constant * (node.visits**self.config.widening_exponent):
                if node.untried_actions:
                    return node  # Expand this node

            # UCT selection
            node = max(node.children, key=lambda c: c.uct_value)
        return node

    async def _expand(self, node: MCTSNode) -> MCTSNode:
        """Expand node by trying an untried action."""
        if not node.untried_actions:
            return node

        action = node.untried_actions.pop()
        node.visits += 1  # Increment for progressive widening

        # Predict next state
        next_state, reward, done = await self.world_model.predict(node.state, action)

        child = MCTSNode(
            state=next_state,
            parent=node,
            action=action,
            depth=node.depth + 1,
            is_terminal=done,
            terminal_reward=reward,
        )
        if not done:
            child.untried_actions = await self.world_model.get_valid_actions(next_state)

        node.children.append(child)
        self.stats["nodes_created"] += 1
        return child

    async def _simulate(self, node: MCTSNode) -> float:
        """Run rollout from node to terminal state."""
        if node.is_terminal:
            return node.terminal_reward

        state = node.state
        total_reward = 0.0
        discount = 1.0

        for _step in range(self.config.max_depth):
            actions = await self.world_model.get_valid_actions(state)
            if not actions:
                break

            # Rollout policy
            action = self._rollout_policy(state, actions)

            next_state, reward, done = await self.world_model.predict(state, action)
            total_reward += discount * reward
            discount *= self.config.discount_factor

            if done:
                break
            state = next_state

        self.stats["rollouts"] += 1
        return total_reward

    def _rollout_policy(self, state: Any, actions: list[Any]) -> Any:
        """Select action for rollout."""
        if self.config.rollout_policy == "random":
            return random.choice(actions)
        elif self.config.rollout_policy == "heuristic":
            # Simple heuristic: prefer actions that seem goal-directed
            return actions[0]  # Simplified
        return random.choice(actions)

    def _backpropagate(self, node: MCTSNode, reward: float):
        """Backpropagate reward up the tree."""
        while node:
            node.visits += 1
            node.total_reward += reward
            node = node.parent

    def _get_best_child(self, node: MCTSNode) -> MCTSNode | None:
        """Get child with highest visit count."""
        if not node.children:
            return None
        return max(node.children, key=lambda c: c.visits)

    async def _extract_plan(self, root: MCTSNode, goal: str) -> Plan:
        """Extract plan from MCTS tree by following best path."""
        steps = []
        node = root
        step_num = 0

        while node.children and step_num < 20:
            best = self._get_best_child(node)
            if not best:
                break

            step = PlanStep(
                id=f"mcts_step_{step_num}",
                description=f"Execute: {best.action}",
                action=str(best.action),
                parameters={"mcts_action": best.action, "q_value": best.q_value},
                status=StepStatus.PENDING,
            )
            steps.append(step)
            node = best
            step_num += 1

        plan = Plan(
            id=f"mcts_plan_{uuid.uuid4().hex[:8]}",
            goal_id=goal,
            steps=steps,
            status=PlanStatus.PENDING,
        )
        return plan

    def get_stats(self) -> dict:
        return self.stats.copy()


class HybridMCTSPlanner(MCTSPlanner):
    """MCTS with LLM-guided action proposal for complex domains."""

    def __init__(
        self,
        world_model: WorldModelInterface,
        backend: CognitiveBackend,
        config: MCTSConfig | None = None,
    ):
        super().__init__(world_model, config, backend)
        self.backend = backend
        self.action_proposals_cache: dict[str, list[str]] = {}

    async def _expand(self, node: MCTSNode) -> MCTSNode:
        """Expand with LLM-proposed actions for complex states."""
        if not node.untried_actions:
            # Use LLM to propose new actions
            state_key = self._state_key(node.state)
            if state_key not in self.action_proposals_cache:
                proposals = await self._llm_propose_actions(node.state)
                self.action_proposals_cache[state_key] = proposals

            node.untried_actions.extend(self.action_proposals_cache.get(state_key, []))

        return await super()._expand(node)

    def _state_key(self, state: Any) -> str:
        return str(state)[:500]

    async def _llm_propose_actions(self, state: Any) -> list[str]:
        """Use LLM to propose relevant actions for this state."""
        prompt = f"""Given this state, propose 3-5 concrete next actions to make progress.

State: {json.dumps(state)[:2000]}

Return JSON array of action strings: ["action1", "action2", ...]"""

        response = await self.backend.complete(prompt, temperature=0.7, max_tokens=500)
        try:
            return json.loads(response.content)
        except Exception:
            return []


async def create_mcts_planner(
    backend: CognitiveBackend,
    bayesian_model: BayesianWorldModel,
    available_actions: list[str],
    config: MCTSConfig | None = None,
) -> MCTSPlanner:
    """Factory for creating MCTS planner with learned world model."""
    world_model = LearnedWorldModel(backend, bayesian_model, available_actions)
    return HybridMCTSPlanner(world_model, backend, config)
