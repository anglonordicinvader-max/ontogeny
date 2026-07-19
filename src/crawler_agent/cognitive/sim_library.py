"""Simulation library with common scenarios and fallback backends.

Provides pre-built simulation scenarios for mechanical, robotic, and physics
use cases. Supports Blender (primary), PyBullet, and MuJoCo as backends.
Preserves the existing Blender grounding system.
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from enum import Enum, StrEnum
from typing import Any, Dict, List, Optional

import structlog

from .blender_sandbox import (
    BlenderSandbox,
    ExportFormat,
    ObjectSpec,
    PhysicsConfig,
    SensorConfig,
    SimulationResult,
    SimulationSpec,
    SimulationType,
)

logger = structlog.get_logger()


class SimBackend(StrEnum):
    BLENDER = "blender"
    PYBULLET = "pybullet"
    MUJOCO = "mujoco"


@dataclass
class ScenarioSpec:
    """A pre-built simulation scenario."""

    name: str
    description: str
    category: str  # mechanical, robotic, physics, emotion
    backend: SimBackend = SimBackend.BLENDER
    spec: SimulationSpec = field(default_factory=SimulationSpec)
    tags: list[str] = field(default_factory=list)
    difficulty: str = "medium"  # easy, medium, hard


class PyBulletBackend:
    """PyBullet simulation backend as fallback when Blender is unavailable."""

    def __init__(self):
        self.logger = logger.bind(backend="pybullet")
        self._available = False
        self._init_pybullet()

    def _init_pybullet(self):
        try:
            import pybullet
            import pybullet_data

            self._pybullet = pybullet
            self._available = True
            self.logger.info("pybullet_available")
        except ImportError:
            self.logger.info("pybullet_not_available")

    @property
    def is_available(self) -> bool:
        return self._available

    async def run_simulation(self, spec: SimulationSpec) -> SimulationResult:
        if not self._available:
            return SimulationResult(success=False, error="PyBullet not available")
        start = time.perf_counter()
        try:
            self._pybullet.connect(self._pybullet.DIRECT)
            self._pybullet.setAdditionalSearchPath(self._pybullet_data.getDataPath())
            self._pybullet.setGravity(*spec.gravity)
            self._pybullet.setTimeStep(1.0 / spec.fps)

            # Ground plane
            if spec.ground:
                self._pybullet.loadURDF("plane.urdf")

            # Add objects
            object_ids = []
            for _i, obj in enumerate(spec.objects):
                if obj.type == "cube":
                    half_extents = [s / 2 for s in obj.scale]
                    col_id = self._pybullet.createCollisionShape(
                        self._pybullet.GEOM_BOX, halfExtents=half_extents
                    )
                    vis_id = self._pybullet.createVisualShape(
                        self._pybullet.GEOM_BOX,
                        halfExtents=half_extents,
                        rgbaColor=[0.5, 0.5, 1.0, 1.0],
                    )
                elif obj.type == "sphere":
                    radius = obj.scale[0] / 2
                    col_id = self._pybullet.createCollisionShape(
                        self._pybullet.GEOM_SPHERE, radius=radius
                    )
                    vis_id = self._pybullet.createVisualShape(
                        self._pybullet.GEOM_SPHERE, radius=radius, rgbaColor=[1.0, 0.5, 0.5, 1.0]
                    )
                else:
                    col_id = self._pybullet.createCollisionShape(
                        self._pybullet.GEOM_BOX, halfExtents=[0.5, 0.5, 0.5]
                    )
                    vis_id = self._pybullet.createVisualShape(
                        self._pybullet.GEOM_BOX,
                        halfExtents=[0.5, 0.5, 0.5],
                        rgbaColor=[0.5, 1.0, 0.5, 1.0],
                    )

                mass = 0 if obj.passive else obj.mass
                obj_id = self._pybullet.createMultiBody(
                    baseMass=mass,
                    baseCollisionShapeIndex=col_id,
                    baseVisualShapeIndex=vis_id,
                    basePosition=obj.position,
                    baseOrientation=self._pybullet.getQuaternionFromEuler(obj.rotation),
                )
                object_ids.append(obj_id)

            # Simulate
            frames = []
            num_steps = int(spec.duration * spec.fps)
            for step in range(num_steps):
                self._pybullet.stepSimulation()
                if step % 10 == 0:
                    frame_data = {"frame": step, "objects": []}
                    for j, obj_id in enumerate(object_ids):
                        pos, orn = self._pybullet.getBasePositionAndOrientation(obj_id)
                        frame_data["objects"].append(
                            {
                                "name": f"Obj_{j}",
                                "position": list(pos),
                                "rotation": list(self._pybullet.getEulerFromQuaternion(orn)),
                            }
                        )
                    frames.append(frame_data)

            self._pybullet.disconnect()
            elapsed = (time.perf_counter() - start) * 1000
            return SimulationResult(
                success=True,
                frames=frames,
                execution_time_ms=elapsed,
                stats={"backend": "pybullet", "objects": len(object_ids), "steps": num_steps},
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return SimulationResult(success=False, error=str(e), execution_time_ms=elapsed)


class MuJoCoBackend:
    """MuJoCo simulation backend (requires mujoco package)."""

    def __init__(self):
        self.logger = logger.bind(backend="mujoco")
        self._available = False
        self._init_mujoco()

    def _init_mujoco(self):
        try:
            import mujoco

            self._mujoco = mujoco
            self._available = True
            self.logger.info("mujoco_available")
        except ImportError:
            self.logger.info("mujoco_not_available")

    @property
    def is_available(self) -> bool:
        return self._available

    async def run_simulation(self, spec: SimulationSpec) -> SimulationResult:
        if not self._available:
            return SimulationResult(success=False, error="MuJoCo not available")
        # MuJoCo requires XML model files - generate a simple one
        start = time.perf_counter()
        try:
            import os
            import tempfile

            # Generate simple MuJoCo XML
            xml_parts = ['<mujoco model="ontogeny_sim">']
            xml_parts.append(
                '  <option gravity="{} {} {}" timestep="{}"/>'.format(*spec.gravity, 1.0 / spec.fps)
            )
            xml_parts.append("  <worldbody>")
            if spec.ground:
                xml_parts.append('    <geom name="ground" type="plane" size="50 50 0.1"/>')
            for i, obj in enumerate(spec.objects):
                pos = " ".join(str(x) for x in obj.position)
                if obj.type == "cube":
                    size = " ".join(str(s / 2) for s in obj.scale)
                    xml_parts.append(
                        f'    <geom name="obj_{i}" type="box" size="{size}" pos="{pos}" mass="{obj.mass}"/>'
                    )
                elif obj.type == "sphere":
                    radius = obj.scale[0] / 2
                    xml_parts.append(
                        f'    <geom name="obj_{i}" type="sphere" size="{radius}" pos="{pos}" mass="{obj.mass}"/>'
                    )
            xml_parts.append("  </worldbody>")
            xml_parts.append("</mujoco>")

            xml_content = "\n".join(xml_parts)
            with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
                f.write(xml_content)
                model_path = f.name

            model = self._mujoco.MjModel.from_xml_path(model_path)
            data = self._mujoco.MjData(model)
            self._mujoco.MjRenderContextOffscreen(model)

            # Simulate
            frames = []
            num_steps = int(spec.duration * spec.fps)
            for step in range(num_steps):
                self._mujoco.mj_step(model, data)
                if step % 10 == 0:
                    frame_data = {"frame": step, "objects": []}
                    for i in range(model.ngeom):
                        geom = model.geom(i)
                        pos = data.geom_xpos[i].tolist()
                        frame_data["objects"].append(
                            {
                                "name": geom.name,
                                "position": pos,
                            }
                        )
                    frames.append(frame_data)

            os.unlink(model_path)
            elapsed = (time.perf_counter() - start) * 1000
            return SimulationResult(
                success=True,
                frames=frames,
                execution_time_ms=elapsed,
                stats={"backend": "mujoco", "objects": model.ngeom, "steps": num_steps},
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return SimulationResult(success=False, error=str(e), execution_time_ms=elapsed)


# Pre-built simulation scenarios
SIMULATION_SCENARIOS: dict[str, ScenarioSpec] = {
    # Mechanical scenarios
    "pendulum": ScenarioSpec(
        name="pendulum",
        description="Simple pendulum swing with gravity",
        category="mechanical",
        tags=["gravity", "oscillation", "basic"],
        difficulty="easy",
        spec=SimulationSpec(
            type=SimulationType.RIGID_BODY,
            objects=[
                ObjectSpec(type="cylinder", position=(0, 0, 5), scale=(0.1, 0.1, 2), mass=1.0),
                ObjectSpec(type="sphere", position=(0, 0, 6), scale=(0.3, 0.3, 0.3), mass=0.5),
            ],
            duration=5.0,
            fps=60,
        ),
    ),
    "spring_mass": ScenarioSpec(
        name="spring_mass",
        description="Mass-spring system with damping",
        category="mechanical",
        tags=["spring", "oscillation", "damping"],
        difficulty="easy",
        spec=SimulationSpec(
            type=SimulationType.SOFT_BODY,
            objects=[
                ObjectSpec(
                    type="cube", position=(0, 0, 5), scale=(1, 1, 1), mass=2.0, soft_body=True
                ),
            ],
            duration=10.0,
            fps=60,
        ),
    ),
    "gears": ScenarioSpec(
        name="gears",
        description="Interlocking gear mechanism",
        category="mechanical",
        tags=["rotation", "transmission", "mechanical"],
        difficulty="medium",
        spec=SimulationSpec(
            type=SimulationType.RIGID_BODY,
            objects=[
                ObjectSpec(type="cylinder", position=(0, 0, 2), scale=(1, 1, 0.3), mass=5.0),
                ObjectSpec(type="cylinder", position=(1.5, 0, 2), scale=(0.7, 0.7, 0.3), mass=3.0),
            ],
            duration=5.0,
            fps=60,
        ),
    ),
    # Robotic scenarios
    "robot_arm_reach": ScenarioSpec(
        name="robot_arm_reach",
        description="Robot arm reaching for target object",
        category="robotic",
        tags=["manipulation", "reach", "inverse_kinematics"],
        difficulty="hard",
        spec=SimulationSpec(
            type=SimulationType.RIGID_BODY,
            objects=[
                ObjectSpec(
                    type="cylinder",
                    position=(0, 0, 0.5),
                    scale=(0.3, 0.3, 1),
                    mass=10.0,
                    passive=True,
                ),
                ObjectSpec(type="cylinder", position=(0, 0, 1.5), scale=(0.2, 0.2, 1), mass=2.0),
                ObjectSpec(
                    type="cylinder", position=(0, 0, 2.5), scale=(0.15, 0.15, 0.8), mass=1.0
                ),
                ObjectSpec(type="sphere", position=(1, 1, 1), scale=(0.2, 0.2, 0.2), mass=0.5),
            ],
            duration=10.0,
            fps=60,
        ),
    ),
    "quadruped_walk": ScenarioSpec(
        name="quadruped_walk",
        description="Four-legged robot walking gait",
        category="robotic",
        tags=["locomotion", "gait", "walking"],
        difficulty="hard",
        spec=SimulationSpec(
            type=SimulationType.RIGID_BODY,
            objects=[
                ObjectSpec(type="cube", position=(0, 0, 1), scale=(1, 0.6, 0.4), mass=5.0),
                ObjectSpec(
                    type="cylinder", position=(-0.3, -0.2, 0.3), scale=(0.1, 0.1, 0.5), mass=0.5
                ),
                ObjectSpec(
                    type="cylinder", position=(0.3, -0.2, 0.3), scale=(0.1, 0.1, 0.5), mass=0.5
                ),
                ObjectSpec(
                    type="cylinder", position=(-0.3, 0.2, 0.3), scale=(0.1, 0.1, 0.5), mass=0.5
                ),
                ObjectSpec(
                    type="cylinder", position=(0.3, 0.2, 0.3), scale=(0.1, 0.1, 0.5), mass=0.5
                ),
            ],
            duration=10.0,
            fps=60,
        ),
    ),
    "humanoid_balance": ScenarioSpec(
        name="humanoid_balance",
        description="Humanoid robot maintaining balance on uneven terrain",
        category="robotic",
        tags=["balance", "humanoid", "stability"],
        difficulty="hard",
        spec=SimulationSpec(
            type=SimulationType.RIGID_BODY,
            objects=[
                ObjectSpec(type="cube", position=(0, 0, 1.5), scale=(0.4, 0.3, 0.8), mass=10.0),
                ObjectSpec(type="sphere", position=(0, 0, 2.2), scale=(0.3, 0.3, 0.3), mass=3.0),
                ObjectSpec(
                    type="cylinder", position=(-0.15, 0, 0.5), scale=(0.1, 0.1, 0.8), mass=2.0
                ),
                ObjectSpec(
                    type="cylinder", position=(0.15, 0, 0.5), scale=(0.1, 0.1, 0.8), mass=2.0
                ),
            ],
            duration=10.0,
            fps=60,
        ),
    ),
    # Physics scenarios
    "fluid_dam": ScenarioSpec(
        name="fluid_dam",
        description="Fluid dynamics - water behind a dam",
        category="physics",
        tags=["fluid", "hydrodynamics", "dam"],
        difficulty="medium",
        spec=SimulationSpec(
            type=SimulationType.FLUID,
            objects=[
                ObjectSpec(
                    type="cube", position=(0, 0, 0.5), scale=(5, 5, 1), mass=100.0, passive=True
                ),
                ObjectSpec(
                    type="cube", position=(2, 0, 1), scale=(0.2, 5, 2), mass=50.0, passive=True
                ),
                ObjectSpec(
                    type="cube", position=(-1, 0, 2), scale=(3, 3, 0.5), mass=10.0, fluid=True
                ),
            ],
            duration=5.0,
            fps=60,
        ),
    ),
    "cloth_drape": ScenarioSpec(
        name="cloth_drape",
        description="Cloth draping over a sphere",
        category="physics",
        tags=["cloth", "deformation", "draping"],
        difficulty="medium",
        spec=SimulationSpec(
            type=SimulationType.CLOTH,
            objects=[
                ObjectSpec(
                    type="sphere", position=(0, 0, 2), scale=(1, 1, 1), mass=5.0, passive=True
                ),
                ObjectSpec(type="plane", position=(0, 0, 4), scale=(3, 3, 1), mass=0.5, cloth=True),
            ],
            duration=5.0,
            fps=60,
        ),
    ),
    "particle_fountain": ScenarioSpec(
        name="particle_fountain",
        description="Particle fountain with gravity",
        category="physics",
        tags=["particles", "fountain", "gravity"],
        difficulty="easy",
        spec=SimulationSpec(
            type=SimulationType.PARTICLES,
            objects=[
                ObjectSpec(
                    type="cone", position=(0, 0, 0), scale=(0.5, 0.5, 1), mass=1.0, passive=True
                ),
            ],
            duration=5.0,
            fps=60,
        ),
    ),
    "collision_domino": ScenarioSpec(
        name="collision_domino",
        description="Domino chain reaction collision",
        category="physics",
        tags=["collision", "chain_reaction", "domino"],
        difficulty="medium",
        spec=SimulationSpec(
            type=SimulationType.RIGID_BODY,
            objects=[
                ObjectSpec(type="cube", position=(i * 0.5, 0, 1), scale=(0.1, 0.3, 1.5), mass=0.5)
                for i in range(10)
            ]
            + [
                ObjectSpec(type="sphere", position=(-1, 0, 1.5), scale=(0.3, 0.3, 0.3), mass=2.0),
            ],
            duration=5.0,
            fps=60,
        ),
    ),
    # Emotion visualization scenarios
    "emotion_happy": ScenarioSpec(
        name="emotion_happy",
        description="Happy emotion visualization (anatomy mode)",
        category="emotion",
        tags=["emotion", "happy", "anatomy"],
        difficulty="easy",
        spec=SimulationSpec(
            type=SimulationType.EMOTION,
            emotion_config={"mood": "happy", "valence": 0.8, "arousal": 0.7},
            emotion_visualizer="anatomy",
            duration=5.0,
        ),
    ),
    "emotion_sad": ScenarioSpec(
        name="emotion_sad",
        description="Sad emotion visualization (sphere mode)",
        category="emotion",
        tags=["emotion", "sad", "sphere"],
        difficulty="easy",
        spec=SimulationSpec(
            type=SimulationType.EMOTION,
            emotion_config={"mood": "sad", "valence": -0.7, "arousal": 0.3},
            emotion_visualizer="sphere",
            duration=5.0,
        ),
    ),
    "emotion_angry": ScenarioSpec(
        name="emotion_angry",
        description="Angry emotion visualization (both modes)",
        category="emotion",
        tags=["emotion", "angry", "both"],
        difficulty="easy",
        spec=SimulationSpec(
            type=SimulationType.EMOTION,
            emotion_config={"mood": "angry", "valence": -0.9, "arousal": 0.9},
            emotion_visualizer="both",
            duration=5.0,
        ),
    ),
}


class SimulationLibrary:
    """Library of pre-built simulation scenarios with multi-backend support."""

    def __init__(self, blender_sandbox: BlenderSandbox | None = None):
        self.blender = blender_sandbox
        self.pybullet = PyBulletBackend()
        self.mujoco = MuJoCoBackend()
        self.scenarios = dict(SIMULATION_SCENARIOS)
        self.logger = logger.bind(component="sim_library")

    def list_scenarios(self, category: str | None = None) -> list[dict]:
        scenarios = []
        for _key, scenario in self.scenarios.items():
            if category and scenario.category != category:
                continue
            scenarios.append(
                {
                    "name": scenario.name,
                    "description": scenario.description,
                    "category": scenario.category,
                    "backend": scenario.backend.value,
                    "tags": scenario.tags,
                    "difficulty": scenario.difficulty,
                }
            )
        return scenarios

    def get_scenario(self, name: str) -> ScenarioSpec | None:
        return self.scenarios.get(name)

    def add_scenario(self, scenario: ScenarioSpec):
        self.scenarios[scenario.name] = scenario

    async def run_scenario(
        self,
        name: str,
        backend: SimBackend | None = None,
        modifications: dict | None = None,
    ) -> SimulationResult:
        scenario = self.scenarios.get(name)
        if not scenario:
            return SimulationResult(success=False, error=f"Scenario '{name}' not found")

        spec = scenario.spec
        if modifications:
            for key, value in modifications.items():
                if hasattr(spec, key):
                    setattr(spec, key, value)

        chosen_backend = backend or scenario.backend

        if chosen_backend == SimBackend.BLENDER:
            if self.blender:
                return await self.blender.run_simulation(spec)
            # Fallback to PyBullet
            self.logger.info("blender_unavailable_fallback", fallback="pybullet")
            chosen_backend = SimBackend.PYBULLET

        if chosen_backend == SimBackend.PYBULLET:
            if self.pybullet.is_available:
                return await self.pybullet.run_simulation(spec)
            # Fallback to MuJoCo
            self.logger.info("pybullet_unavailable_fallback", fallback="mujoco")
            chosen_backend = SimBackend.MUJOCO

        if chosen_backend == SimBackend.MUJOCO:
            if self.mujoco.is_available:
                return await self.mujoco.run_simulation(spec)
            return SimulationResult(success=False, error="No simulation backend available")

        return SimulationResult(success=False, error="No simulation backend available")

    async def run_custom(
        self,
        spec: SimulationSpec,
        backend: SimBackend = SimBackend.BLENDER,
    ) -> SimulationResult:
        if backend == SimBackend.BLENDER:
            if self.blender:
                return await self.blender.run_simulation(spec)
            self.logger.info("blender_unavailable_fallback", fallback="pybullet")
            backend = SimBackend.PYBULLET

        if backend == SimBackend.PYBULLET:
            if self.pybullet.is_available:
                return await self.pybullet.run_simulation(spec)
            backend = SimBackend.MUJOCO

        if backend == SimBackend.MUJOCO:
            if self.mujoco.is_available:
                return await self.mujoco.run_simulation(spec)

        return SimulationResult(success=False, error="No simulation backend available")

    def get_backend_status(self) -> dict[str, bool]:
        return {
            "blender": self.blender is not None,
            "pybullet": self.pybullet.is_available,
            "mujoco": self.mujoco.is_available,
        }
