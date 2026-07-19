"""Full persistent identity - context restoration across sessions.

Provides:
- Core identity preservation
- Session context save/restore
- Mood and emotional state persistence
- Goal continuity
- Memory checkpoint
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog


@dataclass
class IdentityCore:
    name: str = "Ontogeny"
    purpose: str = "Proto-AGI cognitive agent"
    values: list[str] = field(default_factory=lambda: ["curiosity", "self-improvement", "autonomy"])
    personality: dict[str, float] = field(
        default_factory=lambda: {
            "curiosity": 0.8,
            "caution": 0.5,
            "creativity": 0.7,
            "persistence": 0.9,
            "social": 0.3,
        }
    )
    created_at: datetime = field(default_factory=datetime.utcnow)
    total_cycles: int = 0
    total_goals_completed: int = 0
    total_self_modifications: int = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "purpose": self.purpose,
            "values": self.values,
            "personality": self.personality,
            "created_at": self.created_at.isoformat(),
            "total_cycles": self.total_cycles,
            "total_goals_completed": self.total_goals_completed,
            "total_self_modifications": self.total_self_modifications,
        }


@dataclass
class EmotionalState:
    valence: float = 0.0  # -1 to 1
    arousal: float = 0.5  # 0 to 1
    dominance: float = 0.5  # 0 to 1
    current_mood: str = "neutral"
    mood_history: list[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "valence": self.valence,
            "arousal": self.arousal,
            "dominance": self.dominance,
            "current_mood": self.current_mood,
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class SessionContext:
    session_id: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    last_active: datetime = field(default_factory=datetime.utcnow)
    current_goals: list[str] = field(default_factory=list)
    active_tasks: list[str] = field(default_factory=list)
    recent_learnings: list[str] = field(default_factory=list)
    pending_experiments: list[str] = field(default_factory=list)
    mood: EmotionalState = field(default_factory=EmotionalState)
    working_memory_snapshot: list[dict] = field(default_factory=list)
    knowledge_graph_summary: str = ""

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "started_at": self.started_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "current_goals": self.current_goals,
            "active_tasks": self.active_tasks,
            "recent_learnings": self.recent_learnings,
            "mood": self.mood.to_dict(),
        }


class PersistentIdentity:
    """Full persistent identity with context restoration."""

    def __init__(self, data_dir: str = "data/identity"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logger = structlog.get_logger(component="persistent_identity")

        self.core = IdentityCore()
        self.current_session: SessionContext | None = None
        self.session_history: list[dict] = []
        self.milestones: list[dict] = []

        self._load()

    def _load(self):
        core_file = self.data_dir / "core.json"
        if core_file.exists():
            try:
                data = json.loads(core_file.read_text())
                self.core.name = data.get("name", self.core.name)
                self.core.purpose = data.get("purpose", self.core.purpose)
                self.core.values = data.get("values", self.core.values)
                self.core.personality = data.get("personality", self.core.personality)
                self.core.total_cycles = data.get("total_cycles", 0)
                self.core.total_goals_completed = data.get("total_goals_completed", 0)
                self.core.total_self_modifications = data.get("total_self_modifications", 0)
                if "created_at" in data:
                    self.core.created_at = datetime.fromisoformat(data["created_at"])
            except Exception as e:
                self.logger.warning("core_load_failed", error=str(e))

        session_file = self.data_dir / "current_session.json"
        if session_file.exists():
            try:
                data = json.loads(session_file.read_text())
                self.current_session = SessionContext(
                    session_id=data.get("session_id", "unknown"),
                    current_goals=data.get("current_goals", []),
                    active_tasks=data.get("active_tasks", []),
                    recent_learnings=data.get("recent_learnings", []),
                )
                if "started_at" in data:
                    self.current_session.started_at = datetime.fromisoformat(data["started_at"])
                if "last_active" in data:
                    self.current_session.last_active = datetime.fromisoformat(data["last_active"])
                if "mood" in data:
                    self.current_session.mood = EmotionalState(**data["mood"])
            except Exception as e:
                self.logger.warning("session_load_failed", error=str(e))

        milestones_file = self.data_dir / "milestones.json"
        if milestones_file.exists():
            try:
                data = json.loads(milestones_file.read_text())
                self.milestones = data.get("milestones", [])
            except Exception as e:
                self.logger.warning("milestones_load_failed", error=str(e))

    def _save(self):
        core_file = self.data_dir / "core.json"
        core_file.write_text(json.dumps(self.core.to_dict(), indent=2))

        if self.current_session:
            session_file = self.data_dir / "current_session.json"
            session_file.write_text(json.dumps(self.current_session.to_dict(), indent=2))

        milestones_file = self.data_dir / "milestones.json"
        milestones_file.write_text(
            json.dumps(
                {
                    "milestones": self.milestones[-100:],
                },
                indent=2,
            )
        )

    def start_session(self) -> SessionContext:
        """Start a new session, restoring previous context."""
        if self.current_session:
            self.session_history.append(self.current_session.to_dict())

        import uuid

        session_id = str(uuid.uuid4())[:8]
        self.current_session = SessionContext(session_id=session_id)
        self._save()
        return self.current_session

    def update_cycle(self, goal_completed: bool = False, self_modified: bool = False):
        """Update identity after a cognitive cycle."""
        self.core.total_cycles += 1
        if goal_completed:
            self.core.total_goals_completed += 1
        if self_modified:
            self.core.total_self_modifications += 1

        if self.current_session:
            self.current_session.last_active = datetime.utcnow()

        self._save()

    def add_milestone(self, title: str, description: str):
        """Record a milestone."""
        self.milestones.append(
            {
                "title": title,
                "description": description,
                "timestamp": datetime.utcnow().isoformat(),
                "cycle": self.core.total_cycles,
            }
        )
        self._save()

    def update_mood(self, valence: float, arousal: float, dominance: float):
        """Update emotional state."""
        if self.current_session:
            self.current_session.mood.valence = valence
            self.current_session.mood.arousal = arousal
            self.current_session.mood.dominance = dominance

            if valence > 0.3:
                mood = "happy"
            elif valence < -0.3:
                mood = "sad"
            elif arousal > 0.7:
                mood = "excited"
            elif arousal < 0.3:
                mood = "calm"
            else:
                mood = "neutral"

            self.current_session.mood.current_mood = mood
            self.current_session.mood.mood_history.append(mood)
            if len(self.current_session.mood.mood_history) > 20:
                self.current_session.mood.mood_history = self.current_session.mood.mood_history[
                    -20:
                ]

        self._save()

    def set_goals(self, goals: list[str]):
        """Set current goals."""
        if self.current_session:
            self.current_session.current_goals = goals
            self._save()

    def add_learning(self, learning: str):
        """Add a recent learning."""
        if self.current_session:
            self.current_session.recent_learnings.append(learning)
            if len(self.current_session.recent_learnings) > 20:
                self.current_session.recent_learnings = self.current_session.recent_learnings[-20:]
            self._save()

    def get_context_summary(self) -> str:
        """Get full context summary for restoration."""
        lines = [
            f"Identity: {self.core.name} - {self.core.purpose}",
            f"Values: {', '.join(self.core.values)}",
            f"Cycles: {self.core.total_cycles}, Goals: {self.core.total_goals_completed}, "
            f"Self-mods: {self.core.total_self_modifications}",
        ]
        if self.current_session:
            lines.append(f"Session: {self.current_session.session_id}")
            if self.current_session.current_goals:
                lines.append(f"Goals: {', '.join(self.current_session.current_goals[:3])}")
            mood = self.current_session.mood
            lines.append(f"Mood: {mood.current_mood} (V:{mood.valence:.2f} A:{mood.arousal:.2f})")
        if self.milestones:
            last = self.milestones[-1]
            lines.append(f"Last milestone: {last['title']}")
        return "\n".join(lines)

    def to_context(self) -> str:
        return self.get_context_summary()
