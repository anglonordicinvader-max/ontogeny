"""Knowledge validation — evidence-based claim tracking.

Each claim stores:
- confidence
- supporting sources
- contradictory sources
- first observed, last verified
- verification schedule
- source quality score

Conflicting information remains represented instead of being silently overwritten.
"""

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog


@dataclass
class Claim:
    """A knowledge claim with evidence tracking."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    text: str = ""
    subject: str = ""
    predicate: str = ""
    obj: str = ""  # object of the triple

    # Evidence
    supporting_sources: list[str] = field(default_factory=list)  # evidence doc IDs
    contradictory_sources: list[str] = field(default_factory=list)
    supporting_count: int = 0
    contradictory_count: int = 0

    # Quality
    confidence: float = 0.5  # 0-1
    source_quality_score: float = 0.5  # average quality of sources

    # Temporal
    first_observed: datetime = field(default_factory=datetime.utcnow)
    last_verified: datetime = field(default_factory=datetime.utcnow)
    next_verification: datetime | None = None
    verification_interval_hours: float = 168.0  # 1 week default

    # State
    is_stale: bool = False
    is_confirmed: bool = False
    is_disputed: bool = False
    version: int = 1
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_support(self, source_id: str, source_quality: float = 0.5):
        """Add a supporting source."""
        if source_id not in self.supporting_sources:
            self.supporting_sources.append(source_id)
            self.supporting_count += 1
            self._update_confidence(source_quality, agrees=True)
            self.last_verified = datetime.utcnow()
            self.version += 1

    def add_contradiction(self, source_id: str, source_quality: float = 0.5):
        """Add a contradictory source."""
        if source_id not in self.contradictory_sources:
            self.contradictory_sources.append(source_id)
            self.contradictory_count += 1
            self._update_confidence(source_quality, agrees=False)
            self.is_disputed = self.contradictory_count >= 2
            self.version += 1

    def _update_confidence(self, source_quality: float, agrees: bool):
        """Update confidence based on new evidence."""
        if agrees:
            # Bayesian-ish update: more supporting sources increase confidence
            boost = source_quality * 0.1 * (1.0 - self.confidence)
            self.confidence = min(1.0, self.confidence + boost)
        else:
            # Contradictions decrease confidence
            penalty = source_quality * 0.15 * self.confidence
            self.confidence = max(0.0, self.confidence - penalty)

        # Update source quality average
        total = self.supporting_count + self.contradictory_count
        if total > 0:
            self.source_quality_score = (
                self.source_quality_score * (total - 1) + source_quality
            ) / total

    def needs_verification(self) -> bool:
        """Check if this claim needs re-verification."""
        if self.next_verification is None:
            return True
        return datetime.utcnow() >= self.next_verification

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.obj,
            "confidence": self.confidence,
            "supporting_count": self.supporting_count,
            "contradictory_count": self.contradictory_count,
            "is_disputed": self.is_disputed,
            "is_confirmed": self.is_confirmed,
            "is_stale": self.is_stale,
            "version": self.version,
            "first_observed": self.first_observed.isoformat(),
            "last_verified": self.last_verified.isoformat(),
        }


class ClaimValidator:
    """Validates and tracks knowledge claims with evidence."""

    def __init__(self):
        self.claims: dict[str, Claim] = {}
        self._subject_index: dict[str, list[str]] = {}  # subject -> [claim_ids]
        self.logger = structlog.get_logger()

    def add_claim(
        self,
        text: str,
        subject: str = "",
        predicate: str = "",
        obj: str = "",
        source_id: str = "",
        source_quality: float = 0.5,
    ) -> Claim:
        """Add or update a claim. If it already exists, add evidence."""
        # Check for duplicate claim
        for claim in self.claims.values():
            if (
                claim.subject.lower() == subject.lower()
                and claim.predicate.lower() == predicate.lower()
                and claim.obj.lower() == obj.lower()
            ):
                # Update existing claim
                if source_id:
                    claim.add_support(source_id, source_quality)
                return claim

        # Create new claim
        claim = Claim(
            text=text,
            subject=subject,
            predicate=predicate,
            obj=obj,
        )
        if source_id:
            claim.add_support(source_id, source_quality)

        self.claims[claim.id] = claim
        self._subject_index.setdefault(subject.lower(), []).append(claim.id)

        self.logger.info(
            "claim_added",
            claim_id=claim.id,
            subject=subject,
            confidence=claim.confidence,
        )
        return claim

    def find_claims(
        self,
        subject: str = "",
        predicate: str = "",
        min_confidence: float = 0.0,
        include_disputed: bool = True,
    ) -> list[Claim]:
        """Find claims matching criteria."""
        results = list(self.claims.values())
        if subject:
            results = [c for c in results if c.subject.lower() == subject.lower()]
        if predicate:
            results = [c for c in results if c.predicate.lower() == predicate.lower()]
        if min_confidence > 0:
            results = [c for c in results if c.confidence >= min_confidence]
        if not include_disputed:
            results = [c for c in results if not c.is_disputed]
        return results

    def get_disputed_claims(self) -> list[Claim]:
        """Get all claims with contradictions."""
        return [c for c in self.claims.values() if c.is_disputed]

    def get_stale_claims(self, max_age_hours: float = 168.0) -> list[Claim]:
        """Get claims that haven't been verified recently."""
        stale = []
        for claim in self.claims.values():
            if claim.needs_verification():
                stale.append(claim)
        return stale

    def get_confident_claims(self, min_confidence: float = 0.8) -> list[Claim]:
        """Get high-confidence, undisputed claims."""
        return [
            c for c in self.claims.values()
            if c.confidence >= min_confidence and not c.is_disputed
        ]

    def merge_claims(self, claim_id_a: str, claim_id_b: str) -> Claim | None:
        """Merge two claims about the same thing."""
        a = self.claims.get(claim_id_a)
        b = self.claims.get(claim_id_b)
        if not a or not b:
            return None

        # Merge evidence
        for sid in b.supporting_sources:
            if sid not in a.supporting_sources:
                a.add_support(sid, b.source_quality_score)
        for cid in b.contradictory_sources:
            if cid not in a.contradictory_sources:
                a.add_contradiction(cid, b.source_quality_score)

        # Remove b
        del self.claims[claim_id_b]
        self.logger.info("claims_merged", kept=claim_id_a, removed=claim_id_b)
        return a

    def compute_overall_confidence(self, subject: str) -> float:
        """Compute overall confidence for a subject from all its claims."""
        claims = self.find_claims(subject=subject)
        if not claims:
            return 0.0
        return sum(c.confidence for c in claims) / len(claims)

    def get_stats(self) -> dict[str, Any]:
        if not self.claims:
            return {"total_claims": 0}
        return {
            "total_claims": len(self.claims),
            "confirmed": sum(1 for c in self.claims.values() if c.is_confirmed),
            "disputed": sum(1 for c in self.claims.values() if c.is_disputed),
            "stale": sum(1 for c in self.claims.values() if c.is_stale),
            "avg_confidence": sum(
                c.confidence for c in self.claims.values()
            ) / len(self.claims),
        }
