"""Curiosity engine - drives exploration through intrinsic motivation.

Instead of relying only on user-defined goals, this engine
generates intrinsic motivation to explore unknown areas.
"""

import math
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog


@dataclass
class KnowledgeGap:
    """A detected gap in knowledge."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    topic: str = ""
    gap_type: str = ""  # missing, incomplete, contradictory, outdated
    description: str = ""
    curiosity_score: float = 0.5  # How curious we are about this
    priority: int = 5  # 1-10
    discovered_at: datetime = field(default_factory=datetime.utcnow)
    attempts: int = 0
    resolved: bool = False

    @property
    def should_explore(self) -> bool:
        return not self.resolved and self.curiosity_score > 0.3 and self.attempts < 5


@dataclass
class NoveltySignal:
    """Signal indicating something novel was encountered."""
    topic: str = ""
    novelty_score: float = 0.0  # 0-1, higher = more novel
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class CuriosityEngine:
    """Generates intrinsic motivation through information gain.

    Tracks knowledge gaps and novelty to drive exploration
    beyond user-defined goals.
    """

    def __init__(self):
        self.knowledge_gaps: dict[str, KnowledgeGap] = {}
        self.novelty_history: list[NoveltySignal] = []
        self.topic_coverage: dict[str, float] = defaultdict(float)
        self.total_exploration_reward = 0.0
        self.logger = structlog.get_logger()

    async def analyze_novelty(
        self,
        content: str,
        topic: str,
        context: dict[str, Any] | None = None,
    ) -> NoveltySignal:
        """Analyze how novel some content is."""
        # Calculate novelty based on coverage
        current_coverage = self.topic_coverage.get(topic, 0.0)

        # Novelty decreases as we learn more about a topic
        novelty = max(0.1, 1.0 - current_coverage)

        # Check for surprises (unexpected content)
        surprise_factor = self._detect_surprises(content, topic)
        novelty = (novelty + surprise_factor) / 2

        signal = NoveltySignal(
            topic=topic,
            novelty_score=novelty,
            context=context or {},
        )
        self.novelty_history.append(signal)

        # Update topic coverage (learning reduces novelty)
        self.topic_coverage[topic] = min(1.0, current_coverage + 0.1)

        return signal

    async def detect_gaps(
        self,
        knowledge_state: dict[str, Any],
    ) -> list[KnowledgeGap]:
        """Detect gaps in current knowledge."""
        new_gaps = []

        # Check for missing topics
        important_topics = [
            "physics", "mathematics", "computer_science", "biology",
            "chemistry", "philosophy", "economics", "history",
        ]
        for topic in important_topics:
            if topic not in knowledge_state:
                gap = KnowledgeGap(
                    topic=topic,
                    gap_type="missing",
                    description=f"No knowledge about {topic}",
                    curiosity_score=0.8,
                    priority=7,
                )
                new_gaps.append(gap)
                self.knowledge_gaps[gap.id] = gap

        # Check for shallow knowledge
        for topic, depth in knowledge_state.items():
            if isinstance(depth, (int, float)) and depth < 0.3:
                gap = KnowledgeGap(
                    topic=topic,
                    gap_type="incomplete",
                    description=f"Shallow knowledge about {topic} (depth: {depth:.2f})",
                    curiosity_score=0.6,
                    priority=5,
                )
                new_gaps.append(gap)
                self.knowledge_gaps[gap.id] = gap

        self.logger.info("gaps_detected", count=len(new_gaps))
        return new_gaps

    async def generate_exploration_goal(self) -> str | None:
        """Generate an intrinsic exploration goal."""
        # Find most curious unresolved gap
        candidates = [
            gap for gap in self.knowledge_gaps.values()
            if gap.should_explore
        ]

        if not candidates:
            return None

        # Sort by curiosity score * priority
        candidates.sort(
            key=lambda g: g.curiosity_score * g.priority,
            reverse=True,
        )

        best = candidates[0]
        best.attempts += 1

        goal = f"Explore {best.topic}: {best.description}"
        self.logger.info("exploration_goal_generated", goal=goal)
        return goal

    def record_exploration_result(
        self,
        gap_id: str,
        success: bool,
        information_gain: float = 0.0,
    ):
        """Record the result of an exploration attempt."""
        gap = self.knowledge_gaps.get(gap_id)
        if not gap:
            return

        if success:
            gap.curiosity_score *= 0.5  # Less curious after learning
            gap.resolved = information_gain > 0.7
            self.total_exploration_reward += information_gain
        else:
            gap.curiosity_score = min(1.0, gap.curiosity_score + 0.1)  # More curious on failure

    def get_interesting_topics(self, limit: int = 5) -> list[dict[str, Any]]:
        """Get the most interesting topics to explore."""
        topics = []
        for topic, coverage in sorted(
            self.topic_coverage.items(),
            key=lambda x: x[1],
        ):
            if coverage < 0.7:
                topics.append({
                    "topic": topic,
                    "coverage": coverage,
                    "novelty": 1.0 - coverage,
                })

        # Add gaps as topics
        for gap in self.knowledge_gaps.values():
            if gap.should_explore:
                topics.append({
                    "topic": gap.topic,
                    "coverage": 0.0,
                    "novelty": gap.curiosity_score,
                    "gap_type": gap.gap_type,
                })

        return sorted(topics, key=lambda t: t["novelty"], reverse=True)[:limit]

    def calculate_curiosity_reward(
        self,
        topic: str,
        information_novelty: float,
        information_usefulness: float,
    ) -> float:
        """Calculate curiosity-driven reward for an action."""
        # Curiosity reward = novelty * usefulness
        base_reward = information_novelty * information_usefulness

        # Bonus for exploring unknown areas
        coverage = self.topic_coverage.get(topic, 0.0)
        exploration_bonus = (1.0 - coverage) * 0.5

        # Bonus for filling knowledge gaps
        gap_bonus = 0.0
        for gap in self.knowledge_gaps.values():
            if gap.topic == topic and gap.should_explore:
                gap_bonus = 0.3
                break

        total = base_reward + exploration_bonus + gap_bonus
        self.total_exploration_reward += total
        return total

    def get_stats(self) -> dict[str, Any]:
        """Get curiosity engine statistics."""
        unresolved = sum(1 for g in self.knowledge_gaps.values() if not g.resolved)
        return {
            "total_gaps": len(self.knowledge_gaps),
            "unresolved_gaps": unresolved,
            "topics_covered": len(self.topic_coverage),
            "avg_coverage": (
                sum(self.topic_coverage.values()) / len(self.topic_coverage)
                if self.topic_coverage else 0
            ),
            "total_exploration_reward": self.total_exploration_reward,
        }

    def to_context(self) -> str:
        """Convert curiosity state to context string."""
        stats = self.get_stats()
        interesting = self.get_interesting_topics(3)

        lines = [
            "Curiosity Engine:",
            f"  Knowledge Gaps: {stats['unresolved_gaps']}",
            f"  Topics Covered: {stats['topics_covered']}",
        ]
        if interesting:
            lines.append("  Interesting Topics:")
            for t in interesting:
                lines.append(f"    - {t['topic']} (novelty: {t['novelty']:.2f})")
        return "\n".join(lines)

    def _detect_surprises(self, content: str, topic: str) -> float:
        """Detect surprising content (high novelty words/concepts)."""
        # Simple heuristic: unusual words = surprise
        words = set(content.lower().split())
        known_words = set()
        for t in self.topic_coverage:
            known_words.update(t.lower().split())

        if not words:
            return 0.0

        novelty_ratio = len(words - known_words) / len(words)
        return min(1.0, novelty_ratio * 2)
