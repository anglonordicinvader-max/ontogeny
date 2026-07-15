"""Blender Sandbox - Physics simulation and rendering for grounded verification.

Features:
- Rigid/soft body, fluid, cloth, particle physics
- Sensor simulation (camera, lidar, contact, IMU)
- URDF import + joint control for robotics
- Domain randomization (lighting, textures, physics params)
- Scene persistence (load/modify .blend)
- Real-time physics stepping with callbacks
- Multi-format export (USD, glTF, OBJ, glb, STL, PLY, Alembic)
- Procedural generation (terrain, buildings, clutter)
- Domain randomization (lighting, textures, physics params)
- Multi-format export (USD, glTF, OBJ, glb)
- Emotion visualization: sphere (abstract proto-AGI) or anatomy (humanoid robot body with face)
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Awaitable
from enum import Enum

import docker
import structlog

logger = structlog.get_logger()


class SimulationType(Enum):
    RIGID_BODY = "rigid_body"
    SOFT_BODY = "soft_body"
    FLUID = "fluid"
    CLOTH = "cloth"
    PARTICLES = "particles"
    RENDER = "render"
    URDF_ROBOT = "urdf_robot"
    SENSOR = "sensor"
    EMOTION = "emotion"


class ExportFormat(Enum):
    USD = "usd"
    GLTF = "gltf"
    GLB = "glb"
    OBJ = "obj"
    STL = "stl"
    PLY = "ply"
    ALEMBIC = "abc"


@dataclass
class PhysicsConfig:
    """Physics engine configuration."""
    substeps: int = 1
    solver_iterations: int = 20
    time_scale: float = 1.0
    friction: float = 0.5
    restitution: float = 0.3
    collision_margin: float = 0.01
    soft_body_goal_strength: float = 0.5
    soft_body_self_collision: bool = True
    fluid_resolution: int = 64
    fluid_viscosity: float = 0.01
    cloth_bending_stiffness: float = 0.5
    cloth_damping: float = 0.1


@dataclass
class SensorConfig:
    """Sensor simulation configuration."""
    type: str  # camera, lidar, contact, imu, depth
    position: tuple = (0, 0, 0)
    rotation: tuple = (0, 0, 0)
    resolution: tuple = (640, 480)
    fov: float = 60.0
    range_min: float = 0.1
    range_max: float = 100.0
    update_rate: int = 30


@dataclass
class DomainRandomizationConfig:
    """Domain randomization configuration."""
    randomize_lighting: bool = True
    randomize_textures: bool = True
    randomize_physics_params: bool = True
    randomize_object_poses: bool = True
    randomize_camera: bool = True
    lighting_variance: float = 0.3
    texture_variance: float = 0.2
    physics_variance: float = 0.15
    pose_variance: float = 0.1


@dataclass
class ProceduralConfig:
    """Procedural generation configuration."""
    generate_terrain: bool = False
    terrain_size: tuple = (100, 100)
    terrain_octaves: int = 6
    terrain_scale: float = 1.0
    generate_buildings: bool = False
    building_count: int = 10
    building_height_range: tuple = (5, 50)
    generate_clutter: bool = False
    clutter_count: int = 100
    clutter_types: list = field(default_factory=lambda: ["cube", "sphere", "cylinder"])


@dataclass
class RobotConfig:
    """URDF robot configuration."""
    urdf_path: str = ""
    base_position: tuple = (0, 0, 0)
    base_rotation: tuple = (0, 0, 0)
    joint_drives: Dict[str, Dict] = field(default_factory=dict)


@dataclass
class ObjectSpec:
    """Object specification for simulation."""
    type: str = "cube"
    position: tuple = (0, 0, 5)
    rotation: tuple = (0, 0, 0)
    scale: tuple = (1, 1, 1)
    mass: float = 1.0
    passive: bool = False
    friction: float = 0.5
    restitution: float = 0.3
    soft_body: bool = False
    cloth: bool = False
    fluid: bool = False
    urdf_path: Optional[str] = None
    joint_config: Optional[Dict] = None


@dataclass
class RobotConfig:
    """URDF robot configuration."""
    urdf_path: str = ""
    base_position: tuple = (0, 0, 0)
    base_rotation: tuple = (0, 0, 0)
    joint_drives: Dict[str, Dict] = field(default_factory=dict)


@dataclass
class ObjectSpec:
    """Object specification for simulation."""
    type: str = "cube"
    position: tuple = (0, 0, 5)
    rotation: tuple = (0, 0, 0)
    scale: tuple = (1, 1, 1)
    mass: float = 1.0
    passive: bool = False
    friction: float = 0.5
    restitution: float = 0.3
    soft_body: bool = False
    cloth: bool = False
    fluid: bool = False
    urdf_path: Optional[str] = None
    joint_config: Optional[Dict] = None


@dataclass
class SimulationSpec:
    """Specification for a physics simulation."""
    type: SimulationType = SimulationType.RIGID_BODY
    objects: List[ObjectSpec] = field(default_factory=list)
    duration: float = 5.0
    fps: int = 60
    gravity: tuple = (0, 0, -9.81)
    ground: bool = True
    physics: PhysicsConfig = field(default_factory=PhysicsConfig)
    render: bool = False
    render_resolution: tuple = (1920, 1080)
    render_engine: str = "CYCLES"
    render_samples: int = 128
    output_path: str = "/workspace/output"
    load_blend: Optional[str] = None
    save_blend: Optional[str] = None
    exports: List[ExportFormat] = field(default_factory=list)
    sensors: List[SensorConfig] = field(default_factory=list)
    domain_randomization: Optional[DomainRandomizationConfig] = None
    procedural: Optional[ProceduralConfig] = None
    urdf_path: Optional[str] = None
    robot_joints: Optional[Dict] = None
    # Emotion visualization - "sphere" (abstract, proto-AGI internal) or "anatomy" (humanoid robot body with face)
    emotion_config: Optional[Dict] = None
    emotion_visualizer: Optional[str] = "sphere"  # "sphere" | "anatomy" | "both"
    # Video/Animation support
    render_animation: bool = False
    frame_start: int = 1
    frame_end: int = 250
    video_format: str = "FFMPEG"
    video_codec: str = "H264"
    video_bitrate: int = 8000
    video_output_path: Optional[str] = None
    # Snippet mode - short clips of notable moments
    snippet_mode: bool = False
    snippet_duration: float = 3.0  # seconds per snippet
    snippet_max_clips: int = 5  # max clips per session


@dataclass
class SimulationResult:
    """Result of a simulation run."""
    success: bool
    output: Any = None
    error: Optional[str] = None
    frames: List[Dict] = field(default_factory=list)
    sensor_data: Dict = field(default_factory=dict)
    render_path: Optional[str] = None
    video_path: Optional[str] = None
    blend_path: Optional[str] = None
    export_paths: Dict = field(default_factory=dict)
    execution_time_ms: float = 0.0
    stats: Dict = field(default_factory=dict)


@dataclass
class VideoBudget:
    """Tracks video rendering budget to prevent large files."""
    max_total_seconds: float = 60.0  # max total video seconds per session
    max_clip_seconds: float = 5.0  # max seconds per clip
    max_clips: int = 20  # max number of clips
    bitrate_kbps: int = 8000

    # Tracking
    total_seconds_rendered: float = 0.0
    clips_rendered: int = 0
    session_start: float = field(default_factory=time.time)

    def can_render(self, duration_seconds: float) -> bool:
        """Check if we can render another clip within budget."""
        if self.clips_rendered >= self.max_clips:
            return False
        if self.total_seconds_rendered + duration_seconds > self.max_total_seconds:
            return False
        return True

    def record_render(self, duration_seconds: float):
        """Record a rendered clip."""
        self.total_seconds_rendered += duration_seconds
        self.clips_rendered += 1

    def get_stats(self) -> Dict:
        return {
            "total_seconds_rendered": self.total_seconds_rendered,
            "clips_rendered": self.clips_rendered,
            "budget_remaining": max(0, self.max_total_seconds - self.total_seconds_rendered),
            "clips_remaining": max(0, self.max_clips - self.clips_rendered),
        }


class BlenderSandbox:
    """Executes Blender Python scripts in Docker for physics simulation and rendering."""

    def __init__(
        self,
        image: str = "ontogeny-blender",
        docker_client=None,
        timeout: int = 300,
        data_dir: str = "data/blender"
    ):
        self.image = image
        self.docker = docker_client or docker.from_env()
        self.timeout = timeout
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger.bind(component="blender_sandbox")
        self.video_budget = VideoBudget()
        self._verify_image()

    def _verify_image(self):
        try:
            self.docker.images.get(self.image)
            self.logger.info("blender_image_ready", image=self.image)
        except docker.errors.ImageNotFound:
            self.logger.warning("blender_image_not_found", image=self.image)
            raise RuntimeError(
                f"Blender image '{self.image}' not found. Build with:\n"
                f"  docker build -f Dockerfile.blender -t ontogeny-blender ."
            )

    async def run_simulation(self, spec: SimulationSpec) -> SimulationResult:
        """Run a physics simulation and return results."""
        start = time.perf_counter()

        # Check video budget before rendering
        if spec.render_animation and spec.snippet_mode:
            snippet_duration = spec.snippet_duration or 3.0
            if not self.video_budget.can_render(snippet_duration):
                self.logger.info("video_budget_exceeded", budget=self.video_budget.get_stats())
                spec.render_animation = False  # Skip video, still render PNG

        try:
            script = self._build_simulation_script(spec)
            result = await self._run_blender_script(script, spec)

            exec_time = (time.perf_counter() - start) * 1000

            if result.get("success"):
                # Record video budget usage
                if spec.render_animation and result.get("video_path"):
                    snippet_duration = spec.snippet_duration if spec.snippet_mode else (spec.frame_end - spec.frame_start) / spec.fps
                    self.video_budget.record_render(snippet_duration)

                return SimulationResult(
                    success=True,
                    output=result.get("output"),
                    frames=result.get("frames", []),
                    sensor_data=result.get("sensor_data", {}),
                    render_path=result.get("render_path"),
                    video_path=result.get("video_path"),
                    blend_path=result.get("blend_path"),
                    export_paths=result.get("export_paths", {}),
                    execution_time_ms=exec_time,
                    stats=result.get("stats", {})
                )
            else:
                return SimulationResult(
                    success=False,
                    error=result.get("error", "Unknown error"),
                    execution_time_ms=exec_time
                )

        except asyncio.TimeoutError:
            return SimulationResult(
                success=False,
                error=f"Simulation timed out after {self.timeout}s",
                execution_time_ms=(time.perf_counter() - start) * 1000
            )
        except Exception as e:
            return SimulationResult(
                success=False,
                error=str(e),
                execution_time_ms=(time.perf_counter() - start) * 1000
            )

    async def run_render(self, spec: SimulationSpec) -> SimulationResult:
        """Render a scene (non-physics)."""
        spec.render = True
        return await self.run_simulation(spec)

    async def run_custom_script(self, script: str, timeout: Optional[int] = None) -> Dict:
        """Run arbitrary Blender Python script."""
        return await self._run_blender_script(script, timeout=timeout or self.timeout)

    async def step_physics(
        self,
        blend_path: str,
        steps: int = 1,
        callback: Optional[Callable[[Dict], Awaitable[None]]] = None
    ) -> Dict:
        """Step physics in an existing .blend file with optional callback."""
        script = f"""
import bpy
import json

bpy.ops.wm.open_mainfile(filepath="{blend_path}")

for i in range({steps}):
    bpy.context.scene.frame_set(bpy.context.scene.frame_current + 1)
    # Step physics
    bpy.ops.ptcache.bake_all(bake=False)  # Single step
    
    # Callback with frame data
    frame_data = {{
        "frame": bpy.context.scene.frame_current,
        "objects": []
    }}
    for obj in bpy.data.objects:
        if obj.name.startswith("SimObj_") or obj.name.startswith("Robot_"):
            frame_data["objects"].append({{
                "name": obj.name,
                "location": list(obj.location),
                "rotation": list(obj.rotation_euler),
                "velocity": list(obj.rigid_body.linear_velocity) if hasattr(obj, 'rigid_body') and obj.rigid_body else [0,0,0]
            }}
    
    print("STEP_RESULT:" + json.dumps(frame_data))
"""
        result = await self._run_blender_script(script)
        return result

    def _build_object_script(self, obj: ObjectSpec, i: int) -> str:
        """Generate Blender Python code for a single object."""
        otype = obj.type
        loc = obj.position
        rot = obj.rotation
        scale = obj.scale
        mass = obj.mass
        passive = obj.passive
        friction = obj.friction
        restitution = obj.restitution

        if obj.type == "cube":
            prim = f'bpy.ops.mesh.primitive_cube_add(location={loc})'
        elif obj.type == "sphere":
            prim = f'bpy.ops.mesh.primitive_uv_sphere_add(location={loc})'
        elif obj.type == "plane":
            prim = f'bpy.ops.mesh.primitive_plane_add(location={loc}, scale=(50, 50, 1))'
        elif obj.type == "cylinder":
            prim = f'bpy.ops.mesh.primitive_cylinder_add(location={loc})'
        elif obj.type == "cone":
            prim = f'bpy.ops.mesh.primitive_cone_add(location={loc})'
        elif obj.type == "torus":
            prim = f'bpy.ops.mesh.primitive_torus_add(location={loc})'
        else:
            prim = f'bpy.ops.mesh.primitive_cube_add(location={loc})'

        friction = obj.friction
        restitution = obj.restitution

        code = f"""
# Object {i}
{prim}
obj = bpy.context.active_object
obj.name = "SimObj_{i}"
obj.rotation_euler = {rot}
obj.scale = {scale}
bpy.ops.rigidbody.object_add()
obj.rigid_body.type = {'PASSIVE' if passive else 'ACTIVE'}
obj.rigid_body.mass = {mass}
obj.rigid_body.collision_shape = 'BOX'
obj.rigid_body.friction = {friction}
obj.rigid_body.restitution = {restitution}
"""

        # Soft body
        if obj.soft_body:
            code += f"""
# Soft body
bpy.ops.object.modifier_add(type='SOFT_BODY')
obj.modifiers["Softbody"].settings.goal_strength = 0.5
obj.modifiers["Softbody"].settings.use_self_collision = True
obj.modifiers["Softbody"].settings.friction = {friction}
"""

        # Cloth
        if obj.cloth:
            code += f"""
# Cloth
bpy.ops.object.modifier_add(type='CLOTH')
obj.modifiers["Cloth"].settings.quality = 5
obj.modifiers["Cloth"].settings.bending_stiffness = 0.5
obj.modifiers["Cloth"].settings.damping = 0.1
"""

        # Fluid
        if obj.fluid:
            code += f"""
# Fluid
bpy.ops.object.modifier_add(type='FLUID')
obj.modifiers["Fluid"].fluid_type = 'DOMAIN'
obj.modifiers["Fluid"].domain_settings.resolution = 64
obj.modifiers["Fluid"].domain_settings.viscosity = 0.01
"""

        return code

    def _build_emotion_code(self, spec: SimulationSpec) -> str:
        """Generate emotion visualization code."""
        if not spec.emotion_config:
            return ""

        ec = spec.emotion_config
        mood = ec.get("mood", "neutral")
        valence = ec.get("valence", 0.0)
        arousal = ec.get("arousal", 0.5)
        intensity = max(0.1, min(1.0, abs(valence) * 0.5 + arousal * 0.5))

        if valence < -0.3:
            base_color = (0.2, 0.3, 1.0, 1.0)
        elif valence > 0.3:
            base_color = (1.0, 0.6, 0.1, 1.0)
        else:
            base_color = (0.8, 0.8, 0.9, 1.0)

        visualizer = spec.emotion_visualizer or "sphere"

        if visualizer == "anatomy":
            return f"""
# Emotion Visualization - Anatomy Mode (Humanoid Robot Body with Face)
# Mood: {mood}, Valence: {valence:.2f}, Arousal: {arousal:.2f}, Intensity: {intensity:.2f}

# Create a simple face with shape keys for expressions
# Base head
bpy.ops.mesh.primitive_uv_sphere_add(location=(0, 0, 3), radius=1.2)
head_obj = bpy.context.active_object
head_obj.name = "EmotionHead"
head_obj.scale = (1.2, 1.0, 1.0)

# Add shape keys for facial expressions
head_obj.shape_key_add(name="Basis")
sk_brow_down = head_obj.shape_key_add(name="BrowDown")
sk_brow_up = head_obj.shape_key_add(name="BrowUp")
sk_mouth_smile = head_obj.shape_key_add(name="MouthSmile")
sk_mouth_frown = head_obj.shape_key_add(name="MouthFrown")
sk_eyes_wide = head_obj.shape_key_add(name="EyesWide")
sk_eyes_squint = head_obj.shape_key_add(name="EyesSquint")

# Create simple facial features using separate objects
# Eyes
bpy.ops.mesh.primitive_uv_sphere_add(location=(-0.3, 0.9, 3.3), radius=0.15)
left_eye = bpy.context.active_object
left_eye.name = "LeftEye"
bpy.ops.mesh.primitive_uv_sphere_add(location=(0.3, 0.9, 3.3), radius=0.15)
right_eye = bpy.context.active_object
right_eye.name = "RightEye"

# Eyebrows
bpy.ops.mesh.primitive_cube_add(location=(-0.3, 0.95, 3.4), scale=(0.25, 0.02, 0.05))
left_brow = bpy.context.active_object
left_brow.name = "LeftBrow"
bpy.ops.mesh.primitive_cube_add(location=(0.3, 0.95, 3.4), scale=(0.25, 0.02, 0.05))
right_brow = bpy.context.active_object
right_brow.name = "RightBrow"

# Mouth
bpy.ops.mesh.primitive_cube_add(location=(0, 0.6, 3.3), scale=(0.3, 0.02, 0.02))
mouth = bpy.context.active_object
mouth.name = "Mouth"

# Parent facial features to head
for obj in [left_eye, right_eye, left_brow, right_brow, mouth]:
    obj.parent = head_obj

# Head material
head_mat = bpy.data.materials.new(name="FaceMaterial")
head_mat.use_nodes = True
nodes = head_mat.node_tree.nodes
bsdf = nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs['Base Color'].default_value = (0.9, 0.75, 0.65, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.4
head_obj.data.materials.append(head_mat)

# Eye material (white)
eye_mat = bpy.data.materials.new(name="EyeMaterial")
eye_mat.use_nodes = True
nodes = eye_mat.node_tree.nodes
bsdf = nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs['Base Color'].default_value = (1, 1, 1, 1)
left_eye.data.materials.append(eye_mat)
right_eye.data.materials.append(eye_mat)

# Pupil material (black)
pupil_mat = bpy.data.materials.new(name="PupilMaterial")
pupil_mat.use_nodes = True
nodes = pupil_mat.node_tree.nodes
bsdf = nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs['Base Color'].default_value = (0.05, 0.05, 0.05, 1.0)

# Add pupils
bpy.ops.mesh.primitive_uv_sphere_add(location=(-0.3, 1.0, 3.35), radius=0.06)
left_pupil = bpy.context.active_object
left_pupil.name = "LeftPupil"
left_pupil.parent = head_obj
left_pupil.data.materials.append(pupil_mat)

bpy.ops.mesh.primitive_uv_sphere_add(location=(0.3, 1.0, 3.35), radius=0.06)
right_pupil = bpy.context.active_object
right_pupil.name = "RightPupil"
right_pupil.parent = head_obj
right_pupil.data.materials.append(pupil_mat)

# Head position and scale
head_obj.location = (0, 0, 3)
head_obj.scale = (1.0, 1.0, 1.0)

# Add a simple body for the robot/agent
# Torso
bpy.ops.mesh.primitive_cylinder_add(location=(0, 0, 1.5), radius=0.6, depth=1.5)
torso = bpy.context.active_object
torso.name = "Torso"
torso.parent = head_obj

# Torso material
torso_mat = bpy.data.materials.new(name="TorsoMaterial")
torso_mat.use_nodes = True
nodes = torso_mat.node_tree.nodes
bsdf = nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs['Base Color'].default_value = (0.9, 0.75, 0.65, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.4
torso.data.materials.append(torso_mat)

# Arms
for side, x in [("Left", -0.85), ("Right", 0.85)]:
    bpy.ops.mesh.primitive_cylinder_add(location=(x, 0, 2.0), radius=0.12, depth=1.2, rotation=(0, 1.57, 0))
    arm = bpy.context.active_object
    arm.name = f"{side}Arm"
    arm.parent = head_obj
    arm.data.materials.append(torso_mat)

# Legs
for side, x in [("Left", -0.25), ("Right", 0.25)]:
    bpy.ops.mesh.primitive_cylinder_add(location=(x, 0, 0.5), radius=0.18, depth=1.5, rotation=(0, 1.57, 0))
    leg = bpy.context.active_object
    leg.name = f"{side}Leg"
    leg.parent = head_obj
    leg.data.materials.append(torso_mat)

# Parent all to head so body moves with head
torso.parent = head_obj

# Animate based on valence/arousal
# Valence controls mouth smile/frown
if {valence} > 0.3:
    # Happy - smile
    sk_mouth_smile.value = min({valence}, 1.0)
    sk_brow_up.value = min({valence * 0.5}, 1.0)
elif {valence} < -0.3:
    # Sad/angry - frown
    sk_mouth_frown.value = min(abs({valence}), 1.0)
    sk_brow_down.value = min(abs({valence} * 0.5), 1.0)
else:
    # Neutral
    pass

# Arousal controls eye widen/squint and blink rate
if {arousal} > 0.7:
    sk_eyes_wide.value = min(({arousal} - 0.7) * 3, 1.0)
elif {arousal} < 0.3:
    sk_eyes_squint.value = min((0.3 - {arousal}) * 3, 1.0)

# Lighting based on valence
bpy.ops.object.light_add(type='SUN', location=(0, 0, 10))
sun = bpy.context.active_object
sun.name = "EmotionSun"
sun.data.energy = {max(1.0, arousal * 5.0)}
if {valence} < -0.3:
    sun.data.color = (0.3, 0.4, 1.0)
elif {valence} > 0.3:
    sun.data.color = (1.0, 0.7, 0.3)
else:
    sun.data.color = (0.9, 0.9, 1.0)

# Head position
head_obj.location = (0, 0, 3)
head_obj.rotation_euler = (0, 0, 0)

# Background color shift based on mood
world = bpy.context.scene.world
if world is None:
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
world.use_nodes = True
bg_nodes = world.node_tree.nodes
bg_emission = bg_nodes.new(type='ShaderNodeEmission')
if {valence} < -0.3:
    bg_emission.inputs['Color'].default_value = (0.05, 0.1, 0.2, 1.0)
elif {valence} > 0.3:
    bg_emission.inputs['Color'].default_value = (0.2, 0.15, 0.05, 1.0)
else:
    bg_emission.inputs['Color'].default_value = (0.1, 0.1, 0.15, 1.0)
bg_emission.inputs['Strength'].default_value = {arousal * 0.5 + 0.1}
bg_output = bg_nodes.new(type='ShaderNodeOutputWorld')
world.node_tree.links.new(bg_emission.outputs['Emission'], bg_output.inputs['Surface'])
"""
        else:
            # Original sphere visualization (abstract proto-AGI internal state)
            return f"""
# Emotion Visualization - Sphere Mode (Abstract Proto-AGI Internal State)
# Mood: {mood}, Valence: {valence:.2f}, Arousal: {arousal:.2f}, Intensity: {intensity:.2f}

# Create emotion sphere at center
bpy.ops.mesh.primitive_uv_sphere_add(location=(0, 0, 3), radius={max(0.1, min(1.0, abs(valence) * 0.5 + arousal * 0.5))})
emotion_obj = bpy.context.active_object
emotion_obj.name = "EmotionCore"
emotion_obj.scale = ({max(0.1, min(1.0, abs(valence) * 0.5 + arousal * 0.5))},) * 3

# Emission material for core
emotion_mat = bpy.data.materials.new(name="EmotionMaterial")
emotion_mat.use_nodes = True
nodes = emotion_mat.node_tree.nodes
emission = nodes.new(type='ShaderNodeEmission')
emission.inputs['Color'].default_value = ({base_color[0]}, {base_color[1]}, {base_color[2]}, 1.0)
emission.inputs['Strength'].default_value = {max(0.1, min(1.0, abs(valence) * 0.5 + arousal * 0.5)) * 10.0}
output = nodes.new(type='ShaderNodeOutputMaterial')
emotion_mat.node_tree.links.new(emission.outputs['Emission'], output.inputs['Surface'])
emotion_obj.data.materials.append(emotion_mat)

# Animate pulse based on arousal
emotion_obj.scale = ({max(0.1, min(1.0, abs(valence) * 0.5 + arousal * 0.5))},) * 3
emotion_obj.keyframe_insert(data_path="scale", frame=1)
emotion_obj.scale = ({max(0.1, min(1.0, abs(valence) * 0.5 + arousal * 0.5)) * 1.3},) * 3
emotion_obj.keyframe_insert(data_path="scale", frame=int({spec.duration} * {spec.fps} / 2))
emotion_obj.scale = ({max(0.1, min(1.0, abs(valence) * 0.5 + arousal * 0.5))},) * 3
emotion_obj.keyframe_insert(data_path="scale", frame=int({spec.duration} * {spec.fps}))

# Lighting based on valence
bpy.ops.object.light_add(type='SUN', location=(0, 0, 10))
sun = bpy.context.active_object
sun.name = "EmotionSun"
sun.data.energy = {max(1.0, arousal * 5.0)}
if {valence} < -0.3:
    sun.data.color = (0.3, 0.4, 1.0)
elif {valence} > 0.3:
    sun.data.color = (1.0, 0.7, 0.3)
else:
    sun.data.color = (0.9, 0.9, 1.0)

# Background color shift based on mood
world = bpy.context.scene.world
if world is None:
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
world.use_nodes = True
bg_nodes = world.node_tree.nodes
bg_emission = bg_nodes.new(type='ShaderNodeEmission')
if {valence} < -0.3:
    bg_emission.inputs['Color'].default_value = (0.05, 0.1, 0.2, 1.0)
elif {valence} > 0.3:
    bg_emission.inputs['Color'].default_value = (0.2, 0.15, 0.05, 1.0)
else:
    bg_emission.inputs['Color'].default_value = (0.1, 0.1, 0.15, 1.0)
bg_emission.inputs['Strength'].default_value = {arousal * 0.5 + 0.1}
bg_output = bg_nodes.new(type='ShaderNodeOutputWorld')
world.node_tree.links.new(bg_emission.outputs['Emission'], bg_output.inputs['Surface'])
"""
        return emotion_code

    def _build_simulation_script(self, spec: SimulationSpec) -> str:
        """Build complete Blender Python script for simulation."""
        script_parts = []
        
        # Header
        script_parts.append("""
import bpy
import json
import os
import sys
import math

# Clear default scene
bpy.ops.wm.read_factory_settings(use_empty=False)

# Set up scene
scene = bpy.context.scene
scene.render.engine = '{render_engine}'
scene.render.resolution_x = {res_x}
scene.render.resolution_y = {res_y}
scene.render.resolution_percentage = 100
scene.cycles.samples = {render_samples}
scene.frame_start = {frame_start}
scene.frame_end = {frame_end}
scene.frame_set({frame_start})
""".format(
            render_engine=spec.render_engine,
            res_x=spec.render_resolution[0],
            res_y=spec.render_resolution[1],
            render_samples=spec.render_samples,
            frame_start=spec.frame_start,
            frame_end=spec.frame_end
        ))
        
        # Ground plane
        if spec.ground:
            script_parts.append("""
# Ground plane
bpy.ops.mesh.primitive_plane_add(location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = "Ground"
ground.scale = (50, 50, 1)
bpy.ops.rigidbody.object_add()
ground.rigid_body.type = 'PASSIVE'
ground.rigid_body.friction = 0.8
ground.rigid_body.collision_shape = 'BOX'
""")
        
        # Add objects
        for i, obj in enumerate(spec.objects):
            script_parts.append(self._build_object_script(obj, i))
        
        # Add emotion visualization
        if spec.emotion_config and spec.emotion_visualizer:
            script_parts.append(self._build_emotion_code(spec))
        
        # Physics settings
        if spec.type != SimulationType.RENDER:
            script_parts.append("""
# Physics settings
scene.rigidbody_world.point_cache.frame_start = {frame_start}
scene.rigidbody_world.point_cache.frame_end = {frame_end}
scene.rigidbody_world.settings.substeps_per_frame = {substeps}
scene.rigidbody_world.settings.solver_iterations = {solver_iterations}
""".format(
                frame_start=spec.frame_start,
                frame_end=spec.frame_end,
                substeps=spec.physics.substeps,
                solver_iterations=spec.physics.solver_iterations
            ))
        
        # Add camera
        script_parts.append("""
# Camera
bpy.ops.object.camera_add(location=(8, -8, 6))
camera = bpy.context.active_object
camera.name = "MainCamera"
camera.rotation_euler = (math.radians(65), 0, math.radians(45))
scene.camera = camera
""")
        
        # Lighting
        script_parts.append("""
# Lighting
bpy.ops.object.light_add(type='SUN', location=(5, -5, 10))
sun = bpy.context.active_object
sun.name = "SunLight"
sun.data.energy = 3.0
""")
        
        # Render output settings
        if spec.render or spec.render_animation:
            script_parts.append("""
# Render output
scene.render.filepath = '{output_path}/render_'
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
""".format(output_path=spec.output_path))
        
        # FFmpeg MP4 animation settings
        if spec.render_animation:
            video_path = spec.video_output_path or f"{spec.output_path}/animation.mp4"

            # Snippet mode: short clips of notable moments
            if spec.snippet_mode:
                snippet_frames = int(spec.snippet_duration * spec.fps)
                # Start from middle of animation to capture the interesting part
                mid_frame = spec.frame_start + (spec.frame_end - spec.frame_start) // 2
                snippet_start = max(spec.frame_start, mid_frame - snippet_frames // 2)
                snippet_end = min(spec.frame_end, snippet_start + snippet_frames)
                script_parts.append("""
# FFmpeg snippet mode - short clip of notable moment
scene.render.image_settings.file_format = 'FFMPEG'
scene.render.ffmpeg.format = 'MPEG4'
scene.render.ffmpeg.codec = 'H264'
scene.render.ffmpeg.constant_rate_factor = 'PERC_LOSSLESS'
scene.render.ffmpeg.ffmpeg_bitrate = {bitrate}
scene.frame_start = {snippet_start}
scene.frame_end = {snippet_end}

# Render snippet
bpy.ops.render.render(animation=True, write_still=False)

# Save video path
video_path = "{video_path}"
""".format(
                    bitrate=spec.video_bitrate,
                    snippet_start=snippet_start,
                    snippet_end=snippet_end,
                    video_path=video_path
                ))
            else:
                script_parts.append("""
# FFmpeg animation output
scene.render.image_settings.file_format = 'FFMPEG'
scene.render.ffmpeg.format = 'MPEG4'
scene.render.ffmpeg.codec = 'H264'
scene.render.ffmpeg.constant_rate_factor = 'PERC_LOSSLESS'
scene.render.ffmpeg.ffmpeg_bitrate = {bitrate}
scene.frame_start = {frame_start}
scene.frame_end = {frame_end}

# Render animation
bpy.ops.render.render(animation=True, write_still=False)

# Save video path
video_path = "{video_path}"
""".format(
                    bitrate=spec.video_bitrate,
                    frame_start=spec.frame_start,
                    frame_end=spec.frame_end,
                    video_path=video_path
                ))
        elif spec.render:
            script_parts.append("""
# Render single frame
bpy.ops.render.render(write_still=True)
""")
        
        # Domain randomization
        if spec.domain_randomization:
            dr = spec.domain_randomization
            script_parts.append("""
# Domain randomization
import random
if {randomize_lighting}:
    for light in bpy.data.objects:
        if light.type == 'LIGHT':
            light.data.energy *= random.uniform(1.0 - {lighting_var}, 1.0 + {lighting_var})
            light.data.color = tuple(c * random.uniform(1.0 - {lighting_var}, 1.0 + {lighting_var}) for c in light.data.color)
if {randomize_physics}:
    for obj in bpy.data.objects:
        if hasattr(obj, 'rigid_body') and obj.rigid_body:
            obj.rigid_body.mass *= random.uniform(1.0 - {physics_var}, 1.0 + {physics_var})
            obj.rigid_body.friction = max(0, min(1, obj.rigid_body.friction + random.uniform(-{physics_var}, {physics_var})))
""".format(
                randomize_lighting=dr.randomize_lighting,
                lighting_var=dr.lighting_variance,
                randomize_physics=dr.randomize_physics_params,
                physics_var=dr.physics_variance
            ))
        
        # Export settings
        if spec.exports:
            script_parts.append("""
# Export paths
export_paths = {}
""")
            for fmt in spec.exports:
                ext = fmt.value if hasattr(fmt, 'value') else str(fmt)
                script_parts.append("""
export_paths['{ext}'] = "{output_path}/export.{ext}"
""".format(ext=ext, output_path=spec.output_path))
        
        # Save blend file
        if spec.save_blend:
            blend_path = spec.save_blend if isinstance(spec.save_blend, str) else f"{spec.output_path}/scene.blend"
            script_parts.append("""
# Save blend file
bpy.ops.wm.save_as_mainfile(filepath="{blend_path}")
""".format(blend_path=blend_path))
        
        # Output result
        script_parts.append("""
# Output result
result = {
    "success": True,
    "render_path": "{render_path}",
    "video_path": {video_path},
    "blend_path": "{blend_path}",
    "export_paths": {export_paths},
    "frame_count": scene.frame_end - scene.frame_start + 1,
    "stats": {
        "object_count": len(bpy.data.objects),
        "material_count": len(bpy.data.materials),
        "mesh_count": len(bpy.data.meshes)
    }
}
print("SIMULATION_RESULT:" + json.dumps(result))
""".format(
            render_path=f"{spec.output_path}/render_0001.png",
            video_path=f'"{spec.video_output_path}"' if spec.render_animation and spec.video_output_path else "None",
            blend_path=spec.save_blend if isinstance(spec.save_blend, str) else f"{spec.output_path}/scene.blend",
            export_paths="{}" if not spec.exports else str({fmt.value if hasattr(fmt, 'value') else str(fmt): f"{spec.output_path}/export.{fmt.value if hasattr(fmt, 'value') else str(fmt)}" for fmt in spec.exports})
        ))
        
        return "\n".join(script_parts)

    async def _run_blender_script(
        self,
        script: str,
        spec: Optional[SimulationSpec] = None,
        timeout: Optional[int] = None
    ) -> Dict:
        """Execute Blender script in Docker container."""
        script_id = int(time.time() * 1000)
        script_path = f"/workspace/script_{script_id}.py"
        host_script_path = self.data_dir / f"script_{script_id}.py"

        host_script_path.write_text(script)

        try:
            host_dir = str(self.data_dir.absolute()).replace('\\', '/')
            container_dir = '/workspace'

            container = self.docker.containers.run(
                self.image,
                command=[script_path],
                volumes={host_dir: {'bind': container_dir, 'mode': 'rw'}},
                working_dir=container_dir,
                detach=True,
                remove=False,
                user='root',
            )

            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(container.wait, timeout=timeout or self.timeout),
                    timeout=timeout or self.timeout
                )
                logs = container.logs(stdout=True, stderr=True).decode('utf-8', errors='replace')
                container.remove()

                return self._parse_output(logs)

            except asyncio.TimeoutError:
                container.kill()
                container.remove()
                return {"success": False, "error": "Timeout"}

        finally:
            host_script_path.unlink(missing_ok=True)

    def _parse_output(self, logs: str) -> Dict:
        """Parse Blender output for SIMULATION_RESULT."""
        for line in logs.split('\n'):
            if line.startswith("SIMULATION_RESULT:"):
                try:
                    return json.loads(line[len("SIMULATION_RESULT:"):])
                except json.JSONDecodeError:
                    pass
        return {"success": False, "error": "No valid result in output", "raw": logs[-2000:]}

    async def test_connection(self) -> bool:
        """Test that Blender sandbox is working."""
        result = await self.run_custom_script("""
import bpy
print("BLENDER_VERSION:", bpy.app.version)
print("TEST_OK")
""")
        return result.get("success", False) and "TEST_OK" in str(result.get("output", ""))


async def create_blender_sandbox(
    image: str = "ontogeny-blender",
    data_dir: str = "data/blender"
) -> BlenderSandbox:
    """Factory for creating BlenderSandbox."""
    return BlenderSandbox(image=image, data_dir=data_dir)