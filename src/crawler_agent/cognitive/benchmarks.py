"""Capability benchmarks with historical tracking.

Provides:
- Coding benchmarks
- Planning benchmarks
- Reasoning benchmarks
- Historical performance tracking
- Regression detection
- Improvement recommendations
"""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog


@dataclass
class BenchmarkTask:
    id: str
    name: str
    category: str  # coding, planning, reasoning, physics, memory
    difficulty: float  # 0.0 to 1.0
    description: str
    expected_output: str = ""
    time_limit_seconds: float = 30.0
    metadata: Dict = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    task_id: str
    score: float  # 0.0 to 1.0
    time_taken: float
    correct: bool
    output: str = ""
    error: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class BenchmarkRun:
    run_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    results: List[BenchmarkResult] = field(default_factory=list)
    overall_score: float = 0.0
    category_scores: Dict[str, float] = field(default_factory=dict)
    improvement_since_last: float = 0.0
    regressions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp.isoformat(),
            "overall_score": self.overall_score,
            "category_scores": self.category_scores,
            "improvement_since_last": self.improvement_since_last,
            "regressions": self.regressions,
            "num_tasks": len(self.results),
        }


class BenchmarkSuite:
    """Capability benchmarks with historical tracking."""

    def __init__(self, data_dir: str = "data/benchmarks"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logger = structlog.get_logger(component="benchmarks")

        self.tasks: Dict[str, BenchmarkTask] = {}
        self.runs: List[BenchmarkRun] = []
        self.best_scores: Dict[str, float] = {}

        self._setup_tasks()
        self._load()

    def _setup_tasks(self):
        """Setup benchmark tasks."""
        self.tasks = {
            "code_sort": BenchmarkTask(
                id="code_sort", name="Sort Array", category="coding", difficulty=0.3,
                description="Implement a function to sort an array of integers",
            ),
            "code_binary_search": BenchmarkTask(
                id="code_binary_search", name="Binary Search", category="coding", difficulty=0.5,
                description="Implement binary search on a sorted array",
            ),
            "code_fibonacci": BenchmarkTask(
                id="code_fibonacci", name="Fibonacci", category="coding", difficulty=0.4,
                description="Implement efficient fibonacci with memoization",
            ),
            "code_linked_list": BenchmarkTask(
                id="code_linked_list", name="Linked List", category="coding", difficulty=0.6,
                description="Implement a singly linked list with insert, delete, and search",
            ),
            "code_tree_traversal": BenchmarkTask(
                id="code_tree_traversal", name="Tree Traversal", category="coding", difficulty=0.6,
                description="Implement in-order, pre-order, and post-order tree traversal",
            ),
            "plan_tower_hanoi": BenchmarkTask(
                id="plan_tower_hanoi", name="Tower of Hanoi", category="planning", difficulty=0.5,
                description="Plan moves for Tower of Hanoi with 4 disks",
            ),
            "plan_blocks": BenchmarkTask(
                id="plan_blocks", name="Block World", category="planning", difficulty=0.6,
                description="Plan actions to stack blocks A on B on C",
            ),
            "plan_route": BenchmarkTask(
                id="plan_route", name="Route Planning", category="planning", difficulty=0.4,
                description="Find shortest path in a graph with 10 nodes",
            ),
            "plan_schedule": BenchmarkTask(
                id="plan_schedule", name="Task Scheduling", category="planning", difficulty=0.7,
                description="Schedule tasks with dependencies and deadlines",
            ),
            "reason_syllogism": BenchmarkTask(
                id="reason_syllogism", name="Syllogistic Reasoning", category="reasoning", difficulty=0.3,
                description="All men are mortal. Socrates is a man. Therefore?",
            ),
            "reason_analogy": BenchmarkTask(
                id="reason_analogy", name="Analogy", category="reasoning", difficulty=0.5,
                description="A is to B as C is to ? (complete the analogy)",
            ),
            "reason_counterfactual": BenchmarkTask(
                id="reason_counterfactual", name="Counterfactual", category="reasoning", difficulty=0.6,
                description="What would happen if gravity was reversed?",
            ),
            "reason_causal": BenchmarkTask(
                id="reason_causal", name="Causal Reasoning", category="reasoning", difficulty=0.7,
                description="Determine cause and effect in complex scenarios",
            ),
            "physics_projectile": BenchmarkTask(
                id="physics_projectile", name="Projectile Motion", category="physics", difficulty=0.4,
                description="Predict landing position of a thrown object",
            ),
            "physics_collision": BenchmarkTask(
                id="physics_collision", name="Collision", category="physics", difficulty=0.6,
                description="Predict outcome of elastic collision between two objects",
            ),
            "physics_spring": BenchmarkTask(
                id="physics_spring", name="Spring Mass", category="physics", difficulty=0.5,
                description="Predict motion of mass on a spring",
            ),
            "memory_recall": BenchmarkTask(
                id="memory_recall", name="Memory Recall", category="memory", difficulty=0.3,
                description="Recall facts from previous experiments",
            ),
            "memory_sequence": BenchmarkTask(
                id="memory_sequence", name="Sequence Memory", category="memory", difficulty=0.5,
                description="Remember and reproduce a sequence of actions",
            ),
        }

    def _load(self):
        runs_file = self.data_dir / "runs.json"
        if runs_file.exists():
            try:
                data = json.loads(runs_file.read_text())
                for run_data in data.get("runs", []):
                    run = BenchmarkRun(
                        run_id=run_data["run_id"],
                        overall_score=run_data.get("overall_score", 0),
                        category_scores=run_data.get("category_scores", {}),
                        improvement_since_last=run_data.get("improvement_since_last", 0),
                        regressions=run_data.get("regressions", []),
                    )
                    if "timestamp" in run_data:
                        run.timestamp = datetime.fromisoformat(run_data["timestamp"])
                    self.runs.append(run)
            except Exception as e:
                self.logger.warning("runs_load_failed", error=str(e))

    def _save(self):
        runs_file = self.data_dir / "runs.json"
        runs_file.write_text(json.dumps({
            "runs": [run.to_dict() for run in self.runs[-100:]],
            "saved_at": datetime.utcnow().isoformat(),
        }, indent=2))

    def evaluate_code(self, task_id: str, code: str) -> BenchmarkResult:
        """Evaluate code solution."""
        start = time.time()
        task = self.tasks.get(task_id)
        if not task:
            return BenchmarkResult(task_id=task_id, score=0, time_taken=0, correct=False,
                                  error="Unknown task")

        try:
            score = 0.5
            if "def " in code:
                score += 0.1
            if "return" in code:
                score += 0.1
            if len(code) > 50:
                score += 0.1
            if task.category == "coding" and ("for" in code or "while" in code):
                score += 0.1
            score = min(score, 1.0)

            time_taken = time.time() - start
            return BenchmarkResult(
                task_id=task_id,
                score=score,
                time_taken=time_taken,
                correct=score > 0.7,
                output=code[:200],
            )
        except Exception as e:
            return BenchmarkResult(
                task_id=task_id, score=0, time_taken=time.time() - start,
                correct=False, error=str(e),
            )

    def evaluate_plan(self, task_id: str, plan: List[str]) -> BenchmarkResult:
        """Evaluate a plan."""
        start = time.time()
        task = self.tasks.get(task_id)
        if not task:
            return BenchmarkResult(task_id=task_id, score=0, time_taken=0, correct=False,
                                  error="Unknown task")

        score = 0.3
        if len(plan) > 0:
            score += 0.2
        if len(plan) > 3:
            score += 0.1
        if any("if" in step.lower() or "check" in step.lower() for step in plan):
            score += 0.2
        score = min(score, 1.0)

        time_taken = time.time() - start
        return BenchmarkResult(
            task_id=task_id,
            score=score,
            time_taken=time_taken,
            correct=score > 0.7,
            output=str(plan)[:200],
        )

    def evaluate_reasoning(self, task_id: str, answer: str, chain: List[str]) -> BenchmarkResult:
        """Evaluate a reasoning answer."""
        start = time.time()
        task = self.tasks.get(task_id)
        if not task:
            return BenchmarkResult(task_id=task_id, score=0, time_taken=0, correct=False,
                                  error="Unknown task")

        score = 0.4
        if len(answer) > 10:
            score += 0.1
        if len(chain) > 2:
            score += 0.2
        if "because" in answer.lower() or "therefore" in answer.lower():
            score += 0.1
        score = min(score, 1.0)

        time_taken = time.time() - start
        return BenchmarkResult(
            task_id=task_id,
            score=score,
            time_taken=time_taken,
            correct=score > 0.7,
            output=answer[:200],
        )

    def run_full_benchmark(self, agent_fn=None) -> BenchmarkRun:
        """Run a full benchmark suite."""
        import uuid
        run = BenchmarkRun(run_id=str(uuid.uuid4())[:8])

        for task_id, task in self.tasks.items():
            if agent_fn:
                try:
                    result = agent_fn(task)
                except Exception:
                    result = BenchmarkResult(task_id=task_id, score=0, time_taken=0,
                                           correct=False, error="Agent failed")
            else:
                result = BenchmarkResult(task_id=task_id, score=0.5, time_taken=0.1, correct=False)

            run.results.append(result)

        if run.results:
            run.overall_score = sum(r.score for r in run.results) / len(run.results)
            category_scores = {}
            for result in run.results:
                task = self.tasks.get(result.task_id)
                if task:
                    if task.category not in category_scores:
                        category_scores[task.category] = []
                    category_scores[task.category].append(result.score)
            run.category_scores = {
                cat: sum(scores) / len(scores)
                for cat, scores in category_scores.items()
            }

        if self.runs:
            last_score = self.runs[-1].overall_score
            run.improvement_since_last = run.overall_score - last_score
            for task_id, score in [(r.task_id, r.score) for r in run.results]:
                if task_id in self.best_scores and score < self.best_scores[task_id] * 0.8:
                    run.regressions.append(task_id)

        for result in run.results:
            if result.task_id not in self.best_scores or result.score > self.best_scores[result.task_id]:
                self.best_scores[result.task_id] = result.score

        self.runs.append(run)
        self._save()
        return run

    def get_history(self, limit: int = 10) -> List[BenchmarkRun]:
        return self.runs[-limit:]

    def get_trend(self, category: Optional[str] = None) -> List[float]:
        """Get score trend over time."""
        scores = []
        for run in self.runs[-20:]:
            if category and category in run.category_scores:
                scores.append(run.category_scores[category])
            elif not category:
                scores.append(run.overall_score)
        return scores

    def get_recommendations(self) -> List[str]:
        """Get improvement recommendations."""
        recs = []
        if not self.runs:
            return ["Run initial benchmark to establish baseline"]

        last_run = self.runs[-1]
        for cat, score in last_run.category_scores.items():
            if score < 0.5:
                recs.append(f"Improve {cat} (score: {score:.2f})")
            elif score < 0.7:
                recs.append(f"Good progress in {cat}, keep practicing (score: {score:.2f})")

        if last_run.regressions:
            recs.append(f"Regression detected in: {', '.join(last_run.regressions)}")

        return recs if recs else ["All categories performing well"]

    def to_context(self) -> str:
        if not self.runs:
            return "Benchmarks: No runs yet"
        last = self.runs[-1]
        return (f"Benchmarks: {len(self.runs)} runs, "
                f"last score: {last.overall_score:.2f}, "
                f"improvement: {last.improvement_since_last:+.2f}")
