"""Video, OCR, and scene understanding.

Provides:
- Video frame analysis
- OCR text extraction
- Scene object detection
- Action recognition
- Temporal scene understanding
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog


@dataclass
class DetectedObject:
    id: str
    label: str
    confidence: float
    bbox: list[float] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class SceneFrame:
    timestamp: float
    objects: list[DetectedObject] = field(default_factory=list)
    text: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class VideoAnalysis:
    video_id: str
    frames: list[SceneFrame] = field(default_factory=list)
    summary: str = ""
    objects_detected: list[str] = field(default_factory=list)
    actions_recognized: list[str] = field(default_factory=list)
    text_extracted: list[str] = field(default_factory=list)
    duration: float = 0.0


class SceneUnderstanding:
    """Video, OCR, and scene understanding."""

    def __init__(self):
        self.logger = structlog.get_logger(component="scene_understanding")
        self.analysis_history: list[VideoAnalysis] = []

    def analyze_frame(
        self,
        frame_data: Any,
        timestamp: float = 0.0,
    ) -> SceneFrame:
        """Analyze a single video frame."""
        objects = []
        text = []
        actions = []

        if isinstance(frame_data, dict):
            if "objects" in frame_data:
                for obj in frame_data["objects"]:
                    objects.append(
                        DetectedObject(
                            id=obj.get("id", ""),
                            label=obj.get("label", "unknown"),
                            confidence=obj.get("confidence", 0.5),
                            bbox=obj.get("bbox", []),
                        )
                    )

            if "text" in frame_data:
                text = frame_data["text"]

            if "actions" in frame_data:
                actions = frame_data["actions"]

        return SceneFrame(
            timestamp=timestamp,
            objects=objects,
            text=text,
            actions=actions,
            description=frame_data.get("description", "") if isinstance(frame_data, dict) else "",
        )

    def analyze_video(
        self,
        video_id: str,
        frames: list[Any],
        frame_times: list[float] | None = None,
    ) -> VideoAnalysis:
        """Analyze multiple video frames."""
        if frame_times is None:
            frame_times = [i * 0.1 for i in range(len(frames))]

        scene_frames = []
        all_objects = set()
        all_actions = set()
        all_text = set()

        for i, frame_data in enumerate(frames):
            timestamp = frame_times[i] if i < len(frame_times) else i * 0.1
            scene_frame = self.analyze_frame(frame_data, timestamp)
            scene_frames.append(scene_frame)

            for obj in scene_frame.objects:
                all_objects.add(obj.label)
            all_actions.update(scene_frame.actions)
            all_text.update(scene_frame.text)

        analysis = VideoAnalysis(
            video_id=video_id,
            frames=scene_frames,
            objects_detected=list(all_objects),
            actions_recognized=list(all_actions),
            text_extracted=list(all_text),
            duration=frame_times[-1] if frame_times else 0,
        )
        self.analysis_history.append(analysis)
        return analysis

    def detect_changes(
        self,
        frame_a: SceneFrame,
        frame_b: SceneFrame,
    ) -> dict:
        """Detect changes between two frames."""
        objects_a = {obj.label for obj in frame_a.objects}
        objects_b = {obj.label for obj in frame_b.objects}

        return {
            "objects_appeared": list(objects_b - objects_a),
            "objects_disappeared": list(objects_a - objects_b),
            "new_actions": list(set(frame_b.actions) - set(frame_a.actions)),
            "text_changes": frame_b.text != frame_a.text,
        }

    def summarize_video(self, analysis: VideoAnalysis) -> str:
        """Generate a summary of video analysis."""
        lines = [
            f"Video {analysis.video_id}: {len(analysis.frames)} frames, {analysis.duration:.1f}s"
        ]
        if analysis.objects_detected:
            lines.append(f"Objects: {', '.join(analysis.objects_detected[:5])}")
        if analysis.actions_recognized:
            lines.append(f"Actions: {', '.join(analysis.actions_recognized[:5])}")
        if analysis.text_extracted:
            lines.append(f"Text: {', '.join(analysis.text_extracted[:3])}")
        return "\n".join(lines)

    def to_context(self) -> str:
        return f"Scene Understanding: {len(self.analysis_history)} videos analyzed"
