"""Locomotion modes - wheeled, legged, tracked, flying, swimming.

Provides:
- Wheeled (differential drive, ackerman)
- Legged (biped, quadruped, hexapod)
- Tracked (tank treads)
- Flying (drone dynamics)
- Swimming (underwater ROV)
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import structlog


@dataclass
class LocomotionState:
    position: list[float] = field(default_factory=lambda: [0, 0, 0])
    velocity: list[float] = field(default_factory=lambda: [0, 0, 0])
    orientation: list[float] = field(default_factory=lambda: [0, 0, 0])  # roll, pitch, yaw
    angular_velocity: list[float] = field(default_factory=lambda: [0, 0, 0])
    on_ground: bool = True
    in_water: bool = False


class WheeledLocomotion:
    """Wheeled robot (differential drive)."""

    def __init__(self, wheel_radius: float = 0.1, wheel_base: float = 0.5, max_speed: float = 2.0):
        self.wheel_radius = wheel_radius
        self.wheel_base = wheel_base
        self.max_speed = max_speed
        self.state = LocomotionState()
        self.left_speed = 0.0
        self.right_speed = 0.0
        self.logger = structlog.get_logger(component="wheeled")

    def set_cmd(self, linear: float, angular: float):
        """Set differential drive commands."""
        linear = max(-self.max_speed, min(self.max_speed, linear))
        self.left_speed = linear - angular * self.wheel_base / 2
        self.right_speed = linear + angular * self.wheel_base / 2

    def update(self, dt: float, friction: float = 0.5) -> LocomotionState:
        """Update position."""
        v = (self.left_speed + self.right_speed) / 2
        w = (self.right_speed - self.left_speed) / self.wheel_base

        self.state.orientation[2] += w * dt
        self.state.velocity[0] = v * math.cos(self.state.orientation[2])
        self.state.velocity[1] = v * math.sin(self.state.orientation[2])

        for i in range(3):
            self.state.position[i] += self.state.velocity[i] * dt

        self.state.velocity = [vf * (1 - friction * 0.1) for vf in self.state.velocity]
        return self.state


class LeggedLocomotion:
    """Legged robot (quadruped with gait control)."""

    def __init__(self, num_legs: int = 4, leg_length: float = 0.3, max_speed: float = 1.5):
        self.num_legs = num_legs
        self.leg_length = leg_length
        self.max_speed = max_speed
        self.state = LocomotionState()
        self.gait_phase = 0.0
        self.gait_frequency = 2.0
        self.leg_positions = [[0, 0, 0] for _ in range(num_legs)]
        self.logger = structlog.get_logger(component="legged")

    def set_gait(self, frequency: float = 2.0):
        self.gait_frequency = frequency

    def update(self, dt: float, terrain_height_fn=None) -> LocomotionState:
        """Update with gait cycle."""
        self.gait_phase += self.gait_frequency * dt
        if self.gait_phase > 2 * math.pi:
            self.gait_phase -= 2 * math.pi

        stride_length = self.max_speed * dt
        self.state.position[0] += stride_length * math.cos(self.state.orientation[2])
        self.state.position[1] += stride_length * math.sin(self.state.orientation[2])

        for i in range(self.num_legs):
            phase_offset = (i / self.num_legs) * 2 * math.pi
            leg_phase = self.gait_phase + phase_offset
            lift = max(0, math.sin(leg_phase)) * self.leg_length * 0.3
            swing = math.cos(leg_phase) * stride_length * 0.5

            self.leg_positions[i][0] = self.state.position[0] + swing * math.cos(
                self.state.orientation[2]
            )
            self.leg_positions[i][1] = self.state.position[1] + swing * math.sin(
                self.state.orientation[2]
            )
            self.leg_positions[i][2] = lift

        return self.state


class TrackedLocomotion:
    """Tracked vehicle (tank treads)."""

    def __init__(self, track_width: float = 0.4, max_speed: float = 1.0):
        self.track_width = track_width
        self.max_speed = max_speed
        self.state = LocomotionState()
        self.left_speed = 0.0
        self.right_speed = 0.0
        self.logger = structlog.get_logger(component="tracked")

    def set_cmd(self, linear: float, angular: float):
        linear = max(-self.max_speed, min(self.max_speed, linear))
        self.left_speed = linear - angular * self.track_width / 2
        self.right_speed = linear + angular * self.track_width / 2

    def update(self, dt: float, terrain_friction: float = 0.3) -> LocomotionState:
        v = (self.left_speed + self.right_speed) / 2
        w = (self.right_speed - self.left_speed) / self.track_width

        self.state.orientation[2] += w * dt
        effective_friction = max(0.1, 1.0 - terrain_friction)
        self.state.velocity[0] = v * effective_friction * math.cos(self.state.orientation[2])
        self.state.velocity[1] = v * effective_friction * math.sin(self.state.orientation[2])

        for i in range(3):
            self.state.position[i] += self.state.velocity[i] * dt

        return self.state


class FlyingLocomotion:
    """Drone/quadrotor dynamics."""

    def __init__(self, max_speed: float = 5.0, max_altitude: float = 50.0):
        self.max_speed = max_speed
        self.max_altitude = max_altitude
        self.state = LocomotionState()
        self.throttle = 0.0
        self.logger = structlog.get_logger(component="flying")

    def set_cmd(self, vx: float, vy: float, vz: float):
        self.state.velocity[0] = max(-self.max_speed, min(self.max_speed, vx))
        self.state.velocity[1] = max(-self.max_speed, min(self.max_speed, vy))
        self.state.velocity[2] = max(-self.max_speed, min(self.max_speed, vz))

    def update(self, dt: float, gravity: float = 9.81, drag: float = 0.1) -> LocomotionState:
        for i in range(3):
            self.state.position[i] += self.state.velocity[i] * dt

        self.state.position[2] = max(0, min(self.max_altitude, self.state.position[2]))
        self.state.on_ground = self.state.position[2] <= 0.1

        self.state.velocity = [v * (1 - drag * dt) for v in self.state.velocity]

        if not self.state.on_ground:
            self.state.velocity[2] -= gravity * dt * 0.1

        return self.state


class SwimmingLocomotion:
    """Underwater ROV dynamics."""

    def __init__(self, max_speed: float = 2.0, max_depth: float = 100.0, buoyancy: float = 0.5):
        self.max_speed = max_speed
        self.max_depth = max_depth
        self.buoyancy = buoyancy
        self.state = LocomotionState()
        self.thrusters = [0.0, 0.0, 0.0, 0.0]  # front, back, left, right
        self.logger = structlog.get_logger(component="swimming")

    def set_thrusters(self, front: float, back: float, left: float, right: float):
        self.thrusters = [
            max(-1, min(1, front)),
            max(-1, min(1, back)),
            max(-1, min(1, left)),
            max(-1, min(1, right)),
        ]

    def update(
        self, dt: float, water_density: float = 1025.0, drag_coeff: float = 0.5
    ) -> LocomotionState:
        forward = (self.thrusters[0] - self.thrusters[1]) * self.max_speed
        lateral = (self.thrusters[2] - self.thrusters[3]) * self.max_speed * 0.5

        self.state.orientation[2] += lateral * dt * 0.5

        self.state.velocity[0] = forward * math.cos(self.state.orientation[2])
        self.state.velocity[1] = forward * math.sin(self.state.orientation[2])
        self.state.velocity[2] += (self.buoyancy - 0.5) * dt

        drag_factor = 1.0 - drag_coeff * dt
        self.state.velocity = [v * drag_factor for v in self.state.velocity]

        for i in range(3):
            self.state.position[i] += self.state.velocity[i] * dt

        self.state.position[2] = max(-self.max_depth, min(0, self.state.position[2]))
        self.state.in_water = self.state.position[2] < 0

        return self.state


class LocomotionController:
    """Unified locomotion controller."""

    def __init__(self, mode: str = "wheeled"):
        self.mode = mode
        self.wheeled = WheeledLocomotion()
        self.legged = LeggedLocomotion()
        self.tracked = TrackedLocomotion()
        self.flying = FlyingLocomotion()
        self.swimming = SwimmingLocomotion()
        self.logger = structlog.get_logger(component="locomotion")

    def set_mode(self, mode: str):
        self.mode = mode

    def set_cmd(self, **kwargs):
        if self.mode == "wheeled":
            self.wheeled.set_cmd(kwargs.get("linear", 0), kwargs.get("angular", 0))
        elif self.mode == "legged":
            self.legged.set_gait(kwargs.get("frequency", 2.0))
        elif self.mode == "tracked":
            self.tracked.set_cmd(kwargs.get("linear", 0), kwargs.get("angular", 0))
        elif self.mode == "flying":
            self.flying.set_cmd(kwargs.get("vx", 0), kwargs.get("vy", 0), kwargs.get("vz", 0))
        elif self.mode == "swimming":
            self.swimming.set_thrusters(
                kwargs.get("front", 0),
                kwargs.get("back", 0),
                kwargs.get("left", 0),
                kwargs.get("right", 0),
            )

    def update(self, dt: float, **kwargs) -> LocomotionState:
        if self.mode == "wheeled":
            return self.wheeled.update(dt)
        elif self.mode == "legged":
            return self.legged.update(dt)
        elif self.mode == "tracked":
            return self.tracked.update(dt, kwargs.get("terrain_friction", 0.3))
        elif self.mode == "flying":
            return self.flying.update(dt)
        elif self.mode == "swimming":
            return self.swimming.update(dt)
        return LocomotionState()

    def get_position(self) -> list[float]:
        if self.mode == "wheeled":
            return self.wheeled.state.position
        elif self.mode == "legged":
            return self.legged.state.position
        elif self.mode == "tracked":
            return self.tracked.state.position
        elif self.mode == "flying":
            return self.flying.state.position
        elif self.mode == "swimming":
            return self.swimming.state.position
        return [0, 0, 0]

    def to_context(self) -> str:
        pos = self.get_position()
        return f"Locomotion ({self.mode}): pos=[{pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f}]"
