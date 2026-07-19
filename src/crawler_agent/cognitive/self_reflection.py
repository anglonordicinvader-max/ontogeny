"""Self-Reflection Loop - post-action evaluator that stores reflections in memory.

Every action the agent takes gets evaluated:
- Did it achieve the intended outcome?
- What would I do differently?
- What did I learn about my own failure modes?

Over time, reflections accumulate into a model of the agent's own
strengths, weaknesses, and blind spots.
"""

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, StrEnum
from typing import Any

import structlog

from .backend import CognitiveBackend


class ReflectionType(StrEnum):
    SUCCESS = "success"  # Action achieved goal
    PARTIAL = "partial"  # Partially achieved goal
    FAILURE = "failure"  # Action failed
    SURPRISE = "surprise"  # Outcome unexpected
    INSIGHT = "insight"  # Learned something new about self
    PATTERN = "pattern"  # Recognized recurring behavior


class SeverityLevel(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class ActionRecord:
    """Record of an action taken by the agent."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_type: str = ""
    description: str = ""
    intended_outcome: str = ""
    actual_outcome: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    confidence_before: float = 0.5
    confidence_after: float = 0.5


@dataclass
class Reflection:
    """A reflection on an action's outcome."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_id: str = ""
    reflection_type: ReflectionType = ReflectionType.SUCCESS
    severity: SeverityLevel = SeverityLevel.INFO
    what_worked: str = ""
    what_failed: str = ""
    root_cause: str = ""
    lesson_learned: str = ""
    self_model_update: str = ""  # How this changes our understanding of ourselves
    confidence_delta: float = 0.0  # Change in confidence
    emotional_impact: float = 0.0  # -1 (very negative) to +1 (very positive)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SelfModel:
    """The agent's model of itself."""

    strengths: dict[str, float] = field(default_factory=dict)  # capability -> proficiency
    weaknesses: dict[str, float] = field(default_factory=dict)  # capability -> weakness level
    blind_spots: list[str] = field(default_factory=list)
    failure_modes: dict[str, int] = field(default_factory=dict)  # mode -> count
    success_patterns: dict[str, int] = field(default_factory=dict)  # pattern -> count
    total_reflections: int = 0
    avg_confidence_trend: float = 0.5

    def get_known_strengths(self, threshold: float = 0.7) -> list[str]:
        return [k for k, v in self.strengths.items() if v >= threshold]

    def get_known_weaknesses(self, threshold: float = 0.4) -> list[str]:
        return [k for k, v in self.weaknesses.items() if v >= threshold]

    def to_context(self) -> str:
        lines = ["Self-Model:"]
        strengths = self.get_known_strengths()
        weaknesses = self.get_known_weaknesses()
        if strengths:
            lines.append(f"  Strengths: {', '.join(strengths[:5])}")
        if weaknesses:
            lines.append(f"  Weaknesses: {', '.join(weaknesses[:5])}")
        if self.blind_spots:
            lines.append(f"  Blind Spots: {', '.join(self.blind_spots[:3])}")
        top_modes = sorted(self.failure_modes.items(), key=lambda x: x[1], reverse=True)[:3]
        if top_modes:
            lines.append(f"  Top Failure Modes: {', '.join(f'{m}({c})' for m, c in top_modes)}")
        return "\n".join(lines)


class SelfReflectionEngine:
    """Post-action reflection engine.

    After every action, evaluates the outcome and generates a reflection.
    Reflections accumulate into a self-model that improves future decisions.
    """

    def __init__(self, backend: CognitiveBackend):
        self.backend = backend
        self.action_history: list[ActionRecord] = []
        self.reflections: list[Reflection] = []
        self.self_model = SelfModel()
        self.reflection_count = 0
        self.logger = structlog.get_logger()

    async def record_action(
        self,
        action_type: str,
        description: str,
        intended_outcome: str,
        context: dict[str, Any] | None = None,
        confidence: float = 0.5,
    ) -> ActionRecord:
        """Record an action before execution."""
        record = ActionRecord(
            action_type=action_type,
            description=description,
            intended_outcome=intended_outcome,
            context=context or {},
            confidence_before=confidence,
        )
        self.action_history.append(record)
        return record

    async def reflect_on_action(
        self,
        action: ActionRecord,
        actual_outcome: str,
        success: bool,
        surprise: bool = False,
    ) -> Reflection:
        """Generate a reflection after action completion."""
        action.actual_outcome = actual_outcome

        system_prompt = """You are a self-reflective AI agent. Analyze what happened and generate a reflection.

Return JSON with:
- reflection_type: success/partial/failure/surprise/insight/pattern
- what_worked: what went well
- what_failed: what went wrong
- root_cause: why did this happen
- lesson_learned: what to do differently next time
- self_model_update: how this changes understanding of own capabilities
- emotional_impact: -1.0 to 1.0
- severity: info/warning/critical
- failure_mode: if failed, categorize the failure mode"""

        user_prompt = f"""Action: {action.action_type} - {action.description}
Intended: {action.intended_outcome}
Actual: {actual_outcome}
Success: {success}
Surprise: {surprise}
Confidence before: {action.confidence_before:.2f}
Context: {action.context}

Reflect:"""

        response = await self.backend.complete(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=800,
            temperature=0.3,
        )

        try:
            data = response.parsed_json
            reflection = Reflection(
                action_id=action.id,
                reflection_type=ReflectionType(
                    data.get("reflection_type", "success" if success else "failure")
                ),
                severity=SeverityLevel(data.get("severity", "info")),
                what_worked=data.get("what_worked", ""),
                what_failed=data.get("what_failed", ""),
                root_cause=data.get("root_cause", ""),
                lesson_learned=data.get("lesson_learned", ""),
                self_model_update=data.get("self_model_update", ""),
                emotional_impact=data.get("emotional_impact", 0.0 if success else -0.3),
                confidence_delta=0.05 if success else -0.1,
            )
        except Exception:
            reflection = Reflection(
                action_id=action.id,
                reflection_type=ReflectionType.SUCCESS if success else ReflectionType.FAILURE,
                what_worked="Action completed" if success else "Action failed",
                what_failed="" if success else actual_outcome,
                lesson_learned="Continue" if success else "Try different approach",
            )

        self.reflections.append(reflection)
        self.reflection_count += 1

        # Update self-model
        self._update_self_model(action, reflection, success)

        self.logger.info(
            "reflection_generated",
            action=action.action_type,
            type=reflection.reflection_type.value,
            lesson=reflection.lesson_learned[:100],
        )

        return reflection

    def _update_self_model(self, action: ActionRecord, reflection: Reflection, success: bool):
        """Update self-model based on reflection."""
        capability = action.action_type

        if success:
            current = self.self_model.strengths.get(capability, 0.5)
            self.self_model.strengths[capability] = min(1.0, current + 0.05)
            self.self_model.success_patterns[capability] = (
                self.self_model.success_patterns.get(capability, 0) + 1
            )
        else:
            current_weak = self.self_model.weaknesses.get(capability, 0.0)
            self.self_model.weaknesses[capability] = min(1.0, current_weak + 0.05)
            failure_mode = reflection.root_cause or "unknown"
            self.self_model.failure_modes[failure_mode] = (
                self.self_model.failure_modes.get(failure_mode, 0) + 1
            )

        # Track blind spots (high confidence + failure = blind spot)
        if not success and action.confidence_before > 0.7:
            blind_spot = f"{capability}: {reflection.root_cause}"
            if blind_spot not in self.self_model.blind_spots:
                self.self_model.blind_spots.append(blind_spot)
                if len(self.self_model.blind_spots) > 10:
                    self.self_model.blind_spots.pop(0)

        self.self_model.total_reflections = self.reflection_count

    async def pre_action_review(
        self, action_type: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Review past reflections before taking an action. Returns warnings and suggestions."""
        relevant_reflections = [
            r
            for r in self.reflections
            if r.action_id in [a.id for a in self.action_history if a.action_type == action_type]
        ]

        if not relevant_reflections:
            return {
                "warnings": [],
                "suggestions": ["No prior experience with this action type"],
                "confidence": 0.5,
            }

        failures = [r for r in relevant_reflections if r.reflection_type == ReflectionType.FAILURE]
        warnings = []
        suggestions = []

        if failures:
            recent_failures = sorted(failures, key=lambda r: r.timestamp, reverse=True)[:3]
            for f in recent_failures:
                warnings.append(f"Previously failed: {f.root_cause}")
                if f.lesson_learned:
                    suggestions.append(f.lesson_learned)

        # Check if this is a blind spot
        if action_type in [bs.split(":")[0] for bs in self.self_model.blind_spots]:
            warnings.append("BLIND SPOT: This action type has high-confidence failures")

        avg_confidence = sum(r.confidence_delta for r in relevant_reflections) / len(
            relevant_reflections
        )

        return {
            "warnings": warnings,
            "suggestions": suggestions,
            "past_attempts": len(relevant_reflections),
            "historical_success_rate": 1 - len(failures) / len(relevant_reflections),
            "confidence_adjustment": avg_confidence,
        }

    def get_reflection_summary(self, limit: int = 10) -> str:
        """Get a summary of recent reflections for context."""
        recent = sorted(self.reflections, key=lambda r: r.timestamp, reverse=True)[:limit]
        if not recent:
            return "No reflections yet."

        lines = ["Recent Reflections:"]
        for r in recent:
            lines.append(f"  [{r.reflection_type.value}] {r.lesson_learned[:80]}")
        return "\n".join(lines)

    def get_stats(self) -> dict[str, Any]:
        type_counts = defaultdict(int)
        for r in self.reflections:
            type_counts[r.reflection_type.value] += 1

        return {
            "total_actions": len(self.action_history),
            "total_reflections": self.reflection_count,
            "reflection_types": dict(type_counts),
            "self_model": {
                "strengths": len(self.self_model.strengths),
                "weaknesses": len(self.self_model.weaknesses),
                "blind_spots": len(self.self_model.blind_spots),
                "failure_modes": len(self.self_model.failure_modes),
            },
            "avg_emotional_impact": (
                sum(r.emotional_impact for r in self.reflections) / max(1, len(self.reflections))
            ),
        }

    def to_context(self) -> str:
        lines = [self.self_model.to_context()]
        lines.append(f"  Total Reflections: {self.reflection_count}")
        recent = self.get_reflection_summary(3)
        lines.append(f"  {recent}")
        return "\n".join(lines)
