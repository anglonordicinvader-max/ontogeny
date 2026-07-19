"""Evolutionary Architecture Search - evolves agent architecture variants.

Instead of designing fixed architectures, this module:
- Generates architecture variants via mutation/crossover
- Evaluates each variant in simulation
- Selects the best performers for the next generation
- Enables the agent to evolve its own cognitive structure
"""

import copy
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, StrEnum
from typing import Any

import structlog

from .backend import CognitiveBackend


class ArchitectureComponent(StrEnum):
    ATTENTION = "attention"
    WORKING_MEMORY = "working_memory"
    LONG_TERM_MEMORY = "long_term_memory"
    REASONING = "reasoning"
    PLANNING = "planning"
    EMOTION = "emotion"
    PERCEPTION = "perception"
    ACTION_SELECTION = "action_selection"
    SELF_MODEL = "self_model"
    CAUSAL_REASONING = "causal_reasoning"


class MutationType(StrEnum):
    PARAMETER = "parameter"  # Tweak a parameter
    ADD_COMPONENT = "add_component"
    REMOVE_COMPONENT = "remove_component"
    MODIFY_CONNECTION = "modify_connection"
    SWAP_STRATEGY = "swap_strategy"


@dataclass
class ArchitectureVariant:
    """A variant of the agent architecture."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    components: dict[str, dict[str, Any]] = field(default_factory=dict)
    connections: list[dict[str, str]] = field(default_factory=list)
    fitness: float = 0.0
    evaluation_count: int = 0
    generation: int = 0
    parent_id: str = ""
    mutations: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_config(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "components": self.components,
            "connections": self.connections,
            "fitness": self.fitness,
        }


@dataclass
class EvaluationResult:
    """Result of evaluating an architecture variant."""

    variant_id: str = ""
    task_accuracy: float = 0.0
    task_efficiency: float = 0.0  # Time/resources per task
    generalization: float = 0.0  # Performance on unseen tasks
    robustness: float = 0.0  # Performance under noise
    resource_usage: float = 0.0  # Memory/compute efficiency
    overall_fitness: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


class EvoArchitecture:
    """Evolutionary architecture search.

    Evolves the agent's cognitive architecture by:
    1. Generating variants via mutation/crossover
    2. Evaluating with REAL benchmarks (not LLM estimates)
    3. Selecting the fittest
    """

    def __init__(self, backend: CognitiveBackend):
        self.backend = backend
        self.variants: dict[str, ArchitectureVariant] = {}
        self.best_variant: ArchitectureVariant | None = None
        self.generation = 0
        self.population_size = 5
        self.mutation_rate = 0.3
        self.crossover_rate = 0.5
        self.evaluation_history: list[EvaluationResult] = []
        self.benchmark_runner = None  # Initialized lazily
        self.use_real_benchmarks = True
        self.logger = structlog.get_logger()

    def _get_benchmark_runner(self):
        """Lazy-load benchmark runner to avoid circular imports."""
        if self.benchmark_runner is None:
            from .benchmark_runner import BenchmarkRunner

            self.benchmark_runner = BenchmarkRunner(backend=self.backend)
        return self.benchmark_runner

    async def initialize_population(self) -> list[ArchitectureVariant]:
        """Create initial population of architecture variants."""
        defaults = self._get_default_components()
        population = []

        for i in range(self.population_size):
            variant = ArchitectureVariant(
                name=f"variant_{self.generation}_{i}",
                components=copy.deepcopy(defaults),
                connections=self._get_default_connections(),
                generation=self.generation,
            )
            # Add random variation to each
            variant = self._mutate(variant, rate=0.2)
            self.variants[variant.id] = variant
            population.append(variant)

        self.logger.info("population_initialized", size=len(population))
        return population

    async def evaluate_variant(
        self,
        variant: ArchitectureVariant,
        test_tasks: list[str],
    ) -> EvaluationResult:
        """Evaluate an architecture variant.

        Uses real benchmarks when available, falls back to LLM estimation.
        """
        if self.use_real_benchmarks:
            return await self._evaluate_with_real_benchmarks(variant)
        return await self._evaluate_with_llm(variant, test_tasks)

    async def _evaluate_with_real_benchmarks(
        self,
        variant: ArchitectureVariant,
    ) -> EvaluationResult:
        """Evaluate variant using real benchmark measurements."""
        runner = self._get_benchmark_runner()

        try:
            suite = await runner.run_benchmark(
                variant_id=variant.id,
                tasks=runner.get_default_tasks(),
            )

            result = EvaluationResult(
                variant_id=variant.id,
                task_accuracy=suite.success_rate,
                task_efficiency=max(0, 1.0 - suite.avg_latency_ms / 5000),
                generalization=suite.overall_score,
                robustness=suite.success_rate,
                resource_usage=min(1.0, suite.avg_memory_mb / 500),
                overall_fitness=suite.overall_score,
            )
        except Exception as e:
            self.logger.warning("real_benchmark_failed", error=str(e))
            # Fall back to LLM estimation
            return await self._evaluate_with_llm(variant, ["general"])

        variant.fitness = result.overall_fitness
        variant.evaluation_count += 1
        self.evaluation_history.append(result)

        return result

    async def _evaluate_with_llm(
        self,
        variant: ArchitectureVariant,
        test_tasks: list[str],
    ) -> EvaluationResult:
        """Fallback: Evaluate variant using LLM estimation."""
        system_prompt = """You are evaluating a cognitive architecture for an AI agent.

Given an architecture configuration and test tasks, estimate performance.
Consider: component strengths, connection efficiency, bottlenecks.

Return JSON with:
- task_accuracy (0-1)
- task_efficiency (0-1)
- generalization (0-1)
- robustness (0-1)
- resource_usage (0-1, lower is better)
- reasoning: why this architecture works/doesn't work"""

        user_prompt = f"""Architecture: {variant.name}
Components: {variant.components}
Connections: {variant.connections[:10]}

Test Tasks: {test_tasks}

Evaluate:"""

        response = await self.backend.complete(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=1000,
            temperature=0.3,
        )

        try:
            data = response.parsed_json
            accuracy = data.get("task_accuracy", 0.5)
            efficiency = data.get("task_efficiency", 0.5)
            generalization = data.get("generalization", 0.5)
            robustness = data.get("robustness", 0.5)
            resource_usage = data.get("resource_usage", 0.5)

            fitness = (
                accuracy * 0.35
                + generalization * 0.25
                + robustness * 0.2
                + efficiency * 0.1
                + (1 - resource_usage) * 0.1
            )

            result = EvaluationResult(
                variant_id=variant.id,
                task_accuracy=accuracy,
                task_efficiency=efficiency,
                generalization=generalization,
                robustness=robustness,
                resource_usage=resource_usage,
                overall_fitness=fitness,
            )
        except Exception:
            fitness = 0.5
            result = EvaluationResult(variant_id=variant.id, overall_fitness=fitness)

        variant.fitness = fitness
        variant.evaluation_count += 1
        self.evaluation_history.append(result)

        return result

    async def evolve_generation(
        self,
        test_tasks: list[str],
    ) -> list[ArchitectureVariant]:
        """Evolve to the next generation."""
        self.generation += 1

        # Select parents (top 50%)
        evaluated = [v for v in self.variants.values() if v.evaluation_count > 0]
        if not evaluated:
            evaluated = list(self.variants.values())

        evaluated.sort(key=lambda v: v.fitness, reverse=True)
        parents = evaluated[: max(2, len(evaluated) // 2)]

        # Create next generation
        next_gen = []

        # Keep the best (elitism)
        if parents:
            elite = copy.deepcopy(parents[0])
            elite.generation = self.generation
            elite.name = f"elite_{self.generation}"
            next_gen.append(elite)

        while len(next_gen) < self.population_size:
            if random.random() < self.crossover_rate and len(parents) >= 2:
                p1, p2 = random.sample(parents, 2)
                child = self._crossover(p1, p2)
            else:
                parent = random.choice(parents)
                child = self._mutate(parent)

            child.generation = self.generation
            child.name = f"child_{self.generation}_{len(next_gen)}"
            next_gen.append(child)

        # Replace old variants
        self.variants.clear()
        for v in next_gen:
            self.variants[v.id] = v

        # Evaluate new generation
        for v in next_gen:
            if v.evaluation_count == 0:
                await self.evaluate_variant(v, test_tasks)

        # Update best
        best = max(self.variants.values(), key=lambda v: v.fitness)
        if not self.best_variant or best.fitness > self.best_variant.fitness:
            self.best_variant = best

        self.logger.info(
            "generation_evolved",
            generation=self.generation,
            best_fitness=best.fitness,
            population=len(self.variants),
        )

        return list(self.variants.values())

    def _mutate(
        self,
        variant: ArchitectureVariant,
        rate: float | None = None,
    ) -> ArchitectureVariant:
        """Mutate an architecture variant."""
        child = copy.deepcopy(variant)
        child.parent_id = variant.id
        child.id = str(uuid.uuid4())
        child.fitness = 0.0
        child.evaluation_count = 0
        child.mutations = []

        rate = rate or self.mutation_rate

        # Randomly mutate components
        for comp_name in child.components:
            if random.random() < rate:
                comp = child.components[comp_name]
                self._mutate_component(comp)
                child.mutations.append(f"mutate_{comp_name}")

        # Randomly add/remove connections
        if random.random() < rate and child.connections:
            child.connections.pop(random.randint(0, len(child.connections) - 1))
            child.mutations.append("remove_connection")

        return child

    def _crossover(
        self,
        parent1: ArchitectureVariant,
        parent2: ArchitectureVariant,
    ) -> ArchitectureVariant:
        """Crossover two parent architectures."""
        child = ArchitectureVariant(
            parent_id=f"{parent1.id}x{parent2.id}",
        )

        # Take components from both parents
        all_components = set(parent1.components) | set(parent2.components)
        for comp in all_components:
            if random.random() < 0.5:
                if comp in parent1.components:
                    child.components[comp] = copy.deepcopy(parent1.components[comp])
                else:
                    child.components[comp] = copy.deepcopy(parent2.components[comp])
            else:
                if comp in parent2.components:
                    child.components[comp] = copy.deepcopy(parent2.components[comp])
                else:
                    child.components[comp] = copy.deepcopy(parent1.components[comp])

        # Mix connections
        p1_conns = parent1.connections[: len(parent1.connections) // 2]
        p2_conns = parent2.connections[len(parent2.connections) // 2 :]
        child.connections = p1_conns + p2_conns

        child.mutations = ["crossover"]
        return child

    def _mutate_component(self, component: dict[str, Any]):
        """Mutate a single component's parameters."""
        tunable_params = {
            "depth": (1, 5),
            "width": (16, 512),
            "learning_rate": (0.001, 0.1),
            "attention_heads": (1, 8),
            "memory_size": (100, 10000),
            "dropout": (0.0, 0.5),
            "temperature": (0.1, 2.0),
        }

        for param, (lo, hi) in tunable_params.items():
            if param in component and random.random() < 0.5:
                if isinstance(component[param], int):
                    component[param] = random.randint(lo, hi)
                elif isinstance(component[param], float):
                    component[param] = random.uniform(lo, hi)

    def _get_default_components(self) -> dict[str, dict[str, Any]]:
        return {
            ArchitectureComponent.ATTENTION.value: {
                "type": "multi_head",
                "heads": 4,
                "depth": 2,
                "temperature": 1.0,
            },
            ArchitectureComponent.WORKING_MEMORY.value: {
                "capacity": 1000,
                "decay_rate": 0.1,
            },
            ArchitectureComponent.REASONING.value: {
                "type": "chain_of_thought",
                "depth": 3,
                "branching_factor": 2,
            },
            ArchitectureComponent.PLANNING.value: {
                "type": "hierarchical",
                "horizon": 5,
                "branches": 3,
            },
            ArchitectureComponent.EMOTION.value: {
                "type": "dimensional",
                "axes": ["valence", "arousal", "dominance"],
                "decay_rate": 0.05,
            },
            ArchitectureComponent.SELF_MODEL.value: {
                "type": "bayesian",
                "update_rate": 0.1,
                "confidence_threshold": 0.7,
            },
            ArchitectureComponent.ACTION_SELECTION.value: {
                "type": "softmax",
                "temperature": 1.0,
                "exploration_rate": 0.2,
            },
        }

    def _get_default_connections(self) -> list[dict[str, str]]:
        return [
            {"source": "attention", "target": "working_memory"},
            {"source": "working_memory", "target": "reasoning"},
            {"source": "reasoning", "target": "planning"},
            {"source": "emotion", "target": "attention"},
            {"source": "self_model", "target": "action_selection"},
            {"source": "planning", "target": "action_selection"},
        ]

    def get_current_config(self) -> dict[str, Any] | None:
        """Get the best architecture configuration."""
        if self.best_variant:
            return self.best_variant.to_config()
        return None

    def get_benchmark_history(self) -> list[dict[str, Any]]:
        """Get history of benchmark evaluations."""
        return [
            {
                "variant_id": r.variant_id,
                "fitness": r.overall_fitness,
                "accuracy": r.task_accuracy,
                "efficiency": r.task_efficiency,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in self.evaluation_history[-20:]
        ]

    def get_stats(self) -> dict[str, Any]:
        evaluated = [v for v in self.variants.values() if v.evaluation_count > 0]
        return {
            "generation": self.generation,
            "population": len(self.variants),
            "evaluated": len(evaluated),
            "best_fitness": self.best_variant.fitness if self.best_variant else 0,
            "avg_fitness": (sum(v.fitness for v in evaluated) / max(1, len(evaluated))),
            "total_evaluations": len(self.evaluation_history),
            "use_real_benchmarks": self.use_real_benchmarks,
            "benchmark_history": self.get_benchmark_history()[-5:],
        }

    def to_context(self) -> str:
        stats = self.get_stats()
        lines = [
            "EvoArchitecture:",
            f"  Generation: {stats['generation']}",
            f"  Population: {stats['population']}",
            f"  Best Fitness: {stats['best_fitness']:.3f}",
            f"  Avg Fitness: {stats['avg_fitness']:.3f}",
            f"  Real Benchmarks: {stats['use_real_benchmarks']}",
        ]
        if self.best_variant:
            lines.append(f"  Best Variant: {self.best_variant.name}")
            lines.append(f"    Components: {list(self.best_variant.components.keys())}")
            lines.append(f"    Mutations: {self.best_variant.mutations}")
        if stats.get("benchmark_history"):
            lines.append("  Recent Benchmarks:")
            for b in stats["benchmark_history"][-3:]:
                lines.append(f"    {b['variant_id'][:8]}: fitness={b['fitness']:.3f}")
        return "\n".join(lines)
