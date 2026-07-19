"""Production Readiness — monitoring, smart triggers, resilience.

Tracks model performance over time, detects drift, triggers retraining
based on quality degradation (not just iteration count), and provides
circuit breaker / graceful degradation for the maldoror pipeline.
"""

import asyncio
import json
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, StrEnum
from pathlib import Path
from typing import Any

import structlog

# ---------------------------------------------------------------------------
# Monitoring
# ---------------------------------------------------------------------------


class MetricType(StrEnum):
    LATENCY = "latency"
    SUCCESS_RATE = "success_rate"
    QUALITY_SCORE = "quality_score"
    MEMORY_USAGE = "memory_usage"
    ERROR_RATE = "error_rate"


@dataclass
class MetricPoint:
    timestamp: float
    metric_type: MetricType
    value: float
    model_version: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class PerformanceMonitor:
    """Tracks model performance metrics over time and detects drift."""

    def __init__(self, window_size: int = 100, output_dir: str = "data/maldoror/monitoring"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.window_size = window_size
        self.metrics: dict[str, deque[MetricPoint]] = {}
        self.logger = structlog.get_logger()
        self._load_metrics()

    def _metrics_path(self) -> Path:
        return self.output_dir / "metrics.json"

    def _load_metrics(self) -> None:
        path = self._metrics_path()
        if path.exists():
            try:
                data = json.loads(path.read_text())
                for key, points in data.items():
                    self.metrics[key] = deque(
                        [MetricPoint(**p) for p in points],
                        maxlen=self.window_size,
                    )
            except Exception as e:
                self.logger.warning("metrics_load_failed", error=str(e))

    def _save_metrics(self) -> None:
        data = {}
        for key, points in self.metrics.items():
            data[key] = [p.__dict__ for p in points]
        self._metrics_path().write_text(json.dumps(data, indent=2, default=str))

    def record(
        self,
        metric_type: MetricType,
        value: float,
        model_version: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a metric data point."""
        key = f"{metric_type.value}_{model_version}" if model_version else metric_type.value
        if key not in self.metrics:
            self.metrics[key] = deque(maxlen=self.window_size)
        self.metrics[key].append(
            MetricPoint(
                timestamp=time.time(),
                metric_type=metric_type,
                value=value,
                model_version=model_version,
                metadata=metadata or {},
            )
        )

    def get_recent(
        self, metric_type: MetricType, model_version: str = "", n: int = 10
    ) -> list[MetricPoint]:
        """Get recent metric points."""
        key = f"{metric_type.value}_{model_version}" if model_version else metric_type.value
        points = self.metrics.get(key, deque())
        return list(points)[-n:]

    def get_average(self, metric_type: MetricType, model_version: str = "", n: int = 20) -> float:
        """Get average of recent metric points."""
        points = self.get_recent(metric_type, model_version, n)
        if not points:
            return 0.0
        return sum(p.value for p in points) / len(points)

    def detect_drift(
        self,
        metric_type: MetricType,
        baseline_version: str,
        current_version: str,
        threshold: float = 0.15,
    ) -> dict[str, Any]:
        """Detect performance drift between two model versions."""
        baseline_avg = self.get_average(metric_type, baseline_version)
        current_avg = self.get_average(metric_type, current_version)

        if baseline_avg == 0:
            return {"drifted": False, "reason": "no_baseline_data"}

        change_pct = ((current_avg - baseline_avg) / abs(baseline_avg)) * 100

        drifted = abs(change_pct) > (threshold * 100)
        return {
            "drifted": drifted,
            "metric": metric_type.value,
            "baseline_version": baseline_version,
            "current_version": current_version,
            "baseline_avg": baseline_avg,
            "current_avg": current_avg,
            "change_pct": change_pct,
            "threshold": threshold,
        }

    def get_summary(self) -> dict[str, Any]:
        """Get summary of all tracked metrics."""
        summary = {}
        for key, points in self.metrics.items():
            if points:
                values = [p.value for p in points]
                summary[key] = {
                    "count": len(values),
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "latest": values[-1] if values else 0,
                }
        return summary

    def save_snapshot(self) -> None:
        """Save current metrics to a timestamped snapshot."""
        snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": self.get_summary(),
        }
        path = self.output_dir / f"snapshot_{int(time.time())}.json"
        path.write_text(json.dumps(snapshot, indent=2))
        self._save_metrics()


# ---------------------------------------------------------------------------
# Smart Retraining Triggers
# ---------------------------------------------------------------------------


class RetrainingTrigger:
    """Determines when retraining should happen based on quality signals."""

    def __init__(
        self,
        monitor: PerformanceMonitor,
        min_iterations: int = 10,
        quality_threshold: float = 0.7,
        drift_threshold: float = 0.15,
        error_rate_threshold: float = 0.3,
    ):
        self.monitor = monitor
        self.min_iterations = min_iterations
        self.quality_threshold = quality_threshold
        self.drift_threshold = drift_threshold
        self.error_rate_threshold = error_rate_threshold
        self.last_retrain_iteration = 0
        self.logger = structlog.get_logger()

    def should_retrain(
        self,
        current_iteration: int,
        training_data_ready: bool,
        current_model_version: str = "",
    ) -> dict[str, Any]:
        """Evaluate whether retraining should be triggered."""
        reasons = []

        # 1. Minimum iteration gap
        if current_iteration - self.last_retrain_iteration < self.min_iterations:
            return {"retrain": False, "reasons": ["min_iteration_gap"]}

        # 2. Training data available
        if not training_data_ready:
            return {"retrain": False, "reasons": ["no_training_data"]}

        # 3. Quality degradation
        if current_model_version:
            quality = self.monitor.get_average(MetricType.QUALITY_SCORE, current_model_version)
            if 0 < quality < self.quality_threshold:
                reasons.append(f"quality_degradation:{quality:.2f}")

        # 4. High error rate
        if current_model_version:
            error_rate = self.monitor.get_average(MetricType.ERROR_RATE, current_model_version)
            if error_rate > self.error_rate_threshold:
                reasons.append(f"high_error_rate:{error_rate:.2f}")

        # 5. Performance drift from baseline
        if current_model_version:
            drift = self.monitor.detect_drift(
                MetricType.QUALITY_SCORE,
                baseline_version="base",
                current_version=current_model_version,
                threshold=self.drift_threshold,
            )
            if drift["drifted"]:
                reasons.append(f"quality_drift:{drift['change_pct']:+.1f}%")

        # 6. High latency
        if current_model_version:
            latency = self.monitor.get_average(MetricType.LATENCY, current_model_version)
            if latency > 10000:  # 10 seconds
                reasons.append(f"high_latency:{latency:.0f}ms")

        should = len(reasons) > 0
        if should:
            self.last_retrain_iteration = current_iteration
            self.logger.info("retraining_triggered", reasons=reasons, iteration=current_iteration)

        return {"retrain": should, "reasons": reasons}

    def get_stats(self) -> dict[str, Any]:
        return {
            "last_retrain_iteration": self.last_retrain_iteration,
            "min_iterations": self.min_iterations,
            "quality_threshold": self.quality_threshold,
            "drift_threshold": self.drift_threshold,
        }


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------


class CircuitState(StrEnum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitBreaker:
    """Prevents cascading failures in the maldoror pipeline."""

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 300.0,
        success_threshold: int = 2,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        self.logger = structlog.get_logger()

    def can_execute(self) -> bool:
        """Check if a call is allowed."""
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                self.logger.info("circuit_half_open")
                return True
            return False
        if self.state == CircuitState.HALF_OPEN:
            return True
        return False

    def record_success(self) -> None:
        """Record a successful operation."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.logger.info("circuit_closed")
        elif self.state == CircuitState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self) -> None:
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.logger.warning("circuit_open_from_half_open")
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.logger.warning("circuit_open", failures=self.failure_count)

    def get_state(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure": self.last_failure_time,
        }


# ---------------------------------------------------------------------------
# Graceful Degradation
# ---------------------------------------------------------------------------


class GracefulDegradation:
    """Handles failures in the maldoror pipeline with fallback strategies."""

    def __init__(self, circuit_breaker: CircuitBreaker, monitor: PerformanceMonitor):
        self.circuit = circuit_breaker
        self.monitor = monitor
        self.fallback_count = 0
        self.logger = structlog.get_logger()

    async def execute_with_fallback(
        self,
        primary_fn,
        fallback_fn,
        operation_name: str = "unknown",
    ) -> Any:
        """Execute primary function with fallback on failure."""
        if not self.circuit.can_execute():
            self.logger.warning("circuit_open_fallback", operation=operation_name)
            self.fallback_count += 1
            self.monitor.record(MetricType.ERROR_RATE, 1.0, metadata={"operation": operation_name})
            return await fallback_fn()

        try:
            result = await primary_fn()
            self.circuit.record_success()
            self.monitor.record(
                MetricType.SUCCESS_RATE, 1.0, metadata={"operation": operation_name}
            )
            return result
        except Exception as e:
            self.circuit.record_failure()
            self.monitor.record(MetricType.ERROR_RATE, 1.0, metadata={"operation": operation_name})
            self.logger.warning(
                "primary_failed_falling_back", operation=operation_name, error=str(e)
            )
            self.fallback_count += 1
            return await fallback_fn()

    def get_stats(self) -> dict[str, Any]:
        return {
            "fallback_count": self.fallback_count,
            "circuit_state": self.circuit.get_state(),
        }
