"""Source quality scoring and prioritization for the Knowledge Acquisition System.

Assigns weighted quality scores to information sources based on:
- Official status, author reputation, publication quality
- Citation count, corroboration, freshness
- Completeness, consistency, historical reliability

Source categories are prioritized in this order:
1. Official Documentation
2. Research Papers
3. Government Sources
4. Standards Organizations
5. Technical Documentation
6. Reputable Publications
7. Community Forums
8. Blogs
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

import structlog


class SourceCategory(StrEnum):
    """Source categories ordered by inherent trust level."""

    OFFICIAL_API = "official_api"
    OFFICIAL_DOCS = "official_docs"
    ACADEMIC = "academic"
    GOVERNMENT = "government"
    STANDARDS = "standards"
    TECH_DOCS = "tech_docs"
    REPUTABLE_NEWS = "reputable_news"
    FORUM = "forum"
    COMMUNITY = "community"
    BLOG = "blog"
    SOCIAL_MEDIA = "social_media"
    UNKNOWN = "unknown"


# Inherent base trust per category (0.0 - 1.0)
CATEGORY_BASE_TRUST: dict[SourceCategory, float] = {
    SourceCategory.OFFICIAL_API: 0.95,
    SourceCategory.OFFICIAL_DOCS: 0.93,
    SourceCategory.ACADEMIC: 0.90,
    SourceCategory.GOVERNMENT: 0.88,
    SourceCategory.STANDARDS: 0.92,
    SourceCategory.TECH_DOCS: 0.82,
    SourceCategory.REPUTABLE_NEWS: 0.75,
    SourceCategory.FORUM: 0.55,
    SourceCategory.COMMUNITY: 0.50,
    SourceCategory.BLOG: 0.45,
    SourceCategory.SOCIAL_MEDIA: 0.30,
    SourceCategory.UNKNOWN: 0.35,
}


@dataclass
class SourceProfile:
    """Accumulated quality metrics for a source."""

    domain: str
    category: SourceCategory = SourceCategory.UNKNOWN
    official_status: float = 0.0  # 0-1: is this an official source
    author_reputation: float = 0.5  # 0-1: author credibility
    citation_count: int = 0
    corroboration_count: int = 0  # how many other sources agree
    contradiction_count: int = 0
    freshness_hours: float = 0.0  # hours since publication
    completeness: float = 0.5  # 0-1: how complete is the content
    consistency_score: float = 1.0  # 0-1: internal consistency
    historical_reliability: float = 0.5  # 0-1: past accuracy
    last_updated: datetime = field(default_factory=datetime.utcnow)
    total_fetches: int = 0
    successful_fetches: int = 0
    avg_latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SourceScore:
    """Computed quality score for a source."""

    domain: str
    category: SourceCategory
    base_trust: float
    quality_score: float  # final weighted score 0-1
    components: dict[str, float]  # breakdown of score components
    confidence: float  # how confident we are in this score
    recommendation: str  # "prefer", "acceptable", "avoid", "block"


class SourceQualityScorer:
    """Computes weighted quality scores for information sources."""

    # Weight factors for each component
    WEIGHTS = {
        "base_trust": 0.25,
        "official_status": 0.15,
        "author_reputation": 0.10,
        "citations": 0.10,
        "corroboration": 0.10,
        "freshness": 0.10,
        "completeness": 0.05,
        "consistency": 0.05,
        "historical_reliability": 0.10,
    }

    def __init__(self):
        self.profiles: dict[str, SourceProfile] = {}
        self.logger = structlog.get_logger()

    def get_profile(self, domain: str) -> SourceProfile:
        """Get or create a source profile."""
        if domain not in self.profiles:
            self.profiles[domain] = SourceProfile(domain=domain)
        return self.profiles[domain]

    def score(self, domain: str, category: SourceCategory | None = None) -> SourceScore:
        """Compute quality score for a domain."""
        profile = self.get_profile(domain)
        if category:
            profile.category = category

        base_trust = CATEGORY_BASE_TRUST.get(profile.category, 0.35)

        # Compute each component
        components = {}

        # Base trust
        components["base_trust"] = base_trust

        # Official status
        components["official_status"] = profile.official_status

        # Author reputation
        components["author_reputation"] = profile.author_reputation

        # Citation score (logarithmic scaling, capped at 1.0)
        import math

        if profile.citation_count > 0:
            components["citations"] = min(1.0, math.log1p(profile.citation_count) / 10.0)
        else:
            components["citations"] = 0.0

        # Corroboration vs contradiction
        total_refs = profile.corroboration_count + profile.contradiction_count
        if total_refs > 0:
            components["corroboration"] = profile.corroboration_count / total_refs
        else:
            components["corroboration"] = 0.5  # neutral when no references

        # Freshness (decays over time, 1.0 at 0 hours, ~0.2 at 1 year)
        hours = max(0, profile.freshness_hours)
        components["freshness"] = max(0.2, 1.0 / (1.0 + hours / 720.0))

        # Completeness
        components["completeness"] = profile.completeness

        # Consistency
        components["consistency"] = profile.consistency_score

        # Historical reliability
        components["historical_reliability"] = profile.historical_reliability

        # Weighted sum
        quality_score = sum(components[k] * self.WEIGHTS[k] for k in self.WEIGHTS)
        quality_score = max(0.0, min(1.0, quality_score))

        # Confidence based on data availability
        data_points = sum(1 for v in components.values() if v != 0.5)
        confidence = min(1.0, data_points / len(self.WEIGHTS))

        # Recommendation
        if quality_score >= 0.75:
            recommendation = "prefer"
        elif quality_score >= 0.50:
            recommendation = "acceptable"
        elif quality_score >= 0.30:
            recommendation = "avoid"
        else:
            recommendation = "block"

        return SourceScore(
            domain=domain,
            category=profile.category,
            base_trust=base_trust,
            quality_score=quality_score,
            components=components,
            confidence=confidence,
            recommendation=recommendation,
        )

    def update_from_fetch(
        self,
        domain: str,
        success: bool,
        latency_ms: float = 0.0,
        content_length: int = 0,
    ):
        """Update profile after a fetch attempt."""
        profile = self.get_profile(domain)
        profile.total_fetches += 1
        if success:
            profile.successful_fetches += 1
        # Exponential moving average for latency
        alpha = 0.3
        profile.avg_latency_ms = alpha * latency_ms + (1 - alpha) * profile.avg_latency_ms
        profile.last_updated = datetime.utcnow()
        # Completeness hint from content length
        if content_length > 0:
            expected = max(1000, profile.metadata.get("avg_content_length", 1000))
            profile.completeness = min(1.0, content_length / expected)
            profile.metadata["avg_content_length"] = 0.7 * expected + 0.3 * content_length

    def update_corroboration(self, domain: str, agrees: bool):
        """Record corroboration or contradiction from another source."""
        profile = self.get_profile(domain)
        if agrees:
            profile.corroboration_count += 1
        else:
            profile.contradiction_count += 1

    def classify_domain(self, domain: str) -> SourceCategory:
        """Auto-classify a domain into a source category."""
        domain = domain.lower()

        # Official APIs
        if any(
            p in domain
            for p in [
                "api.github.com",
                "api.gitlab.com",
                "pypi.org",
                "registry.npmjs.org",
                "crates.io",
                "api.semanticscholar.org",
                "export.arxiv.org",
            ]
        ):
            return SourceCategory.OFFICIAL_API

        # Academic
        if any(
            p in domain
            for p in [
                "arxiv.org",
                "semanticscholar.org",
                "scholar.google",
                "pubmed",
                "ieee.org",
                "acm.org",
                "springer.com",
                "wiley.com",
            ]
        ):
            return SourceCategory.ACADEMIC

        # Government / standards
        if any(
            p in domain
            for p in [
                ".gov",
                ".mil",
                "nist.gov",
                "iso.org",
                "ietf.org",
                "w3.org",
                "ecma-international.org",
            ]
        ):
            return SourceCategory.GOVERNMENT

        # Official docs
        if any(
            p in domain
            for p in [
                "docs.python.org",
                "developer.mozilla.org",
                "docs.microsoft.com",
                "docs.aws.amazon.com",
                "cloud.google.com/docs",
                "docs.docker.com",
                "docs.blender.org",
            ]
        ):
            return SourceCategory.OFFICIAL_DOCS

        # Tech docs / repos
        if any(
            p in domain
            for p in [
                "github.com",
                "gitlab.com",
                "bitbucket.org",
                "readthedocs.io",
                "crates.io",
                "pkg.go.dev",
            ]
        ):
            return SourceCategory.TECH_DOCS

        # Forums / community
        if any(
            p in domain
            for p in [
                "stackoverflow.com",
                "reddit.com",
                "news.ycombinator.com",
                "discourse.org",
            ]
        ):
            return SourceCategory.FORUM

        # News
        if any(
            p in domain
            for p in [
                "reuters.com",
                "apnews.com",
                "bbc.com",
                "nytimes.com",
                "techcrunch.com",
                "arstechnica.com",
                "theverge.com",
            ]
        ):
            return SourceCategory.REPUTABLE_NEWS

        return SourceCategory.UNKNOWN

    def rank_sources(
        self, domains: list[str], category_filter: SourceCategory | None = None
    ) -> list[SourceScore]:
        """Rank multiple sources by quality score."""
        scores = []
        for domain in domains:
            s = self.score(domain)
            if category_filter and s.category != category_filter:
                continue
            scores.append(s)
        return sorted(scores, key=lambda x: x.quality_score, reverse=True)

    def get_stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        if not self.profiles:
            return {"total_sources": 0}
        categories = {}
        for p in self.profiles.values():
            categories[p.category.value] = categories.get(p.category.value, 0) + 1
        return {
            "total_sources": len(self.profiles),
            "categories": categories,
            "avg_reliability": sum(p.historical_reliability for p in self.profiles.values())
            / len(self.profiles),
        }
