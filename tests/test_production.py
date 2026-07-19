"""Tests for Phase 5: Production Readiness (monitoring, triggers, resilience)."""

import asyncio
import json
import time
from pathlib import Path

import pytest

from src.crawler_agent.cognitive.production import (
    CircuitBreaker,
    CircuitState,
    GracefulDegradation,
    MetricPoint,
    MetricType,
    PerformanceMonitor,
    RetrainingTrigger,
)


class TestPerformanceMonitor:
    def test_record_and_retrieve(self):
        m = PerformanceMonitor(output_dir="data/maldoror/monitoring_test")
        m.metrics.clear()  # Start fresh
        m.record(MetricType.LATENCY, 100.0, model_version="v0")
        m.record(MetricType.LATENCY, 200.0, model_version="v0")
        points = m.get_recent(MetricType.LATENCY, "v0", n=10)
        assert len(points) == 2
        assert points[0].value == 100.0
        assert points[1].value == 200.0

    def test_get_average(self):
        m = PerformanceMonitor(output_dir="data/maldoror/monitoring_test")
        m.metrics.clear()
        m.record(MetricType.QUALITY_SCORE, 0.8, model_version="v0")
        m.record(MetricType.QUALITY_SCORE, 0.6, model_version="v0")
        avg = m.get_average(MetricType.QUALITY_SCORE, "v0")
        assert abs(avg - 0.7) < 0.01

    def test_get_average_empty(self):
        m = PerformanceMonitor(output_dir="data/maldoror/monitoring_test")
        m.metrics.clear()
        avg = m.get_average(MetricType.LATENCY, "nonexistent")
        assert avg == 0.0

    def test_detect_drift_no_drift(self):
        m = PerformanceMonitor(output_dir="data/maldoror/monitoring_test")
        m.metrics.clear()
        for _ in range(10):
            m.record(MetricType.QUALITY_SCORE, 0.8, model_version="base")
            m.record(MetricType.QUALITY_SCORE, 0.8, model_version="v1")
        drift = m.detect_drift(MetricType.QUALITY_SCORE, "base", "v1")
        assert drift["drifted"] is False

    def test_detect_drift_with_drift(self):
        m = PerformanceMonitor(output_dir="data/maldoror/monitoring_test")
        m.metrics.clear()
        for _ in range(10):
            m.record(MetricType.QUALITY_SCORE, 0.8, model_version="base")
            m.record(MetricType.QUALITY_SCORE, 0.4, model_version="v1")
        drift = m.detect_drift(MetricType.QUALITY_SCORE, "base", "v1")
        assert drift["drifted"] is True
        assert drift["change_pct"] < -10

    def test_detect_drift_no_baseline(self):
        m = PerformanceMonitor(output_dir="data/maldoror/monitoring_test")
        m.metrics.clear()
        drift = m.detect_drift(MetricType.QUALITY_SCORE, "base", "v1")
        assert drift["drifted"] is False
        assert drift["reason"] == "no_baseline_data"

    def test_get_summary(self):
        m = PerformanceMonitor(output_dir="data/maldoror/monitoring_test")
        m.metrics.clear()
        m.record(MetricType.LATENCY, 100.0)
        m.record(MetricType.LATENCY, 200.0)
        summary = m.get_summary()
        assert "latency" in summary
        assert summary["latency"]["count"] == 2
        assert summary["latency"]["avg"] == 150.0

    def test_save_and_load(self):
        output_dir = "data/maldoror/monitoring"
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        m = PerformanceMonitor(output_dir=output_dir)
        m.record(MetricType.LATENCY, 100.0, model_version="v0")
        m._save_metrics()

        m2 = PerformanceMonitor(output_dir=output_dir)
        points = m2.get_recent(MetricType.LATENCY, "v0")
        assert len(points) >= 1

    def test_save_snapshot(self):
        m = PerformanceMonitor()
        m.record(MetricType.LATENCY, 100.0)
        m.save_snapshot()
        snapshots = list(Path("data/maldoror/monitoring").glob("snapshot_*.json"))
        assert len(snapshots) >= 1

    def test_window_size_limit(self):
        m = PerformanceMonitor(window_size=5)
        for i in range(10):
            m.record(MetricType.LATENCY, float(i))
        points = m.get_recent(MetricType.LATENCY, n=100)
        assert len(points) <= 5


class TestRetrainingTrigger:
    def test_no_retrain_below_min_iterations(self):
        m = PerformanceMonitor()
        trigger = RetrainingTrigger(monitor=m, min_iterations=10)
        result = trigger.should_retrain(
            current_iteration=5,
            training_data_ready=True,
        )
        assert result["retrain"] is False

    def test_no_retrain_without_data(self):
        m = PerformanceMonitor()
        trigger = RetrainingTrigger(monitor=m, min_iterations=0)
        result = trigger.should_retrain(
            current_iteration=100,
            training_data_ready=False,
        )
        assert result["retrain"] is False

    def test_retrain_on_quality_degradation(self):
        m = PerformanceMonitor()
        for _ in range(10):
            m.record(MetricType.QUALITY_SCORE, 0.3, model_version="v0")
        trigger = RetrainingTrigger(monitor=m, min_iterations=0, quality_threshold=0.7)
        result = trigger.should_retrain(
            current_iteration=100,
            training_data_ready=True,
            current_model_version="v0",
        )
        assert result["retrain"] is True
        assert any("quality_degradation" in r for r in result["reasons"])

    def test_retrain_on_high_error_rate(self):
        m = PerformanceMonitor()
        for _ in range(10):
            m.record(MetricType.ERROR_RATE, 0.5, model_version="v0")
        trigger = RetrainingTrigger(monitor=m, min_iterations=0, error_rate_threshold=0.3)
        result = trigger.should_retrain(
            current_iteration=100,
            training_data_ready=True,
            current_model_version="v0",
        )
        assert result["retrain"] is True
        assert any("high_error_rate" in r for r in result["reasons"])

    def test_stats(self):
        m = PerformanceMonitor()
        trigger = RetrainingTrigger(monitor=m)
        stats = trigger.get_stats()
        assert "last_retrain_iteration" in stats
        assert "min_iterations" in stats


class TestCircuitBreaker:
    def test_starts_closed(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

    def test_opens_after_failures(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() is False

    def test_half_open_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.2)
        assert cb.can_execute() is True
        assert cb.state == CircuitState.HALF_OPEN

    def test_closes_after_successes_in_half_open(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1, success_threshold=2)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.2)
        cb.can_execute()  # transitions to half_open
        cb.record_success()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_reopens_on_failure_in_half_open(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.2)
        cb.can_execute()  # transitions to half_open
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_success_decreases_failure_count(self):
        cb = CircuitBreaker(failure_threshold=5)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.failure_count == 1

    def test_get_state(self):
        cb = CircuitBreaker()
        state = cb.get_state()
        assert "state" in state
        assert "failure_count" in state


class TestGracefulDegradation:
    def test_successful_primary(self):
        cb = CircuitBreaker()
        m = PerformanceMonitor()
        gd = GracefulDegradation(circuit_breaker=cb, monitor=m)

        async def primary():
            return "primary_ok"

        async def fallback():
            return "fallback_ok"

        result = asyncio.run(gd.execute_with_fallback(primary, fallback))
        assert result == "primary_ok"
        assert gd.fallback_count == 0

    def test_fallback_on_failure(self):
        cb = CircuitBreaker()
        m = PerformanceMonitor()
        gd = GracefulDegradation(circuit_breaker=cb, monitor=m)

        async def primary():
            raise ValueError("boom")

        async def fallback():
            return "fallback_ok"

        result = asyncio.run(gd.execute_with_fallback(primary, fallback))
        assert result == "fallback_ok"
        assert gd.fallback_count == 1

    def test_fallback_when_circuit_open(self):
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure()  # opens circuit
        m = PerformanceMonitor()
        gd = GracefulDegradation(circuit_breaker=cb, monitor=m)

        async def primary():
            return "primary_ok"

        async def fallback():
            return "fallback_ok"

        result = asyncio.run(gd.execute_with_fallback(primary, fallback))
        assert result == "fallback_ok"
        assert gd.fallback_count == 1

    def test_stats(self):
        cb = CircuitBreaker()
        m = PerformanceMonitor()
        gd = GracefulDegradation(circuit_breaker=cb, monitor=m)
        stats = gd.get_stats()
        assert "fallback_count" in stats
        assert "circuit_state" in stats


class TestIntegration:
    def test_monitor_to_trigger_flow(self):
        m = PerformanceMonitor()
        trigger = RetrainingTrigger(monitor=m, min_iterations=0, quality_threshold=0.7)

        # Simulate degrading quality
        for i in range(10):
            m.record(MetricType.QUALITY_SCORE, 0.9 - i * 0.1, model_version="v0")

        result = trigger.should_retrain(
            current_iteration=100,
            training_data_ready=True,
            current_model_version="v0",
        )
        assert result["retrain"] is True

    def test_circuit_breaker_with_degradation(self):
        cb = CircuitBreaker(failure_threshold=2)
        m = PerformanceMonitor()
        gd = GracefulDegradation(circuit_breaker=cb, monitor=m)
        call_count = 0

        async def flaky_primary():
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                raise ValueError("intermittent failure")
            return "ok"

        async def fallback():
            return "fallback"

        # First call succeeds
        r1 = asyncio.run(gd.execute_with_fallback(flaky_primary, fallback))
        assert r1 == "ok"

        # Second call fails
        r2 = asyncio.run(gd.execute_with_fallback(flaky_primary, fallback))
        assert r2 == "fallback"

        # Third call fails (circuit opens after 2 failures)
        r3 = asyncio.run(gd.execute_with_fallback(flaky_primary, fallback))
        assert r3 == "fallback"
        assert cb.state == CircuitState.OPEN

        # Fourth call goes directly to fallback (circuit is open)
        r4 = asyncio.run(gd.execute_with_fallback(flaky_primary, fallback))
        assert r4 == "fallback"
