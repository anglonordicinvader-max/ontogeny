"""Persistent domain policies for the Knowledge Acquisition System.

Each domain gets a policy that controls:
- robots.txt status and compliance
- Request delay, concurrent request limits
- Browser requirement, cache policy
- Acquisition budget, retry limits, maximum depth
- Content size limits, preferred retrieval method
- Network transport preference, expiration

Supports: global pause, domain pause, emergency shutdown, allowlist, denylist.
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog


@dataclass
class DomainPolicy:
    """Behavioral policy for a specific domain."""

    domain: str

    # robots.txt
    robots_txt_status: str = "unknown"  # "compliant", "non_compliant", "unknown", "absent"
    robots_crawl_delay: float = 0.0  # seconds, from robots.txt
    robots_disallowed_paths: list[str] = field(default_factory=list)

    # Request behavior
    request_delay: float = 1.0  # minimum seconds between requests
    concurrent_request_limit: int = 2
    max_requests_per_minute: int = 30
    max_requests_per_hour: int = 500

    # Retrieval
    requires_browser: bool = False  # needs Playwright
    preferred_method: str = "api"  # "api", "http", "browser", "feed"
    cache_ttl_seconds: float = 3600.0  # how long to cache responses
    use_cache: bool = True

    # Crawl limits
    crawl_budget: int = 100  # max requests per research session
    max_depth: int = 3
    retry_limit: int = 3
    timeout_seconds: float = 30.0
    max_content_size_bytes: int = 10 * 1024 * 1024  # 10MB

    # Proxy
    proxy_preference: str = "direct"  # "direct", "any", "regional", "none"
    allowed_proxy_regions: list[str] = field(default_factory=list)

    # State
    enabled: bool = True
    paused: bool = False
    paused_reason: str = ""
    last_crawl_time: float = 0.0
    total_requests_today: int = 0
    total_requests_all_time: int = 0
    failed_requests_today: int = 0
    last_robots_check: float = 0.0

    # Expiration
    policy_expires_at: float = 0.0  # 0 = never

    def is_available(self) -> bool:
        """Check if this domain is currently available for crawling."""
        if not self.enabled:
            return False
        if self.paused:
            return False
        if self.policy_expires_at > 0 and time.time() > self.policy_expires_at:
            return False
        return True

    def can_request(self) -> bool:
        """Check if a new request is allowed under current limits."""
        if not self.is_available():
            return False
        now = time.time()
        # Respect crawl delay
        if now - self.last_crawl_time < self.request_delay:
            return False
        # Respect hourly limit (simple rolling window)
        # In production, use a proper sliding window
        if self.total_requests_today >= self.max_requests_per_hour:
            return False
        return True

    def record_request(self, success: bool = True):
        """Record a request was made."""
        self.last_crawl_time = time.time()
        self.total_requests_today += 1
        self.total_requests_all_time += 1
        if not success:
            self.failed_requests_today += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "enabled": self.enabled,
            "paused": self.paused,
            "robots_status": self.robots_txt_status,
            "request_delay": self.request_delay,
            "concurrent_limit": self.concurrent_request_limit,
            "requires_browser": self.requires_browser,
            "preferred_method": self.preferred_method,
            "crawl_budget": self.crawl_budget,
            "max_depth": self.max_depth,
            "total_requests": self.total_requests_all_time,
            "failed_requests": self.failed_requests_today,
        }


class DomainPolicies:
    """Manages persistent policies for all domains."""

    def __init__(self, state_path: str | Path | None = None):
        self.policies: dict[str, DomainPolicy] = {}
        self.global_paused: bool = False
        self.global_pause_reason: str = ""
        self.emergency_shutdown: bool = False
        self.allowlist: set[str] = set()  # if non-empty, ONLY these domains allowed
        self.denylist: set[str] = set()  # these domains never allowed
        self.state_path = Path(state_path) if state_path else None
        self.logger = structlog.get_logger()

        if self.state_path and self.state_path.exists():
            self._load_state()

    def get_policy(self, domain: str) -> DomainPolicy:
        """Get or create a policy for a domain."""
        if domain not in self.policies:
            self.policies[domain] = DomainPolicy(domain=domain)
        return self.policies[domain]

    def is_allowed(self, domain: str) -> bool:
        """Check if a domain is allowed for crawling."""
        if self.emergency_shutdown:
            return False
        if self.global_paused:
            return False
        if domain in self.denylist:
            return False
        if self.allowlist and domain not in self.allowlist:
            return False
        policy = self.get_policy(domain)
        return policy.is_available()

    def pause_domain(self, domain: str, reason: str = ""):
        """Pause crawling for a specific domain."""
        policy = self.get_policy(domain)
        policy.paused = True
        policy.paused_reason = reason
        self.logger.info("domain_paused", domain=domain, reason=reason)

    def resume_domain(self, domain: str):
        """Resume crawling for a domain."""
        policy = self.get_policy(domain)
        policy.paused = False
        policy.paused_reason = ""
        self.logger.info("domain_resumed", domain=domain)

    def pause_global(self, reason: str = ""):
        """Pause all crawling globally."""
        self.global_paused = True
        self.global_pause_reason = reason
        self.logger.info("global_pause", reason=reason)

    def resume_global(self):
        """Resume all crawling."""
        self.global_paused = False
        self.global_pause_reason = ""
        self.logger.info("global_resume")

    def emergency_stop(self):
        """Emergency shutdown of all crawling."""
        self.emergency_shutdown = True
        self.logger.warning("emergency_shutdown")

    def add_to_denylist(self, domain: str):
        self.denylist.add(domain)
        self.logger.info("domain_denied", domain=domain)

    def remove_from_denylist(self, domain: str):
        self.denylist.discard(domain)

    def add_to_allowlist(self, domain: str):
        self.allowlist.add(domain)

    def remove_from_allowlist(self, domain: str):
        self.allowlist.discard(domain)

    def reset_daily_counters(self):
        """Reset daily request counters. Call at midnight."""
        for policy in self.policies.values():
            policy.total_requests_today = 0
            policy.failed_requests_today = 0

    def save_state(self):
        """Persist policies to disk."""
        if not self.state_path:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "global_paused": self.global_paused,
            "global_pause_reason": self.global_pause_reason,
            "emergency_shutdown": self.emergency_shutdown,
            "allowlist": list(self.allowlist),
            "denylist": list(self.denylist),
            "policies": {k: v.to_dict() for k, v in self.policies.items()},
        }
        self.state_path.write_text(json.dumps(data, indent=2))

    def _load_state(self):
        """Load persisted state."""
        try:
            data = json.loads(self.state_path.read_text())
            self.global_paused = data.get("global_paused", False)
            self.global_pause_reason = data.get("global_pause_reason", "")
            self.emergency_shutdown = data.get("emergency_shutdown", False)
            self.allowlist = set(data.get("allowlist", []))
            self.denylist = set(data.get("denylist", []))
            for domain, pdata in data.get("policies", {}).items():
                policy = DomainPolicy(domain=domain)
                policy.enabled = pdata.get("enabled", True)
                policy.paused = pdata.get("paused", False)
                policy.robots_txt_status = pdata.get("robots_status", "unknown")
                policy.request_delay = pdata.get("request_delay", 1.0)
                policy.concurrent_request_limit = pdata.get("concurrent_limit", 2)
                policy.requires_browser = pdata.get("requires_browser", False)
                policy.preferred_method = pdata.get("preferred_method", "api")
                policy.crawl_budget = pdata.get("crawl_budget", 100)
                policy.max_depth = pdata.get("max_depth", 3)
                policy.total_requests_all_time = pdata.get("total_requests", 0)
                self.policies[domain] = policy
        except Exception as e:
            self.logger.warning("policy_load_failed", error=str(e))

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_policies": len(self.policies),
            "enabled": sum(1 for p in self.policies.values() if p.enabled),
            "paused": sum(1 for p in self.policies.values() if p.paused),
            "global_paused": self.global_paused,
            "emergency_shutdown": self.emergency_shutdown,
            "denylist_size": len(self.denylist),
            "allowlist_size": len(self.allowlist),
        }
