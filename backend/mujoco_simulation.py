"""MuJoCo Simulation Server — Multi-model humanoid physics with WebSocket streaming.

Supports TOCABI (33 DOF, URDF-converted) and Unitree G1 (29 DOF, native MJCF).
Standing balance controller, bipedal walking gait, sensor integration,
joint-state telemetry streamed to UI and cognitive system.

Usage:
    python mujoco_simulation.py --port 8767 --model tocabi
    python mujoco_simulation.py --port 8767 --model g1
"""

import asyncio
import base64
import io
import json
import math
import os
import struct
import sys
import tempfile
import threading
import warnings
import xml.etree.ElementTree as ET
import zlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

warnings.filterwarnings("ignore")

src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

try:
    import mujoco
    import numpy as np

    MUJOCO_AVAILABLE = True
except ImportError:
    MUJOCO_AVAILABLE = False
    print("[MuJoCo] mujoco package not installed", flush=True)

import websockets

try:
    from blender_worlds import (
        ALL_SURVIVAL_WORLDS,
        PRACTICAL_WORLDS,
        WorldSelector,
    )

    ALL_WORLDS = {}
    ALL_WORLDS.update(PRACTICAL_WORLDS)
    for name, world in ALL_SURVIVAL_WORLDS.items():
        ALL_WORLDS[name] = world
except ImportError:
    ALL_WORLDS = {}
    WorldSelector = None

TOCABI_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "data", "blender", "models", "tocabi"
)
TOCABI_URDF = os.path.join(TOCABI_DIR, "combined", "urdf", "FullBody.urdf")
TOCABI_MESHES = os.path.join(TOCABI_DIR, "combined", "meshes")

G1_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "data", "mujoco", "models", "unitree_g1"
)
G1_XML = os.path.join(G1_DIR, "g1.xml")

# G1 standing pose from official keyframe (29 joint actuators)
# qpos order after free joint (7): left_hip_pitch, left_hip_roll, left_hip_yaw,
# left_knee, left_ankle_pitch, left_ankle_roll, right_hip_pitch, right_hip_roll,
# right_hip_yaw, right_knee, right_ankle_pitch, right_ankle_roll, waist_yaw,
# waist_roll, waist_pitch, left_shoulder_pitch, left_shoulder_roll, left_shoulder_yaw,
# left_elbow, left_wrist_roll, left_wrist_pitch, left_wrist_yaw, right_shoulder_pitch,
# right_shoulder_roll, right_shoulder_yaw, right_elbow, right_wrist_roll, right_wrist_pitch,
# right_wrist_yaw
G1_STANDING_POSE = [
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0,      # left leg (hip_pitch=0, hip_roll=0, hip_yaw=0, knee=0, ankle_pitch=0, ankle_roll=0)
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0,      # right leg
    0.0, 0.0, 0.0,                       # waist (yaw, roll, pitch)
    0.2, 0.2, 0.0, 1.28, 0.0, 0.0, 0.0, # left arm
    0.2, -0.2, 0.0, 1.28, 0.0, 0.0, 0.0 # right arm
]

# G1 joint info — 29 DOF, all position-controlled with kp=500
G1_JOINT_NAMES = [
    "left_hip_pitch_joint", "left_hip_roll_joint", "left_hip_yaw_joint",
    "left_knee_joint", "left_ankle_pitch_joint", "left_ankle_roll_joint",
    "right_hip_pitch_joint", "right_hip_roll_joint", "right_hip_yaw_joint",
    "right_knee_joint", "right_ankle_pitch_joint", "right_ankle_roll_joint",
    "waist_yaw_joint", "waist_roll_joint", "waist_pitch_joint",
    "left_shoulder_pitch_joint", "left_shoulder_roll_joint", "left_shoulder_yaw_joint",
    "left_elbow_joint", "left_wrist_roll_joint", "left_wrist_pitch_joint", "left_wrist_yaw_joint",
    "right_shoulder_pitch_joint", "right_shoulder_roll_joint", "right_shoulder_yaw_joint",
    "right_elbow_joint", "right_wrist_roll_joint", "right_wrist_pitch_joint", "right_wrist_yaw_joint",
]

G1_JOINT_FUNCTIONS = {
    "left_hip_pitch_joint": ("left", "hip_pitch"),
    "left_hip_roll_joint": ("left", "hip_roll"),
    "left_hip_yaw_joint": ("left", "hip_yaw"),
    "left_knee_joint": ("left", "knee"),
    "left_ankle_pitch_joint": ("left", "ankle_pitch"),
    "left_ankle_roll_joint": ("left", "ankle_roll"),
    "right_hip_pitch_joint": ("right", "hip_pitch"),
    "right_hip_roll_joint": ("right", "hip_roll"),
    "right_hip_yaw_joint": ("right", "hip_yaw"),
    "right_knee_joint": ("right", "knee"),
    "right_ankle_pitch_joint": ("right", "ankle_pitch"),
    "right_ankle_roll_joint": ("right", "ankle_roll"),
    "waist_yaw_joint": ("center", "waist_yaw"),
    "waist_roll_joint": ("center", "waist_roll"),
    "waist_pitch_joint": ("center", "waist_pitch"),
    "left_shoulder_pitch_joint": ("left", "shoulder_pitch"),
    "left_shoulder_roll_joint": ("left", "shoulder_roll"),
    "left_shoulder_yaw_joint": ("left", "shoulder_yaw"),
    "left_elbow_joint": ("left", "elbow"),
    "left_wrist_roll_joint": ("left", "wrist_roll"),
    "left_wrist_pitch_joint": ("left", "wrist_pitch"),
    "left_wrist_yaw_joint": ("left", "wrist_yaw"),
    "right_shoulder_pitch_joint": ("right", "shoulder_pitch"),
    "right_shoulder_roll_joint": ("right", "shoulder_roll"),
    "right_shoulder_yaw_joint": ("right", "shoulder_yaw"),
    "right_elbow_joint": ("right", "elbow"),
    "right_wrist_roll_joint": ("right", "wrist_roll"),
    "right_wrist_pitch_joint": ("right", "wrist_pitch"),
    "right_wrist_yaw_joint": ("right", "wrist_yaw"),
}

EMOTION_STATES = [
    "neutral", "thinking", "curious", "excited",
    "focused", "confused", "satisfied", "alert",
]


# ─── Control Modes ────────────────────────────────────────────────────────

class RobotModel(Enum):
    TOCABI = "tocabi"
    G1 = "g1"


class ControlMode(Enum):
    STAND = "stand"
    WALK = "walk"
    FREEZE = "freeze"
    GRAVITY_COMP = "gravity_comp"


class WalkPhase(Enum):
    IDLE = "idle"
    LEFT_SWING = "left_swing"
    LEFT_SUPPORT = "left_support"
    RIGHT_SWING = "right_swing"
    RIGHT_SUPPORT = "right_support"


# ─── TOCABI Joint Map ─────────────────────────────────────────────────────
# Maps URDF joint names to body-side + function for gait control.

@dataclass
class JointInfo:
    """Metadata for a single revolute joint in TOCABI."""
    name: str
    mj_index: int
    side: str          # "left", "right", "center"
    function: str      # "hip_pitch", "hip_roll", "knee", "ankle_pitch", "ankle_roll", "waist", "arm", etc.
    lower: float
    upper: float
    standing_angle: float  # target angle (rad) for standing pose


STANDING_POSE: dict[str, float] = {}
JOINT_INFO_MAP: dict[str, JointInfo] = {}


def _classify_joint(joint_name: str, child_link: str, axis: tuple[float, float, float]) -> tuple[str, str]:
    """Classify a TOCABI joint by its child link name and axis direction into (side, function).

    TOCABI naming: LL_ = left leg, LR_ = right leg, UL_ = left arm, UR_ = right arm, U_ = center.
    Axis conventions (after normalization):
        [0, 0, ±1] = sagittal plane → pitch (hip_pitch, ankle_pitch if leg)
        [±1, 0, 0] = frontal plane → roll (hip_roll, ankle_roll if leg)
        [0, ±1, 0] = transverse plane → yaw (hip_yaw)
    """
    cl = child_link.lower()
    ax = tuple(round(a, 2) for a in axis)

    # Side from child link prefix
    if cl.startswith("ll_") or cl.startswith("ul_"):
        side = "left"
    elif cl.startswith("lr_") or cl.startswith("ur_"):
        side = "right"
    elif "left" in cl:
        side = "left"
    elif "right" in cl:
        side = "right"
    else:
        side = "center"

    # Function from child link + axis
    if "hip" in cl:
        # Classify by axis direction
        if abs(ax[2]) > 0.5:    # z-axis → pitch
            func = "hip_pitch"
        elif abs(ax[0]) > 0.5:  # x-axis → roll
            func = "hip_roll"
        elif abs(ax[1]) > 0.5:  # y-axis → yaw
            func = "hip_yaw"
        else:
            func = "hip_pitch"
    elif "knee" in cl:
        func = "knee"
    elif "ankle" in cl:
        if abs(ax[1]) > 0.5:    # y-axis → pitch (for ankle in leg)
            func = "ankle_pitch"
        elif abs(ax[0]) > 0.5:  # x-axis → roll
            func = "ankle_roll"
        else:
            func = "ankle_pitch"
    elif "waist" in cl or "body" in cl:
        func = "waist"
    elif "shoulder" in cl:
        func = "shoulder"
    elif "arm" in cl:
        func = "arm"
    elif "wrist" in cl:
        func = "wrist"
    elif "neck" in cl:
        func = "head"
    else:
        func = "other"
    return side, func


def _standing_angle(side: str, func: str) -> float:
    """Return target standing angle (rad) for each joint type.

    TOCABI is ~1.8m tall, ~100kg. Standing pose:
    - Slight knee bend for compliance
    - Hip flexion to move COM over support polygon
    - Ankle dorsiflexion to keep feet flat
    - Arms relaxed at sides

    Note: left/right legs have mirrored URDF axes, so standing angles
    must be applied with the correct sign per side.
    """
    # Base angles (positive = forward flexion for hip_pitch, positive = flexion for knee)
    angles = {
        "hip_pitch": 0.08,
        "hip_roll": 0.0,
        "hip_yaw": 0.0,
        "knee": 0.12,
        "ankle_pitch": -0.06,
        "ankle_roll": 0.0,
        "waist": 0.0,
        "shoulder": 0.0,
        "arm": 0.0,
        "wrist": 0.0,
        "head": 0.0,
        "other": 0.0,
    }
    return angles.get(func, 0.0)


# ─── URDF → MJCF Converter ──────────────────────────────────────────────

def _normalize_axis(axis_str: str) -> tuple[float, float, float]:
    parts = [float(x) for x in axis_str.split()]
    norm = math.sqrt(sum(x * x for x in parts))
    if norm > 0:
        return tuple(x / norm for x in parts)
    return (0.0, 0.0, 1.0)


def _parse_origin(elem: ET.Element) -> tuple[list[float], list[float]]:
    xyz = [0.0, 0.0, 0.0]
    rpy = [0.0, 0.0, 0.0]
    if elem is not None:
        xyz_str = elem.get("xyz", "0 0 0")
        xyz = [float(x) for x in xyz_str.split()]
        rpy_str = elem.get("rpy", "0 0 0")
        rpy = [float(x) for x in rpy_str.split()]
    return xyz, rpy


def _inertia_to_box(ixx: float, iyy: float, izz: float, mass: float) -> list[float]:
    """Derive equivalent box half-sizes from diagonal inertia + mass.

    For a uniform box of half-sizes (a, b, c) and mass m:
        Ixx = m/12 * (4b² + 4c²),  Iyy = m/12 * (4a² + 4c²),  Izz = m/12 * (4a² + 4b²)
    Solve for a, b, c.
    """
    inv_m = 12.0 / max(mass, 1e-6)
    # b² + c² = Ixx * inv_m / 4
    # a² + c² = Iyy * inv_m / 4
    # a² + b² = Izz * inv_m / 4
    rxx = max(ixx * inv_m / 4.0, 1e-8)
    ryy = max(iyy * inv_m / 4.0, 1e-8)
    rzz = max(izz * inv_m / 4.0, 1e-8)
    a2 = (ryy + rzz - rxx) / 2.0
    b2 = (rxx + rzz - ryy) / 2.0
    c2 = (rxx + ryy - rzz) / 2.0
    a = math.sqrt(max(a2, 1e-8))
    b = math.sqrt(max(b2, 1e-8))
    c = math.sqrt(max(c2, 1e-8))
    # Clamp to reasonable range
    lo, hi = 0.005, 0.20
    return [max(lo, min(hi, a)), max(lo, min(hi, b)), max(lo, min(hi, c))]


def _convert_urdf_to_mjcf(urdf_path: str, meshes_dir: str) -> str:
    tree = ET.parse(urdf_path)
    root = tree.getroot()

    links = {}
    for link_elem in root.findall("link"):
        name = link_elem.get("name")
        inertial = link_elem.find("inertial")
        mass = 1.0
        inertia = [0.01, 0.01, 0.01]
        com = [0.0, 0.0, 0.0]
        if inertial is not None:
            mass_elem = inertial.find("mass")
            if mass_elem is not None:
                mass = float(mass_elem.get("value", "1.0"))
            inertia_elem = inertial.find("inertia")
            if inertia_elem is not None:
                inertia = [
                    float(inertia_elem.get("ixx", "0.01")),
                    float(inertia_elem.get("iyy", "0.01")),
                    float(inertia_elem.get("izz", "0.01")),
                ]
            origin_elem = inertial.find("origin")
            if origin_elem is not None:
                com, _ = _parse_origin(origin_elem)

        collision = link_elem.find("collision")
        mesh_file = None
        mesh_scale = [0.001, 0.001, 0.001]
        geom_type = "box"
        geom_size = [0.05, 0.05, 0.05]
        geom_offset = [0.0, 0.0, 0.0]

        if collision is not None:
            origin = collision.find("origin")
            if origin is not None:
                geom_offset, _ = _parse_origin(origin)
            geom = collision.find("geometry")
            if geom is not None:
                mesh_elem = geom.find("mesh")
                if mesh_elem is not None:
                    mesh_file = mesh_elem.get("filename", "")
                    scale_str = mesh_elem.get("scale", "0.001 0.001 0.001")
                    mesh_scale = [float(x) for x in scale_str.split()]
                    geom_type = "mesh"
                box_elem = geom.find("box")
                if box_elem is not None:
                    size_str = box_elem.get("size", "0.1 0.1 0.1")
                    sizes = [float(x) for x in size_str.split()]
                    geom_size = [s / 2 for s in sizes]
                    geom_type = "box"
                sphere_elem = geom.find("sphere")
                if sphere_elem is not None:
                    radius = float(sphere_elem.get("radius", "0.1"))
                    geom_size = [radius]
                    geom_type = "sphere"
                cylinder_elem = geom.find("cylinder")
                if cylinder_elem is not None:
                    radius = float(cylinder_elem.get("radius", "0.05"))
                    length = float(cylinder_elem.get("length", "0.1"))
                    geom_size = [radius, length / 2]
                    geom_type = "cylinder"

        links[name] = {
            "mass": mass,
            "inertia": inertia,
            "com": com,
            "mesh_file": mesh_file,
            "mesh_scale": mesh_scale,
            "geom_type": geom_type,
            "geom_size": geom_size,
            "geom_offset": geom_offset,
        }

    joints = []
    for joint_elem in root.findall("joint"):
        name = joint_elem.get("name")
        jtype = joint_elem.get("type")
        parent_elem = joint_elem.find("parent")
        child_elem = joint_elem.find("child")
        parent_link = parent_elem.get("link") if parent_elem is not None else ""
        child_link = child_elem.get("link") if child_elem is not None else ""
        origin_elem = joint_elem.find("origin")
        xyz, rpy = _parse_origin(origin_elem)
        axis_elem = joint_elem.find("axis")
        axis = _normalize_axis(axis_elem.get("xyz", "0 0 1")) if axis_elem is not None else (0, 0, 1)
        limit_elem = joint_elem.find("limit")
        lower = -3.14159
        upper = 3.14159
        if limit_elem is not None:
            lower = float(limit_elem.get("lower", "-3.14159"))
            upper = float(limit_elem.get("upper", "3.14159"))
        joints.append({
            "name": name,
            "type": jtype,
            "parent": parent_link,
            "child": child_link,
            "xyz": xyz,
            "rpy": rpy,
            "axis": axis,
            "lower": lower,
            "upper": upper,
        })

    global STANDING_POSE, JOINT_INFO_MAP

    lines = ['<mujoco model="tocabi">']
    lines.append('  <compiler meshdir="{}" balanceinertia="true" autolimits="true"/>'.format(
        meshes_dir.replace("\\", "/")
    ))
    lines.append('  <option timestep="0.002" gravity="0 0 -9.81" integrator="implicit"/>')
    lines.append('  <default>')
    lines.append('    <joint armature="0.02" damping="30" limited="true"/>')
    lines.append('    <geom condim="4" friction="1.0 0.5 0.01" margin="0.005" solref="0.02 1"/>')
    lines.append('  </default>')
    lines.append('  <asset>')
    lines.append('    <texture type="2d" name="ground" builtin="checker" '
                 'rgb1="0.2 0.3 0.4" rgb2="0.1 0.15 0.2" width="512" height="512"/>')
    lines.append('    <material name="ground_mat" texture="ground" texrepeat="20 20"/>')
    lines.append('    <material name="robot_mat" rgba="0.6 0.65 0.7 1"/>')
    lines.append('    <material name="robot_left" rgba="0.3 0.6 0.9 1"/>')
    lines.append('    <material name="robot_right" rgba="0.9 0.4 0.3 1"/>')
    lines.append('  </asset>')
    # Sensors are read directly from data.contact / data.sensordata
    lines.append('  <worldbody>')
    lines.append('    <geom name="floor" type="plane" size="5 5 0.1" material="ground_mat" '
                 'condim="4" friction="1.0 0.5 0.01"/>')
    lines.append('    <light pos="0 0 3" dir="0 0 -1" diffuse="0.8 0.8 0.8"/>')
    lines.append('    <light pos="2 2 2" dir="-1 -1 -1" diffuse="0.4 0.4 0.4"/>')

    child_links = {j["child"] for j in joints}
    root_link = None
    for link_name in links:
        if link_name not in child_links:
            root_link = link_name
            break
    if root_link is None:
        root_link = list(links.keys())[0]

    children_map: dict[str, list[dict]] = {}
    for j in joints:
        if j["type"] == "fixed":
            continue
        children_map.setdefault(j["parent"], []).append(j)

    def _emit_body(link_name: str, depth: int = 0, body_offset: list[float] | None = None) -> list[str]:
        result = []
        indent = "      " + "  " * depth
        link = links[link_name]

        mesh_name = None
        if link["mesh_file"]:
            mesh_path = link["mesh_file"]
            if "package://" in mesh_path:
                mesh_path = mesh_path.replace("package://meshes/", "")
            mesh_name = Path(mesh_path).stem
            scale = link["mesh_scale"]
            full_path = os.path.join(meshes_dir, mesh_path)
            if os.path.exists(full_path):
                file_size = os.path.getsize(full_path)
                est_faces = (file_size - 84) // 50
                if est_faces <= 200000:
                    all_meshes[mesh_name] = (mesh_path, scale)
                else:
                    mesh_name = None

        body_name = link_name.replace(" ", "_")
        if body_offset:
            bo = body_offset
            result.append(f'{indent}<body name="{body_name}" pos="{bo[0]:.6f} {bo[1]:.6f} {bo[2]:.6f}">')
        else:
            result.append(f'{indent}<body name="{body_name}">')

        com = link["com"]
        inertial_line = (f'{indent}  <inertial pos="{com[0]:.6f} {com[1]:.6f} {com[2]:.6f}" '
                         f'mass="{link["mass"]:.4f}" '
                         f'diaginertia="{link["inertia"][0]:.6f} {link["inertia"][1]:.6f} '
                         f'{link["inertia"][2]:.6f}"/>')
        result.append(inertial_line)

        offset = link["geom_offset"]
        # Pick material based on link name
        mat = "robot_mat"
        nl = link_name.lower()
        if nl.startswith("l_") or "left" in nl:
            mat = "robot_left"
        elif nl.startswith("r_") or "right" in nl:
            mat = "robot_right"

        if link["geom_type"] == "mesh" and mesh_name:
            result.append(
                f'{indent}  <geom type="mesh" mesh="{mesh_name}" '
                f'pos="{offset[0]:.6f} {offset[1]:.6f} {offset[2]:.6f}" '
                f'material="{mat}"/>'
            )
        elif link["geom_type"] == "mesh" and not mesh_name:
            # Derive box from inertia tensor (much better than mass-based)
            box = _inertia_to_box(*link["inertia"], link["mass"])
            result.append(
                f'{indent}  <geom type="box" size="{box[0]:.4f} {box[1]:.4f} {box[2]:.4f}" '
                f'pos="{offset[0]:.6f} {offset[1]:.6f} {offset[2]:.6f}" '
                f'material="{mat}"/>'
            )
        elif link["geom_type"] == "box":
            s = link["geom_size"]
            result.append(
                f'{indent}  <geom type="box" size="{s[0]:.4f} {s[1]:.4f} {s[2]:.4f}" '
                f'pos="{offset[0]:.6f} {offset[1]:.6f} {offset[2]:.6f}" '
                f'material="{mat}" contype="0"/>'
            )
        elif link["geom_type"] == "sphere":
            result.append(
                f'{indent}  <geom type="sphere" size="{link["geom_size"][0]:.4f}" '
                f'pos="{offset[0]:.6f} {offset[1]:.6f} {offset[2]:.6f}" '
                f'material="{mat}" contype="0"/>'
            )
        elif link["geom_type"] == "cylinder":
            result.append(
                f'{indent}  <geom type="cylinder" size="{link["geom_size"][0]:.4f} {link["geom_size"][1]:.4f}" '
                f'pos="{offset[0]:.6f} {offset[1]:.6f} {offset[2]:.6f}" '
                f'material="{mat}" contype="0"/>'
            )

        for j in children_map.get(link_name, []):
            axis = j["axis"]
            joint_range = f'range="{math.degrees(j["lower"]):.1f} {math.degrees(j["upper"]):.1f}"'
            # Joint at origin of child body (pos="0 0 0")
            result.append(
                f'{indent}  <joint name="{j["name"]}" type="hinge" '
                f'axis="{axis[0]:.4f} {axis[1]:.4f} {axis[2]:.4f}" '
                f'{joint_range}/>'
            )
            child_lines = _emit_body(j["child"], depth + 1, body_offset=j["xyz"])
            result.extend(child_lines)

        result.append(f'{indent}</body>')
        return result

    all_meshes: dict[str, tuple[str, list[float]]] = {}
    body_lines = _emit_body(root_link, 0)

    mesh_decls = []
    for mesh_name, (mesh_path, scale) in all_meshes.items():
        mesh_decls.append(
            f'    <mesh name="{mesh_name}" file="{mesh_path}" '
            f'scale="{scale[0]} {scale[1]} {scale[2]}"/>'
        )

    asset_end = lines.index('  </asset>')
    for decl in mesh_decls:
        lines.insert(asset_end, decl)

    lines.append('    <body name="tocabi_root" pos="0 0 1.2">')
    lines.append('      <inertial pos="0 0 0" mass="0.01" diaginertia="0.001 0.001 0.001"/>')
    lines.append('      <joint name="root_free" type="free"/>')
    for line in body_lines:
        if "<mesh" not in line:
            lines.append(line)
    lines.append('    </body>')
    lines.append('  </worldbody>')
    lines.append('  <actuator>')
    mj_joint_idx = 0
    for j in joints:
        if j["type"] == "revolute":
            side, func = _classify_joint(j["name"], j["child"], j["axis"])
            sa = _standing_angle(side, func)
            STANDING_POSE[j["name"]] = sa
            JOINT_INFO_MAP[j["name"]] = JointInfo(
                name=j["name"],
                mj_index=mj_joint_idx,
                side=side,
                function=func,
                lower=j["lower"],
                upper=j["upper"],
                standing_angle=sa,
            )
            # Position-controlled actuators — high kp for stiff position hold
            lines.append(
                f'    <position joint="{j["name"]}" kp="1000" '
                f'ctrlrange="-500 500" ctrllimited="true" kv="100"/>'
            )
            mj_joint_idx += 1
    lines.append('  </actuator>')
    lines.append('</mujoco>')

    return "\n".join(lines)


# ─── Standing + Walking Controller ───────────────────────────────────────

class TocabiController:
    """PD position controller + sinusoidal bipedal gait for TOCABI."""

    def __init__(self):
        self.mode = ControlMode.STAND
        self.walk_phase = 0.0
        self.walk_frequency = 2.0
        self.walk_speed = 0.4
        self.walk_yaw_rate = 0.0
        self.walk_cmd_linear = 0.0
        self.walk_cmd_angular = 0.0
        self.time = 0.0

    def set_walk_cmd(self, linear: float, angular: float):
        self.walk_cmd_linear = max(-1.0, min(1.0, linear))
        self.walk_cmd_angular = max(-1.0, min(1.0, angular))

    def compute_ctrl(self, model, data) -> list[float]:
        """Compute joint target positions for position actuators.

        ctrl[i] = target angle for position actuator i.
        """
        n_joints = min(model.nu, data.ctrl.shape[0])
        targets = np.zeros(n_joints)

        if self.mode == ControlMode.FREEZE or self.mode == ControlMode.GRAVITY_COMP:
            for jnt_idx in range(model.njnt):
                jname = model.joint(jnt_idx).name
                if jname == "root_free":
                    continue
                ctrl_idx = jnt_idx - 1
                if 0 <= ctrl_idx < n_joints:
                    adr = model.joint(jnt_idx).qposadr[0]
                    if adr < len(data.qpos):
                        targets[ctrl_idx] = data.qpos[adr]
        elif self.mode == ControlMode.STAND:
            for name, info in JOINT_INFO_MAP.items():
                if info.mj_index < n_joints:
                    targets[info.mj_index] = info.standing_angle
        elif self.mode == ControlMode.WALK:
            targets = self._gait_targets(n_joints)

        return targets.tolist()

    def _compute_gravity_comp_torques(self, model, data) -> np.ndarray:
        """Compute approximate gravity compensation torques using recursive algorithm."""
        n = min(model.nu, data.ctrl.shape[0])
        torques = np.zeros(n)
        if model is None or data is None:
            return torques

        # Use MuJoCo's built-in computation: tau_grav = M * qacc_grav
        # where qacc_grav is the acceleration due to gravity with zero velocity
        try:
            # Save state
            qpos_save = data.qpos.copy()
            qvel_save = data.qvel.copy()

            # Set zero velocity, compute gravity torques
            data.qvel[:] = 0.0
            mujoco.mj_forward(model, data)

            # Compute C (Coriolis + gravity) and M (mass matrix)
            mujoco.mj_comVel(model, data)

            # The bias force C includes gravity effects
            # tau_grav ≈ data.qfrc_bias[:n] (gravity compensation)
            for i in range(n):
                # Find the corresponding qfrc_bias index
                jnt_idx = i + 1  # skip root_free
                if jnt_idx < model.njnt:
                    adr = model.joint(jnt_idx).qposadr[0]
                    if adr < len(data.qfrc_bias):
                        torques[i] = data.qfrc_bias[adr]

            # Restore state
            data.qpos[:] = qpos_save
            data.qvel[:] = qvel_save
            mujoco.mj_forward(model, data)
        except Exception as e:
            print(f"[MuJoCo] gravity comp error: {e}", flush=True)

        return torques

    def _gait_targets(self, n_joints: int) -> np.ndarray:
        """Generate sinusoidal gait target angles for bipedal walking."""
        targets = np.zeros(n_joints)
        self.walk_phase += self.walk_frequency * 0.002
        if self.walk_phase > 2 * math.pi:
            self.walk_phase -= 2 * math.pi

        speed_factor = abs(self.walk_cmd_linear)
        if speed_factor < 0.01:
            # Stand still
            for name, info in JOINT_INFO_MAP.items():
                if info.mj_index < n_joints:
                    targets[info.mj_index] = info.standing_angle
            return targets

        phase = self.walk_phase

        for name, info in JOINT_INFO_MAP.items():
            if info.mj_index >= n_joints:
                continue
            if info.function == "hip_pitch":
                if info.side == "left":
                    targets[info.mj_index] = info.standing_angle + 0.3 * speed_factor * math.sin(phase)
                elif info.side == "right":
                    targets[info.mj_index] = info.standing_angle + 0.3 * speed_factor * math.sin(phase + math.pi)
            elif info.function == "knee":
                # Knees bend during swing phase
                if info.side == "left":
                    swing = max(0, math.sin(phase))
                    targets[info.mj_index] = info.standing_angle + 0.4 * speed_factor * swing
                elif info.side == "right":
                    swing = max(0, math.sin(phase + math.pi))
                    targets[info.mj_index] = info.standing_angle + 0.4 * speed_factor * swing
            elif info.function == "ankle_pitch":
                if info.side == "left":
                    targets[info.mj_index] = info.standing_angle - 0.15 * speed_factor * math.sin(phase)
                elif info.side == "right":
                    targets[info.mj_index] = info.standing_angle - 0.15 * speed_factor * math.sin(phase + math.pi)
            elif info.function == "hip_roll":
                roll_amp = 0.05 * speed_factor
                if info.side == "left":
                    targets[info.mj_index] = info.standing_angle + roll_amp * math.sin(phase)
                elif info.side == "right":
                    targets[info.mj_index] = info.standing_angle - roll_amp * math.sin(phase)
            else:
                targets[info.mj_index] = info.standing_angle

        return targets


# ─── G1 Controller ────────────────────────────────────────────────────────

class G1Controller:
    """PD position controller for Unitree G1 (29 DOF, kp=500)."""

    def __init__(self):
        self.mode = ControlMode.STAND
        self.walk_phase = 0.0
        self.walk_frequency = 2.0
        self.walk_speed = 0.4
        self.walk_cmd_linear = 0.0
        self.walk_cmd_angular = 0.0
        self.time = 0.0
        self._ctrl_index_map: dict[str, int] = {}

    def set_ctrl_index_map(self, mapping: dict[str, int]):
        self._ctrl_index_map = mapping

    def set_walk_cmd(self, linear: float, angular: float):
        self.walk_cmd_linear = max(-1.0, min(1.0, linear))
        self.walk_cmd_angular = max(-1.0, min(1.0, angular))

    def compute_ctrl(self, model, data) -> list[float]:
        n_joints = min(model.nu, data.ctrl.shape[0])
        targets = np.zeros(n_joints)

        if self.mode == ControlMode.FREEZE or self.mode == ControlMode.GRAVITY_COMP:
            # Hold current joint positions
            for i in range(model.njnt):
                jname = model.joint(i).name
                if jname == "floating_base_joint":
                    continue
                if jname in self._ctrl_index_map:
                    ctrl_idx = self._ctrl_index_map[jname]
                    adr = model.joint(i).qposadr[0]
                    if adr < len(data.qpos) and ctrl_idx < n_joints:
                        targets[ctrl_idx] = data.qpos[adr]
        elif self.mode == ControlMode.STAND:
            for jname, ctrl_idx in self._ctrl_index_map.items():
                if ctrl_idx < n_joints and ctrl_idx < len(G1_STANDING_POSE):
                    targets[ctrl_idx] = G1_STANDING_POSE[ctrl_idx]
        elif self.mode == ControlMode.WALK:
            targets = self._gait_targets(n_joints)

        return targets.tolist()

    def _gait_targets(self, n_joints: int) -> np.ndarray:
        """Sinusoidal gait for G1 bipedal walking."""
        targets = np.zeros(n_joints)
        self.walk_phase += self.walk_frequency * 0.002
        if self.walk_phase > 2 * math.pi:
            self.walk_phase -= 2 * math.pi

        speed_factor = abs(self.walk_cmd_linear)
        if speed_factor < 0.01:
            for jname, ctrl_idx in self._ctrl_index_map.items():
                if ctrl_idx < n_joints and ctrl_idx < len(G1_STANDING_POSE):
                    targets[ctrl_idx] = G1_STANDING_POSE[ctrl_idx]
            return targets

        phase = self.walk_phase

        for jname, (side, func) in G1_JOINT_FUNCTIONS.items():
            if jname not in self._ctrl_index_map:
                continue
            ctrl_idx = self._ctrl_index_map[jname]
            if ctrl_idx >= n_joints:
                continue

            standing = G1_STANDING_POSE[ctrl_idx] if ctrl_idx < len(G1_STANDING_POSE) else 0.0

            if func == "hip_pitch":
                amp = 0.3 * speed_factor
                offset = math.pi if side == "right" else 0.0
                targets[ctrl_idx] = standing + amp * math.sin(phase + offset)
            elif func == "knee":
                amp = 0.4 * speed_factor
                if side == "left":
                    swing = max(0, math.sin(phase))
                    targets[ctrl_idx] = standing + amp * swing
                else:
                    swing = max(0, math.sin(phase + math.pi))
                    targets[ctrl_idx] = standing + amp * swing
            elif func == "ankle_pitch":
                amp = 0.15 * speed_factor
                offset = math.pi if side == "right" else 0.0
                targets[ctrl_idx] = standing - amp * math.sin(phase + offset)
            elif func == "hip_roll":
                amp = 0.05 * speed_factor
                if side == "left":
                    targets[ctrl_idx] = standing + amp * math.sin(phase)
                else:
                    targets[ctrl_idx] = standing - amp * math.sin(phase)
            else:
                targets[ctrl_idx] = standing

        return targets

class MuJoCoSensorReader:
    """Reads MuJoCo data and feeds it to the sensor_sim modules."""

    def __init__(self):
        self.imu = None
        self.force_torque = None
        try:
            from crawler_agent.cognitive.sensor_sim import IMUSensor, ForceTorqueSensor
            self.imu = IMUSensor()
            self.force_torque = ForceTorqueSensor()
        except ImportError:
            pass

    def read_imu(self, data, model=None) -> dict:
        """Read IMU from MuJoCo root body or named sensors."""
        # Try MuJoCo named sensors first (G1 has built-in IMU sensors)
        if model is not None and hasattr(data, 'sensordata') and len(data.sensordata) > 0:
            # G1 sensor order: imu-torso-angular-velocity(3), imu-torso-linear-acceleration(3),
            #                   imu-pelvis-angular-velocity(3), imu-pelvis-linear-acceleration(3)
            gyro = [0.0, 0.0, 0.0]
            accel = [0.0, 0.0, -9.81]
            for i in range(model.nsensor):
                sname = model.sensor(i).name
                adr = model.sensor(i).adr[0]
                dim = model.sensor(i).dim[0]
                vals = data.sensordata[adr:adr+dim].tolist()
                if "torso" in sname and "angular" in sname:
                    gyro = vals
                elif "torso" in sname and "linear" in sname:
                    accel = vals
            reading = self.imu.read(linear_accel=accel, angular_vel=gyro, dt=0.002)
            return reading.data

        # Fallback to root body velocities
        if self.imu is None or model is None or model.nbody < 2:
            return {"acceleration": [0, 0, -9.81], "angular_velocity": [0, 0, 0]}
        velocity = np.zeros(6)
        mujoco.mj_objectVelocity(
            model,
            data,
            mujoco.mjtObj.mjOBJ_BODY,
            1,
            velocity,
            0,
        )
        accel = velocity[3:6].tolist()
        gyro = velocity[0:3].tolist()
        reading = self.imu.read(
            linear_accel=accel,
            angular_vel=gyro,
            dt=0.002,
        )
        return reading.data

    def read_contacts(self, data, model) -> dict:
        """Read contact forces from MuJoCo."""
        contacts = []
        for i in range(data.ncon):
            c = data.contact[i]
            geom1_name = ""
            geom2_name = ""
            if c.geom1 < model.ngeom:
                geom1_name = model.geom(c.geom1).name
            if c.geom2 < model.ngeom:
                geom2_name = model.geom(c.geom2).name
            force = np.zeros(6)
            mujoco.mj_contactForce(model, data, i, force)
            contacts.append({
                "geom1": geom1_name,
                "geom2": geom2_name,
                "force": force[:3].tolist(),
                "torque": force[3:].tolist(),
            })

        total_force = [0.0, 0.0, 0.0]
        for c in contacts:
            for k in range(3):
                total_force[k] += abs(c["force"][k])

        foot_contact = {
            "left": False,
            "right": False,
        }
        for c in contacts:
            g1 = c["geom1"].lower()
            g2 = c["geom2"].lower()
            if "floor" in g1 or "floor" in g2:
                other = g2 if "floor" in g1 else g1
                if other.startswith("l_") or "left" in other:
                    foot_contact["left"] = True
                elif other.startswith("r_") or "right" in other:
                    foot_contact["right"] = True
            # G1: foot sites at ankle roll links
            for g in (g1, g2):
                if "left_ankle" in g or "left_foot" in g:
                    foot_contact["left"] = True
                elif "right_ankle" in g or "right_foot" in g:
                    foot_contact["right"] = True

        return {
            "num_contacts": len(contacts),
            "total_force": total_force,
            "contacts": contacts[:10],
            "foot_contact": foot_contact,
        }

    def read_full(self, data, model) -> dict:
        """Aggregate all sensor data."""
        result = {}
        try:
            result["imu"] = self.read_imu(data, model)
        except Exception:
            result["imu"] = {"acceleration": [0, 0, -9.81], "angular_velocity": [0, 0, 0]}
        try:
            result["contacts"] = self.read_contacts(data, model)
        except Exception:
            result["contacts"] = {"num_contacts": 0, "total_force": [0, 0, 0], "foot_contact": {"left": False, "right": False}}
        return result


# ─── MuJoCo Simulation ──────────────────────────────────────────────────

class MuJoCoSimulation:
    """MuJoCo physics simulation with WebSocket streaming."""

    def __init__(self, world_name: str | None = None, robot_model: str = "tocabi"):
        self.clients: set = set()
        self.running = True
        self.frame = 0
        self.mode = "anatomy"
        self.emotion = "neutral"
        self.valence = 0.0
        self.arousal = 0.5
        self.world_name = world_name
        self.world_info = None
        self.port = 8767

        self._render_lock = threading.Lock()
        self._pending_frame: str | None = None
        self._render_ready = False

        self.model = None
        self.data = None
        self.renderer = None
        self.camera = None
        self._ctrl_index_map: dict[str, int] = {}

        # Robot model selection
        try:
            self.robot_model = RobotModel(robot_model.lower())
        except ValueError:
            self.robot_model = RobotModel.TOCABI

        if self.robot_model == RobotModel.G1:
            self.controller = G1Controller()
        else:
            self.controller = TocabiController()
        self.sensor_reader = MuJoCoSensorReader()
        self.telemetry_interval = 5
        self._telemetry_counter = 0

        self.world_selector = WorldSelector() if WorldSelector else None

        if MUJOCO_AVAILABLE:
            self._load_model()

    def _load_model(self):
        if self.robot_model == RobotModel.G1:
            self._load_g1_model()
        else:
            self._load_tocabi_model()

    def _load_g1_model(self):
        """Load Unitree G1 from native MJCF."""
        if not os.path.exists(G1_XML):
            print(f"[MuJoCo] G1 XML not found: {G1_XML}", flush=True)
            return
        augmented_xml_path = None
        try:
            with open(G1_XML, encoding="utf-8") as f:
                xml = f.read()
            ground = (
                '<geom name="ontogeny_ground" type="plane" size="0 0 0.05" '
                'rgba="0.08 0.08 0.08 1" friction="0.9 0.02 0.001"/>'
            )
            xml = xml.replace("<worldbody>", f"<worldbody>{ground}", 1)
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".xml",
                dir=G1_DIR,
                encoding="utf-8",
                delete=False,
            ) as augmented_xml:
                augmented_xml.write(xml)
                augmented_xml_path = augmented_xml.name

            self.model = mujoco.MjModel.from_xml_path(augmented_xml_path)
            self.data = mujoco.MjData(self.model)
            self.renderer = mujoco.Renderer(self.model, height=480, width=640)
            self.camera = mujoco.MjvCamera()
            mujoco.mjv_defaultCamera(self.camera)
            self.camera.type = mujoco.mjtCamera.mjCAMERA_TRACKING
            self.camera.trackbodyid = mujoco.mj_name2id(
                self.model, mujoco.mjtObj.mjOBJ_BODY, "pelvis"
            )
            self.camera.distance = 3.0
            self.camera.azimuth = 90.0
            self.camera.elevation = -10.0

            # Build ctrl index mapping from MuJoCo actuator table
            ctrl_index_map: dict[str, int] = {}
            for i in range(self.model.nu):
                a = self.model.actuator(i)
                joint_id = a.trnid[0]
                jname = self.model.joint(joint_id).name
                ctrl_index_map[jname] = i

            self._ctrl_index_map = ctrl_index_map
            self.controller.set_ctrl_index_map(ctrl_index_map)
            self._reset_simulation_state()

            print(f"[MuJoCo] G1 loaded: {self.model.nbody} bodies, "
                  f"{self.model.njnt} joints, {self.model.ngeom} geoms, "
                  f"{self.model.nu} actuators", flush=True)
            for jname, ci in sorted(ctrl_index_map.items(), key=lambda x: x[1]):
                side, func = G1_JOINT_FUNCTIONS.get(jname, ("?", "?"))
                print(f"  ctrl[{ci:2d}] {jname:30s} side={side:5s} func={func}", flush=True)
        except Exception as e:
            print(f"[MuJoCo] Failed to load G1: {e}", flush=True)
            import traceback
            traceback.print_exc()
            self.model = None
        finally:
            if augmented_xml_path and os.path.exists(augmented_xml_path):
                os.unlink(augmented_xml_path)

    def _load_tocabi_model(self):
        """Load TOCABI from URDF → MJCF conversion."""
        if not os.path.exists(TOCABI_URDF):
            print(f"[MuJoCo] URDF not found: {TOCABI_URDF}", flush=True)
            return
        try:
            mjcf_xml = _convert_urdf_to_mjcf(TOCABI_URDF, TOCABI_MESHES)
            mjcf_path = os.path.join(tempfile.gettempdir(), "tocabi_mujoco.xml")
            with open(mjcf_path, "w") as f:
                f.write(mjcf_xml)

            self.model = mujoco.MjModel.from_xml_path(mjcf_path)
            self.data = mujoco.MjData(self.model)
            self.renderer = mujoco.Renderer(self.model, height=480, width=640)

            # Build correct ctrl-index mapping from MuJoCo's actuator table
            # ctrl[i] -> joint at model.actuator(i).trnid[0]
            ctrl_index_map: dict[str, int] = {}
            for i in range(self.model.nu):
                a = self.model.actuator(i)
                joint_id = a.trnid[0]
                jname = self.model.joint(joint_id).name
                ctrl_index_map[jname] = i

            self._ctrl_index_map = ctrl_index_map
            # Update JOINT_INFO_MAP with correct ctrl indices
            for name, info in JOINT_INFO_MAP.items():
                if name in ctrl_index_map:
                    info.mj_index = ctrl_index_map[name]

            self._reset_simulation_state()

            print(f"[MuJoCo] Model loaded: {self.model.nbody} bodies, "
                  f"{self.model.njnt} joints, {self.model.ngeom} geoms", flush=True)
            print(f"[MuJoCo] Joint info map: {len(JOINT_INFO_MAP)} joints classified", flush=True)
            print(f"[MuJoCo] Standing pose targets: {len(STANDING_POSE)} joints", flush=True)
            for name, info in sorted(JOINT_INFO_MAP.items(), key=lambda x: x[1].mj_index):
                print(f"  ctrl[{info.mj_index:2d}] {name:20s} side={info.side} func={info.function:15s} stand={info.standing_angle:.3f}", flush=True)
        except Exception as e:
            print(f"[MuJoCo] Failed to load model: {e}", flush=True)
            import traceback
            traceback.print_exc()
            self.model = None

    def _reset_simulation_state(self):
        """Restore the selected robot to its deterministic standing state."""
        self.frame = 0
        self.controller.mode = ControlMode.STAND
        self.controller.walk_phase = 0.0
        self.controller.walk_cmd_linear = 0.0
        self.controller.walk_cmd_angular = 0.0
        self.controller.time = 0.0

        if self.model is None or self.data is None:
            return

        mujoco.mj_resetData(self.model, self.data)
        self.data.qpos[2] = 0.79 if self.robot_model == RobotModel.G1 else 1.2
        self.data.qpos[3] = 1.0

        standing_pose = G1_STANDING_POSE if self.robot_model == RobotModel.G1 else None
        for jname, ctrl_idx in self._ctrl_index_map.items():
            joint = self.model.joint(jname)
            qpos_adr = joint.qposadr[0]
            if standing_pose is not None:
                if ctrl_idx < len(standing_pose):
                    self.data.qpos[qpos_adr] = standing_pose[ctrl_idx]
            elif jname in STANDING_POSE:
                self.data.qpos[qpos_adr] = STANDING_POSE[jname]

        targets = self.controller.compute_ctrl(self.model, self.data)
        self.data.ctrl[: len(targets)] = targets
        mujoco.mj_forward(self.model, self.data)

    def _step_physics(self, dt: float = 0.002):
        if self.model is None or self.data is None:
            return
        try:
            targets = self.controller.compute_ctrl(self.model, self.data)
            n = min(self.model.nu, len(targets))
            for i in range(n):
                self.data.ctrl[i] = targets[i]

            substeps = max(1, int(dt / self.model.opt.timestep))
            for _ in range(substeps):
                mujoco.mj_step(self.model, self.data)
        except Exception as e:
            print(f"[MuJoCo] Step error: {e}", flush=True)

    def _should_step_physics(self) -> bool:
        return self.running and self.controller.mode != ControlMode.FREEZE

    def _render_frame(self) -> str | None:
        if self.model is None or self.data is None or self.renderer is None:
            return self._placeholder_frame()
        try:
            self.renderer.update_scene(self.data, camera=self.camera)
            pixels = self.renderer.render()
            return self._encode_png(pixels)
        except Exception as e:
            print(f"[MuJoCo] Render error: {e}", flush=True)
            return self._placeholder_frame()

    def _encode_png(self, pixels) -> str:
        try:
            from PIL import Image
            img = Image.fromarray(pixels)
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            return base64.b64encode(buf.getvalue()).decode("ascii")
        except ImportError:
            return base64.b64encode(pixels.tobytes()).decode("ascii")

    def _placeholder_frame(self) -> str:
        width, height = 640, 480
        base = (26, 26, 30) if self.mode == "anatomy" else (22, 22, 26)
        raw_data = bytes(base) * (width * height)

        def make_png(w, h, pixels):
            def chunk(ctype, data):
                c = ctype + data
                crc = zlib.crc32(c) & 0xFFFFFFFF
                return struct.pack(">I", len(data)) + c + struct.pack(">I", crc)
            sig = b"\x89PNG\r\n\x1a\n"
            ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            raw = b""
            for y in range(h):
                raw += b"\x00" + pixels[y * w * 3 : (y + 1) * w * 3]
            idat = chunk(b"IDAT", zlib.compress(raw))
            iend = chunk(b"IEND", b"")
            return sig + ihdr + idat + iend

        png_data = make_png(width, height, raw_data)
        return base64.b64encode(png_data).decode("ascii")

    def _get_joint_state(self) -> dict:
        if self.model is None or self.data is None:
            return {}
        state = {}
        for name, ctrl_idx in self._ctrl_index_map.items():
            joint = self.model.joint(name)
            qpos_adr = joint.qposadr[0]
            dof_adr = joint.dofadr[0]
            state[name] = {
                "pos": float(self.data.qpos[qpos_adr]),
                "vel": float(self.data.qvel[dof_adr]),
                "target": float(self.data.ctrl[ctrl_idx]),
            }
        return state

    def _get_body_state(self) -> dict:
        if self.model is None or self.data is None:
            return {"pos": [0, 0, 1], "quat": [1, 0, 0, 0], "vel": [0, 0, 0], "angvel": [0, 0, 0]}
        # Root body (tocabi_root) is body index 1
        body_idx = 1
        velocity = np.zeros(6)
        mujoco.mj_objectVelocity(
            self.model,
            self.data,
            mujoco.mjtObj.mjOBJ_BODY,
            body_idx,
            velocity,
            0,
        )
        return {
            "pos": self.data.xpos[body_idx].tolist() if len(self.data.xpos) > body_idx else [0, 0, 1],
            "quat": self.data.xquat[body_idx].tolist() if len(self.data.xquat) > body_idx else [1, 0, 0, 0],
            "vel": velocity[3:6].tolist(),
            "angvel": velocity[0:3].tolist(),
        }

    def _get_telemetry(self) -> dict:
        """Build full telemetry payload for UI + cognitive system."""
        self._telemetry_counter += 1
        body = self._get_body_state()
        joints = self._get_joint_state()
        sensor_data = {}
        try:
            sensor_data = self.sensor_reader.read_full(self.data, self.model)
        except Exception:
            pass

        # Compute COM
        com = [0.0, 0.0, 0.0]
        total_mass = 0.0
        if self.model and self.data:
            for i in range(self.model.nbody):
                mass = self.model.body_mass[i]
                com[0] += self.data.xpos[i][0] * mass
                com[1] += self.data.xpos[i][1] * mass
                com[2] += self.data.xpos[i][2] * mass
                total_mass += mass
            if total_mass > 0:
                com = [c / total_mass for c in com]

        return {
            "type": "telemetry",
            "frame": self.frame,
            "mode": self.controller.mode.value,
            "emotion": self.emotion,
            "robot_model": self.robot_model.value,
            "body": body,
            "joints": joints,
            "joint_count": len(joints),
            "com": com,
            "sensor": sensor_data,
            "sim_time": float(self.data.time) if self.data is not None else 0.0,
            "step_count": self.frame,
            "controller": {
                "mode": self.controller.mode.value,
                "walk_phase": self.controller.walk_phase,
                "walk_speed": self.controller.walk_speed,
                "walk_cmd": [self.controller.walk_cmd_linear, self.controller.walk_cmd_angular],
            },
            "world": self.world_info,
        }

    async def run(self):
        if not MUJOCO_AVAILABLE:
            print("[MuJoCo] Cannot start — mujoco package not installed", flush=True)
            return

        async def render_loop():
            target_fps = 30
            physics_dt = 1.0 / target_fps
            while True:
                try:
                    if self.running:
                        if self._should_step_physics():
                            self._step_physics(physics_dt)
                        self.frame += 1

                        frame_data = self._render_frame()
                        if frame_data:
                            self._pending_frame = frame_data
                            self._render_ready = True

                    if self._render_ready and self._pending_frame:
                        msg = json.dumps({
                            "type": "frame",
                            "data": self._pending_frame,
                            "mode": self.mode,
                            "emotion": self.emotion,
                            "frame": self.frame,
                            "world": self.world_info,
                        })
                        dead = []
                        for c in self.clients.copy():
                            try:
                                await c.send(msg)
                            except Exception:
                                dead.append(c)
                        for d in dead:
                            self.clients.discard(d)
                        self._render_ready = False

                        # Send telemetry every N frames
                        if self.frame % self.telemetry_interval == 0:
                            telem = self._get_telemetry()
                            telem_msg = json.dumps(telem)
                            for c in self.clients.copy():
                                try:
                                    await c.send(telem_msg)
                                except Exception:
                                    pass

                except Exception as e:
                    print(f"[RenderLoop] error: {e}", flush=True)
                await asyncio.sleep(1.0 / target_fps)

        async def handler(ws):
            self.clients.add(ws)
            try:
                async for message in ws:
                    try:
                        data = json.loads(message)
                        if data.get("type") == "command":
                            cmd = data.get("command", "")
                            if cmd == "reset":
                                self.emotion = "neutral"
                                self._reset_simulation_state()
                            elif cmd.startswith("model:"):
                                new_model = cmd.split(":", 1)[1].lower()
                                if new_model in ("tocabi", "g1") and new_model != self.robot_model.value:
                                    try:
                                        self.robot_model = RobotModel(new_model)
                                    except ValueError:
                                        pass
                            elif cmd == "pause":
                                self.running = False
                            elif cmd == "resume":
                                self.running = True
                            elif cmd.startswith("mode:"):
                                new_mode = cmd.split(":", 1)[1]
                                if new_mode in ("sphere", "anatomy", "both") and new_mode != self.mode:
                                    self.mode = new_mode
                            elif cmd.startswith("emotion:"):
                                parts = cmd.split(":", 2)
                                if len(parts) >= 2:
                                    self.emotion = parts[1]
                                if len(parts) >= 3:
                                    try:
                                        self.valence = float(parts[2])
                                    except ValueError:
                                        pass
                            elif cmd.startswith("world:"):
                                new_world = cmd.split(":", 1)[1]
                                if new_world in ALL_WORLDS or new_world == "none":
                                    self.world_name = new_world if new_world != "none" else None
                            elif cmd == "stand":
                                self.controller.mode = ControlMode.STAND
                                print("[MuJoCo] Mode → STAND", flush=True)
                            elif cmd == "walk":
                                self.controller.mode = ControlMode.WALK
                                if abs(self.controller.walk_cmd_linear) < 0.01:
                                    self.controller.set_walk_cmd(
                                        self.controller.walk_speed,
                                        self.controller.walk_cmd_angular,
                                    )
                                print("[MuJoCo] Mode → WALK", flush=True)
                            elif cmd == "freeze":
                                self.controller.mode = ControlMode.FREEZE
                                print("[MuJoCo] Mode → FREEZE", flush=True)
                            elif cmd.startswith("walk_cmd:"):
                                parts = cmd.split(":", 1)[1].split(",")
                                if len(parts) >= 2:
                                    self.controller.set_walk_cmd(float(parts[0]), float(parts[1]))
                                    print(f"[MuJoCo] Walk cmd: linear={parts[0]} angular={parts[1]}", flush=True)
                            elif cmd == "health":
                                telem = self._get_telemetry()
                                telem["type"] = "health"
                                telem["status"] = "ok"
                                telem["running"] = self.running
                                telem["model_loaded"] = self.model is not None
                                await ws.send(json.dumps(telem))
                            elif cmd == "telemetry":
                                telem = self._get_telemetry()
                                await ws.send(json.dumps(telem))
                    except Exception:
                        pass
            except websockets.exceptions.ConnectionClosed:
                pass
            finally:
                self.clients.discard(ws)

        async def agent_loop():
            while True:
                try:
                    try:
                        from agent_manager import manager
                        AGENT_AVAILABLE = True
                    except ImportError:
                        AGENT_AVAILABLE = False

                    if AGENT_AVAILABLE:
                        status = manager.get_status()
                        drives = status.get("drives", {})
                        mood = status.get("mood", "neutral")
                        if mood != self.emotion:
                            self.emotion = mood
                        for c in self.clients.copy():
                            try:
                                await c.send(json.dumps({
                                    "type": "blend",
                                    "payload": {
                                        "blend_mode": self.mode,
                                        "blend_world": self.world_name,
                                        "blend_emotion": self.emotion,
                                        "blend_drives": drives,
                                    },
                                }))
                            except Exception:
                                pass
                    await asyncio.sleep(2)
                except Exception as e:
                    print(f"[AgentSync] error: {e}", flush=True)
                    await asyncio.sleep(5)

        async with websockets.serve(handler, "127.0.0.1", self.port):
            print(f"[MuJoCo] ws://127.0.0.1:{self.port} | mode={self.mode} | world={self.world_name}", flush=True)
            render_task = asyncio.create_task(render_loop())
            agent_sync_task = asyncio.create_task(agent_loop())
            await asyncio.Event().wait()
            render_task.cancel()
            agent_sync_task.cancel()


def main():
    port = 8767
    world_name = None
    robot_model = "g1"
    for i, arg in enumerate(sys.argv):
        if arg == "--port" and i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])
        elif arg.startswith("--world="):
            world_name = arg.split("=", 1)[1]
        elif arg == "--world" and i + 1 < len(sys.argv):
            world_name = sys.argv[i + 1]
        elif arg.startswith("--model="):
            robot_model = arg.split("=", 1)[1]
        elif arg == "--model" and i + 1 < len(sys.argv):
            robot_model = sys.argv[i + 1]

    sim = MuJoCoSimulation(world_name=world_name, robot_model=robot_model)
    sim.port = port
    asyncio.run(sim.run())


if __name__ == "__main__":
    main()
