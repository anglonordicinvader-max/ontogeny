"""Sensor simulation - depth, lidar, IMU, force, proximity, touch, thermal.

Provides:
- Depth camera (RGB-D)
- LiDAR (point cloud)
- IMU (accelerometer + gyroscope)
- Force/torque sensor
- Proximity sensor (ultrasonic/IR)
- Touch/pressure sensor
- Thermal camera
"""

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import structlog


@dataclass
class SensorReading:
    sensor_type: str
    timestamp: float
    data: Dict
    noise_level: float = 0.0
    valid: bool = True


class DepthCamera:
    """Depth camera simulation (RGB-D like RealSense)."""

    def __init__(self, resolution: Tuple[int, int] = (640, 480), fov: float = 60.0,
                 near: float = 0.1, far: float = 10.0):
        self.resolution = resolution
        self.fov = fov
        self.near = near
        self.far = far
        self.logger = structlog.get_logger(component="depth_camera")

    def capture(self, object_positions: Dict[str, List[float]], camera_pos: List[float],
                camera_rot: List[float] = None, noise: float = 0.01) -> SensorReading:
        """Capture depth image from camera position."""
        depth_map = []
        rgb_map = []
        h, w = self.resolution

        for y in range(h):
            row = []
            for x in range(w):
                fx = (x - w / 2) / w * math.tan(math.radians(self.fov / 2))
                fy = (y - h / 2) / h * math.tan(math.radians(self.fov / 2))
                ray_dir = [fx, fy, 1.0]
                norm = math.sqrt(sum(r**2 for r in ray_dir))
                ray_dir = [r / norm for r in ray_dir]

                min_depth = self.far
                for obj_id, obj_pos in object_positions.items():
                    dx = obj_pos[0] - camera_pos[0]
                    dy = obj_pos[1] - camera_pos[1]
                    dz = obj_pos[2] - camera_pos[2]
                    t = dx * ray_dir[0] + dy * ray_dir[1] + dz * ray_dir[2]
                    if t > 0:
                        closest = [camera_pos[i] + t * ray_dir[i] for i in range(3)]
                        dist = math.sqrt(sum((closest[i] - camera_pos[i])**2 for i in range(3)))
                        if self.near < dist < min_depth:
                            min_depth = dist

                if noise > 0:
                    min_depth += random.gauss(0, noise * min_depth)
                min_depth = max(self.near, min(self.far, min_depth))
                row.append(min_depth)
            depth_map.append(row)

        return SensorReading(
            sensor_type="depth_camera",
            timestamp=0.0,
            data={"depth_map": depth_map, "resolution": self.resolution,
                  "fov": self.fov, "range": [self.near, self.far]},
            noise_level=noise,
        )


class LiDAR:
    """LiDAR simulation (point cloud generation)."""

    def __init__(self, num_rays: int = 360, horizontal_fov: float = 360.0,
                 vertical_fov: float = 30.0, range_min: float = 0.1, range_max: float = 100.0):
        self.num_rays = num_rays
        self.horizontal_fov = horizontal_fov
        self.vertical_fov = vertical_fov
        self.range_min = range_min
        self.range_max = range_max
        self.logger = structlog.get_logger(component="lidar")

    def scan(self, object_positions: Dict[str, List[float]], sensor_pos: List[float],
             noise: float = 0.02) -> SensorReading:
        """Generate point cloud scan."""
        points = []
        h_rays = self.num_rays
        v_rays = max(1, int(self.num_rays * self.vertical_fov / self.horizontal_fov))

        for i in range(h_rays):
            h_angle = (i / h_rays) * math.radians(self.horizontal_fov)
            for j in range(v_rays):
                v_angle = ((j / v_rays) - 0.5) * math.radians(self.vertical_fov)

                ray_x = math.cos(v_angle) * math.cos(h_angle)
                ray_y = math.cos(v_angle) * math.sin(h_angle)
                ray_z = math.sin(v_angle)

                min_dist = self.range_max
                for obj_id, obj_pos in object_positions.items():
                    dx = obj_pos[0] - sensor_pos[0]
                    dy = obj_pos[1] - sensor_pos[1]
                    dz = obj_pos[2] - sensor_pos[2]
                    t = dx * ray_x + dy * ray_y + dz * ray_z
                    if t > 0:
                        closest = [sensor_pos[k] + t * [ray_x, ray_y, ray_z][k] for k in range(3)]
                        dist = math.sqrt(sum((closest[k] - sensor_pos[k])**2 for k in range(3)))
                        if self.range_min < dist < min_dist:
                            min_dist = dist

                if noise > 0:
                    min_dist += random.gauss(0, noise * min_dist)
                min_dist = max(self.range_min, min(self.range_max, min_dist))

                hit_x = sensor_pos[0] + min_dist * ray_x
                hit_y = sensor_pos[1] + min_dist * ray_y
                hit_z = sensor_pos[2] + min_dist * ray_z
                points.append([hit_x, hit_y, hit_z])

        return SensorReading(
            sensor_type="lidar",
            timestamp=0.0,
            data={"point_cloud": points, "num_points": len(points),
                  "range": [self.range_min, self.range_max]},
            noise_level=noise,
        )


class IMUSensor:
    """IMU simulation (accelerometer + gyroscope)."""

    def __init__(self, noise_accel: float = 0.05, noise_gyro: float = 0.02):
        self.noise_accel = noise_accel
        self.noise_gyro = noise_gyro
        self.gravity = [0, 0, -9.81]
        self.logger = structlog.get_logger(component="imu")

    def read(self, linear_accel: List[float] = None, angular_vel: List[float] = None,
             dt: float = 0.01) -> SensorReading:
        """Read IMU data."""
        if linear_accel is None:
            linear_accel = [0, 0, 0]
        if angular_vel is None:
            angular_vel = [0, 0, 0]

        noisy_accel = [
            linear_accel[i] + self.gravity[i] + random.gauss(0, self.noise_accel)
            for i in range(3)
        ]
        noisy_gyro = [
            angular_vel[i] + random.gauss(0, self.noise_gyro)
            for i in range(3)
        ]

        return SensorReading(
            sensor_type="imu",
            timestamp=0.0,
            data={
                "acceleration": noisy_accel,
                "angular_velocity": noisy_gyro,
                "gravity": self.gravity,
                "dt": dt,
            },
            noise_level=max(self.noise_accel, self.noise_gyro),
        )


class ForceTorqueSensor:
    """Force/torque sensor simulation."""

    def __init__(self, range_force: float = 100.0, range_torque: float = 50.0,
                 noise: float = 0.01):
        self.range_force = range_force
        self.range_torque = range_torque
        self.noise = noise
        self.logger = structlog.get_logger(component="force_torque")

    def read(self, force: List[float] = None, torque: List[float] = None) -> SensorReading:
        """Read force/torque data."""
        if force is None:
            force = [0, 0, 0]
        if torque is None:
            torque = [0, 0, 0]

        noisy_force = [f + random.gauss(0, self.noise * self.range_force) for f in force]
        noisy_torque = [t + random.gauss(0, self.noise * self.range_torque) for t in torque]

        noisy_force = [max(-self.range_force, min(self.range_force, f)) for f in noisy_force]
        noisy_torque = [max(-self.range_torque, min(self.range_torque, t)) for t in noisy_torque]

        return SensorReading(
            sensor_type="force_torque",
            timestamp=0.0,
            data={
                "force": noisy_force,
                "torque": noisy_torque,
                "force_magnitude": math.sqrt(sum(f**2 for f in noisy_force)),
                "torque_magnitude": math.sqrt(sum(t**2 for t in noisy_torque)),
            },
            noise_level=self.noise,
        )


class ProximitySensor:
    """Proximity sensor simulation (ultrasonic/IR)."""

    def __init__(self, range_max: float = 5.0, cone_angle: float = 30.0, noise: float = 0.02):
        self.range_max = range_max
        self.cone_angle = cone_angle
        self.noise = noise
        self.logger = structlog.get_logger(component="proximity")

    def detect(self, object_positions: Dict[str, List[float]], sensor_pos: List[float],
               sensor_direction: List[float] = None) -> SensorReading:
        """Detect nearby objects within cone."""
        if sensor_direction is None:
            sensor_direction = [1, 0, 0]

        detections = []
        closest_dist = self.range_max
        closest_obj = None

        norm = math.sqrt(sum(d**2 for d in sensor_direction))
        sensor_direction = [d / norm for d in sensor_direction]

        for obj_id, obj_pos in object_positions.items():
            dx = obj_pos[0] - sensor_pos[0]
            dy = obj_pos[1] - sensor_pos[1]
            dz = obj_pos[2] - sensor_pos[2]
            dist = math.sqrt(dx**2 + dy**2 + dz**2)

            if dist > 0 and dist < self.range_max:
                to_obj = [dx / dist, dy / dist, dz / dist]
                dot = sum(sensor_direction[i] * to_obj[i] for i in range(3))
                angle = math.degrees(math.acos(max(-1, min(1, dot))))

                if angle < self.cone_angle / 2:
                    if noise > 0:
                        dist += random.gauss(0, noise * dist)
                    detections.append({"id": obj_id, "distance": dist, "angle": angle})
                    if dist < closest_dist:
                        closest_dist = dist
                        closest_obj = obj_id

        return SensorReading(
            sensor_type="proximity",
            timestamp=0.0,
            data={
                "detections": detections,
                "closest_distance": closest_dist,
                "closest_object": closest_obj,
                "num_detections": len(detections),
            },
            noise_level=noise,
        )


class TouchSensor:
    """Touch/pressure sensor simulation."""

    def __init__(self, num_taxels: int = 16, max_force: float = 50.0):
        self.num_taxels = num_taxels
        self.max_force = max_force
        self.logger = structlog.get_logger(component="touch")

    def read(self, contact_forces: List[float] = None) -> SensorReading:
        """Read touch/pressure data."""
        if contact_forces is None:
            contact_forces = [0.0] * self.num_taxels

        contact_forces = contact_forces[:self.num_taxels]
        while len(contact_forces) < self.num_taxels:
            contact_forces.append(0.0)

        total_force = sum(contact_forces)
        max_taxel = max(contact_forces) if contact_forces else 0
        contact_points = sum(1 for f in contact_forces if f > 0.1)

        return SensorReading(
            sensor_type="touch",
            timestamp=0.0,
            data={
                "taxel_forces": contact_forces,
                "total_force": total_force,
                "max_taxel_force": max_taxel,
                "contact_points": contact_points,
                "is_contacting": contact_points > 0,
            },
            noise_level=0.0,
        )


class ThermalCamera:
    """Thermal camera simulation."""

    def __init__(self, resolution: Tuple[int, int] = (160, 120),
                 temp_range: Tuple[float, float] = (-20, 200)):
        self.resolution = resolution
        self.temp_range = temp_range
        self.logger = structlog.get_logger(component="thermal_camera")

    def capture(self, object_temperatures: Dict[str, float] = None,
                ambient_temp: float = 22.0, noise: float = 0.5) -> SensorReading:
        """Capture thermal image."""
        if object_temperatures is None:
            object_temperatures = {}

        h, w = self.resolution
        thermal_map = []

        for y in range(h):
            row = []
            for x in range(w):
                temp = ambient_temp + random.gauss(0, noise)
                row.append(temp)
            thermal_map.append(row)

        hot_spots = []
        for obj_id, temp in object_temperatures.items():
            hot_spots.append({"id": obj_id, "temperature": temp, "is_hot": temp > ambient_temp + 10})

        return SensorReading(
            sensor_type="thermal",
            timestamp=0.0,
            data={
                "thermal_map": thermal_map,
                "resolution": self.resolution,
                "temp_range": self.temp_range,
                "hot_spots": hot_spots,
                "ambient_temp": ambient_temp,
            },
            noise_level=noise,
        )


class NightVision:
    """Night vision camera simulation (image intensification)."""

    def __init__(self, resolution: Tuple[int, int] = (640, 480),
                 gain: float = 10000.0, phosphor_color: str = "green"):
        self.resolution = resolution
        self.gain = gain
        self.phosphor_color = phosphor_color
        self.noise_amplitude = 0.02
        self.logger = structlog.get_logger(component="night_vision")

    def capture(self, ambient_light: float = 0.01, object_positions: Dict[str, List[float]] = None,
                camera_pos: List[float] = None, noise: float = 0.03) -> SensorReading:
        """Capture night vision image."""
        if object_positions is None:
            object_positions = {}
        if camera_pos is None:
            camera_pos = [0, 0, 0]

        h, w = self.resolution
        nv_image = []

        intensified_light = ambient_light * self.gain
        brightness = min(1.0, intensified_light)

        for y in range(h):
            row = []
            for x in range(w):
                base = brightness + random.gauss(0, noise)
                scintillation = random.expovariate(1.0 / 0.01) if random.random() < 0.01 else 0
                pixel = base + scintillation
                row.append(max(0.0, min(1.0, pixel)))
            nv_image.append(row)

        for obj_id, obj_pos in object_positions.items():
            dx = obj_pos[0] - camera_pos[0]
            dy = obj_pos[1] - camera_pos[1]
            dist = math.sqrt(dx**2 + dy**2)
            if dist < 20:
                sig = max(0, 1.0 - dist / 20)
                px = int((obj_pos[0] + 20) / 40 * w) % w
                py = int((obj_pos[1] + 15) / 30 * h) % h
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        ny, nx = py + dy, px + dx
                        if 0 <= ny < h and 0 <= nx < w:
                            nv_image[ny][nx] = min(1.0, nv_image[ny][nx] + sig * 0.5)

        color_mapped = []
        color_channels = {"green": (0.2, 1.0, 0.2), "white": (1, 1, 1), "amber": (1.0, 0.8, 0.2)}
        rgb = color_channels.get(self.phosphor_color, (0.2, 1.0, 0.2))

        for row in nv_image:
            color_row = []
            for pixel in row:
                color_row.append({
                    "r": pixel * rgb[0],
                    "g": pixel * rgb[1],
                    "b": pixel * rgb[2],
                    "intensity": pixel,
                })
            color_mapped.append(color_row)

        return SensorReading(
            sensor_type="night_vision",
            timestamp=0.0,
            data={
                "image": color_mapped,
                "resolution": self.resolution,
                "gain": self.gain,
                "phosphor_color": self.phosphor_color,
                "ambient_light": ambient_light,
                "intensified_brightness": brightness,
                "scintillation_events": sum(1 for row in nv_image for p in row if p > brightness + 0.1),
            },
            noise_level=noise,
            valid=True,
        )


class SensorArray:
    """Unified sensor array for robot."""

    def __init__(self):
        self.depth_camera = DepthCamera()
        self.lidar = LiDAR()
        self.imu = IMUSensor()
        self.force_torque = ForceTorqueSensor()
        self.proximity = ProximitySensor()
        self.touch = TouchSensor()
        self.thermal = ThermalCamera()
        self.night_vision = NightVision()
        self.logger = structlog.get_logger(component="sensor_array")

    def read_all(self, object_positions: Dict[str, List[float]] = None,
                 robot_pos: List[float] = None, **kwargs) -> Dict[str, SensorReading]:
        """Read all sensors."""
        if object_positions is None:
            object_positions = {}
        if robot_pos is None:
            robot_pos = [0, 0, 0]

        return {
            "depth": self.depth_camera.capture(object_positions, robot_pos),
            "lidar": self.lidar.scan(object_positions, robot_pos),
            "imu": self.imu.read(**{k: v for k, v in kwargs.items() if k in ["linear_accel", "angular_vel", "dt"]}),
            "force_torque": self.force_torque.read(**{k: v for k, v in kwargs.items() if k in ["force", "torque"]}),
            "proximity": self.proximity.detect(object_positions, robot_pos),
            "touch": self.touch.read(**{k: v for k, v in kwargs.items() if k in ["contact_forces"]}),
            "thermal": self.thermal.capture(**{k: v for k, v in kwargs.items() if k in ["object_temperatures", "ambient_temp"]}),
            "night_vision": self.night_vision.capture(**{k: v for k, v in kwargs.items() if k in ["ambient_light"]}),
        }

    def to_context(self) -> str:
        return "Sensor Array: depth, lidar, IMU, force/torque, proximity, touch, thermal, night vision"
