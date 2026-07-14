"""Attention mechanism - controls what the agent focuses on.

Implements selective attention to prioritize important information
and ignore noise, similar to human attention.
"""

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog


@dataclass
class AttentionFocus:
    """Current attention focus."""
    topic: str = ""
    focus_level: float = 0.5  # 0-1, how focused
    started_at: datetime = field(default_factory=datetime.utcnow)
    duration: float = 0.0  # How long we've focused
    distractions: int = 0  # Number of distractions ignored

    @property
    def is_focused(self) -> bool:
        return self.focus_level > 0.5 and self.distractions < 3


@dataclass
class AttentionTarget:
    """Something that could attract attention."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    relevance: float = 0.5  # How relevant to current goals
    novelty: float = 0.5  # How novel/surprising
    urgency: float = 0.5  # How time-sensitive
    emotional_charge: float = 0.0  # Emotional valence

    @property
    def attention_score(self) -> float:
        """Calculate overall attention score."""
        return (
            self.relevance * 0.4 +
            self.novelty * 0.3 +
            self.urgency * 0.2 +
            abs(self.emotional_charge) * 0.1
        )


class AttentionMechanism:
    """Selective attention system.

    Controls what the agent focuses on by:
    - Evaluating relevance of incoming information
    - Detecting novelty and surprise
    - Managing attention switching
    - Filtering noise
    """

    def __init__(self):
        self.current_focus: AttentionFocus | None = None
        self.attention_history: list[AttentionFocus] = []
        self.suppressed_items: list[str] = []
        self.focus_duration: dict[str, float] = defaultdict(float)
        self.switch_count = 0
        self.total_suppressed = 0
        self.logger = structlog.get_logger()

    async def evaluate_attention(
        self,
        content: str,
        context: dict[str, Any] | None = None,
    ) -> AttentionTarget:
        """Evaluate whether something deserves attention."""
        context = context or {}

        # Calculate relevance
        relevance = self._calculate_relevance(content, context)

        # Calculate novelty
        novelty = self._calculate_novelty(content)

        # Calculate urgency
        urgency = context.get("urgency", 0.5)

        # Calculate emotional charge
        emotional = self._calculate_emotional_charge(content)

        target = AttentionTarget(
            content=content,
            relevance=relevance,
            novelty=novelty,
            urgency=urgency,
            emotional_charge=emotional,
        )

        return target

    async def decide_focus(
        self,
        targets: list[AttentionTarget],
    ) -> AttentionTarget | None:
        """Decide what to focus on from multiple targets."""
        if not targets:
            return None

        # Score each target
        scored = [(t, t.attention_score) for t in targets]
        scored.sort(key=lambda x: x[1], reverse=True)

        best = scored[0][0]

        # Check if we should switch focus
        if self.current_focus:
            if best.attention_score > self.current_focus.focus_level * 1.5:
                await self._switch_focus(best.content)
            else:
                self.current_focus.distractions += 1
                self.total_suppressed += 1
                return None
        else:
            await self._switch_focus(best.content)

        return best

    async def maintain_focus(self, seconds: float = 1.0):
        """Maintain current focus for a duration."""
        if self.current_focus:
            self.current_focus.duration += seconds
            self.focus_duration[self.current_focus.topic] += seconds

            # Focus naturally decays over time
            self.current_focus.focus_level *= 0.99

    async def _switch_focus(self, topic: str):
        """Switch attention to a new topic."""
        if self.current_focus:
            self.attention_history.append(self.current_focus)

        self.current_focus = AttentionFocus(
            topic=topic,
            focus_level=0.8,
        )
        self.switch_count += 1

        self.logger.debug("attention_switch", topic=topic)

    def _calculate_relevance(self, content: str, context: dict[str, Any]) -> float:
        """Calculate how relevant content is to current goals."""
        relevance = 0.5

        # Check against current goals
        goals = context.get("goals", [])
        for goal in goals:
            if isinstance(goal, str) and any(word in content.lower() for word in goal.lower().split()):
                relevance += 0.2
            elif isinstance(goal, dict) and any(word in content.lower() for word in str(goal).lower().split()):
                relevance += 0.2

        # Check against current focus
        if self.current_focus and self.current_focus.topic in content.lower():
            relevance += 0.3

        return min(1.0, relevance)

    def _calculate_novelty(self, content: str) -> float:
        """Calculate how novel content is."""
        # Simple heuristic: check against suppressed items
        if content in self.suppressed_items:
            return 0.1

        # Check length and complexity as novelty proxy
        words = content.split()
        if len(words) > 50:
            return 0.7  # Complex content is often novel
        elif len(words) < 5:
            return 0.3  # Very short is less novel

        return 0.5

    def _calculate_emotional_charge(self, content: str) -> float:
        """Calculate emotional charge of content."""
        positive_words = {"success", "breakthrough", "discovery", "innovation", "excellent", "amazing"}
        negative_words = {"failure", "error", "problem", "issue", "critical", "warning"}

        words = set(content.lower().split())
        pos = len(words & positive_words)
        neg = len(words & negative_words)

        if pos > neg:
            return min(1.0, pos * 0.2)
        elif neg > pos:
            return max(-1.0, -neg * 0.2)
        return 0.0

    def get_focus_stats(self) -> dict[str, Any]:
        """Get attention statistics."""
        total_time = sum(self.focus_duration.values())
        return {
            "current_focus": self.current_focus.topic if self.current_focus else None,
            "total_switches": self.switch_count,
            "total_suppressed": self.total_suppressed,
            "focus_distribution": {
                topic: time / max(1, total_time)
                for topic, time in self.focus_duration.items()
            } if self.focus_duration else {},
        }

    def to_context(self) -> str:
        """Convert attention state to context string."""
        stats = self.get_focus_stats()
        lines = ["Attention Mechanism:"]
        lines.append(f"  Current Focus: {stats['current_focus'] or 'None'}")
        lines.append(f"  Total Switches: {stats['total_switches']}")
        lines.append(f"  Items Suppressed: {stats['total_suppressed']}")
        if stats['focus_distribution']:
            lines.append("  Focus Distribution:")
            for topic, pct in sorted(stats['focus_distribution'].items(), key=lambda x: x[1], reverse=True)[:3]:
                lines.append(f"    - {topic}: {pct:.0%}")
        return "\n".join(lines)
