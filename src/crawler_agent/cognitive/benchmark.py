"""Benchmark harness for held-out evaluation of agent capabilities."""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .backend import CognitiveBackend


@dataclass
class BenchmarkTask:
    """A single benchmark task."""
    id: str
    category: str  # coding, reasoning, planning, etc.
    prompt: str
    expected_output: str | None = None
    evaluation_criteria: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    """Result of running a benchmark task."""
    task_id: str
    success: bool
    score: float  # 0-1
    output: str
    latency_ms: float
    tokens_used: int
    error: str | None = None


@dataclass
class BenchmarkSuite:
    """Collection of benchmark tasks."""
    name: str
    tasks: list[BenchmarkTask] = field(default_factory=list)
    version: str = "1.0"

    def add_task(self, task: BenchmarkTask) -> None:
        self.tasks.append(task)

    def get_tasks_by_category(self, category: str) -> list[BenchmarkTask]:
        return [t for t in self.tasks if t.category == category]


class TaskEvaluator(ABC):
    """Abstract evaluator for benchmark tasks."""

    @abstractmethod
    async def evaluate(
        self,
        task: BenchmarkTask,
        output: str,
        backend: CognitiveBackend,
    ) -> float:
        """Return score 0-1."""
        ...


class CodeTaskEvaluator(TaskEvaluator):
    """Evaluates coding tasks by running generated code."""

    def __init__(self, sandbox: Any):
        self.sandbox = sandbox

    async def evaluate(
        self,
        task: BenchmarkTask,
        output: str,
        backend: CognitiveBackend,
    ) -> float:
        # Extract code from output
        import re
        code_match = re.search(r"```python\n(.*?)\n```", output, re.DOTALL)
        if not code_match:
            return 0.0
        code = code_match.group(1)

        # Run in sandbox
        try:
            result = await self.sandbox.execute_command(
                f"python -c {code!r}"
            )
            return 1.0 if result.get("success") else 0.0
        except Exception:
            return 0.0


class ReasoningTaskEvaluator(TaskEvaluator):
    """Evaluates reasoning tasks using LLM-as-judge."""

    def __init__(self, backend: CognitiveBackend):
        self.backend = backend

    async def evaluate(
        self,
        task: BenchmarkTask,
        output: str,
        backend: CognitiveBackend,
    ) -> float:
        prompt = f"""Evaluate the quality of this reasoning output.

Task: {task.prompt}
Criteria: {', '.join(task.evaluation_criteria)}

Output:
{output}

Score 0-1 based on:
- Correctness of final answer
- Quality of reasoning steps
- Completeness

Return ONLY a JSON object: {{"score": 0.85, "reasoning": "..."}}"""

        response = await self.backend.complete(prompt, temperature=0.1)
        try:
            data = response.parsed_json
            return data.get("score", 0.0)
        except Exception:
            return 0.0


class PlanningTaskEvaluator(TaskEvaluator):
    """Evaluates planning tasks."""

    def __init__(self, backend: CognitiveBackend):
        self.backend = backend

    async def evaluate(
        self,
        task: BenchmarkTask,
        output: str,
        backend: CognitiveBackend,
    ) -> float:
        prompt = f"""Evaluate this plan.

Goal: {task.prompt}
Plan:
{output}

Criteria: {', '.join(task.evaluation_criteria)}

Score 0-1 for:
- Completeness (all steps needed?)
- Correctness (valid dependencies?)
- Feasibility (executable?)
- Efficiency (minimal steps?)

Return ONLY: {{"score": 0.75, "reasoning": "..."}}"""

        response = await self.backend.complete(prompt, temperature=0.1)
        try:
            return response.parsed_json.get("score", 0.0)
        except Exception:
            return 0.0


class BenchmarkHarness:
    """Runs benchmark suites and tracks performance over time."""

    def __init__(
        self,
        backend: CognitiveBackend,
        sandbox: Any = None,
        results_dir: str = "data/benchmarks",
    ):
        self.backend = backend
        self.sandbox = sandbox
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        self.evaluators = {
            "coding": CodeTaskEvaluator(sandbox) if sandbox else None,
            "reasoning": ReasoningTaskEvaluator(backend),
            "planning": PlanningTaskEvaluator(backend),
        }

        self.suites: dict[str, BenchmarkSuite] = {}
        self._load_default_suites()

    def _load_default_suites(self) -> None:
        """Create default benchmark suites."""
        # Coding benchmarks
        coding = BenchmarkSuite("coding_v1")
        coding.add_task(BenchmarkTask(
            id="code_fibonacci",
            category="coding",
            prompt="Write a Python function fibonacci(n) that returns the nth Fibonacci number efficiently.",
            evaluation_criteria=["correctness", "efficiency", "handles edge cases"],
        ))
        coding.add_task(BenchmarkTask(
            id="code_binary_search",
            category="coding",
            prompt="Implement binary search on a sorted list. Return index or -1.",
            evaluation_criteria=["correctness", "O(log n)", "edge cases"],
        ))
        coding.add_task(BenchmarkTask(
            id="code_serialize_tree",
            category="coding",
            prompt="Write code to serialize and deserialize a binary tree.",
            evaluation_criteria=["correctness", "handles None", "round-trip"],
        ))
        coding.add_task(BenchmarkTask(
            id="code_lru_cache",
            category="coding",
            prompt="Implement an LRU cache with get/put in O(1).",
            evaluation_criteria=["O(1) operations", "eviction works", "thread-safe optional"],
        ))
        coding.add_task(BenchmarkTask(
            id="code_async_fetcher",
            category="coding",
            prompt="Write an async function that fetches URLs concurrently with a semaphore limit.",
            evaluation_criteria=["concurrency limit", "error handling", "returns results"],
        ))
        self.suites["coding"] = coding

        # Reasoning benchmarks
        reasoning = BenchmarkSuite("reasoning_v1")
        reasoning.add_task(BenchmarkTask(
            id="reason_syllogism",
            category="reasoning",
            prompt="All humans are mortal. Socrates is human. Is Socrates mortal? Explain.",
            evaluation_criteria=["valid deduction", "clear explanation"],
        ))
        reasoning.add_task(BenchmarkTask(
            id="reason_counterfactual",
            category="reasoning",
            prompt="If gravity stopped for 5 seconds, what would happen to Earth's atmosphere?",
            evaluation_criteria=["physics accuracy", "causal chain", "specifics"],
        ))
        reasoning.add_task(BenchmarkTask(
            id="reason_probability",
            category="reasoning",
            prompt="A test for a rare disease (1 in 1000) has 99% accuracy. You test positive. What's the probability you have it?",
            evaluation_criteria=["Bayes theorem", "correct calculation", "explains base rate"],
        ))
        self.suites["reasoning"] = reasoning

        # Planning benchmarks
        planning = BenchmarkSuite("planning_v1")
        planning.add_task(BenchmarkTask(
            id="plan_web_scraper",
            category="planning",
            prompt="Plan: Build a web scraper that respects robots.txt, handles rate limits, and stores results in SQLite.",
            evaluation_criteria=["robots.txt", "rate limiting", "SQLite schema", "error handling", "modularity"],
        ))
        planning.add_task(BenchmarkTask(
            id="plan_ml_pipeline",
            category="planning",
            prompt="Plan: End-to-end ML pipeline: data ingestion -> validation -> training -> evaluation -> deployment.",
            evaluation_criteria=["stages", "validation", "monitoring", "rollback", "automation"],
        ))
        self.suites["planning"] = planning

    def register_suite(self, suite: BenchmarkSuite) -> None:
        self.suites[suite.name] = suite

    async def run_suite(
        self,
        suite_name: str,
        max_tasks: int | None = None,
    ) -> list[BenchmarkResult]:
        """Run all tasks in a suite."""
        suite = self.suites.get(suite_name)
        if not suite:
            return []

        tasks = suite.tasks[:max_tasks] if max_tasks else suite.tasks
        results = []

        for task in tasks:
            result = await self._run_task(task)
            results.append(result)

        # Save results
        await self._save_results(suite_name, results)
        return results

    async def _run_task(self, task: BenchmarkTask) -> BenchmarkResult:
        start = time.perf_counter()
        try:
            response = await self.backend.complete(
                task.prompt,
                temperature=0.3,
                max_tokens=2000,
            )
            output = response.content
            latency = (time.perf_counter() - start) * 1000

            evaluator = self.evaluators.get(task.category)
            if evaluator:
                score = await evaluator.evaluate(task, output, self.backend)
            else:
                score = 0.5  # Default

            return BenchmarkResult(
                task_id=task.id,
                success=score > 0.6,
                score=score,
                output=output,
                latency_ms=latency,
                tokens_used=response.tokens_used,
            )
        except Exception as e:
            return BenchmarkResult(
                task_id=task.id,
                success=False,
                score=0.0,
                output="",
                latency_ms=(time.perf_counter() - start) * 1000,
                tokens_used=0,
                error=str(e),
            )

    async def _save_results(self, suite_name: str, results: list[BenchmarkResult]) -> None:
        import datetime
        timestamp = datetime.datetime.utcnow().isoformat()
        data = {
            "suite": suite_name,
            "timestamp": timestamp,
            "results": [
                {
                    "task_id": r.task_id,
                    "success": r.success,
                    "score": r.score,
                    "latency_ms": r.latency_ms,
                    "tokens_used": r.tokens_used,
                    "error": r.error,
                }
                for r in results
            ],
            "summary": {
                "total": len(results),
                "passed": sum(1 for r in results if r.success),
                "avg_score": sum(r.score for r in results) / len(results) if results else 0,
                "avg_latency_ms": sum(r.latency_ms for r in results) / len(results) if results else 0,
            },
        }
        filepath = self.results_dir / f"{suite_name}_{timestamp.replace(':', '-')}.json"
        filepath.write_text(json.dumps(data, indent=2))

    async def run_all(self, max_per_suite: int | None = None) -> dict[str, list[BenchmarkResult]]:
        """Run all registered suites."""
        all_results = {}
        for name in self.suites:
            all_results[name] = await self.run_suite(name, max_per_suite)
        return all_results

    def get_history(self, suite_name: str, limit: int = 10) -> list[dict]:
        """Load historical results."""
        files = sorted(self.results_dir.glob(f"{suite_name}_*.json"))[-limit:]
        history = []
        for f in files:
            try:
                history.append(json.loads(f.read_text()))
            except Exception:
                pass
        return history

    def compare_versions(self, suite_name: str, baseline_file: str, current_file: str) -> dict:
        """Compare two benchmark runs."""
        baseline = json.loads(Path(baseline_file).read_text())
        current = json.loads(Path(current_file).read_text())

        b_scores = {r["task_id"]: r["score"] for r in baseline["results"]}
        c_scores = {r["task_id"]: r["score"] for r in current["results"]}

        improvements = []
        regressions = []
        for task_id in set(b_scores) | set(c_scores):
            b = b_scores.get(task_id, 0)
            c = c_scores.get(task_id, 0)
            diff = c - b
            if diff > 0.1:
                improvements.append({"task": task_id, "delta": diff})
            elif diff < -0.1:
                regressions.append({"task": task_id, "delta": diff})

        return {
            "improvements": improvements,
            "regressions": regressions,
            "baseline_avg": sum(b_scores.values()) / len(b_scores) if b_scores else 0,
            "current_avg": sum(c_scores.values()) / len(c_scores) if c_scores else 0,
        }


# Default benchmark tasks
DEFAULT_CODING_TASKS = [
    BenchmarkTask(
        id="implement_trie",
        category="coding",
        prompt="Implement a Trie (prefix tree) with insert, search, and startsWith methods.",
        evaluation_criteria=["correctness", "time complexity", "memory efficiency"],
    ),
    BenchmarkTask(
        id="implement_graph",
        category="coding",
        prompt="Implement a directed graph with topological sort (Kahn's algorithm).",
        evaluation_criteria=["correctness", "cycle detection", "handles disconnected"],
    ),
    BenchmarkTask(
        id="async_rate_limiter",
        category="coding",
        prompt="Create an async token bucket rate limiter class.",
        evaluation_criteria=["token bucket logic", "async safe", "burst handling"],
    ),
]

DEFAULT_REASONING_TASKS = [
    BenchmarkTask(
        id="causal_chain",
        category="reasoning",
        prompt="A causes B. B causes C. C causes D. If A is prevented, what happens to D? Explain the causal chain.",
        evaluation_criteria=["causal logic", "transitivity", "clear explanation"],
    ),
    BenchmarkTask(
        id="game_theory",
        category="reasoning",
        prompt="Two prisoners can cooperate or defect. Payoff: both cooperate = 3 each; both defect = 1 each; one defects = 5/0. What's the Nash equilibrium?",
        evaluation_criteria=["Nash equilibrium", "dominant strategy", "explanation"],
    ),
]

DEFAULT_PLANNING_TASKS = [
    BenchmarkTask(
        id="plan_cicd",
        category="planning",
        prompt="Design a CI/CD pipeline for a Python project with testing, linting, security scanning, and staged deployments.",
        evaluation_criteria=["stages", "gates", "rollback", "environments", "security"],
    ),
]


async def create_benchmark_harness(backend: CognitiveBackend, sandbox: Any) -> BenchmarkHarness:
    harness = BenchmarkHarness(backend, sandbox)
    # Add default tasks
    for t in DEFAULT_CODING_TASKS:
        harness.suites["coding"].add_task(t)
    for t in DEFAULT_REASONING_TASKS:
        harness.suites["reasoning"].add_task(t)
    for t in DEFAULT_PLANNING_TASKS:
        harness.suites["planning"].add_task(t)
    return harness