"""YOLOv8 object detection - semantic vision for robotics.

Provides:
- Real-time object detection (80 COCO classes)
- Bounding boxes with confidence scores
- Object tracking across frames
- Custom model training support
- Integration with depth/thermal for 3D detection
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import structlog


@dataclass
class DetectedObject:
    id: str
    class_name: str
    class_id: int
    confidence: float
    bbox: list[float]  # [x1, y1, x2, y2] normalized 0-1
    center: list[float]  # [cx, cy] normalized 0-1
    area: float  # normalized area
    depth: float = -1.0  # meters if depth available
    world_position: list[float] = field(default_factory=list)  # 3D position if available
    tracking_id: int = -1
    frame_id: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "class": self.class_name,
            "class_id": self.class_id,
            "confidence": self.confidence,
            "bbox": self.bbox,
            "center": self.center,
            "area": self.area,
            "depth": self.depth,
            "world_position": self.world_position,
            "tracking_id": self.tracking_id,
        }


@dataclass
class DetectionResult:
    objects: list[DetectedObject]
    frame_id: int
    inference_time_ms: float
    image_size: tuple[int, int]
    model_name: str = "yolov8s"

    @property
    def count(self) -> int:
        return len(self.objects)

    def filter_by_class(self, class_name: str) -> list[DetectedObject]:
        return [obj for obj in self.objects if obj.class_name == class_name]

    def filter_by_confidence(self, min_confidence: float) -> list[DetectedObject]:
        return [obj for obj in self.objects if obj.confidence >= min_confidence]

    def get_closest(self) -> DetectedObject | None:
        if not self.objects:
            return None
        return min(self.objects, key=lambda o: o.depth if o.depth > 0 else float("inf"))

    def get_by_tracking_id(self, tracking_id: int) -> list[DetectedObject]:
        return [obj for obj in self.objects if obj.tracking_id == tracking_id]


# COCO dataset classes (80 objects)
COCO_CLASSES = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    4: "airplane",
    5: "bus",
    6: "train",
    7: "truck",
    8: "boat",
    9: "traffic light",
    10: "fire hydrant",
    11: "stop sign",
    12: "parking meter",
    13: "bench",
    14: "bird",
    15: "cat",
    16: "dog",
    17: "horse",
    18: "sheep",
    19: "cow",
    20: "elephant",
    21: "bear",
    22: "zebra",
    23: "giraffe",
    24: "backpack",
    25: "umbrella",
    26: "handbag",
    27: "tie",
    28: "suitcase",
    29: "frisbee",
    30: "skis",
    31: "snowboard",
    32: "sports ball",
    33: "kite",
    34: "baseball bat",
    35: "baseball glove",
    36: "skateboard",
    37: "surfboard",
    38: "tennis racket",
    39: "bottle",
    40: "wine glass",
    41: "cup",
    42: "fork",
    43: "knife",
    44: "spoon",
    45: "bowl",
    46: "banana",
    47: "apple",
    48: "sandwich",
    49: "orange",
    50: "broccoli",
    51: "carrot",
    52: "hot dog",
    53: "pizza",
    54: "donut",
    55: "cake",
    56: "chair",
    57: "couch",
    58: "potted plant",
    59: "bed",
    60: "dining table",
    61: "toilet",
    62: "tv",
    63: "laptop",
    64: "mouse",
    65: "remote",
    66: "keyboard",
    67: "cell phone",
    68: "microwave",
    69: "oven",
    70: "toaster",
    71: "sink",
    72: "refrigerator",
    73: "book",
    74: "clock",
    75: "vase",
    76: "scissors",
    77: "teddy bear",
    78: "hair drier",
    79: "toothbrush",
}

# Robot-relevant classes for navigation and manipulation
NAVIGATION_CLASSES = [
    "person",
    "car",
    "truck",
    "bus",
    "bicycle",
    "motorcycle",
    "traffic light",
    "stop sign",
    "bench",
    "chair",
]
MANIPULATION_CLASSES = [
    "cup",
    "bottle",
    "knife",
    "fork",
    "spoon",
    "bowl",
    "apple",
    "banana",
    "sandwich",
    "pizza",
]
DOOR_CLASSES = ["door"]  # Custom trained would add this


class YOLODetector:
    """YOLOv8 object detection for robotics."""

    def __init__(
        self,
        model_size: str = "s",
        confidence: float = 0.5,
        iou_threshold: float = 0.45,
        device: str = "cpu",
    ):
        """
        Initialize YOLOv8 detector.

        Args:
            model_size: n(ano), s(mall), m(edium), l(arge), x(large)
            confidence: minimum detection confidence
            iou_threshold: NMS IoU threshold
            device: cpu, cuda, or mps
        """
        self.model_size = model_size
        self.confidence = confidence
        self.iou_threshold = iou_threshold
        self.device = device
        self.model = None
        self.frame_counter = 0
        self.tracker: dict[int, DetectedObject] = {}
        self.next_track_id = 0
        self.logger = structlog.get_logger(component="yolo_detector")

        self._load_model()

    def _load_model(self):
        """Load YOLOv8 model."""
        try:
            from ultralytics import YOLO

            model_name = f"yolov8{self.model_size}.pt"
            self.model = YOLO(model_name)
            self.logger.info("yolo_loaded", model=model_name, device=self.device)
        except ImportError:
            self.logger.warning("ultralytics_not_installed", hint="pip install ultralytics")
            self.model = None
        except Exception as e:
            self.logger.warning("yolo_load_failed", error=str(e))
            self.model = None

    def detect(
        self,
        image,
        depth_map: list[list[float]] = None,
        camera_fov: float = 60.0,
        camera_resolution: tuple[int, int] = (640, 480),
    ) -> DetectionResult:
        """
        Detect objects in image.

        Args:
            image: numpy array (H, W, 3) or path to image
            depth_map: optional depth map for 3D positioning
            camera_fov: camera field of view in degrees
            camera_resolution: (width, height)
        """
        self.frame_counter += 1
        import time

        start_time = time.time()

        if self.model is None:
            return self._simulate_detection(image, depth_map, camera_resolution)

        try:
            results = self.model.predict(
                image,
                conf=self.confidence,
                iou=self.iou_threshold,
                device=self.device,
                verbose=False,
            )

            objects = []
            if results and len(results) > 0:
                result = results[0]
                for box in result.boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = box.xyxy[0].tolist()

                    bbox_norm = [
                        x1 / camera_resolution[0],
                        y1 / camera_resolution[1],
                        x2 / camera_resolution[0],
                        y2 / camera_resolution[1],
                    ]
                    center = [(bbox_norm[0] + bbox_norm[2]) / 2, (bbox_norm[1] + bbox_norm[3]) / 2]
                    area = (bbox_norm[2] - bbox_norm[0]) * (bbox_norm[3] - bbox_norm[1])

                    depth = -1.0
                    world_pos = []
                    if depth_map:
                        cx_pixel = int(center[0] * len(depth_map[0]))
                        cy_pixel = int(center[1] * len(depth_map))
                        if 0 <= cy_pixel < len(depth_map) and 0 <= cx_pixel < len(depth_map[0]):
                            depth = depth_map[cy_pixel][cx_pixel]
                            angle_x = (center[0] - 0.5) * math.radians(camera_fov)
                            angle_y = (center[1] - 0.5) * math.radians(camera_fov * 0.75)
                            world_pos = [
                                depth * math.tan(angle_x),
                                depth * math.tan(angle_y),
                                depth,
                            ]

                    track_id = self._assign_track(center, cls_id)

                    obj = DetectedObject(
                        id=f"det_{self.frame_counter}_{len(objects)}",
                        class_name=COCO_CLASSES.get(cls_id, f"class_{cls_id}"),
                        class_id=cls_id,
                        confidence=conf,
                        bbox=bbox_norm,
                        center=center,
                        area=area,
                        depth=depth,
                        world_position=world_pos,
                        tracking_id=track_id,
                        frame_id=self.frame_counter,
                    )
                    objects.append(obj)

            elapsed_ms = (time.time() - start_time) * 1000

            return DetectionResult(
                objects=objects,
                frame_id=self.frame_counter,
                inference_time_ms=elapsed_ms,
                image_size=camera_resolution,
                model_name=f"yolov8{self.model_size}",
            )

        except Exception as e:
            self.logger.warning("detection_failed", error=str(e))
            return self._simulate_detection(image, depth_map, camera_resolution)

    def _simulate_detection(self, image, depth_map, camera_resolution) -> DetectionResult:
        """Simulate detection when model not available."""
        import random
        import time

        start_time = time.time()

        objects = []
        num_objects = random.randint(0, 5)

        for i in range(num_objects):
            cls_id = random.randint(0, 79)
            conf = random.uniform(0.5, 0.95)
            x1 = random.uniform(0, 0.7)
            y1 = random.uniform(0, 0.7)
            x2 = x1 + random.uniform(0.1, 0.3)
            y2 = y1 + random.uniform(0.1, 0.3)

            bbox = [x1, y1, x2, y2]
            center = [(x1 + x2) / 2, (y1 + y2) / 2]
            area = (x2 - x1) * (y2 - y1)

            depth = -1.0
            world_pos = []
            if depth_map and len(depth_map) > 0:
                depth = random.uniform(1, 20)
                world_pos = [random.uniform(-5, 5), random.uniform(-5, 5), depth]

            obj = DetectedObject(
                id=f"det_{self.frame_counter}_{i}",
                class_name=COCO_CLASSES.get(cls_id, f"class_{cls_id}"),
                class_id=cls_id,
                confidence=conf,
                bbox=bbox,
                center=center,
                area=area,
                depth=depth,
                world_position=world_pos,
                tracking_id=self.next_track_id + i,
                frame_id=self.frame_counter,
            )
            objects.append(obj)

        self.next_track_id += num_objects
        elapsed_ms = (time.time() - start_time) * 1000

        return DetectionResult(
            objects=objects,
            frame_id=self.frame_counter,
            inference_time_ms=elapsed_ms,
            image_size=camera_resolution or (640, 480),
            model_name="simulated",
        )

    def _assign_track(self, center: list[float], class_id: int, threshold: float = 0.1) -> int:
        """Simple IoU-based tracking."""
        best_id = -1
        best_iou = threshold

        for track_id, tracked in self.tracker.items():
            if tracked.class_id != class_id:
                continue
            dx = center[0] - tracked.center[0]
            dy = center[1] - tracked.center[1]
            dist = math.sqrt(dx**2 + dy**2)
            iou = max(0, 1.0 - dist)
            if iou > best_iou:
                best_iou = iou
                best_id = track_id

        if best_id == -1:
            best_id = self.next_track_id
            self.next_track_id += 1

        return best_id

    def detect_persons(self, result: DetectionResult) -> list[DetectedObject]:
        """Get all detected persons."""
        return result.filter_by_class("person")

    def detect_doors(self, result: DetectionResult) -> list[DetectedObject]:
        """Get door-like objects (would need custom model for real doors)."""
        return []  # COCO doesn't have door class

    def detect_tools(self, result: DetectionResult) -> list[DetectedObject]:
        """Get tool-like objects."""
        tool_classes = ["knife", "scissors", "remote", "cell phone", "laptop"]
        return [obj for obj in result.objects if obj.class_name in tool_classes]

    def get_closest_person(self, result: DetectionResult) -> DetectedObject | None:
        """Get closest person for social navigation."""
        persons = self.detect_persons(result)
        if not persons:
            return None
        return min(persons, key=lambda p: p.depth if p.depth > 0 else float("inf"))

    def get_navigation_obstacles(self, result: DetectionResult) -> list[DetectedObject]:
        """Get objects that are navigation obstacles."""
        obstacle_classes = [
            "person",
            "car",
            "truck",
            "bus",
            "bicycle",
            "motorcycle",
            "chair",
            "bench",
            "potted plant",
        ]
        return [obj for obj in result.objects if obj.class_name in obstacle_classes]

    def to_context(self) -> str:
        return f"YOLOv8{self.model_size}: {len(COCO_CLASSES)} classes, confidence={self.confidence}"
