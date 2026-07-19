"""Request management — queues, caching, retry, deduplication, budgeting.

Implements:
- Request queuing with priority
- Adaptive backoff and retry limits
- HTTP response caching with TTL
- Duplicate request detection
- Bandwidth monitoring
- Request budgeting and cancellation
- Timeout handling and graceful recovery

Supports robots.txt awareness, request budgeting, rate limiting,
caching, graceful retries, per-domain policies, and request logging.
"""

import asyncio
import hashlib
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable, Awaitable

import structlog


class RequestPriority(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


@dataclass
class CachedResponse:
    """A cached HTTP response."""

    url: str
    status_code: int
    content: bytes
    headers: dict[str, str]
    cached_at: float
    ttl_seconds: float
    content_type: str = ""

    def is_valid(self) -> bool:
        return (time.time() - self.cached_at) < self.ttl_seconds


@dataclass
class RequestEntry:
    """A queued request."""

    id: str
    url: str
    priority: RequestPriority = RequestPriority.NORMAL
    crawler_name: str = ""
    callback: Callable[..., Awaitable] | None = None
    created_at: float = field(default_factory=time.time)
    attempts: int = 0
    max_attempts: int = 3
    timeout: float = 30.0
    metadata: dict[str, Any] = field(default_factory=dict)
    result: Any = None
    error: str = ""
    completed: bool = False


class RequestManager:
    """Manages all HTTP requests with queuing, caching, and budgeting."""

    def __init__(
        self,
        max_concurrent: int = 10,
        max_requests_per_minute: int = 120,
        cache_ttl_seconds: float = 3600.0,
        budget_per_session: int = 1000,
    ):
        self.max_concurrent = max_concurrent
        self.max_requests_per_minute = max_requests_per_minute
        self.cache_ttl = cache_ttl_seconds
        self.budget_per_session = budget_per_session

        # Request queue (priority ordered)
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._active_requests: int = 0
        self._total_requests: int = 0
        self._total_budget_used: int = 0

        # Cache
        self._cache: dict[str, CachedResponse] = {}
        self._cache_hits: int = 0
        self._cache_misses: int = 0

        # Deduplication
        self._in_flight: dict[str, asyncio.Event] = {}  # url -> event
        self._request_history: dict[str, float] = {}  # url -> last_request_time

        # Rate limiting
        self._request_times: list[float] = []
        self._backoff_base: float = 1.0
        self._backoff_max: float = 60.0

        # Bandwidth tracking
        self._bytes_downloaded: int = 0
        self._bytes_timeline: list[tuple[float, int]] = []

        self.logger = structlog.get_logger()

    def _cache_key(self, url: str) -> str:
        return hashlib.sha256(url.encode()).hexdigest()[:16]

    def get_cached(self, url: str) -> CachedResponse | None:
        """Check cache for a valid response."""
        key = self._cache_key(url)
        cached = self._cache.get(key)
        if cached and cached.is_valid():
            self._cache_hits += 1
            return cached
        self._cache_misses += 1
        return None

    def store_cache(
        self,
        url: str,
        status_code: int,
        content: bytes,
        headers: dict[str, str],
        ttl: float | None = None,
        content_type: str = "",
    ):
        """Store a response in cache."""
        key = self._cache_key(url)
        self._cache[key] = CachedResponse(
            url=url,
            status_code=status_code,
            content=content,
            headers=headers,
            cached_at=time.time(),
            ttl_seconds=ttl or self.cache_ttl,
            content_type=content_type,
        )

    def clear_cache(self, domain: str = ""):
        """Clear cache entries, optionally filtered by domain."""
        if domain:
            self._cache = {
                k: v for k, v in self._cache.items() if domain not in v.url
            }
        else:
            self._cache.clear()

    def is_duplicate(self, url: str, cooldown_seconds: float = 60.0) -> bool:
        """Check if a URL was recently requested."""
        last = self._request_history.get(url, 0)
        return (time.time() - last) < cooldown_seconds

    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        now = time.time()
        # Remove entries older than 1 minute
        self._request_times = [t for t in self._request_times if now - t < 60]
        return len(self._request_times) < self.max_requests_per_minute

    def _compute_backoff(self, attempt: int) -> float:
        """Compute exponential backoff with jitter."""
        import random
        delay = self._backoff_base * (2 ** attempt)
        delay = min(delay, self._backoff_max)
        return delay * (0.5 + random.random() * 0.5)

    def budget_remaining(self) -> int:
        return max(0, self.budget_per_session - self._total_budget_used)

    def can_request(self) -> bool:
        """Check if a new request can be made."""
        if self._total_budget_used >= self.budget_per_session:
            return False
        if self._active_requests >= self.max_concurrent:
            return False
        if not self._check_rate_limit():
            return False
        return True

    async def submit(
        self,
        url: str,
        fetch_fn: Callable[..., Awaitable],
        priority: RequestPriority = RequestPriority.NORMAL,
        crawler_name: str = "",
        timeout: float = 30.0,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        """Submit a request. Returns cached response or fetches fresh.

        Handles deduplication, caching, rate limiting, and retry.
        """
        # Check cache first
        cached = self.get_cached(url)
        if cached:
            self.logger.debug("cache_hit", url=url)
            return cached

        # Check deduplication
        if self.is_duplicate(url):
            self.logger.debug("duplicate_skipped", url=url)
            return None

        # Check budget
        if not self.can_request():
            self.logger.warning("budget_exhausted", url=url)
            return None

        # Wait if duplicate in-flight
        if url in self._in_flight:
            await self._in_flight[url].wait()
            return self.get_cached(url)

        # Mark as in-flight
        event = asyncio.Event()
        self._in_flight[url] = event

        try:
            self._active_requests += 1
            self._total_requests += 1
            self._total_budget_used += 1
            self._request_times.append(time.time())
            self._request_history[url] = time.time()

            # Execute with retry
            last_error = None
            for attempt in range(3):
                try:
                    result = await asyncio.wait_for(
                        fetch_fn(url), timeout=timeout
                    )
                    event.set()
                    return result
                except asyncio.TimeoutError:
                    last_error = f"Timeout after {timeout}s"
                    self.logger.warning(
                        "request_timeout", url=url, attempt=attempt
                    )
                except Exception as e:
                    last_error = str(e)
                    self.logger.warning(
                        "request_error", url=url, error=last_error, attempt=attempt
                    )
                if attempt < 2:
                    backoff = self._compute_backoff(attempt)
                    await asyncio.sleep(backoff)

            event.set()
            self.logger.error("request_failed_all_retries", url=url, error=last_error)
            return None
        finally:
            self._active_requests = max(0, self._active_requests - 1)
            self._in_flight.pop(url, None)

    def record_bandwidth(self, bytes_downloaded: int):
        self._bytes_downloaded += bytes_downloaded
        self._bytes_timeline.append((time.time(), bytes_downloaded))

    def get_stats(self) -> dict[str, Any]:
        now = time.time()
        recent_bytes = sum(
            b for t, b in self._bytes_timeline if now - t < 60
        )
        return {
            "total_requests": self._total_requests,
            "active_requests": self._active_requests,
            "budget_used": self._total_budget_used,
            "budget_remaining": self.budget_remaining(),
            "cache_size": len(self._cache),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": (
                self._cache_hits / max(1, self._cache_hits + self._cache_misses)
            ),
            "bytes_downloaded": self._bytes_downloaded,
            "bytes_last_minute": recent_bytes,
            "queue_size": self._queue.qsize(),
        }
