"""Full anatomy mode - humanoid robot body with IK, muscles, grasp, collision.

Provides:
- Inverse kinematics for 7-DOF arm
- Muscle force simulation
- Grasp planning and execution
- Collision detection
- Joint limits and constraints
- Physics-aware planning
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import structlog


class JointType(Enum):
    REVOLUTE = "revolute"
    PRISMATIC = "prismatic"


class LimbType(Enum):
    ARM = "arm"
    LEG = "leg"
    HAND = "hand"
    TORSO = "torso"
    HEAD = "head"


@dataclass
class Joint:
    name: str
    joint_type: JointType
    limb_type: LimbType
    axis: List[float]
    lower_limit: float
    upper_limit: float
    max_torque: float
    current_angle: float = 0.0

    def is_within_limits(self, angle: float) -> bool:
        return self.lower_limit <= angle <= self.upper_limit


@dataclass
class Link:
    name: str
    length: float
    joint: Joint
    parent: Optional[str] = None


@dataclass
class IKSolution:
    joint_angles: Dict[str, float]
    position_error: float
    iterations: int
    converged: bool


@dataclass
class GraspPlan:
    approach_direction: List[float]
    grasp_width: float
    force_newtons: float
    joint_angles: Dict[str, float]
    confidence: float


@dataclass
class CollisionInfo:
    object_a: str
    object_b: str
    contact_point: List[float]
    contact_normal: List[float]
    penetration_depth: float


class AnatomyMode:
    """Full humanoid anatomy with IK, muscles, and physics."""

    def __init__(self):
        self.logger = structlog.get_logger(component="anatomy_mode")
        self.joints: Dict[str, Joint] = {}
        self.links: Dict[str, Link] = {}
        self.muscles: Dict[str, Dict] = {}
        self.collision_pairs: List[CollisionInfo] = []

        self._setup_robot()

    def _setup_robot(self):
        """Setup 7-DOF robotic arm + 5-finger hand."""
        self.joints = {
            # 7-DOF Arm (shoulder to wrist)
            "shoulder_pitch": Joint("shoulder_pitch", JointType.REVOLUTE, LimbType.ARM,
                                   [0, 1, 0], -3.14, 3.14, 50.0),
            "shoulder_roll": Joint("shoulder_roll", JointType.REVOLUTE, LimbType.ARM,
                                  [1, 0, 0], -1.57, 1.57, 50.0),
            "shoulder_yaw": Joint("shoulder_yaw", JointType.REVOLUTE, LimbType.ARM,
                                 [0, 0, 1], -3.14, 3.14, 30.0),
            "elbow_pitch": Joint("elbow_pitch", JointType.REVOLUTE, LimbType.ARM,
                                [0, 1, 0], 0, 2.35, 40.0),
            "elbow_roll": Joint("elbow_roll", JointType.REVOLUTE, LimbType.ARM,
                               [1, 0, 0], -1.57, 1.57, 20.0),
            "wrist_pitch": Joint("wrist_pitch", JointType.REVOLUTE, LimbType.ARM,
                                [0, 1, 0], -1.57, 1.57, 10.0),
            "wrist_yaw": Joint("wrist_yaw", JointType.REVOLUTE, LimbType.ARM,
                              [0, 0, 1], -3.14, 3.14, 10.0),
            # 5-Finger Hand
            "thumb_oppose": Joint("thumb_oppose", JointType.REVOLUTE, LimbType.HAND,
                                 [0, 0, 1], -0.5, 1.5, 5.0),
            "thumb_flex": Joint("thumb_flex", JointType.REVOLUTE, LimbType.HAND,
                               [0, 1, 0], 0, 1.57, 5.0),
            "index_flex": Joint("index_flex", JointType.REVOLUTE, LimbType.HAND,
                               [0, 1, 0], 0, 1.57, 3.0),
            "middle_flex": Joint("middle_flex", JointType.REVOLUTE, LimbType.HAND,
                                [0, 1, 0], 0, 1.57, 3.0),
            "ring_flex": Joint("ring_flex", JointType.REVOLUTE, LimbType.HAND,
                              [0, 1, 0], 0, 1.57, 2.0),
            "pinky_flex": Joint("pinky_flex", JointType.REVOLUTE, LimbType.HAND,
                               [0, 1, 0], 0, 1.57, 2.0),
        }

        self.links = {
            "upper_arm": Link("upper_arm", 0.3, self.joints["elbow_pitch"], "shoulder"),
            "forearm": Link("forearm", 0.25, self.joints["wrist_pitch"], "upper_arm"),
            "hand": Link("hand", 0.1, self.joints["index_flex"], "forearm"),
        }

        self.muscles = {
            "biceps": {"joint": "elbow_pitch", "max_force": 100, "side": "flexor"},
            "triceps": {"joint": "elbow_pitch", "max_force": 80, "side": "extensor"},
            "deltoid": {"joint": "shoulder_pitch", "max_force": 120, "side": "flexor"},
            "rotator_cuff": {"joint": "shoulder_roll", "max_force": 60, "side": "stabilizer"},
        }

    def solve_ik(
        self,
        target_position: List[float],
        seed_angles: Optional[Dict[str, float]] = None,
        max_iterations: int = 100,
        tolerance: float = 0.001,
    ) -> IKSolution:
        """Solve inverse kinematics using Jacobian transpose method."""
        if seed_angles is None:
            seed_angles = {}
            for name, joint in self.joints.items():
                if joint.limb_type == LimbType.ARM:
                    seed_angles[name] = (joint.lower_limit + joint.upper_limit) / 2

        current_angles = dict(seed_angles)

        for iteration in range(max_iterations):
            current_pos = self._forward_kinematics(current_angles)
            error = [target_position[i] - current_pos[i] for i in range(3)]
            error_magnitude = math.sqrt(sum(e**2 for e in error))

            if error_magnitude < tolerance:
                return IKSolution(
                    joint_angles=current_angles,
                    position_error=error_magnitude,
                    iterations=iteration,
                    converged=True,
                )

            jacobian = self._compute_jacobian(current_angles)
            alpha = 0.1
            for i, joint_name in enumerate(["shoulder_pitch", "shoulder_roll", "shoulder_yaw",
                                            "elbow_pitch", "elbow_roll", "wrist_pitch", "wrist_yaw"]):
                if joint_name in current_angles:
                    update = sum(jacobian[i][j] * error[j] for j in range(3)) * alpha
                    current_angles[joint_name] += update

        final_pos = self._forward_kinematics(current_angles)
        final_error = math.sqrt(sum((target_position[i] - final_pos[i])**2 for i in range(3)))

        return IKSolution(
            joint_angles=current_angles,
            position_error=final_error,
            iterations=max_iterations,
            converged=False,
        )

    def _forward_kinematics(self, angles: Dict[str, float]) -> List[float]:
        """Simple forward kinematics (sum of joint contributions)."""
        x = 0.0
        y = 0.0
        z = 0.0
        z += self.links["upper_arm"].length * math.sin(angles.get("shoulder_pitch", 0))
        z += self.links["forearm"].length * math.sin(angles.get("elbow_pitch", 0))
        x += self.links["upper_arm"].length * math.cos(angles.get("shoulder_pitch", 0)) * math.sin(angles.get("shoulder_roll", 0))
        y += self.links["upper_arm"].length * math.cos(angles.get("shoulder_pitch", 0)) * math.cos(angles.get("shoulder_roll", 0))
        return [x, y, z]

    def _compute_jacobian(self, angles: Dict[str, float]) -> List[List[float]]:
        """Compute approximate Jacobian matrix."""
        eps = 0.01
        jacobian = []
        for joint_name in ["shoulder_pitch", "shoulder_roll", "shoulder_yaw",
                          "elbow_pitch", "elbow_roll", "wrist_pitch", "wrist_yaw"]:
            if joint_name in angles:
                angles_plus = dict(angles)
                angles_plus[joint_name] += eps
                pos = self._forward_kinematics(angles)
                pos_plus = self._forward_kinematics(angles_plus)
                row = [(pos_plus[i] - pos[i]) / eps for i in range(3)]
                jacobian.append(row)
            else:
                jacobian.append([0, 0, 0])
        return jacobian

    def plan_grasp(
        self,
        object_position: List[float],
        object_size: float = 0.05,
        approach_from: str = "side",
    ) -> GraspPlan:
        """Plan a grasp for an object."""
        if approach_from == "side":
            approach_dir = [-1, 0, 0]
            pre_grasp_pos = [object_position[0] - 0.1, object_position[1], object_position[2]]
        elif approach_from == "top":
            approach_dir = [0, 0, -1]
            pre_grasp_pos = [object_position[0], object_position[1], object_position[2] + 0.1]
        else:
            approach_dir = [0, -1, 0]
            pre_grasp_pos = [object_position[0], object_position[1] - 0.1, object_position[2]]

        ik_solution = self.solve_ik(pre_grasp_pos)

        grasp_width = object_size * 1.2
        force = min(20.0, object_size * 50)

        return GraspPlan(
            approach_direction=approach_dir,
            grasp_width=grasp_width,
            force_newtons=force,
            joint_angles=ik_solution.joint_angles,
            confidence=0.8 if ik_solution.converged else 0.4,
        )

    def check_joint_limits(self, angles: Dict[str, float]) -> List[str]:
        """Check for joint limit violations."""
        violations = []
        for joint_name, angle in angles.items():
            if joint_name in self.joints:
                if not self.joints[joint_name].is_within_limits(angle):
                    violations.append(f"{joint_name}: {angle:.3f} out of range "
                                    f"[{self.joints[joint_name].lower_limit:.3f}, "
                                    f"{self.joints[joint_name].upper_limit:.3f}]")
        return violations

    def compute_muscle_forces(self, joint_angles: Dict[str, float]) -> Dict[str, float]:
        """Compute approximate muscle forces for given joint angles."""
        forces = {}
        for muscle_name, muscle in self.muscles.items():
            joint_name = muscle["joint"]
            if joint_name in joint_angles:
                angle = joint_angles[joint_name]
                normalized = (angle - self.joints[joint_name].lower_limit) / \
                            (self.joints[joint_name].upper_limit - self.joints[joint_name].lower_limit)
                if muscle["side"] == "flexor":
                    force = muscle["max_force"] * (1 - normalized)
                elif muscle["side"] == "extensor":
                    force = muscle["max_force"] * normalized
                else:
                    force = muscle["max_force"] * 0.5
                forces[muscle_name] = force
        return forces

    def detect_collisions(
        self,
        object_positions: Dict[str, List[float]],
        object_radii: Dict[str, float],
    ) -> List[CollisionInfo]:
        """Simple sphere-sphere collision detection."""
        collisions = []
        objects = list(object_positions.keys())
        for i in range(len(objects)):
            for j in range(i + 1, len(objects)):
                obj_a = objects[i]
                obj_b = objects[j]
                pos_a = object_positions[obj_a]
                pos_b = object_positions[obj_b]
                r_a = object_radii.get(obj_a, 0.05)
                r_b = object_radii.get(obj_b, 0.05)

                dist = math.sqrt(sum((pos_a[k] - pos_b[k])**2 for k in range(3)))
                min_dist = r_a + r_b

                if dist < min_dist:
                    normal = [(pos_a[k] - pos_b[k]) / max(dist, 0.001) for k in range(3)]
                    contact = [(pos_a[k] + pos_b[k]) / 2 for k in range(3)]
                    collisions.append(CollisionInfo(
                        object_a=obj_a,
                        object_b=obj_b,
                        contact_point=contact,
                        contact_normal=normal,
                        penetration_depth=min_dist - dist,
                    ))
        return collisions

    def to_context(self) -> str:
        return (f"Anatomy: {len(self.joints)} joints ({sum(1 for j in self.joints.values() if j.limb_type == LimbType.ARM)} arm, "
                f"{sum(1 for j in self.joints.values() if j.limb_type == LimbType.HAND)} hand), "
                f"{len(self.muscles)} muscles, {len(self.links)} links")
