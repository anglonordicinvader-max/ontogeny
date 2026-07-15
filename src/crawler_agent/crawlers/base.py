"""Base crawler interface and common functionality."""

import asyncio
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator

import httpx
import structlog
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from ..utils.rate_limiter import TokenBucket, SlidingWindowRateLimiter
from ..utils.proxy import ProxyPool, ProxyAwareClient, Proxy
from ..cognitive.reliability import get_reliability_manager, RetryConfig


class ContentType(str, Enum):
    CODE = "code"
    DOCUMENTATION = "documentation"
    REPOSITORY = "repository"
    ISSUE = "issue"
    DISCUSSION = "discussion"
    DATASET = "dataset"
    MODEL = "model"
    PAPER = "paper"
    OTHER = "other"


class CrawlResult(BaseModel):
    """Result from a crawl operation."""
    url: str
    content_type: ContentType
    title: str = ""
    content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    source: str = ""
    crawled_at: datetime = Field(default_factory=datetime.utcnow)
    checksum: str = ""

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


@dataclass
class CrawlerConfig:
    """Configuration for a crawler."""
    requests_per_second: float = 10.0
    burst_size: int = 50
    max_retries: int = 3
    timeout: float = 30.0
    respect_robots: bool = True
    user_agents: list[str] = field(default_factory=list)
    randomize_delay: bool = True
    min_delay: float = 0.5
    max_delay: float = 2.0


class BaseCrawler(ABC):
    """Abstract base crawler class."""

    def __init__(
        self,
        name: str,
        config: CrawlerConfig | None = None,
        proxy_pool: ProxyPool | None = None,
    ):
        self.name = name
        self.config = config or CrawlerConfig()
        self.logger = structlog.get_logger().bind(crawler=name)

        # Rate limiting
        self.rate_limiter = TokenBucket(
            rate=self.config.requests_per_second,
            capacity=self.config.burst_size,
        )

        # HTTP client
        self.proxy_pool = proxy_pool
        self._client: ProxyAwareClient | None = None

    async def initialize(self) -> None:
        """Initialize the crawler."""
        self._client = ProxyAwareClient(
            pool=self.proxy_pool,
            user_agents=self.config.user_agents or None,
            timeout=self.config.timeout,
            retries=self.config.max_retries,
        )
        await self._setup()
        self.logger.info("crawler_initialized", proxy_enabled=bool(self.proxy_pool))

    async def cleanup(self) -> None:
        """Cleanup crawler resources."""
        await self._cleanup()
        self.logger.info("crawler_cleanup")

    @abstractmethod
    async def _setup(self) -> None:
        """Platform-specific setup."""
        pass

    @abstractmethod
    async def _cleanup(self) -> None:
        """Platform-specific cleanup."""
        pass

    @abstractmethod
    async def crawl(self, url: str, depth: int = 0) -> AsyncIterator[CrawlResult]:
        """Crawl a URL and yield results."""
        pass

    @abstractmethod
    async def discover_urls(self, seed_url: str) -> AsyncIterator[str]:
        """Discover URLs to crawl from a seed."""
        pass

    async def _fetch(self, url: str, **kwargs) -> httpx.Response:
        """Fetch URL with rate limiting, proxy rotation, and retries."""
        await self.rate_limiter.wait_and_acquire()

        # Add random delay for anti-detection
        if self.config.randomize_delay:
            delay = random.uniform(self.config.min_delay, self.config.max_delay)
            await asyncio.sleep(delay)

        if not self._client:
            raise RuntimeError("Crawler not initialized")

        # Use reliability manager for structured retry with circuit breaker
        reliability = get_reliability_manager()
        retry_config = RetryConfig(
            max_retries=self.config.max_retries,
            base_delay=1.0,
            max_delay=30.0,
            jitter=True,
            retryable_exceptions=(httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException),
        )

        async def _do_fetch():
            return await self._client.request("GET", url, **kwargs)

        response = await reliability.execute_with_retry(
            _do_fetch,
            config=retry_config,
            circuit_breaker_name=f"crawler_{self.name}",
            operation_name=f"fetch_{self.name}",
        )
        return response

    async def _fetch_with_proxy(self, url: str, proxy: Proxy | None = None, **kwargs) -> httpx.Response:
        """Fetch URL with specific proxy."""
        await self.rate_limiter.wait_and_acquire()

        if not self._client:
            raise RuntimeError("Crawler not initialized")

        if proxy:
            # Use specific proxy
            async with httpx.AsyncClient(
                proxy=proxy.to_httpx(),
                timeout=self.config.timeout,
                follow_redirects=True,
            ) as client:
                response = await client.request("GET", url, **kwargs)
                return response
        else:
            return await self._client.request("GET", url, **kwargs)

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
