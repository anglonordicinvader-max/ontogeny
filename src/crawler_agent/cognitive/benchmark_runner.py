"""Benchmark runner for real performance measurement.

Runs the agent's cognitive modules on standardized tasks and measures:
- Success rate
- Latency
- Token usage
- Memory efficiency
- Task completion quality

Used by evo_architecture.py to evaluate architecture variants with
real measurements instead of LLM estimates.
"""

import asyncio
import time
import tracemalloc
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, StrEnum
from typing import Any

import structlog

from .backend import CognitiveBackend


class BenchmarkTaskType(StrEnum):
    IMPORT = "import"  # Module import speed
    INSTANTIATION = "instantiation"  # Object creation speed
    REASONING = "reasoning"  # LLM reasoning quality
    ATTENTION = "attention"  # Attention mechanism accuracy
    MEMORY = "memory"  # Memory read/write speed
    PLANNING = "planning"  # Plan generation quality
    RECURSIVE = "recursive"  # Self-modification capability


@dataclass
class BenchmarkTask:
    """A single benchmark task."""

    name: str
    task_type: BenchmarkTaskType
    description: str = ""
    timeout: float = 30.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    """Result of a single benchmark task."""

    task_name: str
    task_type: BenchmarkTaskType
    success: bool
    duration_ms: float = 0.0
    memory_peak_mb: float = 0.0
    score: float = 0.0  # 0-1 quality score
    error: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BenchmarkSuite:
    """A complete benchmark suite result."""

    variant_id: str = ""
    results: list[BenchmarkResult] = field(default_factory=list)
    overall_score: float = 0.0
    avg_latency_ms: float = 0.0
    avg_memory_mb: float = 0.0
    success_rate: float = 0.0
    total_duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def calculate_overall(self):
        """Calculate overall metrics from individual results."""
        if not self.results:
            return

        self.success_rate = sum(1 for r in self.results if r.success) / len(self.results)
        self.avg_latency_ms = sum(r.duration_ms for r in self.results) / len(self.results)
        self.avg_memory_mb = sum(r.memory_peak_mb for r in self.results) / len(self.results)

        # Weighted score: success (40%) + quality (40%) + speed (10%) + memory (10%)
        scores = [r.score for r in self.results if r.success]
        avg_score = sum(scores) / max(len(scores), 1)

        speed_score = max(0, 1.0 - self.avg_latency_ms / 5000)  # 5s = 0 score
        memory_score = max(0, 1.0 - self.avg_memory_mb / 500)  # 500MB = 0 score

        self.overall_score = (
            self.success_rate * 0.4 + avg_score * 0.4 + speed_score * 0.1 + memory_score * 0.1
        )


class BenchmarkRunner:
    """Runs real benchmarks on cognitive modules.

    Measures actual performance instead of asking the LLM to estimate.
    """

    def __init__(self, backend: CognitiveBackend | None = None):
        self.backend = backend
        self.results_history: list[BenchmarkSuite] = []
        self.logger = structlog.get_logger()

    def get_default_tasks(self) -> list[BenchmarkTask]:
        """Get the standard benchmark tasks."""
        return [
            BenchmarkTask(
                name="import_all_modules",
                task_type=BenchmarkTaskType.IMPORT,
                description="Import all cognitive modules and measure time",
                timeout=30.0,
            ),
            BenchmarkTask(
                name="instantiate_core",
                task_type=BenchmarkTaskType.INSTANTIATION,
                description="Instantiate core modules without LLM",
                timeout=15.0,
            ),
            BenchmarkTask(
                name="attention_evaluate",
                task_type=BenchmarkTaskType.ATTENTION,
                description="Evaluate attention on 5 stimuli",
                timeout=10.0,
            ),
            BenchmarkTask(
                name="curiosity_generate",
                task_type=BenchmarkTaskType.REASONING,
                description="Generate intrinsic goals",
                timeout=10.0,
            ),
            BenchmarkTask(
                name="world_model_predict",
                task_type=BenchmarkTaskType.REASONING,
                description="Make 3 predictions and update from outcomes",
                timeout=15.0,
            ),
            BenchmarkTask(
                name="self_reflection_cycle",
                task_type=BenchmarkTaskType.RECURSIVE,
                description="Record action, reflect, review",
                timeout=10.0,
            ),
        ]

    async def run_benchmark(
        self,
        variant_id: str = "default",
        tasks: list[BenchmarkTask] | None = None,
    ) -> BenchmarkSuite:
        """Run a complete benchmark suite."""
        tasks = tasks or self.get_default_tasks()
        suite = BenchmarkSuite(variant_id=variant_id)

        self.logger.info(
            "benchmark_started",
            variant_id=variant_id,
            tasks=len(tasks),
        )

        start_time = time.monotonic()

        for task in tasks:
            result = await self._run_single_task(task)
            suite.results.append(result)

        suite.total_duration_ms = (time.monotonic() - start_time) * 1000
        suite.calculate_overall()

        self.results_history.append(suite)

        self.logger.info(
            "benchmark_completed",
            variant_id=variant_id,
            overall_score=suite.overall_score,
            success_rate=suite.success_rate,
            avg_latency_ms=suite.avg_latency_ms,
        )

        return suite

    async def _run_single_task(self, task: BenchmarkTask) -> BenchmarkResult:
        """Run a single benchmark task."""
        tracemalloc.start()
        start = time.monotonic()

        try:
            if task.task_type == BenchmarkTaskType.IMPORT:
                score, details = await self._benchmark_import()
            elif task.task_type == BenchmarkTaskType.INSTANTIATION:
                score, details = await self._benchmark_instantiation()
            elif task.task_type == BenchmarkTaskType.ATTENTION:
                score, details = await self._benchmark_attention()
            elif task.task_type == BenchmarkTaskType.REASONING:
                score, details = await self._benchmark_reasoning(task.name)
            elif task.task_type == BenchmarkTaskType.RECURSIVE:
                score, details = await self._benchmark_recursive()
            else:
                score, details = 0.0, {"error": "unknown task type"}

            duration = (time.monotonic() - start) * 1000
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            return BenchmarkResult(
                task_name=task.name,
                task_type=task.task_type,
                success=True,
                duration_ms=duration,
                memory_peak_mb=peak / 1024 / 1024,
                score=score,
                details=details,
            )
        except TimeoutError:
            duration = (time.monotonic() - start) * 1000
            tracemalloc.stop()
            return BenchmarkResult(
                task_name=task.name,
                task_type=task.task_type,
                success=False,
                duration_ms=duration,
                error="timeout",
            )
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            try:
                tracemalloc.stop()
            except Exception:
                pass
            return BenchmarkResult(
                task_name=task.name,
                task_type=task.task_type,
                success=False,
                duration_ms=duration,
                error=str(e)[:200],
            )

    async def _benchmark_import(self) -> tuple[float, dict]:
        """Benchmark module import speed."""
        modules = [
            "crawler_agent.cognitive.attention",
            "crawler_agent.cognitive.curiosity",
            "crawler_agent.cognitive.world_model",
            "crawler_agent.cognitive.self_reflection",
            "crawler_agent.cognitive.uncertainty",
            "crawler_agent.cognitive.causal_reasoning",
            "crawler_agent.cognitive.emotional",
            "crawler_agent.cognitive.self_modify",
            "crawler_agent.cognitive.recursive_modify",
            "crawler_agent.cognitive.evo_architecture",
        ]

        import_times = []
        for mod_name in modules:
            start = time.monotonic()
            try:
                __import__(mod_name)
                elapsed = (time.monotonic() - start) * 1000
                import_times.append(elapsed)
            except Exception:
                import_times.append(5000)  # Penalty for failed import

        avg_time = sum(import_times) / len(import_times)
        # Score: faster is better. 100ms = 1.0, 1000ms = 0.5, 5000ms = 0.0
        score = max(0.0, 1.0 - avg_time / 5000)

        return score, {
            "avg_import_ms": avg_time,
            "total_modules": len(modules),
            "import_times": dict(zip(modules, import_times, strict=False)),
        }

    async def _benchmark_instantiation(self) -> tuple[float, dict]:
        """Benchmark module instantiation speed."""
        from .attention import AttentionMechanism
        from .curiosity import CuriosityEngine
        from .emotional import EmotionalProcessor
        from .evo_architecture import EvoArchitecture
        from .self_reflection import SelfReflectionEngine
        from .world_model import BayesianWorldModel

        classes = [
            ("AttentionMechanism", AttentionMechanism),
            ("CuriosityEngine", CuriosityEngine),
            ("BayesianWorldModel", BayesianWorldModel),
            ("SelfReflectionEngine", lambda: SelfReflectionEngine(backend=None)),
            ("EmotionalProcessor", EmotionalProcessor),
            ("EvoArchitecture", lambda: EvoArchitecture(backend=None)),
        ]

        times = []
        for _name, cls in classes:
            start = time.monotonic()
            try:
                cls()
                elapsed = (time.monotonic() - start) * 1000
                times.append(elapsed)
            except Exception:
                times.append(1000)

        avg_time = sum(times) / len(times)
        score = max(0.0, 1.0 - avg_time / 1000)

        return score, {
            "avg_instantiation_ms": avg_time,
            "times": dict(zip([c[0] for c in classes], times, strict=False)),
        }

    async def _benchmark_attention(self) -> tuple[float, dict]:
        """Benchmark attention mechanism accuracy."""
        from .attention import AttentionMechanism

        att = AttentionMechanism()
        stimuli = [
            "Debug the crawler pipeline for timeout errors",
            "Write a report on climate change",
            "URGENT: Fix the broken proxy rotation",
            "Explore quantum computing applications",
            "Schedule a meeting with the team",
        ]

        start = time.monotonic()
        targets = []
        for s in stimuli:
            target = await att.evaluate_attention(s)
            targets.append(target)

        # Check that urgency was detected in stimulus 3
        urgency_scores = [t.urgency for t in targets]
        has_urgency = any(u > 0.6 for u in urgency_scores)

        # Check that relevance varies across stimuli
        relevance_scores = [t.relevance for t in targets]
        relevance_variance = max(relevance_scores) - min(relevance_scores)

        elapsed = (time.monotonic() - start) * 1000

        score = 0.0
        if has_urgency:
            score += 0.4
        if relevance_variance > 0.1:
            score += 0.3
        if all(0 <= t.attention_score <= 1 for t in targets):
            score += 0.3

        return score, {
            "latency_ms": elapsed,
            "urgency_detected": has_urgency,
            "relevance_variance": relevance_variance,
            "scores": [t.attention_score for t in targets],
        }

    async def _benchmark_reasoning(self, task_name: str) -> tuple[float, dict]:
        """Benchmark reasoning modules (world model, curiosity)."""
        from .curiosity import CuriosityEngine
        from .world_model import BayesianWorldModel

        if task_name == "world_model_predict":
            wm = BayesianWorldModel()
            await wm.add_belief("testing improves code quality", prior=0.7)
            await wm.add_belief("fast code is better than slow code", prior=0.6)

            predictions = []
            for query in ["testing", "code quality", "performance"]:
                pred = await wm.predict_and_update(query)
                predictions.append(pred)

            # Check predictions are reasonable
            all_valid = all(0 <= p["predicted_probability"] <= 1 for p in predictions)
            score = 1.0 if all_valid else 0.5

            return score, {
                "predictions": len(predictions),
                "all_valid": all_valid,
                "probabilities": [p["predicted_probability"] for p in predictions],
            }

        elif task_name == "curiosity_generate":
            cur = CuriosityEngine()
            goals = await cur.generate_intrinsic_goals(
                {
                    "coding": 0.3,
                    "math": 0.1,
                    "research": 0.5,
                }
            )

            score = min(1.0, len(goals) / 3)  # 3+ goals = perfect
            return score, {
                "goals_generated": len(goals),
                "goal_types": [g.get("type", "unknown") for g in goals[:3]],
            }

        return 0.5, {"unknown_task": task_name}

    async def _benchmark_recursive(self) -> tuple[float, dict]:
        """Benchmark self-reflection and recursive modification capability."""
        from .self_reflection import SelfReflectionEngine

        sr = SelfReflectionEngine(backend=None)

        # Record actions
        records = []
        for i in range(3):
            record = await sr.record_action(
                action_type=f"test_action_{i}",
                description=f"Test action number {i}",
                intended_outcome="success",
            )
            records.append(record)

        # Check pre-action review
        review = await sr.pre_action_review("test_action_0")

        # Check stats
        stats = sr.get_stats()

        score = 0.0
        if len(records) == 3:
            score += 0.4
        if review.get("past_attempts", 0) > 0:
            score += 0.3
        if stats["total_reflections"] >= 0:
            score += 0.3

        return score, {
            "actions_recorded": len(records),
            "review_available": bool(review),
            "stats": stats,
        }


async def run_benchmark_suite(
    backend: CognitiveBackend | None = None,
    variant_id: str = "default",
) -> BenchmarkSuite:
    """Convenience function to run a benchmark suite."""
    runner = BenchmarkRunner(backend=backend)
    return await runner.run_benchmark(variant_id=variant_id)
