"""Blender Sandbox - Physics simulation and rendering for grounded verification."""

import asyncio
import json
import tempfile
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


@dataclass
class SimulationSpec:
    """Specification for a physics simulation."""
    type: SimulationType = SimulationType.RIGID_BODY
    objects: List[Dict] = field(default_factory=list)
    duration: float = 5.0
    fps: int = 60
    gravity: tuple = (0, 0, -9.81)
    ground: bool = True
    render: bool = False
    render_resolution: tuple = (1920, 1080)
    render_engine: str = "CYCLES"
    render_samples: int = 128
    output_path: str = "/workspace/output"
    metadata: Dict = field(default_factory=dict)


@dataclass
class SimulationResult:
    """Result of a simulation run."""
    success: bool
    output: Any = None
    error: Optional[str] = None
    frames: List[Dict] = field(default_factory=list)
    render_path: Optional[str] = None
    blend_path: Optional[str] = None
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
                    render_path=result.get("render_path"),
                    blend_path=result.get("blend_path"),
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

    def _build_simulation_script(self, spec: SimulationSpec) -> str:
        """Generate Blender Python script for simulation."""
        objects_code = []
        for i, obj in enumerate(spec.objects):
            otype = obj.get("type", "cube")
            loc = obj.get("position", [0, 0, 5])
            rot = obj.get("rotation", [0, 0, 0])
            scale = obj.get("scale", [1, 1, 1])
            mass = obj.get("mass", 1.0)
            passive = obj.get("passive", False)

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

            objects_code.append(f"""
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
obj.rigid_body.friction = {obj.get('friction', 0.5)}
obj.rigid_body.restitution = {obj.get('restitution', 0.3)}
""")

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

        blend_path = f"{spec.output_path}/simulation_{int(time.time())}.blend"

        return f"""
import bpy
import json
import math
import time

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Set units
bpy.context.scene.unit_settings.system = 'METRIC'

# Rigid body world
bpy.context.scene.rigidbody_world.enabled = True
bpy.context.scene.rigidbody_world.time_scale = 1.0
bpy.context.scene.rigidbody_world.steps_per_second = {spec.fps}
bpy.context.scene.rigidbody_world.solver_iterations = 20
bpy.context.scene.gravity = {spec.gravity}

# Ground plane
{"bpy.ops.mesh.primitive_plane_add(location=(0, 0, 0), scale=(50, 50, 1))" if spec.ground else "# No ground"}
{"ground = bpy.context.active_object; ground.name = 'Ground'; bpy.ops.rigidbody.object_add(); ground.rigid_body.type = 'PASSIVE'; ground.rigid_body.collision_shape = 'BOX'" if spec.ground else ""}

{"".join(objects_code)}

# Bake simulation
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = int({spec.duration} * {spec.fps})
bpy.ops.ptcache.bake_all(bake=True)

# Collect frame data
frames = []
for frame in range(1, bpy.context.scene.frame_end + 1):
    bpy.context.scene.frame_set(frame)
    frame_data = {{"frame": frame, "objects": []}}
    for obj in bpy.data.objects:
        if obj.name.startswith("SimObj_"):
            frame_data["objects"].append({{
                "name": obj.name,
                "location": list(obj.location),
                "rotation": list(obj.rotation_euler),
                "velocity": list(obj.rigid_body.linear_velocity) if hasattr(obj, 'rigid_body') and obj.rigid_body else [0,0,0]
            }})
    frames.append(frame_data)

# Save .blend
bpy.ops.wm.save_as_mainfile(filepath="{blend_path}")

{render_code}

# Output results
result = {{
    "success": True,
    "output": {{"frames": len(frames), "duration": {spec.duration}}},
    "frames": frames,
    "blend_path": "{blend_path}",
    {"render_path": "{render_path}" if spec.render else ""}
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

        # Write script to host
        host_script_path.write_text(script)

        try:
            # Prepare volume mount
            host_dir = str(self.data_dir.absolute()).replace('\\', '/')
            container_dir = '/workspace'

            container = self.docker.containers.run(
                self.image,
                command=[script_path],
                volumes={host_dir: {'bind': container_dir, 'mode': 'rw'}},
                working_dir=container_dir,
                detach=True,
                remove=False,
                user='root',  # Blender needs root for some operations
            )

            # Wait with timeout
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(container.wait, timeout=timeout or self.timeout),
                    timeout=timeout or self.timeout
                )
                logs = container.logs(stdout=True, stderr=True).decode('utf-8', errors='replace')
                container.remove()

                # Parse result
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