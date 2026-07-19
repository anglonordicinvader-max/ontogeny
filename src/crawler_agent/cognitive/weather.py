"""Weather effects - wind, rain, day/night cycle.

Provides:
- Wind force simulation
- Rain particle simulation
- Day/night cycle with lighting
- Fog visibility reduction
"""

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import structlog


@dataclass
class WeatherState:
    wind_direction: list[float] = field(default_factory=lambda: [1, 0, 0])
    wind_speed: float = 0.0  # m/s
    wind_gusts: bool = False
    rain_intensity: float = 0.0  # 0.0 to 1.0
    fog_density: float = 0.0  # 0.0 to 1.0
    visibility: float = 1.0  # 0.0 to 1.0
    temperature: float = 22.0  # Celsius
    time_of_day: float = 12.0  # 0-24 hours
    sun_angle: float = 90.0  # degrees from horizon


class WindSimulation:
    """Wind force simulation."""

    def __init__(self):
        self.state = WeatherState()
        self.logger = structlog.get_logger(component="wind")

    def set_wind(self, direction: list[float], speed: float, gusts: bool = False):
        norm = math.sqrt(sum(d**2 for d in direction))
        if norm > 0:
            direction = [d / norm for d in direction]
        self.state.wind_direction = direction
        self.state.wind_speed = speed
        self.state.wind_gusts = gusts

    def get_force(self, object_mass: float, dt: float = 0.01) -> list[float]:
        """Get wind force on an object."""
        base_force = [
            self.state.wind_direction[i] * self.state.wind_speed * object_mass * 0.1
            for i in range(3)
        ]

        if self.state.wind_gusts:
            gust_factor = 1.0 + random.uniform(-0.3, 0.5)
            base_force = [f * gust_factor for f in base_force]

        return base_force

    def apply_to_position(
        self, position: list[float], mass: float, dt: float = 0.01
    ) -> list[float]:
        """Apply wind to position."""
        force = self.get_force(mass, dt)
        acceleration = [f / mass for f in force]
        new_pos = [position[i] + acceleration[i] * dt**2 / 2 for i in range(3)]
        return new_pos

    def to_context(self) -> str:
        return (
            f"Wind: {self.state.wind_speed:.1f}m/s {'gusty' if self.state.wind_gusts else 'steady'}"
        )


class RainSimulation:
    """Rain particle simulation."""

    def __init__(self, max_particles: int = 500):
        self.max_particles = max_particles
        self.particles: list[dict] = []
        self.intensity = 0.0
        self.logger = structlog.get_logger(component="rain")

    def set_intensity(self, intensity: float):
        self.intensity = max(0.0, min(1.0, intensity))

    def update(self, dt: float, wind: WindSimulation = None) -> list[dict]:
        """Update rain particles."""
        target_count = int(self.intensity * self.max_particles)

        while len(self.particles) < target_count:
            self.particles.append(
                {
                    "x": random.uniform(-20, 20),
                    "y": random.uniform(-20, 20),
                    "z": random.uniform(10, 20),
                    "vx": 0,
                    "vy": 0,
                    "vz": -10 - random.uniform(0, 5),
                    "size": random.uniform(0.01, 0.03),
                }
            )

        while len(self.particles) > target_count:
            self.particles.pop()

        active = []
        for p in self.particles:
            if wind:
                wind_force = wind.get_force(0.001)
                p["vx"] += wind_force[0] * dt
                p["vy"] += wind_force[1] * dt

            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["z"] += p["vz"] * dt

            if p["z"] > 0:
                active.append(p)

        self.particles = active
        return self.particles

    def get_ground_impact(self) -> list[dict]:
        """Get particles hitting ground."""
        impacts = []
        for p in self.particles:
            if 0 <= p["z"] <= 0.5:
                impacts.append({"x": p["x"], "y": p["y"], "intensity": self.intensity})
        return impacts

    def to_context(self) -> str:
        return f"Rain: {self.intensity:.0%} intensity, {len(self.particles)} particles"


class DayNightCycle:
    """Day/night cycle with lighting changes."""

    def __init__(self):
        self.time_of_day = 12.0  # noon
        self.logger = structlog.get_logger(component="day_night")

    def set_time(self, hour: float):
        self.time_of_day = hour % 24.0

    def get_sun_angle(self) -> float:
        """Get sun angle from horizon (0=horizon, 90=zenith)."""
        return max(0, 90 - abs(self.time_of_day - 12) * 15)

    def get_sun_color(self) -> tuple[float, float, float]:
        """Get sun color based on time."""
        hour = self.time_of_day
        if 6 <= hour <= 8:
            t = (hour - 6) / 2
            return (1.0, 0.4 + 0.6 * t, 0.2 + 0.8 * t)
        elif 8 < hour <= 16:
            return (1.0, 1.0, 0.9)
        elif 16 < hour <= 18:
            t = (hour - 16) / 2
            return (1.0, 1.0 - 0.3 * t, 0.9 - 0.5 * t)
        else:
            return (0.1, 0.1, 0.2)

    def get_sun_energy(self) -> float:
        """Get sun light energy."""
        angle = self.get_sun_angle()
        return max(0, math.sin(math.radians(angle)) * 3.0)

    def get_ambient_color(self) -> tuple[float, float, float]:
        """Get ambient light color."""
        hour = self.time_of_day
        if 6 <= hour <= 18:
            return (0.3, 0.3, 0.4)
        else:
            return (0.05, 0.05, 0.1)

    def get_visibility(self) -> float:
        """Get visibility factor (0=dark, 1=bright)."""
        angle = self.get_sun_angle()
        return max(0.05, math.sin(math.radians(angle)))

    def is_night(self) -> bool:
        return self.time_of_day < 6 or self.time_of_day > 18

    def to_context(self) -> str:
        hour = int(self.time_of_day)
        minute = int((self.time_of_day % 1) * 60)
        return f"Day/Night: {hour:02d}:{minute:02d}, sun={self.get_sun_angle():.0f}°"


class FogSimulation:
    """Fog visibility reduction."""

    def __init__(self):
        self.density = 0.0
        self.logger = structlog.get_logger(component="fog")

    def set_density(self, density: float):
        self.density = max(0.0, min(1.0, density))

    def get_visibility(self) -> float:
        return max(0.05, 1.0 - self.density)

    def apply_to_distance(self, distance: float) -> float:
        """Reduce apparent brightness with distance."""
        attenuation = math.exp(-self.density * distance * 0.1)
        return attenuation

    def to_context(self) -> str:
        return f"Fog: {self.density:.0%} density, visibility={self.get_visibility():.0%}"


class WeatherSystem:
    """Unified weather system."""

    def __init__(self):
        self.wind = WindSimulation()
        self.rain = RainSimulation()
        self.day_night = DayNightCycle()
        self.fog = FogSimulation()
        self.temperature = 22.0
        self.logger = structlog.get_logger(component="weather")

    def set_weather(
        self,
        wind_speed: float = 0,
        rain_intensity: float = 0,
        fog_density: float = 0,
        temperature: float = 22.0,
    ):
        self.wind.set_wind([1, 0, 0], wind_speed, gusts=wind_speed > 10)
        self.rain.set_intensity(rain_intensity)
        self.fog.set_density(fog_density)
        self.temperature = temperature

    def update(self, dt: float) -> dict:
        rain_particles = self.rain.update(dt, self.wind)
        return {
            "wind_force": self.wind.get_force(1.0),
            "rain_particles": len(rain_particles),
            "visibility": min(self.day_night.get_visibility(), self.fog.get_visibility()),
            "sun_energy": self.day_night.get_sun_energy(),
            "temperature": self.temperature,
        }

    def to_context(self) -> str:
        return (
            f"Weather: wind={self.wind.to_context()}, "
            f"{self.rain.to_context()}, {self.fog.to_context()}, "
            f"{self.day_night.to_context()}, temp={self.temperature:.0f}°C"
        )
