"""Multi-agent instances with behavioral variation.

Provides:
- Agent instances with different behavioral parameters
- Strategy propagation from successful agents
- Population-based learning
- Behavioral diversity for exploration
"""

import asyncio
import json
import random
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog


@dataclass
class BehavioralParams:
    """Behavioral parameters that vary between agent instances."""

    exploration_rate: float = 0.3  # How much to explore vs exploit
    risk_tolerance: float = 0.5  # Willingness to take risky actions
    creativity: float = 0.5  # Tendency to try novel approaches
    persistence: float = 0.5  # How long to stick with a strategy
    social_learning: float = 0.3  # Tendency to learn from other agents
    memory_retention: float = 0.7  # How much to retain from experiences
    planning_horizon: int = 5  # Steps ahead to plan
    reflection_depth: int = 2  # How deeply to reflect on outcomes

    def to_dict(self) -> dict:
        return {
            "exploration_rate": self.exploration_rate,
            "risk_tolerance": self.risk_tolerance,
            "creativity": self.creativity,
            "persistence": self.persistence,
            "social_learning": self.social_learning,
            "memory_retention": self.memory_retention,
            "planning_horizon": self.planning_horizon,
            "reflection_depth": self.reflection_depth,
        }

    @classmethod
    def random(cls) -> "BehavioralParams":
        """Create random behavioral parameters."""
        return cls(
            exploration_rate=random.uniform(0.1, 0.9),
            risk_tolerance=random.uniform(0.1, 0.9),
            creativity=random.uniform(0.1, 0.9),
            persistence=random.uniform(0.1, 0.9),
            social_learning=random.uniform(0.1, 0.9),
            memory_retention=random.uniform(0.3, 0.9),
            planning_horizon=random.randint(2, 10),
            reflection_depth=random.randint(1, 4),
        )

    @classmethod
    def from_parent(
        cls, parent: "BehavioralParams", mutation_rate: float = 0.1
    ) -> "BehavioralParams":
        """Create params from parent with mutation."""
        return cls(
            exploration_rate=max(
                0.05, min(0.95, parent.exploration_rate + random.gauss(0, mutation_rate))
            ),
            risk_tolerance=max(
                0.05, min(0.95, parent.risk_tolerance + random.gauss(0, mutation_rate))
            ),
            creativity=max(0.05, min(0.95, parent.creativity + random.gauss(0, mutation_rate))),
            persistence=max(0.05, min(0.95, parent.persistence + random.gauss(0, mutation_rate))),
            social_learning=max(
                0.05, min(0.95, parent.social_learning + random.gauss(0, mutation_rate))
            ),
            memory_retention=max(
                0.1, min(0.95, parent.memory_retention + random.gauss(0, mutation_rate))
            ),
            planning_horizon=max(1, min(15, parent.planning_horizon + random.randint(-1, 1))),
            reflection_depth=max(1, min(5, parent.reflection_depth + random.randint(-1, 1))),
        )


@dataclass
class AgentInstance:
    """An agent instance with unique behavioral parameters."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    params: BehavioralParams = field(default_factory=BehavioralParams)
    parent_id: str | None = None
    generation: int = 0
    fitness: float = 0.0
    total_reward: float = 0.0
    episodes: int = 0
    success_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_active: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)

    def update_fitness(self, reward: float, success: bool):
        """Update fitness based on outcome."""
        self.total_reward += reward
        self.episodes += 1
        if success:
            self.success_count += 1
        # Exponential moving average of reward
        alpha = 0.1
        self.fitness = alpha * reward + (1 - alpha) * self.fitness
        self.last_active = datetime.utcnow()

    @property
    def success_rate(self) -> float:
        return self.success_count / max(1, self.episodes)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "params": self.params.to_dict(),
            "parent_id": self.parent_id,
            "generation": self.generation,
            "fitness": self.fitness,
            "total_reward": self.total_reward,
            "episodes": self.episodes,
            "success_count": self.success_count,
            "success_rate": self.success_rate,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
        }


class AgentPopulation:
    """Population of agent instances with behavioral variation."""

    def __init__(self, data_dir: str = "data/agent_population"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.agents: dict[str, AgentInstance] = {}
        self.logger = structlog.get_logger(component="agent_population")
        self._load()

    def _load(self):
        """Load population from disk."""
        population_file = self.data_dir / "population.json"
        if population_file.exists():
            try:
                with open(population_file) as f:
                    data = json.load(f)
                for agent_data in data.get("agents", []):
                    agent = AgentInstance(
                        id=agent_data["id"],
                        name=agent_data.get("name", ""),
                        params=BehavioralParams(**agent_data.get("params", {})),
                        parent_id=agent_data.get("parent_id"),
                        generation=agent_data.get("generation", 0),
                        fitness=agent_data.get("fitness", 0.0),
                        total_reward=agent_data.get("total_reward", 0.0),
                        episodes=agent_data.get("episodes", 0),
                        success_count=agent_data.get("success_count", 0),
                    )
                    self.agents[agent.id] = agent
                self.logger.info("population_loaded", count=len(self.agents))
            except Exception as e:
                self.logger.warning("population_load_failed", error=str(e))

    def _save(self):
        """Save population to disk."""
        population_file = self.data_dir / "population.json"
        data = {
            "agents": [a.to_dict() for a in self.agents.values()],
            "saved_at": datetime.utcnow().isoformat(),
        }
        with open(population_file, "w") as f:
            json.dump(data, f, indent=2)

    def create_agent(
        self,
        name: str = "",
        params: BehavioralParams | None = None,
        parent_id: str | None = None,
    ) -> AgentInstance:
        """Create a new agent instance."""
        if params is None:
            if parent_id and parent_id in self.agents:
                parent = self.agents[parent_id]
                params = BehavioralParams.from_parent(parent.params)
                generation = parent.generation + 1
            else:
                params = BehavioralParams.random()
                generation = 0

        agent = AgentInstance(
            name=name or f"agent_{len(self.agents)}",
            params=params,
            parent_id=parent_id,
            generation=generation,
        )
        self.agents[agent.id] = agent
        self._save()
        self.logger.info("agent_created", id=agent.id, name=agent.name, generation=agent.generation)
        return agent

    def select_parent(self, top_k: int = 3) -> AgentInstance | None:
        """Select a parent for reproduction based on fitness."""
        if not self.agents:
            return None
        sorted_agents = sorted(self.agents.values(), key=lambda a: a.fitness, reverse=True)
        candidates = sorted_agents[:top_k]
        return random.choice(candidates) if candidates else None

    def reproduce(self, mutation_rate: float = 0.1) -> AgentInstance:
        """Create a new agent from the best performers."""
        parent = self.select_parent()
        if parent:
            return self.create_agent(
                name=f"child_{len(self.agents)}",
                parent_id=parent.id,
            )
        return self.create_agent()

    def get_best(self, n: int = 5) -> list[AgentInstance]:
        """Get the top N agents by fitness."""
        return sorted(self.agents.values(), key=lambda a: a.fitness, reverse=True)[:n]

    def get_diverse_sample(self, n: int = 5) -> list[AgentInstance]:
        """Get a diverse sample of agents (maximize behavioral distance)."""
        if len(self.agents) <= n:
            return list(self.agents.values())

        # Simple diversity sampling: pick agents with most different params
        selected = [random.choice(list(self.agents.values()))]
        remaining = [a for a in self.agents.values() if a.id != selected[0].id]

        while len(selected) < n and remaining:
            # Find agent most different from already selected
            best_candidate = None
            best_distance = -1
            for candidate in remaining:
                min_distance = float("inf")
                for sel in selected:
                    distance = self._behavioral_distance(candidate.params, sel.params)
                    min_distance = min(min_distance, distance)
                if min_distance > best_distance:
                    best_distance = min_distance
                    best_candidate = candidate
            if best_candidate:
                selected.append(best_candidate)
                remaining.remove(best_candidate)

        return selected

    def _behavioral_distance(self, p1: BehavioralParams, p2: BehavioralParams) -> float:
        """Calculate behavioral distance between two parameter sets."""
        return (
            abs(p1.exploration_rate - p2.exploration_rate)
            + abs(p1.risk_tolerance - p2.risk_tolerance)
            + abs(p1.creativity - p2.creativity)
            + abs(p1.persistence - p2.persistence)
            + abs(p1.social_learning - p2.social_learning)
            + abs(p1.memory_retention - p2.memory_retention)
        ) / 6.0

    def propagate_successful_strategies(
        self,
        successful_agent_id: str,
        num_offspring: int = 2,
        mutation_rate: float = 0.05,
    ) -> list[AgentInstance]:
        """Propagate strategies from a successful agent."""
        if successful_agent_id not in self.agents:
            return []

        parent = self.agents[successful_agent_id]
        offspring = []
        for _ in range(num_offspring):
            child = self.create_agent(
                name=f"propagated_{len(self.agents)}",
                parent_id=parent.id,
            )
            offspring.append(child)

        self.logger.info(
            "strategies_propagated",
            parent=successful_agent_id,
            offspring=len(offspring),
        )
        return offspring

    def get_population_stats(self) -> dict:
        """Get population statistics."""
        if not self.agents:
            return {"count": 0}

        agents = list(self.agents.values())
        fitnesses = [a.fitness for a in agents]
        episodes = [a.episodes for a in agents]
        generations = [a.generation for a in agents]

        return {
            "count": len(agents),
            "avg_fitness": sum(fitnesses) / len(fitnesses),
            "max_fitness": max(fitnesses),
            "min_fitness": min(fitnesses),
            "avg_episodes": sum(episodes) / len(episodes),
            "max_generation": max(generations),
            "avg_success_rate": sum(a.success_rate for a in agents) / len(agents),
        }

    def to_context(self) -> str:
        """Convert population state to context string."""
        stats = self.get_population_stats()
        best = self.get_best(3)
        lines = [
            f"Agent Population: {stats['count']} agents",
            f"  Avg Fitness: {stats.get('avg_fitness', 0):.3f}",
            f"  Best Fitness: {stats.get('max_fitness', 0):.3f}",
            f"  Max Generation: {stats.get('max_generation', 0)}",
        ]
        if best:
            lines.append("  Top Agents:")
            for agent in best:
                lines.append(
                    f"    {agent.name}: fitness={agent.fitness:.3f}, episodes={agent.episodes}"
                )
        return "\n".join(lines)
