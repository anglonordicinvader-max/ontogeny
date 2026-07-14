"""Enhanced proxy management with health checks and rotation."""

import asyncio
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import AsyncIterator
from urllib.parse import urlparse, urlunparse

import httpx
import structlog
from fake_useragent import UserAgent


class ProxyProtocol(str, Enum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"


class ProxyStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DEAD = "dead"
    UNKNOWN = "unknown"


@dataclass
class Proxy:
    """Proxy configuration with health tracking."""
    url: str
    protocol: ProxyProtocol = ProxyProtocol.HTTP
    username: str | None = None
    password: str | None = None
    
    # Health tracking
    status: ProxyStatus = ProxyStatus.UNKNOWN
    success_count: int = 0
    failure_count: int = 0
    total_requests: int = 0
    last_used: float = 0.0
    last_success: float = 0.0
    last_failure: float = 0.0
    avg_response_time: float = 0.0
    
    # Configuration
    max_failures: int = 3
    timeout: float = 10.0

    @property
    def is_healthy(self) -> bool:
        """Check if proxy is healthy enough to use."""
        if self.status == ProxyStatus.DEAD:
            return False
        if self.failure_count >= self.max_failures:
            return False
        # Check success rate if we have enough data
        if self.total_requests >= 5:
            success_rate = self.success_count / self.total_requests
            return success_rate > 0.3
        return True

    @property
    def health_score(self) -> float:
        """Calculate health score (0-1)."""
        if self.total_requests == 0:
            return 0.5
        success_rate = self.success_count / self.total_requests
        # Penalize high response times
        time_penalty = min(1.0, self.avg_response_time / 5.0)
        return success_rate * (1 - time_penalty * 0.3)

    def to_httpx(self) -> str:
        """Convert to httpx proxy format."""
        if self.username and self.password:
            # URL encode special characters
            from urllib.parse import quote
            user = quote(self.username, safe='')
            pwd = quote(self.password, safe='')
            return f"{self.protocol.value}://{user}:{pwd}@{self._host_port}"
        return f"{self.protocol.value}://{self._host_port}"

    @property
    def _host_port(self) -> str:
        """Extract host:port from URL."""
        parsed = urlparse(self.url)
        return f"{parsed.hostname}:{parsed.port}" if parsed.port else parsed.hostname

    def record_success(self, response_time: float) -> None:
        """Record successful request."""
        self.success_count += 1
        self.total_requests += 1
        self.last_success = time.monotonic()
        self.last_used = time.monotonic()
        # Update average response time
        if self.avg_response_time == 0:
            self.avg_response_time = response_time
        else:
            self.avg_response_time = (self.avg_response_time + response_time) / 2
        # Reset failure count on success
        if self.status == ProxyStatus.DEGRADED:
            self.status = ProxyStatus.HEALTHY
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self) -> None:
        """Record failed request."""
        self.failure_count += 1
        self.total_requests += 1
        self.last_failure = time.monotonic()
        self.last_used = time.monotonic()
        
        if self.failure_count >= self.max_failures:
            self.status = ProxyStatus.DEAD
        elif self.failure_count >= self.max_failures // 2:
            self.status = ProxyStatus.DEGRADED

    @classmethod
    def from_string(cls, proxy_str: str, **kwargs) -> "Proxy":
        """Parse proxy string like protocol://user:pass@host:port."""
        parsed = urlparse(proxy_str)
        
        protocol_map = {
            "http": ProxyProtocol.HTTP,
            "https": ProxyProtocol.HTTPS,
            "socks5": ProxyProtocol.SOCKS5,
        }
        
        protocol = protocol_map.get(parsed.scheme, ProxyProtocol.HTTP)
        
        return cls(
            url=proxy_str,
            protocol=protocol,
            username=parsed.username,
            password=parsed.password,
            **kwargs,
        )


class ProxyPool:
    """Manages a pool of rotating proxies with health tracking."""

    def __init__(
        self,
        proxies: list[str] | None = None,
        max_failures: int = 3,
        health_check_interval: int = 300,
    ):
        self._proxies: list[Proxy] = []
        self._index = 0
        self._lock = asyncio.Lock()
        self.max_failures = max_failures
        self.health_check_interval = health_check_interval
        self.logger = structlog.get_logger()
        self._last_health_check = time.monotonic()

        if proxies:
            for url in proxies:
                self.add_proxy(url)

    def add_proxy(self, url: str, **kwargs) -> Proxy:
        """Add a proxy to the pool."""
        proxy = Proxy.from_string(url, max_failures=self.max_failures, **kwargs)
        self._proxies.append(proxy)
        self.logger.debug("proxy_added", url=proxy._host_port)
        return proxy

    def load_from_file(self, filepath: str) -> int:
        """Load proxies from file (one per line)."""
        path = Path(filepath)
        if not path.exists():
            self.logger.warning("proxy_file_not_found", path=filepath)
            return 0

        count = 0
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                self.add_proxy(line)
                count += 1

        self.logger.info("proxies_loaded", count=count, file=filepath)
        return count

    async def get_proxy(self, prefer_healthy: bool = True) -> Proxy | None:
        """Get next proxy with rotation."""
        async with self._lock:
            # Health check if needed
            now = time.monotonic()
            if now - self._last_health_check > self.health_check_interval:
                await self._health_check()
                self._last_health_check = now

            if not self._proxies:
                return None

            # Filter healthy proxies
            if prefer_healthy:
                healthy = [p for p in self._proxies if p.is_healthy]
                if not healthy:
                    # Reset dead proxies and try again
                    for p in self._proxies:
                        if p.status == ProxyStatus.DEAD:
                            p.failure_count = max(0, p.failure_count - 2)
                            p.status = ProxyStatus.DEGRADED
                    healthy = self._proxies
            else:
                healthy = self._proxies

            # Round-robin with some randomization
            if random.random() < 0.3:  # 30% random selection
                proxy = random.choice(healthy)
            else:
                proxy = healthy[self._index % len(healthy)]
                self._index += 1

            proxy.last_used = now
            return proxy

    async def _health_check(self) -> None:
        """Check health of all proxies."""
        self.logger.debug("running_proxy_health_check")
        
        for proxy in self._proxies:
            if proxy.total_requests > 0 and not proxy.is_healthy:
                # Reset old failures
                age = time.monotonic() - proxy.last_failure
                if age > 3600:  # 1 hour
                    proxy.failure_count = max(0, proxy.failure_count - 1)
                    if proxy.status == ProxyStatus.DEAD and proxy.failure_count < proxy.max_failures:
                        proxy.status = ProxyStatus.DEGRADED

    def report_success(self, proxy: Proxy, response_time: float = 0.0) -> None:
        """Report successful use of proxy."""
        proxy.record_success(response_time)

    def report_failure(self, proxy: Proxy) -> None:
        """Report failed use of proxy."""
        proxy.record_failure()

    def get_stats(self) -> dict:
        """Get pool statistics."""
        return {
            "total": len(self._proxies),
            "healthy": sum(1 for p in self._proxies if p.is_healthy),
            "dead": sum(1 for p in self._proxies if p.status == ProxyStatus.DEAD),
            "avg_health": sum(p.health_score for p in self._proxies) / max(len(self._proxies), 1),
        }


class ProxyAwareClient:
    """HTTP client with automatic proxy rotation and failover."""

    def __init__(
        self,
        pool: ProxyPool | None = None,
        user_agents: list[str] | None = None,
        timeout: float = 30.0,
        retries: int = 3,
        **client_kwargs,
    ):
        self.pool = pool or ProxyPool()
        self.timeout = timeout
        self.retries = retries
        self._client_kwargs = client_kwargs
        self.logger = structlog.get_logger()
        
        # User agent rotation
        try:
            self._ua = UserAgent()
        except Exception:
            self._ua = None
        self._user_agents = user_agents or [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        ]

    def _get_headers(self, extra_headers: dict | None = None) -> dict:
        """Get headers with random user agent."""
        if self._ua:
            ua = self._ua.random
        else:
            ua = random.choice(self._user_agents)

        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
        if extra_headers:
            headers.update(extra_headers)
        return headers

    async def request(
        self,
        method: str,
        url: str,
        headers: dict | None = None,
        **kwargs,
    ) -> httpx.Response:
        """Make request with proxy rotation and failover."""
        last_error = None
        used_proxies = set()

        for attempt in range(self.retries + 1):
            proxy = await self.pool.get_proxy()
            if not proxy:
                # Try without proxy if none available
                if not self.pool._proxies:
                    return await self._make_request(method, url, None, headers, **kwargs)
                raise RuntimeError("No proxies available")

            # Skip already failed proxies
            proxy_key = proxy._host_port
            if proxy_key in used_proxies and len(used_proxies) < len(self.pool._proxies):
                continue
            used_proxies.add(proxy_key)

            try:
                start_time = time.monotonic()
                response = await self._make_request(
                    method, url, proxy, headers, **kwargs
                )
                elapsed = time.monotonic() - start_time
                self.pool.report_success(proxy, elapsed)
                return response

            except Exception as e:
                last_error = e
                self.pool.report_failure(proxy)
                self.logger.warning(
                    "proxy_request_failed",
                    proxy=proxy._host_port,
                    attempt=attempt + 1,
                    error=str(e),
                )
                continue

        raise last_error or RuntimeError("All proxy attempts failed")

    async def _make_request(
        self,
        method: str,
        url: str,
        proxy: Proxy | None,
        headers: dict | None = None,
        **kwargs,
    ) -> httpx.Response:
        """Make actual HTTP request."""
        proxy_url = proxy.to_httpx() if proxy else None
        request_headers = self._get_headers(headers)

        async with httpx.AsyncClient(
            proxy=proxy_url,
            timeout=self.timeout,
            follow_redirects=True,
            **self._client_kwargs,
        ) as client:
            response = await client.request(
                method, url, headers=request_headers, **kwargs
            )
            response.raise_for_status()
            return response

    async def get(self, url: str, **kwargs) -> httpx.Response:
        """GET request."""
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        """POST request."""
        return await self.request("POST", url, **kwargs)


class AnonymityLayer:
    """Multi-layer anonymity with proxy chaining."""

    def __init__(self, primary_pool: ProxyPool, exit_pool: ProxyPool | None = None):
        self.primary = primary_pool
        self.exit = exit_pool or primary_pool
        self.logger = structlog.get_logger()

    async def create_chain(self) -> list[Proxy]:
        """Create proxy chain for request."""
        primary = await self.primary.get_proxy()
        exit_proxy = await self.exit.get_proxy()
        
        chain = []
        if primary:
            chain.append(primary)
        if exit_proxy and exit_proxy != primary:
            chain.append(exit_proxy)
        
        return chain

    async def get_anonymous_client(self) -> ProxyAwareClient:
        """Get client configured for anonymity."""
        # Use exit proxy as the main proxy
        exit_proxy = await self.exit.get_proxy()
        
        client = ProxyAwareClient(pool=self.exit)
        return client
