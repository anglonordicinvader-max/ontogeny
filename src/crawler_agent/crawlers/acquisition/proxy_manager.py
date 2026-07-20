"""Network Transport Layer — centralized network routing management.

Responsible for:
- Network endpoint registry and health monitoring
- Authentication, latency tracking
- Retry handling, failover, regional routing
- Connection statistics

Network routing exists for:
- enterprise routing
- authenticated outbound gateways
- regional testing
- failover
- network isolation

Direct connections are preferred by default. Network routing is configurable
and optional — not a primary feature.
"""

import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import structlog


class ProxyStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DISABLED = "disabled"


@dataclass
class ProxyEndpoint:
    """A single proxy endpoint."""

    url: str
    name: str = ""
    proxy_type: str = "http"  # http, https, socks5
    region: str = "global"
    username: str = ""
    password: str = ""

    # Health tracking
    status: ProxyStatus = ProxyStatus.HEALTHY
    latency_ms: float = 0.0
    success_rate: float = 1.0
    total_requests: int = 0
    failed_requests: int = 0
    last_used: float = 0.0
    last_health_check: float = 0.0
    consecutive_failures: int = 0

    # Limits
    max_concurrent: int = 10
    current_concurrent: int = 0
    requests_per_minute: int = 60
    allowed_domains: list[str] = field(default_factory=list)
    disabled_domains: list[str] = field(default_factory=list)

    def is_available(self, domain: str = "") -> bool:
        if self.status == ProxyStatus.DISABLED:
            return False
        if self.status == ProxyStatus.UNHEALTHY:
            return False
        if self.current_concurrent >= self.max_concurrent:
            return False
        if domain and self.disabled_domains and domain not in self.allowed_domains:
            return False
        return True

    def record_request(self, success: bool, latency_ms: float = 0.0):
        self.total_requests += 1
        self.last_used = time.time()
        if success:
            self.failed_requests = max(0, self.failed_requests - 1)
            self.consecutive_failures = 0
        else:
            self.failed_requests += 1
            self.consecutive_failures += 1
        # Update success rate (rolling)
        if self.total_requests > 0:
            self.success_rate = 1.0 - (self.failed_requests / self.total_requests)
        # Update latency (EMA)
        if latency_ms > 0:
            self.latency_ms = 0.3 * latency_ms + 0.7 * self.latency_ms
        # Update status based on health
        if self.consecutive_failures >= 5:
            self.status = ProxyStatus.UNHEALTHY
        elif self.success_rate < 0.7:
            self.status = ProxyStatus.DEGRADED
        elif self.success_rate >= 0.95:
            self.status = ProxyStatus.HEALTHY


class ProxyManager:
    """Centralized proxy management and selection."""

    def __init__(self):
        self.proxies: list[ProxyEndpoint] = []
        self.logger = structlog.get_logger()

    def register(self, proxy: ProxyEndpoint):
        """Register a proxy endpoint."""
        self.proxies.append(proxy)
        self.logger.info("proxy_registered", name=proxy.name, region=proxy.region)

    def unregister(self, name: str):
        self.proxies = [p for p in self.proxies if p.name != name]

    def select(
        self,
        domain: str = "",
        region: str = "",
        prefer_direct: bool = True,
    ) -> ProxyEndpoint | None:
        """Select the best available proxy.

        Priority: direct (None) -> approved -> regional -> any healthy.
        """
        available = [p for p in self.proxies if p.is_available(domain)]

        if not available:
            return None  # will use direct connection

        # Prefer direct if no proxy needed
        if prefer_direct and not available:
            return None

        # Filter by region if specified
        if region:
            regional = [p for p in available if p.region == region]
            if regional:
                available = regional

        # Filter by allowed domains
        domain_ok = [p for p in available if not p.allowed_domains or domain in p.allowed_domains]
        if domain_ok:
            available = domain_ok

        # Sort by: success rate (desc), latency (asc), current load (asc)
        available.sort(key=lambda p: (-p.success_rate, p.latency_ms, p.current_concurrent))

        return available[0] if available else None

    def record_result(self, proxy_name: str, success: bool, latency_ms: float = 0.0):
        """Record a request result for a proxy."""
        for p in self.proxies:
            if p.name == proxy_name:
                p.record_request(success, latency_ms)
                break

    def health_check_all(self) -> dict[str, str]:
        """Check health of all proxies. Returns status map."""
        results = {}
        for p in self.proxies:
            # Mark stale proxies as unhealthy
            if p.last_health_check > 0:
                age = time.time() - p.last_health_check
                if age > 300 and p.consecutive_failures > 0:  # 5 min
                    p.status = ProxyStatus.UNHEALTHY
            results[p.name] = p.status.value
        return results

    def get_stats(self) -> dict[str, Any]:
        if not self.proxies:
            return {"total": 0, "healthy": 0}
        return {
            "total": len(self.proxies),
            "healthy": sum(1 for p in self.proxies if p.status == ProxyStatus.HEALTHY),
            "degraded": sum(1 for p in self.proxies if p.status == ProxyStatus.DEGRADED),
            "unhealthy": sum(1 for p in self.proxies if p.status == ProxyStatus.UNHEALTHY),
            "avg_latency_ms": (sum(p.latency_ms for p in self.proxies) / len(self.proxies)),
            "avg_success_rate": (sum(p.success_rate for p in self.proxies) / len(self.proxies)),
        }
