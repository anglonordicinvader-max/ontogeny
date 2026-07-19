"""Acquisition observability — real-time metrics for the Knowledge Acquisition System.

Displays:
- Active research goals
- Current acquisitions
- Requests per minute
- Cache hit rate
- Evidence accepted/rejected
- Network routing, robots exclusions
- Bandwidth usage, latency
- Knowledge graph updates
- Memory additions
- Planning integration
"""

import time
from dataclasses import dataclass, field
from typing import Any

import structlog


@dataclass
class MetricsSnapshot:
    """Point-in-time metrics snapshot."""

    timestamp: float = field(default_factory=time.time)

    # Research
    active_plans: int = 0
    active_objectives: int = 0
    completed_plans: int = 0

    # Requests
    requests_per_minute: float = 0.0
    total_requests: int = 0
    active_requests: int = 0
    failed_requests: int = 0
    retry_count: int = 0

    # Cache
    cache_hit_rate: float = 0.0
    cache_size: int = 0

    # Evidence
    evidence_stored: int = 0
    evidence_accepted: int = 0
    evidence_rejected: int = 0
    evidence_duplicates: int = 0

    # Domains
    domains_accessed: int = 0
    robots_exclusions: int = 0
    domains_paused: int = 0

    # Proxy
    proxy_requests: int = 0
    proxy_failures: int = 0
    direct_requests: int = 0

    # Bandwidth
    bytes_downloaded: int = 0
    bandwidth_last_minute: int = 0

    # Latency
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0

    # Knowledge
    kg_updates: int = 0
    claims_added: int = 0
    claims_verified: int = 0
    claims_disputed: int = 0

    # Memory
    memory_additions: int = 0
    episodic_additions: int = 0
    semantic_additions: int = 0

    # Planning
    plans_created: int = 0
    objectives_completed: int = 0
    objectives_failed: int = 0

    # Depth
    max_depth_reached: int = 0
    avg_depth: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "research": {
                "active_plans": self.active_plans,
                "active_objectives": self.active_objectives,
                "completed_plans": self.completed_plans,
            },
            "requests": {
                "per_minute": self.requests_per_minute,
                "total": self.total_requests,
                "active": self.active_requests,
                "failed": self.failed_requests,
                "retries": self.retry_count,
            },
            "cache": {
                "hit_rate": self.cache_hit_rate,
                "size": self.cache_size,
            },
            "evidence": {
                "stored": self.evidence_stored,
                "accepted": self.evidence_accepted,
                "rejected": self.evidence_rejected,
                "duplicates": self.evidence_duplicates,
            },
            "domains": {
                "accessed": self.domains_accessed,
                "robots_exclusions": self.robots_exclusions,
                "paused": self.domains_paused,
            },
            "proxy": {
                "requests": self.proxy_requests,
                "failures": self.proxy_failures,
                "direct": self.direct_requests,
            },
            "bandwidth": {
                "total_bytes": self.bytes_downloaded,
                "last_minute_bytes": self.bandwidth_last_minute,
            },
            "latency": {
                "avg_ms": self.avg_latency_ms,
                "p95_ms": self.p95_latency_ms,
            },
            "knowledge": {
                "kg_updates": self.kg_updates,
                "claims_added": self.claims_added,
                "claims_verified": self.claims_verified,
                "claims_disputed": self.claims_disputed,
            },
            "memory": {
                "additions": self.memory_additions,
                "episodic": self.episodic_additions,
                "semantic": self.semantic_additions,
            },
            "planning": {
                "plans_created": self.plans_created,
                "objectives_completed": self.objectives_completed,
                "objectives_failed": self.objectives_failed,
            },
            "depth": {
                "max": self.max_depth_reached,
                "avg": self.avg_depth,
            },
        }


class AcquisitionObservability:
    """Tracks and reports acquisition metrics for the observability dashboard."""

    def __init__(self):
        self.snapshots: list[MetricsSnapshot] = []
        self._current = MetricsSnapshot()
        self._request_times: list[float] = []
        self._latencies: list[float] = []
        self.logger = structlog.get_logger()

    @property
    def current(self) -> MetricsSnapshot:
        return self._current

    def record_request(self, latency_ms: float = 0.0, success: bool = True):
        """Record a request event."""
        self._current.total_requests += 1
        self._request_times.append(time.time())
        if not success:
            self._current.failed_requests += 1
        if latency_ms > 0:
            self._latencies.append(latency_ms)

    def record_retry(self):
        self._current.retry_count += 1

    def record_evidence(self, accepted: bool, duplicate: bool = False):
        self._current.evidence_stored += 1
        if accepted:
            self._current.evidence_accepted += 1
        else:
            self._current.evidence_rejected += 1
        if duplicate:
            self._current.evidence_duplicates += 1

    def record_domain_access(self, domain: str):
        self._current.domains_accessed += 1

    def record_robots_exclusion(self):
        self._current.robots_exclusions += 1

    def record_proxy(self, success: bool):
        self._current.proxy_requests += 1
        if not success:
            self._current.proxy_failures += 1

    def record_direct(self):
        self._current.direct_requests += 1

    def record_kg_update(self):
        self._current.kg_updates += 1

    def record_claim(self, disputed: bool = False):
        self._current.claims_added += 1
        if disputed:
            self._current.claims_disputed += 1

    def record_memory(self, memory_type: str = "episodic"):
        self._current.memory_additions += 1
        if memory_type == "episodic":
            self._current.episodic_additions += 1
        elif memory_type == "semantic":
            self._current.semantic_additions += 1

    def record_plan(self):
        self._current.plans_created += 1

    def record_objective(self, success: bool):
        if success:
            self._current.objectives_completed += 1
        else:
            self._current.objectives_failed += 1

    def snapshot(self) -> MetricsSnapshot:
        """Take a metrics snapshot and reset counters."""
        now = time.time()

        # Compute rates
        recent = [t for t in self._request_times if now - t < 60]
        self._current.requests_per_minute = len(recent)

        if self._latencies:
            self._current.avg_latency_ms = sum(self._latencies) / len(self._latencies)
            sorted_lat = sorted(self._latencies)
            idx = int(len(sorted_lat) * 0.95)
            self._current.p95_latency_ms = sorted_lat[min(idx, len(sorted_lat) - 1)]

        snap = MetricsSnapshot(
            timestamp=now,
            active_plans=self._current.active_plans,
            active_objectives=self._current.active_objectives,
            completed_plans=self._current.completed_plans,
            requests_per_minute=self._current.requests_per_minute,
            total_requests=self._current.total_requests,
            active_requests=self._current.active_requests,
            failed_requests=self._current.failed_requests,
            retry_count=self._current.retry_count,
            cache_hit_rate=self._current.cache_hit_rate,
            cache_size=self._current.cache_size,
            evidence_stored=self._current.evidence_stored,
            evidence_accepted=self._current.evidence_accepted,
            evidence_rejected=self._current.evidence_rejected,
            evidence_duplicates=self._current.evidence_duplicates,
            domains_accessed=self._current.domains_accessed,
            robots_exclusions=self._current.robots_exclusions,
            proxy_requests=self._current.proxy_requests,
            proxy_failures=self._current.proxy_failures,
            direct_requests=self._current.direct_requests,
            avg_latency_ms=self._current.avg_latency_ms,
            p95_latency_ms=self._current.p95_latency_ms,
            kg_updates=self._current.kg_updates,
            claims_added=self._current.claims_added,
            claims_verified=self._current.claims_verified,
            claims_disputed=self._current.claims_disputed,
            memory_additions=self._current.memory_additions,
            episodic_additions=self._current.episodic_additions,
            semantic_additions=self._current.semantic_additions,
            plans_created=self._current.plans_created,
            objectives_completed=self._current.objectives_completed,
            objectives_failed=self._current.objectives_failed,
        )
        self.snapshots.append(snap)
        return snap

    def get_dashboard_data(self) -> dict[str, Any]:
        """Get formatted data for the UI dashboard."""
        snap = self._current
        return {
            "status": "active" if snap.active_requests > 0 else "idle",
            "requests_per_minute": snap.requests_per_minute,
            "cache_hit_rate": snap.cache_hit_rate,
            "evidence_stored": snap.evidence_stored,
            "evidence_accepted": snap.evidence_accepted,
            "evidence_rejected": snap.evidence_rejected,
            "avg_latency_ms": snap.avg_latency_ms,
            "active_plans": snap.active_plans,
            "active_objectives": snap.active_objectives,
            "domains_accessed": snap.domains_accessed,
            "bandwidth_bytes": snap.bytes_downloaded,
            "kg_updates": snap.kg_updates,
            "memory_additions": snap.memory_additions,
        }
