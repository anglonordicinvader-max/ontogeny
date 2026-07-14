"""Meta-learning module - learns how to learn better.

Tracks learning strategies and their effectiveness to
optimize future learning sessions.
"""

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog


@dataclass
class LearningStrategy:
    """A strategy for learning."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    success_rate: float = 0.5
    total_attempts: int = 0
    successes: int = 0
    avg_quality: float = 0.5
    avg_speed: float = 0.5
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used: datetime = field(default_factory=datetime.utcnow)

    def record_attempt(self, success: bool, quality: float, speed: float):
        """Record an attempt with this strategy."""
        self.total_attempts += 1
        self.last_used = datetime.utcnow()
        if success:
            self.successes += 1
        self.success_rate = self.successes / self.total_attempts
        self.avg_quality = (self.avg_quality * (self.total_attempts - 1) + quality) / self.total_attempts
        self.avg_speed = (self.avg_speed * (self.total_attempts - 1) + speed) / self.total_attempts


@dataclass
class LearningSession:
    """A record of a learning session."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    topic: str = ""
    strategy_id: str = ""
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: datetime | None = None
    items_learned: int = 0
    quality_score: float = 0.0
    duration_seconds: float = 0.0
    insights: list[str] = field(default_factory=list)


class MetaLearner:
    """Learns how to learn better by tracking strategies.

    Analyzes what learning strategies work best for different
    types of content and optimizes future learning.
    """

    def __init__(self):
        self.strategies: dict[str, LearningStrategy] = {}
        self.sessions: list[LearningSession] = []
        self.strategy_performance: dict[str, list[float]] = defaultdict(list)
        self.logger = structlog.get_logger()

        self._init_default_strategies()

    def _init_default_strategies(self):
        """Initialize default learning strategies."""
        defaults = [
            LearningStrategy(
                name="focused_deep",
                description="Deep dive on single topic",
                parameters={"depth": "deep", "sources": 3, "mode": "focused"},
            ),
            LearningStrategy(
                name="broad_exploration",
                description="Wide coverage of many topics",
                parameters={"depth": "shallow", "sources": 10, "mode": "exploratory"},
            ),
            LearningStrategy(
                name="sequential_learning",
                description="Learn topics in logical order",
                parameters={"depth": "moderate", "sources": 5, "mode": "sequential"},
            ),
            LearningStrategy(
                name="contrastive_learning",
                description="Compare and contrast related topics",
                parameters={"depth": "moderate", "sources": 4, "mode": "contrastive"},
            ),
            LearningStrategy(
                name="problem_focused",
                description="Learn by solving specific problems",
                parameters={"depth": "deep", "sources": 3, "mode": "problem"},
            ),
        ]
        for strategy in defaults:
            self.strategies[strategy.id] = strategy

    async def select_strategy(
        self,
        topic: str,
        available_time: float = 300.0,
        goal: str = "understand",
    ) -> LearningStrategy:
        """Select the best learning strategy for a situation."""
        # Score each strategy
        scored = []
        for strategy in self.strategies.values():
            score = self._score_strategy(strategy, topic, available_time, goal)
            scored.append((strategy, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        # Epsilon-greedy: sometimes try suboptimal strategies
        import random
        if random.random() < 0.2 and len(scored) > 1:
            return scored[1][0]

        return scored[0][0]

    async def record_session(
        self,
        topic: str,
        strategy_id: str,
        items_learned: int,
        quality: float,
        duration: float,
        insights: list[str] | None = None,
    ):
        """Record a learning session for meta-analysis."""
        session = LearningSession(
            topic=topic,
            strategy_id=strategy_id,
            items_learned=items_learned,
            quality_score=quality,
            duration_seconds=duration,
            insights=insights or [],
        )
        self.sessions.append(session)

        # Update strategy performance
        strategy = self.strategies.get(strategy_id)
        if strategy:
            success = quality > 0.6 and items_learned > 0
            speed = items_learned / max(1, duration) * 60  # items per minute
            strategy.record_attempt(success, quality, speed)

            self.strategy_performance[strategy.name].append(quality)

        self.logger.info(
            "learning_session_recorded",
            topic=topic,
            strategy=strategy.name if strategy else "unknown",
            quality=quality,
        )

    async def analyze_effectiveness(self) -> dict[str, Any]:
        """Analyze which strategies are most effective."""
        analysis = {}
        for strategy in self.strategies.values():
            if strategy.total_attempts > 0:
                analysis[strategy.name] = {
                    "success_rate": strategy.success_rate,
                    "avg_quality": strategy.avg_quality,
                    "avg_speed": strategy.avg_speed,
                    "total_attempts": strategy.total_attempts,
                }

        return {
            "strategies": analysis,
            "total_sessions": len(self.sessions),
            "best_strategy": max(
                analysis.items(),
                key=lambda x: x[1]["avg_quality"],
                default=(None, None),
            )[0] if analysis else None,
        }

    async def suggest_improvements(self) -> list[str]:
        """Suggest improvements to learning approach."""
        suggestions = []
        analysis = await self.analyze_effectiveness()

        for name, stats in analysis.get("strategies", {}).items():
            if stats["success_rate"] < 0.5:
                suggestions.append(f"Strategy '{name}' has low success rate ({stats['success_rate']:.0%}), consider alternatives")
            if stats["avg_quality"] < 0.4:
                suggestions.append(f"Strategy '{name}' produces low quality results ({stats['avg_quality']:.2f})")
            if stats["avg_speed"] < 0.1:
                suggestions.append(f"Strategy '{name}' is slow ({stats['avg_speed']:.2f} items/min)")

        if not suggestions:
            suggestions.append("All strategies performing adequately")

        return suggestions

    def get_strategy(self, name: str) -> LearningStrategy | None:
        """Get strategy by name."""
        for strategy in self.strategies.values():
            if strategy.name == name:
                return strategy
        return None

    def get_stats(self) -> dict[str, Any]:
        """Get meta-learning statistics."""
        return {
            "total_strategies": len(self.strategies),
            "total_sessions": len(self.sessions),
            "strategies_used": len(self.strategy_performance),
        }

    def to_context(self) -> str:
        """Convert meta-learning state to context string."""
        analysis = self._sync_analyze()
        lines = ["Meta-Learning:"]
        lines.append(f"  Strategies: {len(self.strategies)}")
        lines.append(f"  Sessions: {len(self.sessions)}")
        if analysis.get("best_strategy"):
            lines.append(f"  Best Strategy: {analysis['best_strategy']}")
        return "\n".join(lines)

    def _score_strategy(
        self,
        strategy: LearningStrategy,
        topic: str,
        available_time: float,
        goal: str,
    ) -> float:
        """Score a strategy for a given situation."""
        score = 0.5

        # Past performance
        score += strategy.success_rate * 0.3
        score += strategy.avg_quality * 0.2

        # Time fit
        estimated_time = strategy.parameters.get("sources", 5) * 60
        if estimated_time <= available_time:
            score += 0.2

        # Goal match
        if goal == "understand" and strategy.parameters.get("depth") == "deep":
            score += 0.2
        elif goal == "explore" and strategy.parameters.get("mode") == "exploratory":
            score += 0.2

        return score

    def _sync_analyze(self) -> dict[str, Any]:
        """Synchronous version of analyze for context generation."""
        analysis = {}
        for strategy in self.strategies.values():
            if strategy.total_attempts > 0:
                analysis[strategy.name] = {
                    "success_rate": strategy.success_rate,
                    "avg_quality": strategy.avg_quality,
                }
        return {
            "strategies": analysis,
            "best_strategy": max(
                analysis.items(),
                key=lambda x: x[1]["avg_quality"],
                default=(None, None),
            )[0] if analysis else None,
        }
