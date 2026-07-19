"""Token bucket rate limiter with async support."""

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class TokenBucket:
    """Token bucket rate limiter."""

    rate: float  # tokens per second
    capacity: int  # burst capacity
    tokens: float = field(init=False)
    last_update: float = field(init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def __post_init__(self):
        self.tokens = float(self.capacity)
        self.last_update = time.monotonic()

    async def acquire(self, tokens: int = 1) -> float:
        """Acquire tokens, returns wait time."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return 0.0
            else:
                wait_time = (tokens - self.tokens) / self.rate
                self.tokens = 0
                return wait_time

    async def wait_and_acquire(self, tokens: int = 1) -> None:
        """Wait for tokens to become available."""
        wait_time = await self.acquire(tokens)
        if wait_time > 0:
            await asyncio.sleep(wait_time)


@dataclass
class SlidingWindowRateLimiter:
    """Sliding window rate limiter for API compliance."""

    max_requests: int
    window_seconds: float
    _requests: deque = field(default_factory=deque)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def acquire(self) -> float:
        """Acquire slot, returns wait time if needed."""
        async with self._lock:
            now = time.monotonic()
            cutoff = now - self.window_seconds

            # Remove old requests
            while self._requests and self._requests[0] < cutoff:
                self._requests.popleft()

            if len(self._requests) < self.max_requests:
                self._requests.append(now)
                return 0.0
            else:
                wait_time = self._requests[0] - cutoff
                return wait_time

    async def wait_and_acquire(self) -> None:
        """Wait for slot to become available."""
        wait_time = await self.acquire()
        if wait_time > 0:
            await asyncio.sleep(wait_time)
            # Record this request
            async with self._lock:
                self._requests.append(time.monotonic())
