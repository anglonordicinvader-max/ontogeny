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
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
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
    clutter_types: List[str] = field(default_factory=lambda: ["cube", "sphere", "cylinder"])


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
    save_blend: bool = True
    render: bool = False
    render_resolution: tuple = (1920, 1080)
    render_engine: str = "CYCLES"
    render_samples: int = 128


@dataclass
class SimulationResult:
    """Result of a simulation run."""
    success: bool
    output: Any = None
    error: Optional[str] = None
    frames: List[Dict] = field(default_factory=list)
    sensor_data: Dict = field(default_factory=dict)
    render_path: Optional[str] = None
    blend_path: Optional[str] = None
    export_paths: Dict = field(default_factory=dict)
    execution_time_ms: float = 0.0
    stats: Dict = field(default_factory=dict)


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
        self._verify_image()

    def _verify_image(self):
        try:
            self.docker.images.get(self.image)
            self.logger.info("blender_image_ready", image=self.image)
        except docker.errors.ImageNotFound:
            self.logger.warning("blender_image_not_found", image=self.image)
            raise RuntimeError(
                f"Blender image '{self.image}' not found. Build with:\n"
                f"  docker build -f Dockerfile.blender -t {self.image} ."
            )

    async def run_simulation(self, spec: SimulationSpec) -> SimulationResult:
        """Run a physics simulation and return results."""
        start = time.perf_counter()

        try:
            script = self._build_simulation_script(spec)
            result = await self._run_blender_script(script, spec)

            exec_time = (time.perf_counter() - start) * 1000

            if result.get("success"):
                return SimulationResult(
                    success=True,
                    output=result.get("output"),
                    frames=result.get("frames", []),
                    sensor_data=result.get("sensor_data", {}),
                    render_path=result.get("render_path"),
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
            }})
    
    print("STEP_RESULT:" + json.dumps(frame_data))
"""
        result = await self._run_blender_script(script)
        return result

    def _build_object_script(self, obj: ObjectSpec, i: int) -> str:
        """Generate Blender Python code for an object."""
        otype = obj.type
        loc = obj.position
        rot = obj.rotation
        scale = obj.scale
        mass = obj.mass
        passive = obj.passive

        if otype == "cube":
            prim = f'bpy.ops.mesh.primitive_cube_add(location={loc})'
        elif otype == "sphere":
            prim = f'bpy.ops.mesh.primitive_uv_sphere_add(location={loc})'
        elif otype == "plane":
            prim = f'bpy.ops.mesh.primitive_plane_add(location={loc}, scale=(50, 50, 1))'
        elif otype == "cylinder":
            prim = f'bpy.ops.mesh.primitive_cylinder_add(location={loc})'
        elif otype == "cone":
            prim = f'bpy.ops.mesh.primitive_cone_add(location={loc})'
        elif otype == "torus":
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

    def _build_simulation_script(self, spec: SimulationSpec) -> str:
        """Generate Blender Python script for simulation."""
        objects_code = [self._build_object_script(obj, i) for i, obj in enumerate(spec.objects)]

        # Domain randomization
        randomization_code = ""
        if spec.domain_randomization:
            dr = spec.domain_randomization
            randomization_code = f"""
# Domain Randomization
import random
import math

# Randomize lighting
if {dr.randomize_lighting}:
    for light in bpy.data.lights:
        light.energy *= random.uniform(1 - {dr.lighting_variance}, 1 + {dr.lighting_variance})
        light.color = (
            random.uniform(0.8, 1.0),
            random.uniform(0.8, 1.0),
            random.uniform(0.8, 1.0)
        )

# Randomize physics parameters
if {dr.randomize_physics_params}:
    bpy.context.scene.gravity = (
        {spec.gravity[0]} * random.uniform(1 - {dr.physics_variance}, 1 + {dr.physics_variance}),
        {spec.gravity[1]} * random.uniform(1 - {dr.physics_variance}, 1 + {dr.physics_variance}),
        {spec.gravity[2]} * random.uniform(1 - {dr.physics_variance}, 1 + {dr.physics_variance})
    )

# Randomize object poses
if {dr.randomize_object_poses}:
    for obj in bpy.data.objects:
        if obj.name.startswith("SimObj_"):
            obj.location = (
                obj.location[0] + random.uniform(-{dr.pose_variance}, {dr.pose_variance}),
                obj.location[1] + random.uniform(-{dr.pose_variance}, {dr.pose_variance}),
                obj.location[2] + random.uniform(-{dr.pose_variance}, {dr.pose_variance})
            )

# Randomize camera
if {dr.randomize_camera}:
    for cam in bpy.data.cameras:
        cam.lens = cam.lens * random.uniform(0.9, 1.1)
"""

        # Procedural generation
        procedural_code = ""
        if spec.procedural:
            proc = spec.procedural
            procedural_code = f"""
# Procedural Generation
import random
import math

# Terrain
if {proc.generate_terrain}:
    bpy.ops.mesh.primitive_plane_add(size={proc.terrain_size[0]}, location=(0, 0, 0))
    terrain = bpy.context.active_object
    terrain.name = "Terrain"
    bpy.ops.object.modifier_add(type='DISPLACE')
    terrain.modifiers["Displace"].strength = 5.0
    terrain.modifiers["Displace"].texture = bpy.data.textures.new("TerrainTex", 'CLOUDS')
    terrain.modifiers["Displace"].texture.noise_scale = {proc.terrain_scale}
    terrain.modifiers["Displace"].texture.noise_depth = {proc.terrain_octaves}
    bpy.ops.rigidbody.object_add()
    terrain.rigid_body.type = 'PASSIVE'
    terrain.rigid_body.collision_shape = 'MESH'

# Buildings
if {proc.generate_buildings}:
    for i in range({proc.building_count}):
        x = random.uniform(-{proc.terrain_size[0]/2}, {proc.terrain_size[0]/2})
        y = random.uniform(-{proc.terrain_size[1]/2}, {proc.terrain_size[1]/2})
        h = random.uniform({proc.building_height_range[0]}, {proc.building_height_range[1]})
        bpy.ops.mesh.primitive_cube_add(location=(x, y, h/2), scale=(5, 5, h/2))
        bldg = bpy.context.active_object
        bldg.name = f"Building_{{i}}"
        bpy.ops.rigidbody.object_add()
        bldg.rigid_body.type = 'PASSIVE'
        bldg.rigid_body.collision_shape = 'BOX'

# Clutter
if {proc.generate_clutter}:
    for i in range({proc.clutter_count}):
        x = random.uniform(-{proc.terrain_size[0]/2}, {proc.terrain_size[0]/2})
        y = random.uniform(-{proc.terrain_size[1]/2}, {proc.terrain_size[1]/2})
        obj_type = random.choice({proc.clutter_types})
        if obj_type == "cube":
            bpy.ops.mesh.primitive_cube_add(location=(x, y, 2), scale=(0.5, 0.5, 0.5))
        elif obj_type == "sphere":
            bpy.ops.mesh.primitive_uv_sphere_add(location=(x, y, 2), radius=0.5)
        elif obj_type == "cylinder":
            bpy.ops.mesh.primitive_cylinder_add(location=(x, y, 2), radius=0.3, depth=1)
        obj = bpy.context.active_object
        obj.name = f"Clutter_{{i}}"
        bpy.ops.rigidbody.object_add()
        obj.rigid_body.type = 'ACTIVE'
        obj.rigid_body.mass = 0.1
"""

        # Robot/URDF
        robot_code = ""
        if spec.urdf_path:
            robot_code = f"""
# URDF Robot Import
bpy.ops.import_scene.urdf(filepath="{spec.urdf_path}")
# Rename imported objects
for obj in bpy.data.objects:
    if obj.name.startswith("link") or obj.name.startswith("joint"):
        obj.name = "Robot_" + obj.name
        # Add rigid body for links
        bpy.ops.rigidbody.object_add()
        obj.rigid_body.type = 'ACTIVE'
        obj.rigid_body.mass = 1.0

# Joint control
if {bool(spec.robot_joints)}:
    # Apply joint commands
    for joint_name, command in {json.dumps(spec.robot_joints)}.items():
        obj = bpy.data.objects.get(joint_name)
        if obj and command.get("type") == "position":
            obj.rotation_euler = command.get("value", [0,0,0])
        elif obj and command.get("type") == "velocity":
            obj.rigid_body.angular_velocity = command.get("value", [0,0,0])
        elif obj and command.get("type") == "torque":
            obj.rigid_body.angular_velocity = command.get("value", [0,0,0])  # Simplified
"""

        # Sensor init
        sensor_init = []
        sensor_update = []
        if spec.sensors:
            for i, s in enumerate(spec.sensors):
                if s.type == "camera":
                    sensor_init.append(f"""
# Camera sensor {i}
bpy.ops.object.camera_add(location={s.position}, rotation={s.rotation})
cam = bpy.context.active_object
cam.name = "Sensor_Camera_{i}"
cam.data.angle = {s.fov * 3.14159 / 180.0}
cam.data.clip_start = {s.range_min}
cam.data.clip_end = {s.range_max}
""")
                    sensor_update.append(f"""
# Render camera {i}
bpy.context.scene.camera = bpy.data.objects["Sensor_Camera_{i}"]
bpy.context.scene.render.filepath = "{spec.output_path}/camera_{i}_frame_{{frame}}.png"
bpy.ops.render.render(write_still=True)
""")
                elif s.type == "lidar":
                    sensor_init.append(f"""
# LIDAR sensor {i}
lidar_{i} = {{"position": {s.position}, "rotation": {s.rotation}, "range": {s.range_max}, "rays": 360}}
""")
                    sensor_update.append(f"""
# LIDAR {i} raycast
import math
lidar_data_{i} = []
for angle in range(360):
    rad = angle * 3.14159 / 180.0
    dir = (math.cos(rad), math.sin(rad), 0)
    result, location, normal, index, object, matrix = bpy.context.scene.ray_cast(
        bpy.context.view_layer.depsgraph, {s.position}, dir, distance={s.range_max})
    if result:
        lidar_data_{i}.append({{"angle": angle, "distance": (location[0]-{s.position[0]})**2 + (location[1]-{s.position[1]})**2}})
"""
            sensor_update.append(f"sensor_data['lidar_{i}'] = lidar_data_{i}")

        sensor_init_code = "".join(sensor_init)
        sensor_update_code = "".join(sensor_update)

        # Exports
        export_code = ""
        if spec.exports:
            for fmt in spec.exports:
                if fmt == ExportFormat.USD:
                    export_code += f'bpy.ops.wm.usd_export(filepath="{spec.output_path}/export.usd")\n'
                elif fmt == ExportFormat.GLTF:
                    export_code += f'bpy.ops.export_scene.gltf(filepath="{spec.output_path}/export.gltf", export_format="GLTF_SEPARATE")\n'
                elif fmt == ExportFormat.GLB:
                    export_code += f'bpy.ops.export_scene.gltf(filepath="{spec.output_path}/export.glb", export_format="GLB")\n'
                elif fmt == ExportFormat.OBJ:
                    export_code += f'bpy.ops.export_scene.obj(filepath="{spec.output_path}/export.obj")\n'
                elif fmt == ExportFormat.STL:
                    export_code += f'bpy.ops.export_mesh.stl(filepath="{spec.output_path}/export.stl")\n'
                elif fmt == ExportFormat.PLY:
                    export_code += f'bpy.ops.export_mesh.ply(filepath="{spec.output_path}/export.ply")\n'
                elif fmt == ExportFormat.ALEMBIC:
                    export_code += f'bpy.ops.wm.alembic_export(filepath="{spec.output_path}/export.abc")\n'

        # Load/save blend
        load_code = f'bpy.ops.wm.open_mainfile(filepath="{spec.load_blend}")\n' if spec.load_blend else ""
        save_code = f'bpy.ops.wm.save_as_mainfile(filepath="{spec.save_blend}")\n' if spec.save_blend else ""

        # Render
        render_code = ""
        if spec.render:
            render_path = f"{spec.output_path}/render_{int(time.time())}.png"
            render_code = f"""
# Render settings
bpy.context.scene.render.filepath = "{render_path}"
bpy.context.scene.render.resolution_x = {spec.render_resolution[0]}
bpy.context.scene.render.resolution_y = {spec.render_resolution[1]}
bpy.context.scene.render.engine = "{spec.render_engine}"
if spec.render_engine == "CYCLES":
    bpy.context.scene.cycles.samples = {spec.render_samples}
    bpy.context.scene.cycles.device = "CPU"
bpy.ops.render.render(write_still=True)
"""

        blend_path = spec.save_blend or f"{spec.output_path}/simulation_{int(time.time())}.blend"

        return f"""
import bpy
import json
import math
import time
import os

# Clear scene (unless loading existing)
{"" if spec.load_blend else "bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()"}

# Load existing blend
{load_code}

# Set units
bpy.context.scene.unit_settings.system = 'METRIC'

# Rigid body world
bpy.context.scene.rigidbody_world.enabled = True
bpy.context.scene.rigidbody_world.time_scale = {spec.physics.time_scale}
bpy.context.scene.rigidbody_world.steps_per_second = {spec.fps}
bpy.context.scene.rigidbody_world.solver_iterations = {spec.physics.solver_iterations}
bpy.context.scene.rigidbody_world.substeps_per_frame = {spec.physics.substeps}
bpy.context.scene.gravity = {spec.gravity}

# Physics settings
bpy.context.scene.rigidbody_world.collision_margin = {spec.physics.collision_margin}

# Ground plane
{("bpy.ops.mesh.primitive_plane_add(location=(0, 0, 0), scale=(50, 50, 1))" if spec.ground else "# No ground")}
{("ground = bpy.context.active_object; ground.name = 'Ground'; bpy.ops.rigidbody.object_add(); ground.rigid_body.type = 'PASSIVE'; ground.rigid_body.collision_shape = 'BOX'" if spec.ground else ""})

# Objects
{"".join(objects_code)}

# Robot/URDF
{robot_code}

# Domain Randomization
{randomization_code}

# Procedural Generation
{procedural_code}

# Sensors init
{sensor_init_code}

# Bake simulation
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = int({spec.duration} * {spec.fps})
bpy.ops.ptcache.bake_all(bake=True)

# Collect frame data
frames = []
sensor_data = {{}}
for frame in range(1, bpy.context.scene.frame_end + 1):
    bpy.context.scene.frame_set(frame)
    frame_data = {{"frame": frame, "objects": []}}
    for obj in bpy.data.objects:
        if obj.name.startswith("SimObj_") or obj.name.startswith("Robot_"):
            frame_data["objects"].append({{
                "name": obj.name,
                "location": list(obj.location),
                "rotation": list(obj.rotation_euler),
                "velocity": list(obj.rigid_body.linear_velocity) if hasattr(obj, 'rigid_body') and obj.rigid_body else [0,0,0]
            }})
    frames.append(frame_data)
    
    # Sensor updates
    {sensor_update_code if spec.sensors else ""}

# Save .blend
{save_code}

# Render
{render_code}

# Exports
{export_code}

# Output results
result = {{
    "success": True,
    "output": {{"frames": len(frames), "duration": {spec.duration}}},
    "frames": frames,
    "sensor_data": sensor_data,
    "blend_path": "{blend_path}",
    {"render_path": "{render_path}" if spec.render else ""},
    "export_paths": {{}}
}}
print("SIMULATION_RESULT:" + json.dumps(result))
"""

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