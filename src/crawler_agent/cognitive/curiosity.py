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

    # === Intrinsic Motivation: Goal Generation from Capability Gaps ===

    async def generate_intrinsic_goals(
        self,
        current_capabilities: dict[str, float],
        self_model_weaknesses: list[str] | None = None,
        world_model_knowledge: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Generate intrinsic motivation goals from multiple sources.

        Sources of motivation:
        1. Capability gaps - things we can't do well
        2. Knowledge gaps - things we don't know
        3. Novelty seeking - unexplored territories
        4. Boredom detection - need for new challenges
        5. Competence drive - desire to improve
        """
        goals = []

        # 1. Capability gap goals
        for cap, score in current_capabilities.items():
            if score < 0.6:
                goals.append({
                    "type": "capability_gap",
                    "goal": f"Improve competency in {cap}",
                    "description": f"Current proficiency: {score:.0%}. Target: >80%",
                    "motivation": "competence_drive",
                    "urgency": 1.0 - score,
                    "expected_difficulty": 0.5,
                    "learning_potential": 0.8,
                })

        # 2. Knowledge gap goals
        for gap in self.knowledge_gaps.values():
            if gap.should_explore:
                goals.append({
                    "type": "knowledge_gap",
                    "goal": f"Learn about {gap.topic}: {gap.description}",
                    "motivation": "curiosity",
                    "urgency": gap.curiosity_score,
                    "expected_difficulty": gap.priority / 10,
                    "learning_potential": gap.curiosity_score,
                })

        # 3. Novelty seeking goals
        underexplored = [
            (topic, coverage) for topic, coverage in self.topic_coverage.items()
            if coverage < 0.3
        ]
        for topic, coverage in underexplored[:3]:
            goals.append({
                "type": "novelty_seeking",
                "goal": f"Explore underexplored topic: {topic}",
                "description": f"Current coverage: {coverage:.0%}",
                "motivation": "novelty_seeking",
                "urgency": 0.3,
                "expected_difficulty": 0.4,
                "learning_potential": 0.6,
            })

        # 4. Boredom detection
        if self._detect_boredom():
            goals.append({
                "type": "boredom_relief",
                "goal": "Seek novel or challenging tasks",
                "description": "Boredom detected - repeated similar activities",
                "motivation": "boredom_relief",
                "urgency": 0.7,
                "expected_difficulty": 0.3,
                "learning_potential": 0.9,
            })

        # Sort by combined score
        for g in goals:
            g["priority_score"] = g["urgency"] * 0.4 + g["learning_potential"] * 0.6

        goals.sort(key=lambda g: g["priority_score"], reverse=True)

        self.logger.info("intrinsic_goals_generated", count=len(goals))
        return goals

    async def assess_competence_gaps(
        self,
        task_performance: dict[str, list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        """Analyze task performance to identify competence gaps.

        Args:
            task_performance: {task_type: [{success, duration, resources_used}]}
        """
        gaps = []

        for task_type, attempts in task_performance.items():
            if not attempts:
                continue

            successes = sum(1 for a in attempts if a.get("success"))
            success_rate = successes / len(attempts)

            if success_rate < 0.7:
                # Analyze failure patterns
                failures = [a for a in attempts if not a.get("success")]
                failure_reasons = [a.get("failure_reason", "unknown") for a in failures]

                gaps.append({
                    "task_type": task_type,
                    "success_rate": success_rate,
                    "total_attempts": len(attempts),
                    "failure_patterns": failure_reasons,
                    "improvement_priority": (1 - success_rate) * len(attempts),
                    "recommended_action": self._recommend_improvement(failure_reasons),
                })

        gaps.sort(key=lambda g: g["improvement_priority"], reverse=True)
        return gaps

    async def generate_learning_objectives(
        self,
        competence_gaps: list[dict[str, Any]],
        available_resources: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Turn competence gaps into concrete learning objectives."""
        objectives = []

        for gap in competence_gaps[:5]:
            objective = {
                "task_type": gap["task_type"],
                "current_success_rate": gap["success_rate"],
                "target_success_rate": min(1.0, gap["success_rate"] + 0.3),
                "learning_activities": [],
            }

            if gap["success_rate"] < 0.3:
                objective["learning_activities"] = [
                    "Study successful approaches for this task type",
                    "Practice with guided examples",
                    "Identify and address root causes of failure",
                ]
            elif gap["success_rate"] < 0.5:
                objective["learning_activities"] = [
                    "Review and learn from past failures",
                    "Experiment with alternative strategies",
                    "Seek feedback on approach quality",
                ]
            else:
                objective["learning_activities"] = [
                    "Fine-tune approach parameters",
                    "Practice edge cases",
                    "Optimize for speed and efficiency",
                ]

            objectives.append(objective)

        return objectives

    async def evaluate_drive_state(self) -> dict[str, Any]:
        """Evaluate the agent's current motivational state.

        Returns:
            Overall drive state with urgency scores for different motivations.
        """
        competence_drive = self._calculate_competence_urgency()
        curiosity_drive = self._calculate_curiosity_urgency()
        novelty_drive = self._calculate_novelty_urgency()

        drives = {
            "competence": competence_drive,
            "curiosity": curiosity_drive,
            "novelty": novelty_drive,
        }

        # Determine dominant drive
        dominant = max(drives, key=drives.get)

        # Check for motivational conflicts
        conflicts = []
        if competence_drive > 0.7 and curiosity_drive > 0.7:
            conflicts.append("high_competence_and_curiosity")

        return {
            "drives": drives,
            "dominant_drive": dominant,
            "overall_motivation": sum(drives.values()) / 3,
            "boredom_level": self._calculate_boredom_level(),
            "frustration_level": self._calculate_frustration_level(),
            "conflicts": conflicts,
            "recommended_focus": self._recommend_drive_focus(drives),
        }

    def _detect_boredom(self) -> bool:
        """Detect if agent is experiencing boredom (too much repetition)."""
        if len(self.novelty_history) < 5:
            return False

        recent_novelty = [
            s.novelty_score for s in self.novelty_history[-10:]
        ]
        avg_novelty = sum(recent_novelty) / len(recent_novelty)
        return avg_novelty < 0.2

    def _calculate_boredom_level(self) -> float:
        """Calculate current boredom level."""
        if len(self.novelty_history) < 3:
            return 0.3

        recent = self.novelty_history[-10:]
        avg = sum(s.novelty_score for s in recent) / len(recent)
        return max(0.0, 1.0 - avg * 2)

    def _calculate_frustration_level(self) -> float:
        """Calculate frustration level from unresolved gaps."""
        unresolved = [g for g in self.knowledge_gaps.values() if g.should_explore]
        if not unresolved:
            return 0.0

        high_attempts = [g for g in unresolved if g.attempts >= 3]
        return min(1.0, len(high_attempts) / max(1, len(unresolved)))

    def _calculate_competence_urgency(self) -> float:
        return 1.0 - (sum(self.topic_coverage.values()) / max(1, len(self.topic_coverage)))

    def _calculate_curiosity_urgency(self) -> float:
        unresolved = sum(1 for g in self.knowledge_gaps.values() if g.should_explore)
        return min(1.0, unresolved / 10)

    def _calculate_novelty_urgency(self) -> float:
        return self._calculate_boredom_level()

    def _recommend_improvement(self, failure_reasons: list[str]) -> str:
        if not failure_reasons:
            return "Gather more data on task failures"
        most_common = max(set(failure_reasons), key=failure_reasons.count)
        return f"Address primary failure cause: {most_common}"

    def _recommend_drive_focus(self, drives: dict[str, float]) -> str:
        dominant = max(drives, key=drives.get)
        if drives[dominant] < 0.3:
            return "No strong drive - general exploration recommended"
        return f"Focus on {dominant} drive (score: {drives[dominant]:.2f})"
