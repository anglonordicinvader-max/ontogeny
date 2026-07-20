import asyncio
import math
import os
import sys
import tempfile
import time
import warnings

import bpy

warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*use_nodes.*")

# Add project src to path for Blender's Python
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Add backend dir to path for blender_worlds
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Prefer the packaged dependency bundle; retain user-site discovery for development.
blender_vendor = os.path.join(backend_dir, "blender_vendor")
if os.path.isdir(blender_vendor) and blender_vendor not in sys.path:
    sys.path.insert(0, blender_vendor)
for python_minor in ("Python314", "Python313", "Python312", "Python311"):
    user_site = os.path.join(
        os.path.expanduser("~"), "AppData", "Roaming", "Python", python_minor, "site-packages"
    )
    if os.path.isdir(user_site) and user_site not in sys.path:
        sys.path.append(user_site)

import base64
import json

import websockets

# Import standalone world data - avoid full cognitive stack (SQLAlchemy, etc.)
from blender_worlds import (
    ALL_SURVIVAL_WORLDS,
    PRACTICAL_WORLDS,
    PracticalWorld,
    SelectionCriteria,
    SurvivalChallenge,
    WorldSelector,
    WorldType,
    list_workspace_worlds,
)

ALL_WORLDS = {}
ALL_WORLDS.update(PRACTICAL_WORLDS)
for name, world in ALL_SURVIVAL_WORLDS.items():
    ALL_WORLDS[name] = world

MESHES_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "data",
    "blender",
    "models",
    "tocabi",
    "combined",
    "meshes",
)

STL_CACHE_PATH = os.path.join(tempfile.gettempdir(), "ontogeny_tocabi_cache.blend")

EMOTION_STATES = [
    "neutral",
    "thinking",
    "curious",
    "excited",
    "focused",
    "confused",
    "satisfied",
    "alert",
]

# Import backend agent manager for autonomous world selection
try:
    from agent_manager import manager

    AGENT_MANAGER_AVAILABLE = True
except ImportError:
    AGENT_MANAGER_AVAILABLE = False
    manager = None


def _mat(name, color, metallic=0.0, roughness=0.5, emission=0.0):
    existing = bpy.data.materials.get(name)
    if existing:
        return existing
    m = bpy.data.materials.new(name=name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    if b:
        b.inputs["Base Color"].default_value = color
        if "Metallic" in b.inputs:
            b.inputs["Metallic"].default_value = metallic
        if "Roughness" in b.inputs:
            b.inputs["Roughness"].default_value = roughness
        if "Emission Color" in b.inputs:
            b.inputs["Emission Color"].default_value = color
            b.inputs["Emission Strength"].default_value = emission
    return m


class BlenderSimulation:
    def __init__(self, world_name=None):
        self.clients = set()
        self.frame_clients = set()
        self.running = True
        self.frame = 0
        self.mode = "anatomy"
        self.emotion = "neutral"
        self.valence = 0.0
        self.arousal = 0.5
        self.world_name = world_name
        self.world_source = "manual" if world_name else "autonomous"
        self.world_info = None
        self.tmp_path = os.path.join(tempfile.gettempdir(), "ontogeny_rt.png")
        self._pending_frame = None
        self._render_ready = False
        self._render_error = None
        self._skip_cache_setup = False

        # Initialize WorldSelector for autonomous world selection
        self.world_selector = WorldSelector()

        self._setup_scene()

    def _setup_scene(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        scene = bpy.context.scene
        self.scene = scene

        scene.render.engine = "CYCLES"
        scene.cycles.device = "CPU"
        scene.cycles.samples = 16

        # Remove default speakers to avoid depsgraph crash in Blender 5.2
        for obj in list(bpy.data.objects):
            if obj.type == "SPEAKER":
                bpy.data.objects.remove(obj, do_unlink=True)
        scene.render.resolution_x = 480
        scene.render.resolution_y = 360
        scene.render.resolution_percentage = 100
        scene.render.film_transparent = False

        world = bpy.data.worlds.new("World")
        scene.world = world
        world.use_nodes = True
        bg = world.node_tree.nodes.get("Background")
        if bg:
            bg.inputs[0].default_value = (0.02, 0.02, 0.04, 1)
            bg.inputs[1].default_value = 1.0

        self._setup_lighting()
        self._setup_camera()

        self.col_world = bpy.data.collections.new("World")
        scene.collection.children.link(self.col_world)
        self.col_anatomy = bpy.data.collections.new("Anatomy")
        scene.collection.children.link(self.col_anatomy)
        self.col_sphere = bpy.data.collections.new("Sphere")
        scene.collection.children.link(self.col_sphere)

        self._build_world_scene()
        self._build_anatomy_scene()
        self._build_sphere_scene()

        self._update_visibility()

    def _setup_lighting(self):
        bpy.ops.object.light_add(type="SUN", location=(5, -5, 10))
        sun = bpy.context.active_object
        sun.name = "KeyLight"

        bpy.ops.object.light_add(type="AREA", location=(0, 0, 10))
        sky = bpy.context.active_object
        sky.name = "SkyLight"
        sky.data.size = 10
        sky.data.energy = 3

    def _setup_camera(self):
        bpy.ops.object.camera_add()
        cam = bpy.context.active_object
        cam.name = "Camera"
        cam.data.name = "Camera"
        self.cam = cam
        self.scene.camera = cam
        self.cam_target = bpy.data.objects.new("CamTarget", None)
        bpy.context.collection.objects.link(self.cam_target)
        constraint = cam.constraints.new("TRACK_TO")
        constraint.target = self.cam_target
        constraint.track_axis = "TRACK_NEGATIVE_Z"
        constraint.up_axis = "UP_Y"
        self.cam_target.location = (0, 0, 2)

    def _update_visibility(self):
        self.col_world.hide_viewport = self.mode != "both" and self.world_name is None
        self.col_world.hide_render = self.col_world.hide_viewport
        self.col_anatomy.hide_viewport = self.mode not in ("anatomy", "both")
        self.col_anatomy.hide_render = self.col_anatomy.hide_viewport
        self.col_sphere.hide_viewport = self.mode not in ("sphere", "both")
        self.col_sphere.hide_render = self.col_sphere.hide_viewport

    # ================================================================
    # WORLD
    # ================================================================
    def _build_world_scene(self, preserve_camera: bool = False):
        camera_location = self.cam.location.copy() if preserve_camera and self.cam else None
        target_location = (
            self.cam_target.location.copy() if preserve_camera and self.cam_target else None
        )
        for obj in list(self.col_world.objects):
            object_data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if object_data and getattr(object_data, "users", 0) == 0:
                if isinstance(object_data, bpy.types.Mesh):
                    bpy.data.meshes.remove(object_data)

        if self.world_source == "autonomous" and self.world_selector:
            try:
                result = self.world_selector.select(SelectionCriteria(max_difficulty=1.0))
                if result.world.name != self.world_name:
                    self.world_name = result.world.name
                    print(
                        f"[Blender] Autonomous world selection: {self.world_name} (reason: {result.reason})",
                        flush=True,
                    )
            except Exception as e:
                print(f"[Blender] Error in autonomous world selection: {e}", flush=True)

        if not self.world_name or self.world_name not in ALL_WORLDS:
            self.world_info = None
            return

        world_data = ALL_WORLDS[self.world_name]

        mat_ground = _mat("WGround", (0.1, 0.1, 0.12, 1))
        mat_agent = _mat("W_Agent", (0.2, 0.6, 1.0, 1), 0.3, 2.0)
        mat_goal = _mat("W_Goal", (0.9, 0.3, 0.1, 1), 0.8, 1.5)
        mat_interactive = _mat("WInteractive", (0.3, 0.4, 0.5, 1), 0.1, 0.8)

        bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
        bpy.context.active_object.data.materials.append(mat_ground)

        for obj_def in world_data.objects:
            obj = None
            obj_type = obj_def.get("type")
            if obj_type == "plane":
                bpy.ops.mesh.primitive_plane_add(
                    size=1, location=obj_def.get("position", [0, 0, 0])
                )
                obj = bpy.context.active_object
                obj.scale = tuple(obj_def.get("scale", [1, 1, 1]))
            elif obj_type == "cube":
                bpy.ops.mesh.primitive_cube_add(size=1, location=obj_def.get("position", [0, 0, 0]))
                obj = bpy.context.active_object
                obj.scale = tuple(obj_def.get("scale", [1, 1, 1]))
            elif obj_type == "sphere":
                bpy.ops.mesh.primitive_uv_sphere_add(
                    radius=0.5, location=obj_def.get("position", [0, 0, 0])
                )
                obj = bpy.context.active_object
                obj.scale = tuple(obj_def.get("scale", [1, 1, 1]))
            elif obj_type == "cylinder":
                bpy.ops.mesh.primitive_cylinder_add(
                    radius=0.5, depth=1, location=obj_def.get("position", [0, 0, 0])
                )
                obj = bpy.context.active_object
                obj.scale = tuple(obj_def.get("scale", [1, 1, 1]))
            elif obj_type == "cone":
                bpy.ops.mesh.primitive_cone_add(
                    radius1=0.5, depth=1, location=obj_def.get("position", [0, 0, 0])
                )
                obj = bpy.context.active_object
                obj.scale = tuple(obj_def.get("scale", [1, 1, 1]))

            if obj:
                obj.name = f"WO_{obj_def.get('type')}_{len(self.col_world.objects)}"
                if "mass" in obj_def and obj_def["mass"] > 0:
                    bpy.context.view_layer.objects.active = obj
                    bpy.ops.rigidbody.object_add()
                    obj.rigid_body.mass = obj_def["mass"]
                if "rotation" in obj_def:
                    obj.rotation_euler = tuple(obj_def["rotation"])
                self._link_to_collection(obj, self.col_world)

        interactive = world_data.interactive if hasattr(world_data, "interactive") else []
        for inter_def in interactive:
            pos = inter_def.position if hasattr(inter_def, "position") else [0, 0, 0]
            scale = inter_def.scale if hasattr(inter_def, "scale") else [1, 1, 1]

            bpy.ops.mesh.primitive_cube_add(size=1, location=pos)
            obj = bpy.context.active_object
            obj.name = f"WInteractive_{inter_def.object_type.value}"
            obj.scale = scale
            obj.data.materials.append(mat_interactive)
            self._link_to_collection(obj, self.col_world)

        spawn = world_data.spawn_point if hasattr(world_data, "spawn_point") else [0, 0, 1]
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.3, location=spawn)
        agent = bpy.context.active_object
        agent.name = "W_Agent"
        agent.data.materials.append(mat_agent)
        self._link_to_collection(agent, self.col_world)

        goal = world_data.goal_point if hasattr(world_data, "goal_point") else None
        if goal:
            bpy.ops.mesh.primitive_cone_add(radius1=0.2, depth=0.5, location=goal)
            goal_obj = bpy.context.active_object
            goal_obj.name = "W_Goal"
            goal_obj.data.materials.append(mat_goal)
            self._link_to_collection(goal_obj, self.col_world)

        if self.cam and camera_location is None:
            self.cam.location = (spawn[0] + 7, spawn[1] - 7, 5)
            self.cam_target.location = tuple(spawn)
        elif self.cam and camera_location is not None:
            self.cam.location = camera_location
            self.cam_target.location = target_location

        w_info = {
            "name": self.world_name,
            "description": world_data.description if hasattr(world_data, "description") else "",
            "difficulty": world_data.difficulty if hasattr(world_data, "difficulty") else 0.5,
            "tags": world_data.tags if hasattr(world_data, "tags") else [],
            "type": world_data.world_type.value if hasattr(world_data, "world_type") else "unknown",
            "num_objects": len(world_data.objects) if hasattr(world_data, "objects") else 0,
            "num_interactive": len(world_data.interactive)
            if hasattr(world_data, "interactive")
            else 0,
        }
        self.world_info = w_info

    # ================================================================
    # ANATOMY
    # ================================================================
    def _build_anatomy_scene(self):
        for obj in list(self.col_anatomy.objects):
            bpy.data.objects.remove(obj, do_unlink=True)

        loaded, needs_processing = self._load_tocabi_cached()
        if not loaded:
            loaded = self._build_fallback_anatomy()
            return

        if needs_processing:
            self._process_anatomy_meshes(loaded)
            self._save_tocabi_cache(loaded)

    def _load_tocabi_cached(self):
        meshes_path = MESHES_DIR
        if not os.path.exists(meshes_path):
            return [], False

        stl_files = sorted([f for f in os.listdir(meshes_path) if f.endswith(".stl")])
        if not stl_files:
            return [], False

        if self._cache_valid():
            print(f"[Anatomy] Loading from cache: {STL_CACHE_PATH}", flush=True)
            try:
                with bpy.data.libraries.load(STL_CACHE_PATH) as (data_from, data_to):
                    data_to.objects = data_from.objects

                loaded = []
                for obj in data_to.objects:
                    if obj is not None:
                        self._link_to_collection(obj, self.col_anatomy)
                        loaded.append(obj)

                if loaded:
                    print(
                        f"[Anatomy] Loaded {len(loaded)} cached meshes (no processing needed)",
                        flush=True,
                    )
                    return loaded, False
                else:
                    print("[Anatomy] Cache returned 0 objects, falling back to import", flush=True)
            except Exception as e:
                print(f"[Anatomy] Cache load failed: {e}", flush=True)

        print(f"[Anatomy] Importing {len(stl_files)} STL files (first time)...", flush=True)
        loaded = []
        for fname in stl_files:
            fpath = os.path.join(meshes_path, fname)
            try:
                bpy.ops.wm.stl_import(filepath=fpath)
                obj = bpy.context.active_object
                if obj:
                    obj.name = fname.replace(".stl", "")
                    loaded.append(obj)
            except Exception as e:
                print(f"[Anatomy] skip {fname}: {e}", flush=True)

        return loaded, True

    def _cache_valid(self):
        if not os.path.exists(STL_CACHE_PATH):
            return False
        try:
            meshes_path = MESHES_DIR
            stl_files = [f for f in os.listdir(meshes_path) if f.endswith(".stl")]
            stl_times = []
            for fname in stl_files:
                fpath = os.path.join(meshes_path, fname)
                try:
                    stl_times.append(os.path.getmtime(fpath))
                except OSError:
                    stl_times.append(0)
            cache_mtime = os.path.getmtime(STL_CACHE_PATH)
            return all(t <= cache_mtime for t in stl_times)
        except OSError:
            return False

    def _process_anatomy_meshes(self, loaded):
        for obj in loaded:
            obj.scale = (0.001, 0.001, 0.001)
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.object.transform_apply(scale=True)
            obj.select_set(False)

        cx = sum(o.location.x for o in loaded) / len(loaded)
        cy = sum(o.location.y for o in loaded) / len(loaded)
        cz = sum(o.location.z for o in loaded) / len(loaded)
        for obj in loaded:
            obj.location.x -= cx
            obj.location.y -= cy
            obj.location.z -= cz

        max_dim = max(max(o.dimensions) for o in loaded)
        sf = 2.0 / max_dim if max_dim > 0 else 1.0
        for obj in loaded:
            obj.scale = (sf, sf, sf)

        for obj in loaded:
            if obj.type == "MESH" and len(obj.data.polygons) > 1000:
                mod = obj.modifiers.new(name="Decimate", type="DECIMATE")
                mod.ratio = 0.15
                bpy.context.view_layer.objects.active = obj
                obj.select_set(True)
                bpy.ops.object.modifier_apply(modifier="Decimate")
                obj.select_set(False)

        mat_body = _mat("Anat_Body", (0.55, 0.58, 0.62, 1), metallic=0.8, roughness=0.25)
        mat_joint = _mat("Anat_Joint", (0.2, 0.22, 0.25, 1), metallic=0.9, roughness=0.15)
        mat_accent = _mat(
            "Anat_Accent", (0.0, 0.5, 0.9, 1), metallic=0.7, roughness=0.3, emission=0.5
        )

        for obj in loaded:
            if obj.type == "MESH":
                obj.data.materials.clear()
                nl = obj.name.lower()
                if any(k in nl for k in ["ankle", "wrist", "knee", "hip_1", "hip_2"]):
                    obj.data.materials.append(mat_joint)
                elif any(k in nl for k in ["waist", "body", "neck", "shoulder", "pelvis"]):
                    obj.data.materials.append(mat_accent)
                else:
                    obj.data.materials.append(mat_body)
            self._link_to_collection(obj, self.col_anatomy)

    def _save_tocabi_cache(self, loaded):
        try:
            with bpy.data.libraries.write(STL_CACHE_PATH, set(loaded)):
                pass
            print(f"[Anatomy] Cached {len(loaded)} meshes to {STL_CACHE_PATH}", flush=True)
        except Exception as e:
            print(f"[Anatomy] Cache save failed: {e}", flush=True)

    def _build_fallback_anatomy(self):
        mat_body = _mat("Anat_FBody", (0.5, 0.55, 0.6, 1), 0.6, 0.3)
        mat_joint = _mat("Anat_FJoint", (0.2, 0.2, 0.25, 1), 0.8, 0.15)

        parts = [
            ("Pelvis", (0, 0, 0.9), (0.3, 0.25, 0.15)),
            ("Spine", (0, 0, 1.2), (0.2, 0.15, 0.4)),
            ("Chest", (0, 0, 1.5), (0.35, 0.2, 0.35)),
            ("Neck", (0, 0, 1.85), (0.08, 0.08, 0.12)),
            ("Head", (0, 0, 2.1), (0.18, 0.2, 0.2)),
            ("L_UpperArm", (-0.3, 0, 1.6), (0.08, 0.08, 0.3)),
            ("L_LowerArm", (-0.3, 0, 1.25), (0.07, 0.07, 0.28)),
            ("L_Hand", (-0.3, 0, 0.95), (0.08, 0.05, 0.1)),
            ("R_UpperArm", (0.3, 0, 1.6), (0.08, 0.08, 0.3)),
            ("R_LowerArm", (0.3, 0, 1.25), (0.07, 0.07, 0.28)),
            ("R_Hand", (0.3, 0, 0.95), (0.08, 0.05, 0.1)),
            ("L_Thigh", (-0.12, 0, 0.6), (0.1, 0.1, 0.35)),
            ("L_Shin", (-0.12, 0, 0.25), (0.08, 0.08, 0.3)),
            ("L_Foot", (-0.12, 0.05, 0.05), (0.1, 0.15, 0.05)),
            ("R_Thigh", (0.12, 0, 0.6), (0.1, 0.1, 0.35)),
            ("R_Shin", (0.12, 0, 0.25), (0.08, 0.08, 0.3)),
            ("R_Foot", (0.12, 0.05, 0.05), (0.1, 0.15, 0.05)),
        ]

        loaded = []
        for name, loc, scale in parts:
            bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
            obj = bpy.context.active_object
            obj.name = name
            obj.scale = scale
            if "joint" in name.lower() or "ankle" in name.lower() or "knee" in name.lower():
                obj.data.materials.append(mat_joint)
            else:
                obj.data.materials.append(mat_body)
            loaded.append(obj)
            self._link_to_collection(obj, self.col_anatomy)

        return loaded

    def _link_to_collection(self, obj, collection):
        for c in obj.users_collection:
            c.objects.unlink(obj)
        collection.objects.link(obj)

    # ================================================================
    # SPHERE
    # ================================================================
    def _build_sphere_scene(self):
        for obj in list(self.col_sphere.objects):
            bpy.data.objects.remove(obj, do_unlink=True)

        mat_ground = _mat("Sph_Ground", (0.06, 0.06, 0.08, 1))
        mat_agent = _mat("Sph_Agent", (0.15, 0.45, 0.95, 1), 0.3, 2.0)
        mat_sensor = _mat("Sph_Sensor", (0.95, 0.25, 0.3, 1), 0.2, 3.0)
        mat_memory = _mat("Sph_Memory", (0.2, 0.85, 0.45, 1), 0.4, 1.5)
        mat_reason = _mat("Sph_Reason", (0.95, 0.7, 0.15, 1), 0.5, 2.0)
        mat_curious = _mat("Sph_Curious", (0.65, 0.25, 0.9, 1), 0.2, 2.5)
        mat_know = _mat("Sph_Know", (0.1, 0.8, 1.0, 1), 0.1, 3.5)
        mat_ring = _mat("Sph_Ring", (0.08, 0.08, 0.12, 1))
        mat_conn = _mat("Sph_Conn", (0.3, 0.3, 0.4, 1), 0.0, 0.3)

        bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
        ground = bpy.context.active_object
        ground.name = "Sph_Ground"
        ground.data.materials.append(mat_ground)
        self._link_to_collection(ground, self.col_sphere)

        for r in [3, 5, 7]:
            bpy.ops.mesh.primitive_circle_add(
                radius=r, vertices=64, fill_type="NGON", location=(0, 0, 0.005)
            )
            ring = bpy.context.active_object
            ring.name = f"Sph_Ring_{r}"
            ring.data.materials.append(mat_ring)
            self._link_to_collection(ring, self.col_sphere)

        self.sphere_objects = []
        defs = [
            (
                "Sph_Agent",
                mat_agent,
                lambda: bpy.ops.mesh.primitive_cube_add(size=0.9, location=(0, 0, 0.5)),
            ),
            (
                "Sph_Sensor",
                mat_sensor,
                lambda: bpy.ops.mesh.primitive_uv_sphere_add(
                    radius=0.5, segments=24, ring_count=16, location=(2.5, 0, 0.5)
                ),
            ),
            (
                "Sph_Memory",
                mat_memory,
                lambda: bpy.ops.mesh.primitive_cylinder_add(
                    radius=0.35, depth=1.4, location=(-2.5, 0, 0.7)
                ),
            ),
            (
                "Sph_Reason",
                mat_reason,
                lambda: bpy.ops.mesh.primitive_torus_add(
                    major_radius=0.45, minor_radius=0.12, location=(0, 2.5, 0.5)
                ),
            ),
            (
                "Sph_Curious",
                mat_curious,
                lambda: bpy.ops.mesh.primitive_cone_add(
                    radius1=0.4, depth=1.0, vertices=32, location=(0, -2.5, 0.5)
                ),
            ),
            (
                "Sph_Know",
                mat_know,
                lambda: bpy.ops.mesh.primitive_ico_sphere_add(
                    radius=0.4, subdivisions=2, location=(-2.5, 2.5, 0.5)
                ),
            ),
        ]
        for name, mat, create_fn in defs:
            create_fn()
            obj = bpy.context.active_object
            obj.name = name
            obj.data.materials.append(mat)
            self._link_to_collection(obj, self.col_sphere)
            self.sphere_objects.append(obj)

        self.sphere_connections = []
        pairs = [(0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (1, 5), (2, 5), (3, 4)]
        for ai, bi in pairs:
            a = self.sphere_objects[ai]
            b = self.sphere_objects[bi]
            curve_data = bpy.data.curves.new(f"Sph_Conn_{ai}_{bi}", type="CURVE")
            curve_data.dimensions = "3D"
            curve_data.bevel_depth = 0.02
            curve_data.resolution_u = 8
            spline = curve_data.splines.new("NURBS")
            spline.points.add(1)
            spline.points[0].co = (*a.location, 1)
            spline.points[1].co = (*b.location, 1)
            spline.use_endpoint_u = True
            obj = bpy.data.objects.new(f"Sph_Conn_{ai}_{bi}", curve_data)
            bpy.context.collection.objects.link(obj)
            obj.data.materials.append(mat_conn)
            self._link_to_collection(obj, self.col_sphere)
            self.sphere_connections.append((obj, a, b, spline))

    # ================================================================
    # Animation
    # ================================================================
    def animate(self):
        t = self.frame * 0.04

        if self.mode in ("sphere", "both") and self.sphere_objects:
            self._animate_sphere(t)
        if self.mode in ("anatomy", "both"):
            self._animate_anatomy(t)

        cam_angle = t * 0.12
        if self.world_name and self.world_name in ALL_WORLDS:
            dist = 12
            height = 8
        elif self.mode == "anatomy":
            dist = 7
            height = 5
        else:
            dist = 8
            height = 5

        self.cam.location = (
            dist * math.cos(cam_angle),
            dist * math.sin(cam_angle),
            height + 1.5 * math.sin(t * 0.08),
        )
        if self.cam_target:
            self.cam_target.location = (0, 0, 1.2)

        self.scene.frame_set(self.frame % 250 + 1)

    def _animate_sphere(self, t):
        obj = self.sphere_objects
        if not obj:
            return

        pulse = 1.0 + 0.15 * math.sin(t * 2.5)
        obj[0].scale = (pulse, pulse, pulse)
        obj[0].rotation_euler = (t * 0.3, t * 0.2, 0)

        obj[1].location = (
            2.8 * math.cos(t * 0.8),
            2.8 * math.sin(t * 0.8),
            0.5 + 0.3 * math.sin(t * 1.5),
        )
        obj[2].location = (-2.5 + 0.5 * math.sin(t * 0.3), 0.5 * math.cos(t * 0.4), 0.7)
        obj[2].rotation_euler = (0, 0, t * 0.15)
        obj[3].location = (
            2.5 * math.cos(t * 0.6 + math.pi),
            2.5 * math.sin(t * 0.6 + math.pi),
            0.5 + 0.5 * math.sin(t * 0.8),
        )
        obj[3].rotation_euler = (t * 0.8, t * 0.6, 0)
        obj[4].location = (
            2.5 * math.cos(t * 0.7 + math.pi / 2) + 0.5 * math.sin(t * 3),
            2.5 * math.sin(t * 0.7 + math.pi / 2) + 0.3 * math.cos(t * 2.5),
            0.5 + 0.4 * abs(math.sin(t * 1.2)),
        )
        obj[4].rotation_euler = (t * 1.0, t * 0.7, t * 0.5)
        obj[5].location = (
            -2.5 + 0.8 * math.sin(t * 0.5),
            2.5 + 0.6 * math.cos(t * 0.6),
            0.5 + 0.4 * math.sin(t * 0.9),
        )
        obj[5].rotation_euler = (t * 0.4, t * 0.3, t * 0.2)

        for _, a, b, spline in self.sphere_connections:
            spline.points[0].co = (*a.location, 1)
            spline.points[1].co = (*b.location, 1)

    def _animate_anatomy(self, t):
        parts = [o for o in self.col_anatomy.objects if o.type == "MESH"]
        if not parts:
            return

        breath = 0.02 * math.sin(t * 2.0)
        sway = 0.01 * math.sin(t * 0.8)
        emotion_idx = EMOTION_STATES.index(self.emotion) if self.emotion in EMOTION_STATES else 0
        emotion_t = t + emotion_idx * 1.5

        for part in parts:
            nl = part.name.lower()
            if "chest" in nl or "spine" in nl:
                part.scale.z = 1.0 + breath
            elif "neck" in nl:
                part.rotation_euler.y = sway * 0.5
            elif "head" in nl:
                part.rotation_euler.y = sway
                part.location.z = 2.1 + breath * 0.3
                if self.emotion == "curious":
                    part.rotation_euler.x = 0.15 * math.sin(emotion_t * 1.5)
                elif self.emotion == "alert":
                    part.rotation_euler.x = -0.1
                else:
                    part.rotation_euler.x = 0.05 * math.sin(emotion_t * 0.5)
            elif "l_upperarm" in nl:
                if self.emotion == "excited":
                    part.rotation_euler.z = 0.3 * math.sin(emotion_t * 2)
                elif self.emotion == "confused":
                    part.rotation_euler.z = -0.5 + 0.2 * math.sin(emotion_t)
                else:
                    part.rotation_euler.z = 0.1 * math.sin(emotion_t * 0.5)
            elif "r_upperarm" in nl:
                if self.emotion == "excited":
                    part.rotation_euler.z = -0.3 * math.sin(emotion_t * 2)
                else:
                    part.rotation_euler.z = -0.1 * math.sin(emotion_t * 0.5)
            elif "l_hand" in nl or "r_hand" in nl:
                tremor = 0.02 * self.arousal * math.sin(emotion_t * 8)
                part.location.x += tremor
            elif "thigh" in nl or "shin" in nl:
                part.rotation_euler.x = 0.05 * math.sin(emotion_t * 0.3)

    # ================================================================
    # Render — bpy scene access must remain on Blender's owning thread.
    # ================================================================
    def _render_to_file(self):
        self._render_ready = False
        self._pending_frame = None
        self._render_error = None
        try:
            # Aggressively clean depsgraph triggers before render
            self._cleanup_depsgraph_triggers()
            # Try real Cycles render
            self._try_render_cycles()
        except Exception as e:
            print(f"[Blender] Cycles render failed: {e}", flush=True)
            try:
                # Fallback: try Eevee (faster, different depsgraph path)
                self._try_render_eevee()
            except Exception as e2:
                print(f"[Blender] Eevee render failed: {e2}", flush=True)
                self._render_error = str(e2)

    def _cleanup_depsgraph_triggers(self):
        """Remove objects that trigger the Blender 5.2 depsgraph speaker crash."""
        import bpy

        # Remove ALL speaker objects
        for obj in list(bpy.data.objects):
            if obj.type == "SPEAKER":
                bpy.data.objects.remove(obj, do_unlink=True)
        # Remove orphan speaker data
        for speaker in list(bpy.data.speakers):
            bpy.data.speakers.remove(speaker)
        # Force garbage collection
        import gc

        gc.collect()

    def _try_render_cycles(self):
        """Attempt Cycles render with write_still to a temp file."""
        import base64

        import bpy

        scene = bpy.context.scene
        scene.render.engine = "CYCLES"
        scene.cycles.device = "CPU"
        scene.cycles.samples = 8  # Low samples for speed
        scene.render.resolution_x = 480
        scene.render.resolution_y = 360
        scene.render.resolution_percentage = 100

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            tmp_path = f.name
        try:
            scene.render.filepath = tmp_path
            bpy.ops.render.render(write_still=True)
            with open(tmp_path, "rb") as f:
                png_bytes = f.read()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        if len(png_bytes) > 100:  # Valid PNG
            self._pending_frame = base64.b64encode(png_bytes).decode("ascii")
            self._render_ready = True
        else:
            raise RuntimeError("Empty render output")

    def _try_render_eevee(self):
        """Attempt Eevee render (different depsgraph path, may avoid crash)."""
        import base64

        import bpy

        scene = bpy.context.scene
        scene.render.engine = "BLENDER_EEVEE"
        scene.render.resolution_x = 480
        scene.render.resolution_y = 360
        scene.render.resolution_percentage = 100

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            tmp_path = f.name
        try:
            scene.render.filepath = tmp_path
            bpy.ops.render.render(write_still=True)
            with open(tmp_path, "rb") as f:
                png_bytes = f.read()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        if len(png_bytes) > 100:
            self._pending_frame = base64.b64encode(png_bytes).decode("ascii")
            self._render_ready = True
        else:
            raise RuntimeError("Empty Eevee render")

    # ================================================================
    # WebSocket + main loop
    # ================================================================
    async def run(self):
        async def render_loop():
            while True:
                try:
                    if self.running:
                        self.animate()
                        self._render_to_file()

                        frame = self._pending_frame
                        if frame:
                            self.frame += 1
                            msg = json.dumps(
                                {
                                    "type": "frame",
                                    "data": frame,
                                    "mode": self.mode,
                                    "emotion": self.emotion,
                                    "frame": self.frame,
                                    "world": self.world_info,
                                }
                            )
                            dead = []
                            for c in self.clients.copy():
                                try:
                                    await c.send(msg)
                                except Exception:
                                    dead.append(c)
                            for d in dead:
                                self.clients.discard(d)
                        elif self._render_error:
                            error_msg = json.dumps(
                                {"type": "render_error", "error": self._render_error}
                            )
                            for c in self.frame_clients.copy():
                                try:
                                    await c.send(error_msg)
                                except Exception:
                                    self.clients.discard(c)
                except Exception as e:
                    print(f"[RenderLoop] error: {e}")
                await asyncio.sleep(0.01)

        async def handler(ws):
            self.clients.add(ws)
            self.frame_clients.add(ws)
            try:
                async for message in ws:
                    try:
                        data = json.loads(message)
                        if data.get("type") == "command":
                            cmd = data.get("command", "")
                            request_id = data.get("request_id")
                            handled = True
                            if cmd == "subscribe:telemetry":
                                self.frame_clients.discard(ws)
                            elif cmd == "reset":
                                self.frame = 0
                                self.emotion = "neutral"
                            elif cmd == "pause":
                                self.running = False
                            elif cmd == "resume":
                                self.running = True
                            elif cmd.startswith("mode:"):
                                new_mode = cmd.split(":", 1)[1]
                                if (
                                    new_mode in ("sphere", "anatomy", "both")
                                    and new_mode != self.mode
                                ):
                                    self.mode = new_mode
                                    self._update_visibility()
                            elif cmd.startswith("emotion:"):
                                parts = cmd.split(":", 2)
                                if len(parts) >= 2:
                                    self.emotion = parts[1]
                                if len(parts) >= 3:
                                    try:
                                        self.valence = float(parts[2])
                                    except ValueError:
                                        pass
                            elif cmd == "health":
                                await ws.send(
                                    json.dumps(
                                        {
                                            "type": "health",
                                            "status": "ok",
                                            "mode": self.mode,
                                            "world": self.world_name,
                                            "emotion": self.emotion,
                                            "frame": self.frame,
                                            "running": self.running,
                                            "clients": len(self.clients),
                                        }
                                    )
                                )
                            elif cmd == "worlds":
                                await ws.send(
                                    json.dumps(
                                        {
                                            "type": "world_catalog",
                                            "worlds": list_workspace_worlds(),
                                            "active": self.world_name,
                                        }
                                    )
                                )
                            elif cmd.startswith("world:"):
                                new_world = cmd.split(":", 1)[1]
                                if new_world in ALL_WORLDS or new_world == "none":
                                    self.world_name = new_world if new_world != "none" else None
                                    self.world_source = "manual"
                                    self._build_world_scene(preserve_camera=True)
                                    self._update_visibility()
                                    await ws.send(
                                        json.dumps(
                                            {
                                                "type": "world_changed",
                                                "world": self.world_info,
                                                "active": self.world_name,
                                            }
                                        )
                                    )
                                else:
                                    handled = False
                            else:
                                handled = False
                            if request_id:
                                await ws.send(
                                    json.dumps(
                                        {
                                            "type": "command_result",
                                            "request_id": request_id,
                                            "success": handled,
                                            "command": cmd,
                                            "running": self.running,
                                            "world": self.world_name,
                                            "frame": self.frame,
                                        }
                                    )
                                )
                    except Exception:
                        pass
            except websockets.exceptions.ConnectionClosed:
                pass
            finally:
                self.clients.discard(ws)
                self.frame_clients.discard(ws)

        async def agent_loop():
            """Sync with real agent state from main backend."""
            while True:
                try:
                    # Get current agent status
                    if AGENT_MANAGER_AVAILABLE and manager and manager._agent:
                        status = manager.get_status()

                        # Get current CognitiveOrchestrator emotional state if available
                        emotion_state = None
                        if hasattr(manager, "_agent") and hasattr(manager._agent, "emotional"):
                            emotion_state = manager._agent.emotional.get_stats()

                        # Update world based on agent state and autonomous selection
                        current_world_name = status.get("world", {}).get("name")

                        # Check for autonomous world selection based on agent goals and skills
                        if self.world_source == "autonomous" and self.world_selector:
                            try:
                                selector_criteria = SelectionCriteria(
                                    weak_skills=[],  # Will be populated from agent state if available
                                    max_difficulty=1.0,
                                )
                                world_result = self.world_selector.select(selector_criteria)
                                if world_result.world.name != current_world_name:
                                    current_world_name = world_result.world.name
                                    print(
                                        f"[Blender] Autonomous world selection: {current_world_name}",
                                        flush=True,
                                    )
                            except Exception as e:
                                print(f"[Blender] Autonomous selection error: {e}", flush=True)

                        if (
                            self.world_source == "autonomous"
                            and current_world_name != self.world_name
                        ):
                            self.world_name = current_world_name
                            self._build_world_scene()
                            self._update_visibility()

                        # Update mode based on agent drives and goals
                        drives = status.get("drives", {})
                        current_goals = status.get("goals", [])

                        # Make mode selection decisions based on drives and goal types
                        # Curiosity-driven exploration -> Sphere mode (abstract visualization)
                        if drives.get("curiosity", 0) > 0.6 and self.mode != "sphere":
                            self.mode = "sphere"
                            print(
                                "[Blender] Mode switched to sphere driven by curiosity", flush=True
                            )
                            self._update_visibility()
                        # Mastery/goal-driven exploration -> Anatomy mode (detailed robot visualization)
                        elif drives.get("mastery", 0) > 0.6 and self.mode not in (
                            "anatomy",
                            "both",
                        ):
                            self.mode = "anatomy"
                            print(
                                "[Blender] Mode switched to anatomy driven by mastery", flush=True
                            )
                            self._update_visibility()
                        # Learning state -> Both mode
                        elif drives.get("competence", 0) > 0.7 and self.mode != "both":
                            self.mode = "both"
                            print("[Blender] Mode switched to both for integrated view", flush=True)
                            self._update_visibility()

                        # Update emotion based on agent state and emotional triggers
                        mood = status.get("mood", "neutral")

                        # Also check emotional processor if available
                        if emotion_state and "current_mood" in emotion_state:
                            agent_mood = emotion_state["current_mood"]
                            if agent_mood != self.emotion:
                                self.emotion = agent_mood
                                print(
                                    f"[Blender] Emotion synchronized from agent: {self.emotion}",
                                    flush=True,
                                )
                        elif mood != self.emotion:
                            self.emotion = mood
                            print(
                                f"[Blender] Emotion updated from agent status: {self.emotion}",
                                flush=True,
                            )

                        # Send status updates to connected clients (UI)
                        for c in self.clients.copy():
                            try:
                                await c.send(
                                    json.dumps(
                                        {
                                            "type": "blend",
                                            "payload": {
                                                "blend_mode": self.mode,
                                                "blend_world": self.world_name,
                                                "blend_emotion": self.emotion,
                                                "blend_drives": drives,
                                                "blend_goals": len(current_goals)
                                                if isinstance(current_goals, list)
                                                else 0,
                                            },
                                        }
                                    )
                                )
                            except Exception:
                                pass

                    await asyncio.sleep(2)
                except Exception as e:
                    print(f"[AgentSync] error: {e}")
                    await asyncio.sleep(5)

        async with websockets.serve(handler, "127.0.0.1", self.port):
            print(
                f"[BlenderSim] ws://127.0.0.1:{self.port} | mode={self.mode} | world={self.world_name}"
            )
            render_task = asyncio.create_task(render_loop())
            agent_sync_task = asyncio.create_task(agent_loop())
            try:
                await asyncio.Event().wait()
            finally:
                render_task.cancel()
                agent_sync_task.cancel()
                await asyncio.gather(render_task, agent_sync_task, return_exceptions=True)


def main():
    port = 8766
    world_name = None
    for i, arg in enumerate(sys.argv):
        if arg == "--port" and i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])
        elif arg.startswith("--world="):
            world_name = arg.split("=", 1)[1]
        elif arg == "--world" and i + 1 < len(sys.argv):
            world_name = sys.argv[i + 1]

    sim = BlenderSimulation(world_name=world_name)
    sim.port = port
    asyncio.run(sim.run())


if __name__ == "__main__":
    main()
