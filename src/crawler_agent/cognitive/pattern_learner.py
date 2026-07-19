"""Pattern learner - extracts and applies patterns from experience.

This module learns actual patterns from crawl results and experiences,
rather than just storing text. It builds a pattern library that can
be used for predictions and decision-making.
"""

import json
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog


@dataclass
class Pattern:
    """A learned pattern."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pattern_type: str = ""  # frequency, sequence, association, causal
    description: str = ""
    conditions: dict[str, Any] = field(default_factory=dict)
    outcomes: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    support: int = 1  # How many times observed
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    tags: list[str] = field(default_factory=list)

    def update_confidence(self, was_correct: bool):
        """Update confidence based on prediction outcome."""
        if was_correct:
            self.confidence = min(1.0, self.confidence + 0.1)
        else:
            self.confidence = max(0.0, self.confidence - 0.05)
        self.support += 1
        self.last_updated = datetime.utcnow()


class PatternLearner:
    """Learns patterns from experience and crawl results.

    Extracts:
    - Frequency patterns (what appears together)
    - Sequence patterns (what follows what)
    - Association patterns (A implies B)
    - Causal patterns (A causes B)
    """

    def __init__(self):
        self.patterns: dict[str, Pattern] = {}
        self.frequency_counts: dict[str, defaultdict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        self.sequence_counts: dict[str, defaultdict[tuple, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        self.association_counts: dict[str, defaultdict[tuple, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        self.logger = structlog.get_logger()

    async def learn_from_experience(
        self,
        experience: dict[str, Any],
    ) -> list[Pattern]:
        """Extract patterns from a single experience."""
        new_patterns = []

        # Extract frequency patterns
        freq_patterns = self._extract_frequency_patterns(experience)
        new_patterns.extend(freq_patterns)

        # Extract sequence patterns
        seq_patterns = self._extract_sequence_patterns(experience)
        new_patterns.extend(seq_patterns)

        # Extract association patterns
        assoc_patterns = self._extract_association_patterns(experience)
        new_patterns.extend(assoc_patterns)

        # Store and deduplicate
        for pattern in new_patterns:
            existing = self._find_similar(pattern)
            if existing:
                existing.update_confidence(True)
            else:
                self.patterns[pattern.id] = pattern

        self.logger.info(
            "patterns_extracted",
            count=len(new_patterns),
            total=len(self.patterns),
        )
        return new_patterns

    async def learn_from_batch(
        self,
        experiences: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Learn from a batch of experiences."""
        all_patterns = []
        for exp in experiences:
            patterns = await self.learn_from_experience(exp)
            all_patterns.extend(patterns)

        # Find strong patterns (high confidence + high support)
        strong = [p for p in self.patterns.values() if p.confidence > 0.7 and p.support > 3]

        return {
            "total_experiences": len(experiences),
            "new_patterns": len(all_patterns),
            "total_patterns": len(self.patterns),
            "strong_patterns": len(strong),
            "top_patterns": [
                {"type": p.pattern_type, "desc": p.description, "conf": p.confidence}
                for p in sorted(strong, key=lambda x: x.confidence, reverse=True)[:5]
            ],
        }

    def predict(
        self,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Make a prediction based on learned patterns."""
        predictions = []
        for pattern in self.patterns.values():
            if self._matches_conditions(pattern, context):
                predictions.append(
                    {
                        "pattern_id": pattern.id,
                        "type": pattern.pattern_type,
                        "description": pattern.description,
                        "outcomes": pattern.outcomes,
                        "confidence": pattern.confidence,
                    }
                )

        # Sort by confidence
        predictions.sort(key=lambda x: x["confidence"], reverse=True)

        return {
            "predictions": predictions[:5],
            "best": predictions[0] if predictions else None,
            "pattern_count": len(self.patterns),
        }

    def get_patterns_by_type(self, pattern_type: str) -> list[Pattern]:
        """Get all patterns of a specific type."""
        return [p for p in self.patterns.values() if p.pattern_type == pattern_type]

    def get_strong_patterns(self, min_confidence: float = 0.7) -> list[Pattern]:
        """Get high-confidence patterns."""
        return [p for p in self.patterns.values() if p.confidence >= min_confidence]

    def decay_patterns(self, decay_rate: float = 0.01):
        """Apply decay to old patterns (forgetting)."""
        to_remove = []
        for pid, pattern in self.patterns.items():
            pattern.confidence *= 1 - decay_rate
            if pattern.confidence < 0.1:
                to_remove.append(pid)

        for pid in to_remove:
            del self.patterns[pid]

    def _extract_frequency_patterns(self, experience: dict[str, Any]) -> list[Pattern]:
        """Extract co-occurrence frequency patterns."""
        patterns = []
        keys = list(experience.keys())

        for i, key1 in enumerate(keys):
            for key2 in keys[i + 1 :]:
                pair = (key1, key2)
                self.frequency_counts[experience.get("type", "general")][str(pair)] += 1

                count = self.frequency_counts[experience.get("type", "general")][str(pair)]
                if count >= 3:
                    patterns.append(
                        Pattern(
                            pattern_type="frequency",
                            description=f"{key1} co-occurs with {key2}",
                            conditions={"has_key": key1},
                            outcomes={"likely_has_key": key2},
                            confidence=min(0.9, count / 10),
                            support=count,
                        )
                    )

        return patterns

    def _extract_sequence_patterns(self, experience: dict[str, Any]) -> list[Pattern]:
        """Extract sequential patterns (what follows what)."""
        patterns = []
        events = experience.get("events", [])

        for i in range(len(events) - 1):
            current = events[i]
            next_event = events[i + 1]
            pair = (str(current), str(next_event))

            self.sequence_counts["events"][pair] += 1
            count = self.sequence_counts["events"][pair]

            if count >= 2:
                patterns.append(
                    Pattern(
                        pattern_type="sequence",
                        description=f"'{current}' is often followed by '{next_event}'",
                        conditions={"after": current},
                        outcomes={"expect": next_event},
                        confidence=min(0.85, count / 8),
                        support=count,
                    )
                )

        return patterns

    def _extract_association_patterns(self, experience: dict[str, Any]) -> list[Pattern]:
        """Extract association patterns (A implies B)."""
        patterns = []
        features = {k: str(v) for k, v in experience.items() if k != "events"}

        for key, value in features.items():
            for other_key, other_value in features.items():
                if key != other_key:
                    pair = (f"{key}={value}", f"{other_key}={other_value}")
                    self.association_counts["associations"][pair] += 1

                    count = self.association_counts["associations"][pair]
                    if count >= 3:
                        patterns.append(
                            Pattern(
                                pattern_type="association",
                                description=f"When {key}={value}, then {other_key}={other_value}",
                                conditions={key: value},
                                outcomes={other_key: other_value},
                                confidence=min(0.8, count / 10),
                                support=count,
                            )
                        )

        return patterns

    def _find_similar(self, pattern: Pattern) -> Pattern | None:
        """Find an existing similar pattern."""
        for existing in self.patterns.values():
            if (
                existing.pattern_type == pattern.pattern_type
                and existing.description == pattern.description
            ):
                return existing
        return None

    def _matches_conditions(self, pattern: Pattern, context: dict[str, Any]) -> bool:
        """Check if context matches pattern conditions."""
        for key, value in pattern.conditions.items():
            if key == "has_key" and value not in context:
                return False
            elif key == "after":
                events = context.get("events", [])
                if value not in [str(e) for e in events]:
                    return False
            elif context.get(key) != value:
                return False
        return True

    def to_context(self) -> str:
        """Convert patterns to context string for LLM."""
        strong = self.get_strong_patterns(0.6)
        if not strong:
            return "No strong patterns learned yet."

        lines = ["Learned Patterns:"]
        for p in strong[:10]:
            lines.append(f"  [{p.pattern_type}] {p.description} (conf: {p.confidence:.2f})")
        return "\n".join(lines)

    def get_stats(self) -> dict[str, Any]:
        """Return stats about learned patterns."""
        strong = self.get_strong_patterns(0.6)
        return {
            "total_patterns": len(self.patterns),
            "strong_patterns": len(strong),
            "frequency_groups": len(self.frequency_counts),
            "sequence_groups": len(self.sequence_counts),
            "association_groups": len(self.association_counts),
        }
