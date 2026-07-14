"""Emotional processor - valence-driven behavior.

Implements emotional processing that influences decision-making,
memory encoding, and attention. Not just a field, but actual
processing that affects agent behavior.
"""

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog


@dataclass
class EmotionalState:
    """Current emotional state."""
    valence: float = 0.0  # -1 (negative) to 1 (positive)
    arousal: float = 0.5  # 0 (calm) to 1 (excited)
    dominance: float = 0.5  # 0 (submissive) to 1 (dominant)
    confidence: float = 0.5
    curiosity: float = 0.5
    satisfaction: float = 0.5
    frustration: float = 0.0
    last_updated: datetime = field(default_factory=datetime.utcnow)

    @property
    def mood(self) -> str:
        """Get current mood label."""
        if self.valence > 0.5 and self.arousal > 0.5:
            return "excited"
        elif self.valence > 0.5 and self.arousal < 0.5:
            return "content"
        elif self.valence < -0.5 and self.arousal > 0.5:
            return "frustrated"
        elif self.valence < -0.5 and self.arousal < 0.5:
            return "sad"
        elif self.curiosity > 0.7:
            return "curious"
        elif self.confidence > 0.7:
            return "confident"
        return "neutral"

    def to_vector(self) -> list[float]:
        """Convert to feature vector."""
        return [
            self.valence,
            self.arousal,
            self.dominance,
            self.confidence,
            self.curiosity,
            self.satisfaction,
            self.frustration,
        ]


@dataclass
class EmotionalEvent:
    """An event that triggers emotional response."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""  # success, failure, discovery, error, etc.
    description: str = ""
    valence_impact: float = 0.0  # How much to shift valence
    arousal_impact: float = 0.0  # How much to shift arousal
    timestamp: datetime = field(default_factory=datetime.utcnow)
    context: dict[str, Any] = field(default_factory=dict)


class EmotionalProcessor:
    """Processes emotions that influence agent behavior.

    Emotions affect:
    - Decision making (risk tolerance under different moods)
    - Memory encoding (emotional events remembered better)
    - Attention (emotional content gets more focus)
    - Learning (frustration can help or hinder)
    """

    def __init__(self):
        self.state = EmotionalState()
        self.emotional_history: list[EmotionalEvent] = []
        self.mood_history: list[str] = []
        self.emotional_triggers: dict[str, float] = {
            "success": 0.3,
            "failure": -0.3,
            "discovery": 0.4,
            "error": -0.4,
            "progress": 0.2,
            "setback": -0.2,
            "surprise": 0.1,
            "boredom": -0.1,
        }
        self.logger = structlog.get_logger()

    async def process_event(
        self,
        event_type: str,
        description: str = "",
        context: dict[str, Any] | None = None,
    ) -> EmotionalState:
        """Process an event and update emotional state."""
        # Get trigger impact
        valence_impact = self.emotional_triggers.get(event_type, 0.0)
        arousal_impact = 0.1 if event_type in ["success", "failure", "discovery"] else 0.0

        # Create emotional event
        event = EmotionalEvent(
            event_type=event_type,
            description=description,
            valence_impact=valence_impact,
            arousal_impact=arousal_impact,
            context=context or {},
        )
        self.emotional_history.append(event)

        # Update emotional state
        self.state.valence = max(-1.0, min(1.0, self.state.valence + valence_impact))
        self.state.arousal = max(0.0, min(1.0, self.state.arousal + arousal_impact))

        # Update specific emotions
        if event_type == "success":
            self.state.confidence = min(1.0, self.state.confidence + 0.1)
            self.state.satisfaction = min(1.0, self.state.satisfaction + 0.15)
            self.state.frustration = max(0.0, self.state.frustration - 0.1)
        elif event_type == "failure":
            self.state.confidence = max(0.0, self.state.confidence - 0.1)
            self.state.frustration = min(1.0, self.state.frustration + 0.2)
            self.state.satisfaction = max(0.0, self.state.satisfaction - 0.1)
        elif event_type == "discovery":
            self.state.curiosity = min(1.0, self.state.curiosity + 0.2)
            self.state.satisfaction = min(1.0, self.state.satisfaction + 0.1)

        # Natural decay toward neutral
        self.state.valence *= 0.95
        self.state.arousal *= 0.9
        self.state.frustration *= 0.85

        self.state.last_updated = datetime.utcnow()
        self.mood_history.append(self.state.mood)

        self.logger.debug(
            "emotional_update",
            event=event_type,
            mood=self.state.mood,
            valence=self.state.valence,
        )

        return self.state

    def should_take_risk(self) -> bool:
        """Determine if agent should take risks based on emotional state."""
        # High confidence and positive valence = more risk tolerant
        # High frustration = more risk seeking (desperate)
        # Low confidence = risk averse
        risk_tolerance = (
            self.state.confidence * 0.4 +
            (self.state.valence + 1) / 2 * 0.3 +
            self.state.frustration * 0.3
        )
        return risk_tolerance > 0.6

    def get_learning_motivation(self) -> float:
        """Get motivation to learn based on emotional state."""
        motivation = 0.5

        # Curiosity drives learning
        motivation += self.state.curiosity * 0.3

        # Positive valence helps
        motivation += (self.state.valence + 1) / 2 * 0.2

        # Too much frustration hurts
        if self.state.frustration > 0.7:
            motivation -= 0.2

        # Confidence helps
        motivation += self.state.confidence * 0.2

        return max(0.0, min(1.0, motivation))

    def should_persist(self) -> bool:
        """Determine if agent should persist on current task."""
        # High frustration might mean time to switch
        if self.state.frustration > 0.8:
            return False

        # High satisfaction means we're making progress
        if self.state.satisfaction > 0.7:
            return True

        # High confidence means we can succeed
        if self.state.confidence > 0.6:
            return True

        return True

    def get_memory_encoding_boost(self, emotional_charge: float) -> float:
        """Get memory encoding boost based on emotional state."""
        # Emotional events are remembered better
        base_boost = abs(emotional_charge) * 0.5

        # Current mood affects encoding
        mood_boost = abs(self.state.valence) * 0.3

        # Arousal helps encoding
        arousal_boost = self.state.arousal * 0.2

        return min(1.0, base_boost + mood_boost + arousal_boost)

    def get_attention_bias(self, content_valence: float) -> float:
        """Get attention bias based on emotional state."""
        # We pay attention to emotionally congruent content
        if self.state.valence > 0:
            # Positive mood -> attend to positive content
            return content_valence * 0.3
        else:
            # Negative mood -> attend to negative content (mood congruent)
            return -content_valence * 0.3

    def get_stats(self) -> dict[str, Any]:
        """Get emotional processor statistics."""
        mood_counts = defaultdict(int)
        for mood in self.mood_history[-100:]:
            mood_counts[mood] += 1

        return {
            "current_mood": self.state.mood,
            "valence": self.state.valence,
            "arousal": self.state.arousal,
            "confidence": self.state.confidence,
            "frustration": self.state.frustration,
            "total_events": len(self.emotional_history),
            "dominant_mood": max(mood_counts, key=mood_counts.get) if mood_counts else "neutral",
        }

    def to_context(self) -> str:
        """Convert emotional state to context string."""
        stats = self.get_stats()
        lines = [
            "Emotional State:",
            f"  Mood: {stats['current_mood']}",
            f"  Valence: {stats['valence']:.2f}",
            f"  Confidence: {stats['confidence']:.2f}",
            f"  Frustration: {stats['frustration']:.2f}",
            f"  Total Events: {stats['total_events']}",
        ]
        return "\n".join(lines)
