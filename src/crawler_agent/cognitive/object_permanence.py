"""Object permanence - maintain world model when objects leave view.

Provides:
- Object tracking across frames
- Predict hidden object positions
- Re-identify objects
- Handle occlusion
"""

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import structlog


@dataclass
class TrackedObject:
    id: str
    label: str
    position: List[float] = field(default_factory=lambda: [0, 0, 0])
    velocity: List[float] = field(default_factory=lambda: [0, 0, 0])
    last_seen: datetime = field(default_factory=datetime.utcnow)
    first_seen: datetime = field(default_factory=datetime.utcnow)
    times_seen: int = 1
    occluded: bool = False
    occlusion_start: Optional[datetime] = None
    confidence: float = 1.0

    def predict_position(self, dt: float) -> List[float]:
        """Predict position after dt seconds."""
        return [
            self.position[i] + self.velocity[i] * dt
            for i in range(3)
        ]


class ObjectPermanence:
    """Object permanence system."""

    def __init__(self):
        self.logger = structlog.get_logger(component="object_permanence")
        self.objects: Dict[str, TrackedObject] = {}
        self.disappeared: List[TrackedObject] = []

    def update(
        self,
        detected_objects: List[Dict],
        timestamp: Optional[datetime] = None,
    ) -> Dict[str, str]:
        """Update tracking with newly detected objects."""
        ts = timestamp or datetime.utcnow()
        detected_ids = set()
        updates = {}

        for obj_data in detected_objects:
            obj_id = obj_data.get("id", str(uuid.uuid4())[:8])
            detected_ids.add(obj_id)

            if obj_id in self.objects:
                obj = self.objects[obj_id]
                old_pos = obj.position
                new_pos = obj_data.get("position", [0, 0, 0])

                dt = (ts - obj.last_seen).total_seconds()
                if dt > 0:
                    obj.velocity = [
                        (new_pos[i] - old_pos[i]) / dt
                        for i in range(3)
                    ]

                obj.position = new_pos
                obj.last_seen = ts
                obj.times_seen += 1
                obj.occluded = False
                obj.occlusion_start = None
                obj.confidence = min(1.0, obj.confidence + 0.1)
                updates[obj_id] = "updated"
            else:
                obj = TrackedObject(
                    id=obj_id,
                    label=obj_data.get("label", "unknown"),
                    position=obj_data.get("position", [0, 0, 0]),
                    first_seen=ts,
                    last_seen=ts,
                )
                self.objects[obj_id] = obj
                updates[obj_id] = "new"

        for obj_id, obj in list(self.objects.items()):
            if obj_id not in detected_ids:
                if not obj.occluded:
                    obj.occluded = True
                    obj.occlusion_start = ts
                    obj.confidence *= 0.9
                    updates[obj_id] = "occluded"
                else:
                    occlusion_time = (ts - obj.occlusion_start).total_seconds()
                    if occlusion_time > 5.0:
                        obj.confidence *= 0.8
                        updates[obj_id] = "fading"
                    else:
                        updates[obj_id] = "still_hidden"

        return updates

    def get_visible(self) -> List[TrackedObject]:
        """Get currently visible objects."""
        return [obj for obj in self.objects.values() if not obj.occluded]

    def get_hidden(self) -> List[TrackedObject]:
        """Get currently hidden (occluded) objects."""
        return [obj for obj in self.objects.values() if obj.occluded]

    def predict_hidden_positions(self, dt: float = 1.0) -> Dict[str, List[float]]:
        """Predict positions of hidden objects."""
        predictions = {}
        for obj in self.get_hidden():
            predictions[obj.id] = obj.predict_position(dt)
        return predictions

    def reidentify(
        self,
        detected: Dict,
        threshold: float = 0.5,
    ) -> Optional[str]:
        """Re-identify a detected object as a previously seen object."""
        det_pos = detected.get("position", [0, 0, 0])
        det_label = detected.get("label", "")

        best_match = None
        best_score = 0.0

        for obj_id, obj in self.objects.items():
            if not obj.occluded:
                continue

            pos_dist = math.sqrt(sum((det_pos[i] - obj.position[i])**2 for i in range(3)))
            label_match = 1.0 if det_label == obj.label else 0.0

            score = label_match * 0.6 + max(0, 1.0 - pos_dist) * 0.4

            if score > best_score and score > threshold:
                best_score = score
                best_match = obj_id

        return best_match

    def to_context(self) -> str:
        visible = len(self.get_visible())
        hidden = len(self.get_hidden())
        return f"Object Permanence: {visible} visible, {hidden} hidden, {len(self.objects)} total tracked"
