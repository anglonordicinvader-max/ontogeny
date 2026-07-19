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
            self.relevance * 0.4
            + self.novelty * 0.3
            + self.urgency * 0.2
            + abs(self.emotional_charge) * 0.1
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
            if isinstance(goal, str) and any(
                word in content.lower() for word in goal.lower().split()
            ):
                relevance += 0.2
            elif isinstance(goal, dict) and any(
                word in content.lower() for word in str(goal).lower().split()
            ):
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
        positive_words = {
            "success",
            "breakthrough",
            "discovery",
            "innovation",
            "excellent",
            "amazing",
        }
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
                topic: time / max(1, total_time) for topic, time in self.focus_duration.items()
            }
            if self.focus_duration
            else {},
        }

    def to_context(self) -> str:
        """Convert attention state to context string."""
        stats = self.get_focus_stats()
        lines = ["Attention Mechanism:"]
        lines.append(f"  Current Focus: {stats['current_focus'] or 'None'}")
        lines.append(f"  Total Switches: {stats['total_switches']}")
        lines.append(f"  Items Suppressed: {stats['total_suppressed']}")
        if stats["focus_distribution"]:
            lines.append("  Focus Distribution:")
            for topic, pct in sorted(
                stats["focus_distribution"].items(), key=lambda x: x[1], reverse=True
            )[:3]:
                lines.append(f"    - {topic}: {pct:.0%}")
        return "\n".join(lines)

    # === Compute Allocation Based on Relevance × Uncertainty ===

    @dataclass
    class ComputeBudget:
        """Computational resource budget for a task."""

        total_compute: float = 1.0  # Normalized total compute
        allocated: dict[str, float] = field(default_factory=dict)
        remaining: float = 1.0

        def allocate(self, component: str, amount: float) -> bool:
            """Allocate compute to a component. Returns False if insufficient."""
            if amount > self.remaining:
                return False
            self.allocated[component] = self.allocated.get(component, 0) + amount
            self.remaining -= amount
            return True

    @dataclass
    class ComputePriority:
        """Priority for compute allocation."""

        component: str = ""
        relevance: float = 0.5
        uncertainty: float = 0.5
        urgency: float = 0.5
        fatigue_cost: float = 0.0

        @property
        def priority_score(self) -> float:
            """Priority = relevance × uncertainty × urgency - fatigue."""
            return (
                self.relevance * 0.3
                + self.uncertainty * 0.3
                + self.urgency * 0.2
                + (1 - self.fatigue_cost) * 0.2
            )

    async def allocate_compute(
        self,
        available_components: list[str],
        task_context: dict[str, Any] | None = None,
        uncertainty_data: dict[str, float] | None = None,
        total_budget: float = 1.0,
    ) -> dict[str, float]:
        """Allocate compute resources across components.

        Uses relevance × uncertainty × urgency as the allocation formula.
        Higher uncertainty + higher relevance = more compute allocated.

        Args:
            available_components: Components that need compute
            task_context: Current task context for relevance scoring
            uncertainty_data: {component: uncertainty_level}
            total_budget: Total compute budget (normalized)

        Returns:
            {component: allocated_compute}
        """
        task_context = task_context or {}
        uncertainty_data = uncertainty_data or {}

        budget = self.ComputeBudget(total_compute=total_budget)

        # Score each component
        priorities = []
        for component in available_components:
            relevance = self._score_component_relevance(component, task_context)
            uncertainty = uncertainty_data.get(component, 0.5)
            urgency = task_context.get("urgency", 0.5)
            fatigue = self._calculate_fatigue(component)

            priority = self.ComputePriority(
                component=component,
                relevance=relevance,
                uncertainty=uncertainty,
                urgency=urgency,
                fatigue_cost=fatigue,
            )
            priorities.append(priority)

        # Sort by priority score
        priorities.sort(key=lambda p: p.priority_score, reverse=True)

        # Allocate compute proportionally
        total_score = sum(p.priority_score for p in priorities) or 1.0

        allocations = {}
        for priority in priorities:
            proportion = priority.priority_score / total_score
            allocation = proportion * total_budget
            if budget.allocate(priority.component, allocation):
                allocations[priority.component] = allocation

        self.logger.info(
            "compute_allocated",
            components=len(allocations),
            total_used=sum(allocations.values()),
        )

        return allocations

    def _score_component_relevance(self, component: str, context: dict[str, Any]) -> float:
        """Score how relevant a component is to the current context."""
        relevance_keywords = {
            "attention": ["focus", "prioritize", "filter", "select"],
            "working_memory": ["remember", "recall", "hold", "process"],
            "reasoning": ["think", "deduce", "infer", "analyze", "plan"],
            "perception": ["see", "observe", "detect", "sense", "image"],
            "emotion": ["feel", "mood", "valence", "arousal", "motivation"],
            "self_model": ["reflect", "self", "capability", "strength", "weakness"],
            "causal_reasoning": ["cause", "effect", "why", "intervention", "counterfactual"],
        }

        keywords = relevance_keywords.get(component, [])
        context_str = str(context).lower()

        matches = sum(1 for kw in keywords if kw in context_str)
        base_relevance = 0.3

        if matches > 0:
            base_relevance = min(1.0, 0.3 + matches * 0.2)

        # Boost if component was recently relevant
        if self.current_focus and component in self.current_focus.topic:
            base_relevance = min(1.0, base_relevance + 0.3)

        return base_relevance

    def _calculate_fatigue(self, component: str) -> float:
        """Calculate fatigue for a component (high usage = high fatigue)."""
        total_time = sum(self.focus_duration.values()) or 1.0
        component_time = self.focus_duration.get(component, 0)

        # Fatigue increases with usage proportion
        usage_ratio = component_time / total_time
        fatigue = min(1.0, usage_ratio * 2)

        return fatigue

    async def adaptive_attention(
        self,
        stimulus: str,
        uncertainty: float = 0.5,
        task_relevance: float = 0.5,
        compute_budget: float = 1.0,
    ) -> dict[str, Any]:
        """Adapt attention allocation based on stimulus properties.

        Combines:
        - Relevance scoring
        - Uncertainty-based exploration
        - Fatigue management
        - Compute budget constraints

        Returns:
            Attention decision with allocation details
        """
        # Evaluate the stimulus
        target = await self.evaluate_attention(stimulus)

        # Calculate exploration vs exploitation
        if uncertainty > 0.6:
            # High uncertainty: allocate more compute to explore
            exploration_allocation = 0.4
            exploitation_allocation = 0.3
        else:
            # Low uncertainty: exploit current knowledge
            exploration_allocation = 0.2
            exploitation_allocation = 0.5

        # Calculate fatigue-adjusted attention level
        fatigue = self._calculate_fatigue(stimulus[:20])
        adjusted_focus = target.attention_score * (1 - fatigue * 0.3)

        # Decide whether to focus or suppress
        should_focus = adjusted_focus > 0.4

        # Allocate compute if focusing
        allocation = {}
        if should_focus:
            allocation = await self.allocate_compute(
                available_components=["attention", "working_memory", "reasoning", "perception"],
                task_context={
                    "stimulus": stimulus,
                    "urgency": target.urgency,
                    "novelty": target.novelty,
                },
                uncertainty_data={
                    "attention": uncertainty,
                    "working_memory": 0.3,
                    "reasoning": uncertainty * 0.8,
                    "perception": 0.4,
                },
                total_budget=compute_budget,
            )

        return {
            "should_focus": should_focus,
            "attention_score": target.attention_score,
            "adjusted_focus": adjusted_focus,
            "fatigue_level": fatigue,
            "exploration_allocation": exploration_allocation,
            "exploitation_allocation": exploitation_allocation,
            "compute_allocation": allocation,
            "recommendation": (
                "Focus and explore"
                if uncertainty > 0.6 and should_focus
                else "Focus and exploit"
                if should_focus
                else "Suppress and maintain current focus"
            ),
        }
