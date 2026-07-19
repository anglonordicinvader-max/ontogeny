"""Reliability module - retry logic, fault tolerance, structured logging.

Provides:
- Retry decorators with exponential backoff and jitter
- Circuit breaker pattern for external services
- Structured health monitoring
- Fault-tolerant wrapper for async operations
"""

import asyncio
import functools
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, StrEnum
from typing import Any, Dict, List, Optional

import structlog


class CircuitState(StrEnum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple = (Exception,)


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3


@dataclass
class HealthStatus:
    """Health status of a component."""

    name: str
    healthy: bool = True
    last_check: datetime = field(default_factory=datetime.utcnow)
    error_count: int = 0
    success_count: int = 0
    last_error: str | None = None
    avg_response_time_ms: float = 0.0
    metadata: dict = field(default_factory=dict)


class CircuitBreaker:
    """Circuit breaker pattern for external service calls."""

    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: float | None = None
        self.half_open_calls = 0
        self.logger = structlog.get_logger().bind(circuit_breaker=name)

    def record_success(self):
        self.success_count += 1
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.config.half_open_max_calls:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.half_open_calls = 0
                self.logger.info("circuit_closed", successes=self.success_count)

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.half_open_calls = 0
            self.logger.warning("circuit_reopened", failures=self.failure_count)
        elif self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            self.logger.warning("circuit_opened", failures=self.failure_count)

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if (
                self.last_failure_time
                and (time.time() - self.last_failure_time) > self.config.recovery_timeout
            ):
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                self.logger.info("circuit_half_open")
                return True
            return False
        else:  # HALF_OPEN
            return self.half_open_calls < self.config.half_open_max_calls

    def get_status(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure": self.last_failure_time,
        }


class ReliabilityManager:
    """Manages retry logic, circuit breakers, and health monitoring."""

    def __init__(self):
        self.logger = structlog.get_logger(component="reliability")
        self.circuit_breakers: dict[str, CircuitBreaker] = {}
        self.health_status: dict[str, HealthStatus] = {}
        self._response_times: dict[str, list[float]] = {}

    def get_circuit_breaker(self, name: str, config: CircuitBreakerConfig = None) -> CircuitBreaker:
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(name, config)
        return self.circuit_breakers[name]

    def record_health(
        self, name: str, success: bool, response_time_ms: float = 0.0, error: str = None
    ):
        if name not in self.health_status:
            self.health_status[name] = HealthStatus(name=name)

        status = self.health_status[name]
        status.last_check = datetime.utcnow()

        if success:
            status.success_count += 1
            status.healthy = True
        else:
            status.error_count += 1
            status.last_error = error
            if status.error_count > 10:
                status.healthy = False

        # Track response times
        if name not in self._response_times:
            self._response_times[name] = []
        self._response_times[name].append(response_time_ms)
        if len(self._response_times[name]) > 100:
            self._response_times[name] = self._response_times[name][-100:]
        status.avg_response_time_ms = sum(self._response_times[name]) / len(
            self._response_times[name]
        )

    def get_health_report(self) -> dict[str, dict]:
        report = {}
        for name, status in self.health_status.items():
            report[name] = {
                "healthy": status.healthy,
                "last_check": status.last_check.isoformat(),
                "error_count": status.error_count,
                "success_count": status.success_count,
                "success_rate": status.success_count
                / max(1, status.success_count + status.error_count),
                "avg_response_time_ms": status.avg_response_time_ms,
                "last_error": status.last_error,
            }
        return report

    def get_circuit_breaker_report(self) -> dict[str, dict]:
        return {name: cb.get_status() for name, cb in self.circuit_breakers.items()}

    async def execute_with_retry(
        self,
        func: Callable,
        config: RetryConfig = None,
        circuit_breaker_name: str = None,
        operation_name: str = "operation",
    ) -> Any:
        """Execute a function with retry logic and optional circuit breaker."""
        config = config or RetryConfig()

        # Check circuit breaker
        if circuit_breaker_name:
            cb = self.get_circuit_breaker(circuit_breaker_name)
            if not cb.can_execute():
                raise RuntimeError(f"Circuit breaker '{circuit_breaker_name}' is OPEN")

        last_exception = None
        for attempt in range(config.max_retries + 1):
            try:
                start = time.perf_counter()
                result = await func()
                elapsed = (time.perf_counter() - start) * 1000

                # Record success
                if circuit_breaker_name:
                    self.get_circuit_breaker(circuit_breaker_name).record_success()
                self.record_health(operation_name, success=True, response_time_ms=elapsed)

                if attempt > 0:
                    self.logger.info(
                        "operation_succeeded_after_retry",
                        operation=operation_name,
                        attempt=attempt + 1,
                        elapsed_ms=elapsed,
                    )
                return result

            except config.retryable_exceptions as e:
                last_exception = e
                if circuit_breaker_name:
                    self.get_circuit_breaker(circuit_breaker_name).record_failure()
                self.record_health(
                    operation_name,
                    success=False,
                    response_time_ms=0,
                    error=str(e),
                )

                if attempt < config.max_retries:
                    delay = min(
                        config.base_delay * (config.exponential_base**attempt),
                        config.max_delay,
                    )
                    if config.jitter:
                        delay *= 0.5 + random.random()
                    self.logger.warning(
                        "operation_retry",
                        operation=operation_name,
                        attempt=attempt + 1,
                        max_retries=config.max_retries,
                        delay=delay,
                        error=str(e),
                    )
                    await asyncio.sleep(delay)

        raise last_exception


def retry_async(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (Exception,),
):
    """Decorator for retrying async functions with exponential backoff."""

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            config = RetryConfig(
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter=jitter,
                retryable_exceptions=retryable_exceptions,
            )

            last_exception = None
            for attempt in range(config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e
                    if attempt < config.max_retries:
                        delay = min(
                            config.base_delay * (config.exponential_base**attempt),
                            config.max_delay,
                        )
                        if config.jitter:
                            delay *= 0.5 + random.random()
                        await asyncio.sleep(delay)

            raise last_exception

        return wrapper

    return decorator


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
):
    """Decorator for circuit breaker pattern on async functions."""
    _breaker = CircuitBreaker(
        name,
        CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        ),
    )

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if not _breaker.can_execute():
                raise RuntimeError(f"Circuit breaker '{name}' is OPEN")
            try:
                result = await func(*args, **kwargs)
                _breaker.record_success()
                return result
            except Exception:
                _breaker.record_failure()
                raise

        wrapper.circuit_breaker = _breaker
        return wrapper

    return decorator


# Global reliability manager instance
_reliability_manager: ReliabilityManager | None = None


def get_reliability_manager() -> ReliabilityManager:
    global _reliability_manager
    if _reliability_manager is None:
        _reliability_manager = ReliabilityManager()
    return _reliability_manager
