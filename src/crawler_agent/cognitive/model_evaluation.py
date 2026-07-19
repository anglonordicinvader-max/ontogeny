"""Model Evaluation — benchmarks, A/B testing, rollback, quality gates.

Compares maldoror against the base model on self-modification tasks,
manages rollback on regression, and enforces quality gates before deployment.
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, StrEnum
from pathlib import Path
from typing import Any

import structlog

from .backend import CognitiveBackend, CognitiveResponse
from .custom_model_manager import CustomModelManager, ModelState
from .modification_memory import ModificationMemory


class EvalTaskType(StrEnum):
    CODE_REWRITE = "code_rewrite"
    BUG_FIX = "bug_fix"
    OPTIMIZATION = "optimization"
    ARCHITECTURE = "architecture"


@dataclass
class EvalTask:
    name: str
    task_type: EvalTaskType
    prompt: str
    expected_pattern: str = ""
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalResult:
    task_name: str
    model_name: str
    response_text: str
    score: float  # 0-1
    latency_ms: float
    has_code: bool
    has_diff: bool
    matches_pattern: bool
    error: str = ""
    timestamp: str = ""


@dataclass
class ComparisonReport:
    base_model: str
    maldoror_model: str
    base_scores: list[float] = field(default_factory=list)
    maldoror_scores: list[float] = field(default_factory=list)
    base_avg: float = 0.0
    maldoror_avg: float = 0.0
    improvement_pct: float = 0.0
    base_latency_ms: float = 0.0
    maldoror_latency_ms: float = 0.0
    verdict: str = ""  # "maldoror_wins", "base_wins", "tie"
    timestamp: str = ""


class ModelEvaluator:
    """Evaluates maldoror against the base model."""

    BENCHMARK_TASKS = [
        EvalTask(
            name="fix_memory_leak",
            task_type=EvalTaskType.BUG_FIX,
            prompt="The track_action_confidence() method in uncertainty.py has a memory leak - old entries are never pruned. Fix it.",
            expected_pattern="prune",
            weight=1.5,
        ),
        EvalTask(
            name="optimize_quadratic",
            task_type=EvalTaskType.OPTIMIZATION,
            prompt="The allocate_compute() method has O(n^2) complexity. Optimize it to O(n log n) or better.",
            expected_pattern="sort",
            weight=1.0,
        ),
        EvalTask(
            name="add_timeout",
            task_type=EvalTaskType.BUG_FIX,
            prompt="The apply() method in recursive_modify.py can hang forever on stuck diffs. Add a timeout with rollback.",
            expected_pattern="timeout",
            weight=1.5,
        ),
        EvalTask(
            name="add_deduplication",
            task_type=EvalTaskType.CODE_REWRITE,
            prompt="The generate_intrinsic_goals() method can produce duplicate goals. Add deduplication.",
            expected_pattern="seen",
            weight=1.0,
        ),
        EvalTask(
            name="add_batch_processing",
            task_type=EvalTaskType.ARCHITECTURE,
            prompt="The consolidate() method processes all memories at once. Add batch processing with configurable batch size.",
            expected_pattern="batch",
            weight=1.0,
        ),
        EvalTask(
            name="add_error_handling",
            task_type=EvalTaskType.BUG_FIX,
            prompt="The observe() method in world_model.py crashes on bad observations. Add error handling so one bad observation doesn't crash the cycle.",
            expected_pattern="try",
            weight=1.0,
        ),
        EvalTask(
            name="add_versioning",
            task_type=EvalTaskType.ARCHITECTURE,
            prompt="The refine_skill() method overwrites skills without backup. Add versioning to preserve history.",
            expected_pattern="version",
            weight=1.0,
        ),
        EvalTask(
            name="parallel_execution",
            task_type=EvalTaskType.ARCHITECTURE,
            prompt="The run_batch() method processes tasks sequentially. Add parallel execution with a concurrency limit.",
            expected_pattern="Semaphore",
            weight=1.0,
        ),
    ]

    def __init__(
        self,
        base_backend: CognitiveBackend,
        maldoror_backend: CognitiveBackend | None = None,
        output_dir: str = "data/maldoror/eval",
    ):
        self.base = base_backend
        self.maldoror = maldoror_backend
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = structlog.get_logger()
        self.reports: list[ComparisonReport] = []
        self._load_reports()

    def _load_reports(self) -> None:
        path = self.output_dir / "reports.json"
        if path.exists():
            try:
                data = json.loads(path.read_text())
                self.reports = [ComparisonReport(**r) for r in data.get("reports", [])]
            except Exception as e:
                self.logger.warning("reports_load_failed", error=str(e))

    def _save_reports(self) -> None:
        path = self.output_dir / "reports.json"
        path.write_text(
            json.dumps({"reports": [r.__dict__ for r in self.reports]}, indent=2, default=str)
        )

    async def _evaluate_model(
        self, backend: CognitiveBackend, model_name: str, tasks: list[EvalTask]
    ) -> list[EvalResult]:
        """Run all benchmark tasks against a single model."""
        results = []
        for task in tasks:
            start = time.time()
            try:
                response = await backend.complete(
                    prompt=task.prompt,
                    system="You are a Python developer. Return only the modified code.",
                    max_tokens=1500,
                    temperature=0.3,
                )
                latency = (time.time() - start) * 1000

                text = response.content
                has_code = "```" in text or "def " in text or "async def " in text
                has_diff = "---" in text or "+++" in text or "@@" in text
                matches = (
                    task.expected_pattern.lower() in text.lower() if task.expected_pattern else True
                )

                # Score: 0.4 has_code + 0.3 has_diff + 0.3 matches_pattern
                score = 0.0
                if has_code:
                    score += 0.4
                if has_diff:
                    score += 0.3
                if matches:
                    score += 0.3

                results.append(
                    EvalResult(
                        task_name=task.name,
                        model_name=model_name,
                        response_text=text[:2000],
                        score=score,
                        latency_ms=latency,
                        has_code=has_code,
                        has_diff=has_diff,
                        matches_pattern=matches,
                        timestamp=datetime.utcnow().isoformat(),
                    )
                )
            except Exception as e:
                results.append(
                    EvalResult(
                        task_name=task.name,
                        model_name=model_name,
                        response_text="",
                        score=0.0,
                        latency_ms=(time.time() - start) * 1000,
                        has_code=False,
                        has_diff=False,
                        matches_pattern=False,
                        error=str(e),
                        timestamp=datetime.utcnow().isoformat(),
                    )
                )
        return results

    async def compare(
        self,
        maldoror_backend: CognitiveBackend | None = None,
        tasks: list[EvalTask] | None = None,
    ) -> ComparisonReport:
        """Run full comparison between base and maldoror models."""
        backend = maldoror_backend or self.maldoror
        if not backend:
            raise ValueError("No maldoror backend provided")

        tasks = tasks or self.BENCHMARK_TASKS
        base_name = self.base.get_name()
        mal_name = backend.get_name()

        self.logger.info("evaluation_start", base=base_name, maldoror=mal_name, tasks=len(tasks))

        base_results = await self._evaluate_model(self.base, base_name, tasks)
        mal_results = await self._evaluate_model(backend, mal_name, tasks)

        base_scores = [r.score for r in base_results]
        mal_scores = [r.score for r in mal_results]
        base_avg = sum(base_scores) / max(len(base_scores), 1)
        mal_avg = sum(mal_scores) / max(len(mal_scores), 1)
        base_lat = sum(r.latency_ms for r in base_results) / max(len(base_results), 1)
        mal_lat = sum(r.latency_ms for r in mal_results) / max(len(mal_results), 1)

        improvement = ((mal_avg - base_avg) / max(base_avg, 0.01)) * 100

        if improvement > 5:
            verdict = "maldoror_wins"
        elif improvement < -5:
            verdict = "base_wins"
        else:
            verdict = "tie"

        report = ComparisonReport(
            base_model=base_name,
            maldoror_model=mal_name,
            base_scores=base_scores,
            maldoror_scores=mal_scores,
            base_avg=base_avg,
            maldoror_avg=mal_avg,
            improvement_pct=improvement,
            base_latency_ms=base_lat,
            maldoror_latency_ms=mal_lat,
            verdict=verdict,
            timestamp=datetime.utcnow().isoformat(),
        )

        self.reports.append(report)
        self._save_reports()

        # Save detailed results
        detail_path = self.output_dir / f"eval_{len(self.reports):04d}.json"
        detail_path.write_text(
            json.dumps(
                {
                    "report": report.__dict__,
                    "base_results": [r.__dict__ for r in base_results],
                    "maldoror_results": [r.__dict__ for r in mal_results],
                },
                indent=2,
                default=str,
            )
        )

        self.logger.info(
            "evaluation_complete",
            verdict=verdict,
            improvement=f"{improvement:+.1f}%",
            base_avg=f"{base_avg:.2f}",
            maldoror_avg=f"{mal_avg:.2f}",
        )
        return report


class QualityGate:
    """Pre-deployment quality checks."""

    def __init__(self, min_score: float = 0.5, max_latency_ms: float = 10000):
        self.min_score = min_score
        self.max_latency_ms = max_latency_ms
        self.logger = structlog.get_logger()

    async def check(self, report: ComparisonReport) -> dict[str, Any]:
        """Run quality gates on an evaluation report."""
        checks = {
            "maldoror_not_worse": report.improvement_pct >= -10,
            "maldoror_score_above_min": report.maldoror_avg >= self.min_score,
            "latency_acceptable": report.maldoror_latency_ms <= self.max_latency_ms,
            "majority_tasks_pass": sum(1 for s in report.maldoror_scores if s > 0.3)
            > len(report.maldoror_scores) / 2,
        }
        passed = all(checks.values())
        return {
            "passed": passed,
            "checks": checks,
            "verdict": report.verdict,
            "improvement_pct": report.improvement_pct,
        }


class RollbackManager:
    """Manages model rollback on regression."""

    def __init__(self, custom_model_manager: CustomModelManager):
        self.manager = custom_model_manager
        self.logger = structlog.get_logger()
        self.rollback_history: list[dict[str, Any]] = []
        self._load_history()

    def _history_path(self) -> Path:
        return self.manager.trainer.output_dir / "rollback_history.json"

    def _load_history(self) -> None:
        path = self._history_path()
        if path.exists():
            try:
                self.rollback_history = json.loads(path.read_text())
            except Exception:
                pass

    def _save_history(self) -> None:
        self._history_path().write_text(json.dumps(self.rollback_history, indent=2, default=str))

    async def should_rollback(self, gate_result: dict[str, Any]) -> bool:
        """Determine if we should rollback based on quality gate results."""
        if gate_result["passed"]:
            return False

        # Rollback if maldoror is significantly worse
        if gate_result["improvement_pct"] < -15:
            self.logger.warning("rollback_recommended", reason="significant_regression")
            return True

        # Rollback if multiple checks failed
        failed = sum(1 for v in gate_result["checks"].values() if not v)
        if failed >= 2:
            self.logger.warning(
                "rollback_recommended", reason="multiple_gate_failures", failed=failed
            )
            return True

        return False

    async def rollback(self, reason: str = "") -> bool:
        """Rollback to the previous active model."""
        if not self.manager.active_model:
            self.logger.error("no_active_model_to_rollback_from")
            return False

        old_version = self.manager.active_model.version

        # Find the previous version
        prev_version = None
        for m in reversed(self.manager.models):
            if m.version != old_version:
                prev_version = m.version
                break

        if not prev_version:
            self.logger.error("no_previous_version_to_rollback_to")
            return False

        success = await self.manager.switch_to(prev_version)
        if success:
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "from_version": old_version,
                "to_version": prev_version,
                "reason": reason,
            }
            self.rollback_history.append(entry)
            self._save_history()
            self.logger.info("rollback_complete", **entry)

        return success

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_rollbacks": len(self.rollback_history),
            "recent": self.rollback_history[-3:] if self.rollback_history else [],
        }


class ABTestRunner:
    """Structured A/B testing with metrics collection."""

    def __init__(self, evaluator: ModelEvaluator):
        self.evaluator = evaluator
        self.logger = structlog.get_logger()
        self.results: list[dict[str, Any]] = []

    async def run_test(
        self,
        prompt: str,
        num_rounds: int = 3,
        version_a: str = "base",
        version_b: str = "maldoror",
    ) -> dict[str, Any]:
        """Run an A/B test with multiple rounds."""
        a_scores = []
        b_scores = []
        a_latencies = []
        b_latencies = []

        for _round_num in range(num_rounds):
            # Model A
            start = time.time()
            try:
                resp_a = await self.evaluator.base.complete(
                    prompt=prompt,
                    system="You are a Python developer. Return only the modified code.",
                    max_tokens=1500,
                    temperature=0.3,
                )
                a_lat = (time.time() - start) * 1000
                a_scores.append(self._score_response(resp_a.content))
                a_latencies.append(a_lat)
            except Exception:
                a_scores.append(0.0)
                a_latencies.append(5000.0)

            # Model B
            start = time.time()
            try:
                resp_b = await self.evaluator.maldoror.complete(
                    prompt=prompt,
                    system="You are a Python developer. Return only the modified code.",
                    max_tokens=1500,
                    temperature=0.3,
                )
                b_lat = (time.time() - start) * 1000
                b_scores.append(self._score_response(resp_b.content))
                b_latencies.append(b_lat)
            except Exception:
                b_scores.append(0.0)
                b_latencies.append(5000.0)

        a_avg = sum(a_scores) / max(len(a_scores), 1)
        b_avg = sum(b_scores) / max(len(b_scores), 1)
        a_lat_avg = sum(a_latencies) / max(len(a_latencies), 1)
        b_lat_avg = sum(b_latencies) / max(len(b_latencies), 1)

        result = {
            "prompt": prompt[:200],
            "rounds": num_rounds,
            f"{version_a}_avg_score": a_avg,
            f"{version_b}_avg_score": b_avg,
            f"{version_a}_avg_latency_ms": a_lat_avg,
            f"{version_b}_avg_latency_ms": b_lat_avg,
            "winner": version_b if b_avg > a_avg else version_a if a_avg > b_avg else "tie",
            "score_diff": b_avg - a_avg,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.results.append(result)
        return result

    def _score_response(self, text: str) -> float:
        score = 0.0
        if "```" in text or "def " in text:
            score += 0.4
        if "---" in text or "+++" in text:
            score += 0.3
        if any(kw in text.lower() for kw in ["try:", "except", "async def", "timeout"]):
            score += 0.3
        return min(score, 1.0)

    def get_stats(self) -> dict[str, Any]:
        if not self.results:
            return {"tests_run": 0}
        wins_a = sum(1 for r in self.results if r["winner"] == "base")
        wins_b = sum(1 for r in self.results if r["winner"] == "maldoror")
        ties = sum(1 for r in self.results if r["winner"] == "tie")
        return {
            "tests_run": len(self.results),
            "base_wins": wins_a,
            "maldoror_wins": wins_b,
            "ties": ties,
            "avg_score_diff": sum(r["score_diff"] for r in self.results) / len(self.results),
        }
