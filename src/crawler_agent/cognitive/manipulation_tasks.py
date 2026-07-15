"""Manipulation tasks - assembly, cutting, pouring, folding.

Provides:
- Assembly (peg-in-hole, snap-fit, screwing)
- Cutting (material separation)
- Pouring (liquid transfer)
- Folding (cloth manipulation)
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import structlog


@dataclass
class TaskState:
    progress: float = 0.0  # 0.0 to 1.0
    success: bool = False
    step: int = 0
    data: Dict = field(default_factory=dict)


class AssemblyTask:
    """Assembly tasks (peg-in-hole, snap-fit, screwing)."""

    def __init__(self):
        self.logger = structlog.get_logger(component="assembly")
        self.task_type = "peg_in-hole"
        self.state = TaskState()

    def setup(self, task_type: str = "peg_in-hole", **kwargs):
        self.task_type = task_type
        self.state = TaskState()
        self.state.data = {
            "peg_position": kwargs.get("peg_position", [0, 0, 0]),
            "hole_position": kwargs.get("hole_position", [0.5, 0, 0]),
            "hole_radius": kwargs.get("hole_radius", 0.025),
            "peg_radius": kwargs.get("peg_radius", 0.02),
            "tolerance": kwargs.get("tolerance", 0.005),
        }

    def check_alignment(self, peg_pos: List[float], hole_pos: List[float]) -> float:
        """Check alignment score (0=bad, 1=perfect)."""
        dx = peg_pos[0] - hole_pos[0]
        dy = peg_pos[1] - hole_pos[1]
        dist = math.sqrt(dx**2 + dy**2)
        tolerance = self.state.data.get("tolerance", 0.005)
        return max(0, 1.0 - dist / (tolerance * 10))

    def insert(self, peg_pos: List[float], hole_pos: List[float],
               force: float = 0.0) -> TaskState:
        """Attempt insertion."""
        alignment = self.check_alignment(peg_pos, hole_pos)
        tolerance = self.state.data.get("tolerance", 0.005)
        dist_xy = math.sqrt((peg_pos[0] - hole_pos[0])**2 + (peg_pos[1] - hole_pos[1])**2)
        depth = hole_pos[2] - peg_pos[2]

        if dist_xy < tolerance and force > 0:
            self.state.progress = min(1.0, self.state.progress + 0.1 * force)
            self.state.step += 1

        if self.state.progress >= 0.9:
            self.state.success = True

        return self.state


class CuttingTask:
    """Cutting material separation."""

    def __init__(self):
        self.logger = structlog.get_logger(component="cutting")
        self.state = TaskState()

    def setup(self, material: str = "wood", thickness: float = 0.02, **kwargs):
        self.state = TaskState()
        self.state.data = {
            "material": material,
            "thickness": thickness,
            "cut_line": kwargs.get("cut_line", [[0, 0], [1, 0]]),
            "material_hardness": {"wood": 0.5, "metal": 0.9, "plastic": 0.3, "cloth": 0.1}.get(material, 0.5),
        }

    def cut(self, tool_position: List[float], force: float = 1.0,
            sharpness: float = 0.8) -> TaskState:
        """Execute cutting action."""
        hardness = self.state.data.get("material_hardness", 0.5)
        cut_rate = (force * sharpness) / (hardness + 0.1)
        self.state.progress = min(1.0, self.state.progress + cut_rate * 0.05)
        self.state.step += 1

        if self.state.progress >= 0.95:
            self.state.success = True

        return self.state


class PouringTask:
    """Pouring liquid transfer."""

    def __init__(self):
        self.logger = structlog.get_logger(component="pouring")
        self.state = TaskState()

    def setup(self, source_volume: float = 1.0, target_volume: float = 0.5,
              viscosity: float = 0.5, **kwargs):
        self.state = TaskState()
        self.state.data = {
            "source_volume": source_volume,
            "target_volume": target_volume,
            "current_poured": 0.0,
            "viscosity": viscosity,
            "spilled": 0.0,
            "target_position": kwargs.get("target_position", [0.5, 0, 0]),
        }

    def pour(self, source_pos: List[float], target_pos: List[float],
             angle: float = 0.0, flow_rate: float = 0.5) -> TaskState:
        """Execute pouring action."""
        if angle < 30:
            return self.state

        viscosity = self.state.data.get("viscosity", 0.5)
        effective_flow = flow_rate * (1 - viscosity * 0.5) * (angle / 90)

        dx = source_pos[0] - target_pos[0]
        dy = source_pos[1] - target_pos[1]
        miss_distance = math.sqrt(dx**2 + dy**2)

        spill_factor = min(1.0, miss_distance / 0.1)
        spilled = effective_flow * spill_factor * 0.01
        poured = effective_flow * (1 - spill_factor) * 0.01

        self.state.data["current_poured"] = self.state.data.get("current_poured", 0) + poured
        self.state.data["spilled"] = self.state.data.get("spilled", 0) + spilled

        target = self.state.data.get("target_volume", 0.5)
        current = self.state.data["current_poured"]
        self.state.progress = min(1.0, current / target)

        if current >= target * 0.95 and spilled < target * 0.1:
            self.state.success = True

        return self.state


class FoldingTask:
    """Folding cloth manipulation."""

    def __init__(self):
        self.logger = structlog.get_logger(component="folding")
        self.state = TaskState()

    def setup(self, cloth_size: Tuple[float, float] = (0.5, 0.5), **kwargs):
        self.state = TaskState()
        self.state.data = {
            "cloth_size": cloth_size,
            "fold_count": 0,
            "target_folds": kwargs.get("target_folds", 4),
            "fold_points": [],
            "smoothness": 1.0,
        }

    def fold(self, grasp_point: List[float], target_point: List[float],
             fold_axis: str = "x") -> TaskState:
        """Execute folding action."""
        cloth_size = self.state.data.get("cloth_size", (0.5, 0.5))
        center = [cloth_size[0] / 2, cloth_size[1] / 2]

        dx = grasp_point[0] - center[0]
        dy = grasp_point[1] - center[1]
        grasp_dist = math.sqrt(dx**2 + dy**2)

        if grasp_dist > 0.05:
            self.state.data["fold_count"] = self.state.data.get("fold_count", 0) + 1
            self.state.data["fold_points"].append({
                "grasp": grasp_point,
                "target": target_point,
                "axis": fold_axis,
            })

            smoothness = self.state.data.get("smoothness", 1.0)
            self.state.data["smoothness"] = smoothness * 0.95

        target_folds = self.state.data.get("target_folds", 4)
        current_folds = self.state.data.get("fold_count", 0)
        self.state.progress = min(1.0, current_folds / target_folds)

        if current_folds >= target_folds and self.state.data.get("smoothness", 0) > 0.5:
            self.state.success = True

        self.state.step += 1
        return self.state


class ManipulationController:
    """Unified manipulation controller."""

    def __init__(self):
        self.assembly = AssemblyTask()
        self.cutting = CuttingTask()
        self.pouring = PouringTask()
        self.folding = FoldingTask()
        self.current_task = None
        self.logger = structlog.get_logger(component="manipulation")

    def start_task(self, task_type: str, **kwargs):
        if task_type == "assembly":
            self.current_task = self.assembly
            self.assembly.setup(**kwargs)
        elif task_type == "cutting":
            self.current_task = self.cutting
            self.cutting.setup(**kwargs)
        elif task_type == "pouring":
            self.current_task = self.pouring
            self.pouring.setup(**kwargs)
        elif task_type == "folding":
            self.current_task = self.folding
            self.folding.setup(**kwargs)

    def execute(self, **kwargs) -> TaskState:
        if self.current_task == self.assembly:
            return self.assembly.insert(
                kwargs.get("peg_pos", [0, 0, 0]),
                kwargs.get("hole_pos", [0.5, 0, 0]),
                kwargs.get("force", 1.0))
        elif self.current_task == self.cutting:
            return self.cutting.cut(
                kwargs.get("tool_pos", [0, 0, 0]),
                kwargs.get("force", 1.0),
                kwargs.get("sharpness", 0.8))
        elif self.current_task == self.pouring:
            return self.pouring.pour(
                kwargs.get("source_pos", [0, 0, 1]),
                kwargs.get("target_pos", [0.5, 0, 0]),
                kwargs.get("angle", 45),
                kwargs.get("flow_rate", 0.5))
        elif self.current_task == self.folding:
            return self.folding.fold(
                kwargs.get("grasp_point", [0.25, 0, 0]),
                kwargs.get("target_point", [0.25, 0.5, 0]),
                kwargs.get("fold_axis", "x"))
        return TaskState()

    def to_context(self) -> str:
        task_name = "none"
        if self.current_task == self.assembly:
            task_name = "assembly"
        elif self.current_task == self.cutting:
            task_name = "cutting"
        elif self.current_task == self.pouring:
            task_name = "pouring"
        elif self.current_task == self.folding:
            task_name = "folding"
        return f"Manipulation: {task_name}"
