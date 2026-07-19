"""Persistent world memory - Blender scenes persist across sessions.

Provides:
- Save/load Blender scenes between sessions
- Track object locations and states
- Remember previous experiments
- Object permanence (track objects not in view)
- Affordance learning (what objects can do)
"""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog


@dataclass
class WorldObject:
    """An object in the persistent world."""

    id: str
    name: str
    object_type: str  # cube, sphere, cylinder, robot, etc.
    position: list[float] = field(default_factory=lambda: [0, 0, 0])
    rotation: list[float] = field(default_factory=lambda: [0, 0, 0])
    scale: list[float] = field(default_factory=lambda: [1, 1, 1])
    mass: float = 1.0
    is_static: bool = False
    last_seen: datetime = field(default_factory=datetime.utcnow)
    first_seen: datetime = field(default_factory=datetime.utcnow)
    times_observed: int = 1
    times_interacted: int = 0
    affordances: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "object_type": self.object_type,
            "position": self.position,
            "rotation": self.rotation,
            "scale": self.scale,
            "mass": self.mass,
            "is_static": self.is_static,
            "last_seen": self.last_seen.isoformat(),
            "first_seen": self.first_seen.isoformat(),
            "times_observed": self.times_observed,
            "times_interacted": self.times_interacted,
            "affordances": self.affordances,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorldObject":
        data = dict(data)
        for date_field in ["last_seen", "first_seen"]:
            if date_field in data and isinstance(data[date_field], str):
                data[date_field] = datetime.fromisoformat(data[date_field])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ExperimentRecord:
    """Record of a physics experiment."""

    id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    hypothesis: str = ""
    objects_involved: list[str] = field(default_factory=list)
    actions_taken: list[str] = field(default_factory=list)
    outcome: str = ""
    learned: str = ""
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "hypothesis": self.hypothesis,
            "objects_involved": self.objects_involved,
            "actions_taken": self.actions_taken,
            "outcome": self.outcome,
            "learned": self.learned,
            "confidence": self.confidence,
        }


@dataclass
class Affordance:
    """Learned affordance of an object type."""

    object_type: str
    affordance: str  # pushable, throwable, stackable, climbable, graspable, rotatable, movable
    confidence: float = 0.0
    examples: int = 0
    last_tested: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "object_type": self.object_type,
            "affordance": self.affordance,
            "confidence": self.confidence,
            "examples": self.examples,
            "last_tested": self.last_tested.isoformat(),
        }


class PersistentWorldMemory:
    """Persistent world memory that survives across sessions."""

    def __init__(self, data_dir: str = "data/world_memory"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logger = structlog.get_logger(component="world_memory")

        self.objects: dict[str, WorldObject] = {}
        self.experiments: list[ExperimentRecord] = []
        self.affordances: dict[str, list[Affordance]] = {}  # object_type -> affordances
        self.scene_history: list[dict] = []

        self._load()

    def _load(self):
        objects_file = self.data_dir / "objects.json"
        if objects_file.exists():
            try:
                data = json.loads(objects_file.read_text())
                for obj_data in data.get("objects", []):
                    obj = WorldObject.from_dict(obj_data)
                    self.objects[obj.id] = obj
            except Exception as e:
                self.logger.warning("objects_load_failed", error=str(e))

        experiments_file = self.data_dir / "experiments.json"
        if experiments_file.exists():
            try:
                data = json.loads(experiments_file.read_text())
                for exp_data in data.get("experiments", []):
                    self.experiments.append(
                        ExperimentRecord(
                            id=exp_data["id"],
                            hypothesis=exp_data.get("hypothesis", ""),
                            objects_involved=exp_data.get("objects_involved", []),
                            actions_taken=exp_data.get("actions_taken", []),
                            outcome=exp_data.get("outcome", ""),
                            learned=exp_data.get("learned", ""),
                            confidence=exp_data.get("confidence", 0.0),
                        )
                    )
            except Exception as e:
                self.logger.warning("experiments_load_failed", error=str(e))

        affordances_file = self.data_dir / "affordances.json"
        if affordances_file.exists():
            try:
                data = json.loads(affordances_file.read_text())
                for obj_type, aff_list in data.get("affordances", {}).items():
                    self.affordances[obj_type] = [Affordance(**aff) for aff in aff_list]
            except Exception as e:
                self.logger.warning("affordances_load_failed", error=str(e))

    def _save(self):
        objects_file = self.data_dir / "objects.json"
        objects_file.write_text(
            json.dumps(
                {
                    "objects": [obj.to_dict() for obj in self.objects.values()],
                    "saved_at": datetime.utcnow().isoformat(),
                },
                indent=2,
            )
        )

        experiments_file = self.data_dir / "experiments.json"
        experiments_file.write_text(
            json.dumps(
                {
                    "experiments": [
                        exp.to_dict() for exp in self.experiments[-100:]
                    ],  # Keep last 100
                    "saved_at": datetime.utcnow().isoformat(),
                },
                indent=2,
            )
        )

        affordances_file = self.data_dir / "affordances.json"
        affordances_file.write_text(
            json.dumps(
                {
                    "affordances": {
                        obj_type: [aff.to_dict() for aff in affs]
                        for obj_type, affs in self.affordances.items()
                    },
                    "saved_at": datetime.utcnow().isoformat(),
                },
                indent=2,
            )
        )

    def update_object(
        self,
        obj_id: str,
        name: str,
        object_type: str,
        position: list[float] = None,
        rotation: list[float] = None,
        scale: list[float] = None,
        mass: float = None,
        is_static: bool = None,
    ) -> WorldObject:
        """Update or create a world object."""
        if obj_id in self.objects:
            obj = self.objects[obj_id]
            obj.times_observed += 1
            obj.last_seen = datetime.utcnow()
            if position:
                obj.position = position
            if rotation:
                obj.rotation = rotation
            if scale:
                obj.scale = scale
            if mass is not None:
                obj.mass = mass
            if is_static is not None:
                obj.is_static = is_static
        else:
            obj = WorldObject(
                id=obj_id,
                name=name,
                object_type=object_type,
                position=position or [0, 0, 0],
                rotation=rotation or [0, 0, 0],
                scale=scale or [1, 1, 1],
                mass=mass or 1.0,
                is_static=is_static or False,
            )
            self.objects[obj_id] = obj

        self._save()
        return obj

    def record_interaction(self, obj_id: str, action: str, outcome: str):
        """Record an interaction with an object."""
        if obj_id in self.objects:
            self.objects[obj_id].times_interacted += 1
            self.objects[obj_id].last_seen = datetime.utcnow()
            self._save()

    def add_affordance(self, object_type: str, affordance: str, confidence: float = 0.5):
        """Add a learned affordance for an object type."""
        if object_type not in self.affordances:
            self.affordances[object_type] = []

        # Check if already exists
        for aff in self.affordances[object_type]:
            if aff.affordance == affordance:
                aff.confidence = max(aff.confidence, confidence)
                aff.examples += 1
                aff.last_tested = datetime.utcnow()
                self._save()
                return

        self.affordances[object_type].append(
            Affordance(
                object_type=object_type,
                affordance=affordance,
                confidence=confidence,
                examples=1,
            )
        )
        self._save()

    def get_affordances(self, object_type: str) -> list[str]:
        """Get learned affordances for an object type."""
        affs = self.affordances.get(object_type, [])
        return [aff.affordance for aff in affs if aff.confidence > 0.3]

    def predict_affordances(self, object_type: str) -> dict[str, float]:
        """Predict affordances for an object type."""
        affs = self.affordances.get(object_type, [])
        return {aff.affordance: aff.confidence for aff in affs}

    def record_experiment(
        self,
        hypothesis: str,
        objects_involved: list[str],
        actions_taken: list[str],
        outcome: str,
        learned: str,
        confidence: float = 0.5,
    ) -> ExperimentRecord:
        """Record a physics experiment."""
        import uuid

        exp = ExperimentRecord(
            id=str(uuid.uuid4())[:8],
            hypothesis=hypothesis,
            objects_involved=objects_involved,
            actions_taken=actions_taken,
            outcome=outcome,
            learned=learned,
            confidence=confidence,
        )
        self.experiments.append(exp)
        self._save()
        return exp

    def get_object(self, obj_id: str) -> WorldObject | None:
        return self.objects.get(obj_id)

    def get_objects_by_type(self, object_type: str) -> list[WorldObject]:
        return [obj for obj in self.objects.values() if obj.object_type == object_type]

    def get_recent_experiments(self, limit: int = 10) -> list[ExperimentRecord]:
        return self.experiments[-limit:]

    def get_hidden_objects(self, visible_ids: list[str]) -> list[WorldObject]:
        """Get objects not currently visible (object permanence)."""
        return [obj for obj in self.objects.values() if obj.id not in visible_ids]

    def predict_object_location(self, obj_id: str) -> list[float] | None:
        """Predict location of a hidden object based on last known state."""
        obj = self.objects.get(obj_id)
        if obj:
            return obj.position
        return None

    def to_context(self) -> str:
        """Convert world memory to context string."""
        lines = [
            f"World Memory: {len(self.objects)} objects, {len(self.experiments)} experiments",
            f"Affordance types: {len(self.affordances)}",
        ]
        if self.objects:
            lines.append("Objects:")
            for obj in list(self.objects.values())[:5]:
                affordances = self.get_affordances(obj.object_type)
                aff_str = f" [{', '.join(affordances)}]" if affordances else ""
                lines.append(f"  {obj.name} ({obj.object_type}) at {obj.position}{aff_str}")
        if self.experiments:
            last_exp = self.experiments[-1]
            lines.append(f"Last experiment: {last_exp.learned}")
        return "\n".join(lines)
