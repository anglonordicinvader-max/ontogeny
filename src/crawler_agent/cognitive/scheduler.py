"""Intelligent crawl scheduling with adaptive proxy management."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable

import structlog

from ..utils.proxy import ProxyPool
from ..utils.proxy_fetcher import RotatingProxyManager


class CrawlIntensity(str, Enum):
    LIGHT = "light"        # 1-5 requests/min, focused sources
    MODERATE = "moderate"  # 5-20 requests/min, balanced
    HEAVY = "heavy"        # 20-100 requests/min, broad coverage
    BURST = "burst"        # Temporary high intensity


@dataclass
class CrawlSchedule:
    """Schedule for crawl operations."""
    intensity: CrawlIntensity
    requests_per_minute: float
    min_delay: float
    max_delay: float
    proxy_refresh_interval: int  # seconds
    min_proxies: int
    sources_per_session: int
    max_items_per_source: int
    quality_threshold: float


@dataclass
class CrawlBudget:
    """Budget for crawl resources."""
    max_requests_today: int = 1000
    max_bandwidth_mb: float = 100.0
    max_proxy_usage: int = 100
    requests_today: int = 0
    bandwidth_used_mb: float = 0.0
    proxy_rotations: int = 0
    reset_time: datetime = field(default_factory=lambda: datetime.utcnow().replace(hour=0, minute=0))

    @property
    def requests_remaining(self) -> int:
        self._check_reset()
        return max(0, self.max_requests_today - self.requests_today)

    @property
    def is_exhausted(self) -> bool:
        return self.requests_remaining <= 0

    def _check_reset(self) -> None:
        now = datetime.utcnow()
        if now.date() > self.reset_time.date():
            self.requests_today = 0
            self.bandwidth_used_mb = 0.0
            self.proxy_rotations = 0
            self.reset_time = now.replace(hour=0, minute=0, second=0)


# Pre-defined schedules
SCHEDULES = {
    CrawlIntensity.LIGHT: CrawlSchedule(
        intensity=CrawlIntensity.LIGHT,
        requests_per_minute=2.0,
        min_delay=10.0,
        max_delay=30.0,
        proxy_refresh_interval=600,  # 10 minutes
        min_proxies=3,
        sources_per_session=2,
        max_items_per_source=10,
        quality_threshold=0.7,
    ),
    CrawlIntensity.MODERATE: CrawlSchedule(
        intensity=CrawlIntensity.MODERATE,
        requests_per_minute=10.0,
        min_delay=3.0,
        max_delay=10.0,
        proxy_refresh_interval=300,  # 5 minutes
        min_proxies=8,
        sources_per_session=5,
        max_items_per_source=20,
        quality_threshold=0.6,
    ),
    CrawlIntensity.HEAVY: CrawlSchedule(
        intensity=CrawlIntensity.HEAVY,
        requests_per_minute=50.0,
        min_delay=0.5,
        max_delay=2.0,
        proxy_refresh_interval=120,  # 2 minutes
        min_proxies=20,
        sources_per_session=10,
        max_items_per_source=50,
        quality_threshold=0.5,
    ),
    CrawlIntensity.BURST: CrawlSchedule(
        intensity=CrawlIntensity.BURST,
        requests_per_minute=100.0,
        min_delay=0.1,
        max_delay=0.5,
        proxy_refresh_interval=60,  # 1 minute
        min_proxies=50,
        sources_per_session=20,
        max_items_per_source=100,
        quality_threshold=0.4,
    ),
}


class AdaptiveScheduler:
    """Intelligent scheduler that adapts to conditions."""

    def __init__(
        self,
        proxy_manager: RotatingProxyManager,
        initial_intensity: CrawlIntensity = CrawlIntensity.LIGHT,
    ):
        self.proxy_manager = proxy_manager
        self.intensity = initial_intensity
        self.schedule = SCHEDULES[initial_intensity]
        self.budget = CrawlBudget()
        self.logger = structlog.get_logger()

        # Adaptive state
        self._success_rate = 1.0
        self._avg_response_time = 1.0
        self._proxy_health = 1.0
        self._recent_errors = 0

        # Callbacks
        self._on_intensity_change: list[Callable] = []

    def set_intensity(self, intensity: CrawlIntensity) -> None:
        """Change crawl intensity."""
        old = self.intensity
        self.intensity = intensity
        self.schedule = SCHEDULES[intensity]

        # Update proxy requirements
        self.proxy_manager.pool.max_failures = 5 if intensity == CrawlIntensity.LIGHT else 3

        self.logger.info(
            "intensity_changed",
            old=old.value,
            new=intensity.value,
            rpm=self.schedule.requests_per_minute,
        )

        for callback in self._on_intensity_change:
            callback(old, intensity)

    def on_intensity_change(self, callback: Callable) -> None:
        """Register intensity change callback."""
        self._on_intensity_change.append(callback)

    async def adapt_intensity(self) -> CrawlIntensity:
        """Automatically adapt intensity based on conditions."""
        stats = self.proxy_manager.get_stats()

        # Check conditions
        proxy_health = stats.get("healthy", 0) / max(stats.get("total", 1), 1)
        self._proxy_health = proxy_health

        # Determine new intensity
        if proxy_health < 0.3 or self.budget.is_exhausted:
            new_intensity = CrawlIntensity.LIGHT
        elif proxy_health < 0.6 or self._recent_errors > 5:
            new_intensity = CrawlIntensity.MODERATE
        elif proxy_health > 0.8 and self._success_rate > 0.9:
            new_intensity = CrawlIntensity.HEAVY
        else:
            new_intensity = self.intensity  # Keep current

        if new_intensity != self.intensity:
            self.set_intensity(new_intensity)

        return new_intensity

    def get_delay(self) -> float:
        """Get appropriate delay between requests."""
        import random
        return random.uniform(self.schedule.min_delay, self.schedule.max_delay)

    def can_crawl(self) -> bool:
        """Check if we can crawl within budget."""
        return not self.budget.is_exhausted and self._proxy_health > 0.2

    def record_request(self, success: bool, response_time: float = 0.0) -> None:
        """Record a crawl request for adaptation."""
        self.budget.requests_today += 1

        if success:
            self._success_rate = (self._success_rate * 0.9) + 0.1
            self._recent_errors = max(0, self._recent_errors - 1)
        else:
            self._success_rate = (self._success_rate * 0.9)
            self._recent_errors += 1

        if response_time > 0:
            self._avg_response_time = (self._avg_response_time * 0.9) + (response_time * 0.1)

    async def wait_if_needed(self) -> None:
        """Wait if we're exceeding rate limits."""
        if self.budget.is_exhausted:
            wait_time = 60  # Wait 1 minute if budget exhausted
            self.logger.warning("budget_exhausted", wait=wait_time)
            await asyncio.sleep(wait_time)
        else:
            delay = self.get_delay()
            await asyncio.sleep(delay)

    def get_stats(self) -> dict[str, Any]:
        """Get scheduler statistics."""
        return {
            "intensity": self.intensity.value,
            "requests_per_minute": self.schedule.requests_per_minute,
            "success_rate": self._success_rate,
            "proxy_health": self._proxy_health,
            "budget": {
                "remaining": self.budget.requests_remaining,
                "used": self.budget.requests_today,
                "exhausted": self.budget.is_exhausted,
            },
            "recent_errors": self._recent_errors,
        }


class CrawlOrchestrator:
    """High-level crawl orchestration with scheduling."""

    def __init__(
        self,
        proxy_manager: RotatingProxyManager,
        intensity: CrawlIntensity = CrawlIntensity.LIGHT,
    ):
        self.proxy_manager = proxy_manager
        self.scheduler = AdaptiveScheduler(proxy_manager, intensity)
        self.logger = structlog.get_logger()

        # Source tracking
        self._source_queue: list[tuple[float, str, dict]] = []  # priority, url, metadata
        self._active_sources: set[str] = set()

    def queue_source(
        self,
        url: str,
        priority: float = 0.5,
        metadata: dict | None = None,
    ) -> None:
        """Queue a source for crawling."""
        import heapq
        heapq.heappush(self._source_queue, (-priority, url, metadata or {}))
        self.logger.debug("source_queued", url=url, priority=priority)

    async def get_next_source(self) -> tuple[str, dict] | None:
        """Get next source to crawl."""
        import heapq
        while self._source_queue:
            priority, url, metadata = heapq.heappop(self._source_queue)
            if url not in self._active_sources:
                return url, metadata
        return None

    def mark_source_complete(self, url: str) -> None:
        """Mark source as complete."""
        self._active_sources.discard(url)

    async def run_batch(
        self,
        crawler_callback: Callable,
        max_items: int | None = None,
    ) -> dict[str, Any]:
        """Run a batch of crawl operations."""
        max_items = max_items or self.scheduler.schedule.sources_per_session
        results = []

        for _ in range(max_items):
            if not self.scheduler.can_crawl():
                break

            source = await self.get_next_source()
            if not source:
                break

            url, metadata = source
            self._active_sources.add(url)

            try:
                # Wait for appropriate delay
                await self.scheduler.wait_if_needed()

                # Execute crawl
                result = await crawler_callback(url, metadata)

                # Record success
                self.scheduler.record_request(True, result.get("response_time", 1.0))
                results.append(result)

            except Exception as e:
                self.scheduler.record_request(False)
                self.logger.warning("crawl_failed", url=url, error=str(e))

            finally:
                self.mark_source_complete(url)

        return {
            "items_crawled": len(results),
            "intensity": self.scheduler.intensity.value,
            "budget_remaining": self.scheduler.budget.requests_remaining,
        }
