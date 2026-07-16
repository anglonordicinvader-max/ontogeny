"""Tests for Phase 4: Model Evaluation, Quality Gates, Rollback, A/B Testing."""
import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.crawler_agent.cognitive.model_evaluation import (
    ModelEvaluator, EvalTask, EvalTaskType, EvalResult,
    ComparisonReport, QualityGate, RollbackManager, ABTestRunner,
)
from src.crawler_agent.cognitive.custom_model_manager import CustomModelManager, ModelState
from src.crawler_agent.cognitive.model_trainer import ModelTrainer
from src.crawler_agent.cognitive.modification_memory import ModificationMemory
from src.crawler_agent.cognitive.backend import HybridBackend


def _mock_backend(name="mock", content="```python\ntry:\n    pass\nexcept:\n    pass\n```"):
    m = MagicMock()
    m.complete = AsyncMock(return_value=MagicMock(content=content, confidence=0.8))
    m.embed = AsyncMock(return_value=[0.0] * 384)
    m.classify = AsyncMock(return_value={"a": 1.0})
    m.extract_patterns = AsyncMock(return_value=[])
    m.get_name = MagicMock(return_value=name)
    return m


class TestModelEvaluator:
    def test_benchmark_tasks_defined(self):
        assert len(ModelEvaluator.BENCHMARK_TASKS) >= 8
        for task in ModelEvaluator.BENCHMARK_TASKS:
            assert isinstance(task, EvalTask)
            assert task.name
            assert task.task_type in EvalTaskType

    def test_evaluate_model(self):
        base = _mock_backend("base")
        mal = _mock_backend("maldoror")
        evaluator = ModelEvaluator(base_backend=base, maldoror_backend=mal)
        tasks = evaluator.BENCHMARK_TASKS[:2]

        results = asyncio.run(
            evaluator._evaluate_model(base, "base", tasks)
        )
        assert len(results) == 2
        for r in results:
            assert isinstance(r, EvalResult)
            assert r.model_name == "base"
            assert r.score >= 0.0

    def test_compare(self):
        base = _mock_backend("base", "```python\ntry:\n    pass\n```")
        mal = _mock_backend("maldoror", "```python\ntry:\n    pass\nexcept:\n    pass\n```")
        evaluator = ModelEvaluator(base_backend=base, maldoror_backend=mal)
        tasks = evaluator.BENCHMARK_TASKS[:2]

        report = asyncio.run(
            evaluator.compare(tasks=tasks)
        )
        assert isinstance(report, ComparisonReport)
        assert report.base_model == "base"
        assert report.maldoror_model == "maldoror"
        assert len(report.base_scores) == 2
        assert len(report.maldoror_scores) == 2
        assert report.verdict in ("maldoror_wins", "base_wins", "tie")

    def test_compare_saves_report(self):
        base = _mock_backend("base")
        mal = _mock_backend("maldoror")
        evaluator = ModelEvaluator(base_backend=base, maldoror_backend=mal)
        tasks = evaluator.BENCHMARK_TASKS[:1]

        asyncio.run(evaluator.compare(tasks=tasks))
        assert len(evaluator.reports) >= 1
        # Check detail file was saved
        eval_files = list(Path("data/maldoror/eval").glob("eval_*.json"))
        assert len(eval_files) >= 1


class TestQualityGate:
    def test_passes_when_maldoror_wins(self):
        gate = QualityGate()
        report = ComparisonReport(
            base_model="base", maldoror_model="maldoror",
            base_avg=0.5, maldoror_avg=0.7, improvement_pct=40.0,
            maldoror_latency_ms=1000,
            maldoror_scores=[0.7, 0.8, 0.6],
            verdict="maldoror_wins",
        )
        result = asyncio.run(gate.check(report))
        assert result["passed"] is True

    def test_fails_when_maldoror_worse(self):
        gate = QualityGate(min_score=0.5)
        report = ComparisonReport(
            base_model="base", maldoror_model="maldoror",
            base_avg=0.7, maldoror_avg=0.2, improvement_pct=-70.0,
            maldoror_latency_ms=1000,
            maldoror_scores=[0.1, 0.2, 0.3],
            verdict="base_wins",
        )
        result = asyncio.run(gate.check(report))
        assert result["passed"] is False

    def test_fails_on_high_latency(self):
        gate = QualityGate(max_latency_ms=5000)
        report = ComparisonReport(
            base_model="base", maldoror_model="maldoror",
            base_avg=0.5, maldoror_avg=0.6, improvement_pct=20.0,
            maldoror_latency_ms=10000,
            maldoror_scores=[0.6, 0.7, 0.5],
            verdict="maldoror_wins",
        )
        result = asyncio.run(gate.check(report))
        assert result["passed"] is False
        assert result["checks"]["latency_acceptable"] is False

    def test_tie_passes(self):
        gate = QualityGate()
        report = ComparisonReport(
            base_model="base", maldoror_model="maldoror",
            base_avg=0.5, maldoror_avg=0.52, improvement_pct=4.0,
            maldoror_latency_ms=2000,
            maldoror_scores=[0.5, 0.6, 0.5],
            verdict="tie",
        )
        result = asyncio.run(gate.check(report))
        assert result["passed"] is True


class TestRollbackManager:
    def test_should_rollback_on_major_regression(self):
        mm = ModificationMemory()
        t = ModelTrainer(modification_memory=mm, output_dir="data/maldoror")
        mgr = CustomModelManager(model_trainer=t)
        mgr.models.append(ModelState(name="maldoror:v0", version="v0", adapter_path="x"))
        mgr.models.append(ModelState(name="maldoror:v1", version="v1", adapter_path="y", active=True))
        mgr.active_model = mgr.models[1]

        rb = RollbackManager(custom_model_manager=mgr)
        gate = {"passed": False, "improvement_pct": -20, "checks": {"a": False}}

        should = asyncio.run(rb.should_rollback(gate))
        assert should is True

    def test_no_rollback_when_passed(self):
        mm = ModificationMemory()
        t = ModelTrainer(modification_memory=mm, output_dir="data/maldoror")
        mgr = CustomModelManager(model_trainer=t)
        rb = RollbackManager(custom_model_manager=mgr)

        gate = {"passed": True, "improvement_pct": 10, "checks": {"a": True}}
        should = asyncio.run(rb.should_rollback(gate))
        assert should is False

    def test_rollback_switches_model(self):
        # Clean up any leftover history
        hist_path = Path("data/maldoror/rollback_history.json")
        if hist_path.exists():
            hist_path.unlink()

        mm = ModificationMemory()
        t = ModelTrainer(modification_memory=mm, output_dir="data/maldoror")
        mgr = CustomModelManager(model_trainer=t)
        mgr.models.append(ModelState(name="maldoror:v0", version="v0", adapter_path="x"))
        mgr.models.append(ModelState(name="maldoror:v1", version="v1", adapter_path="y", active=True))
        mgr.active_model = mgr.models[1]

        rb = RollbackManager(custom_model_manager=mgr)
        result = asyncio.run(rb.rollback(reason="test"))
        assert result is True
        assert mgr.active_model.version == "v0"
        assert len(rb.rollback_history) == 1

    def test_stats(self):
        mm = ModificationMemory()
        t = ModelTrainer(modification_memory=mm, output_dir="data/maldoror")
        mgr = CustomModelManager(model_trainer=t)
        rb = RollbackManager(custom_model_manager=mgr)
        stats = rb.get_stats()
        assert "total_rollbacks" in stats
        assert "recent" in stats


class TestABTestRunner:
    def test_run_test(self):
        base = _mock_backend("base", "```python\ntry:\n    pass\n```")
        mal = _mock_backend("maldoror", "```python\ntry:\n    pass\nexcept:\n    pass\n```")
        evaluator = ModelEvaluator(base_backend=base, maldoror_backend=mal)
        runner = ABTestRunner(evaluator=evaluator)

        result = asyncio.run(
            runner.run_test(prompt="Fix the bug", num_rounds=2)
        )
        assert "winner" in result
        assert result["rounds"] == 2
        assert "base_avg_score" in result
        assert "maldoror_avg_score" in result

    def test_stats(self):
        base = _mock_backend("base")
        mal = _mock_backend("maldoror")
        evaluator = ModelEvaluator(base_backend=base, maldoror_backend=mal)
        runner = ABTestRunner(evaluator=evaluator)

        asyncio.run(
            runner.run_test(prompt="test", num_rounds=1)
        )
        stats = runner.get_stats()
        assert stats["tests_run"] == 1


class TestIntegration:
    def test_full_evaluation_flow(self):
        base = _mock_backend("base", "```python\ntry:\n    pass\nexcept:\n    pass\n```")
        mal = _mock_backend("maldoror", "```python\ntry:\n    pass\nexcept:\n    pass\n```")
        evaluator = ModelEvaluator(base_backend=base, maldoror_backend=mal)
        gate = QualityGate()
        mm = ModificationMemory()
        t = ModelTrainer(modification_memory=mm, output_dir="data/maldoror")
        mgr = CustomModelManager(model_trainer=t)
        mgr.models.append(ModelState(name="maldoror:v0", version="v0", adapter_path="x", active=True))
        rb = RollbackManager(custom_model_manager=mgr)
        ab = ABTestRunner(evaluator=evaluator)

        # Run evaluation
        report = asyncio.run(
            evaluator.compare(tasks=evaluator.BENCHMARK_TASKS[:2])
        )
        assert report.verdict in ("maldoror_wins", "base_wins", "tie")

        # Run quality gate
        gate_result = asyncio.run(gate.check(report))
        assert "passed" in gate_result

        # Check rollback
        should_rb = asyncio.run(rb.should_rollback(gate_result))
        assert isinstance(should_rb, bool)

        # Run A/B test
        ab_result = asyncio.run(
            ab.run_test(prompt="test prompt", num_rounds=1)
        )
        assert "winner" in ab_result
