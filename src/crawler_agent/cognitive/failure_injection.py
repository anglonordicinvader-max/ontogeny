"""Failure injection - sensor noise, actuator jamming, battery drain, communication loss, structural damage.

Provides:
- Sensor noise injection
- Actuator jamming simulation
- Battery drain simulation
- Communication loss simulation
- Structural damage propagation
"""

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import structlog


@dataclass
class FailureState:
    battery_level: float = 1.0  # 0.0 to 1.0
    structural_integrity: float = 1.0  # 0.0 to 1.0
    sensor_health: Dict[str, float] = field(default_factory=lambda: {
        "depth": 1.0, "lidar": 1.0, "imu": 1.0,
        "force_torque": 1.0, "proximity": 1.0, "touch": 1.0, "thermal": 1.0,
    })
    actuator_health: Dict[str, float] = field(default_factory=lambda: {
        "arm": 1.0, "gripper": 1.0, "wheel_left": 1.0, "wheel_right": 1.0,
        "leg_front_left": 1.0, "leg_front_right": 1.0,
        "leg_rear_left": 1.0, "leg_rear_right": 1.0,
    })
    communication_quality: float = 1.0  # 0.0 to 1.0
    temperature: float = 25.0  # Celsius
    uptime: float = 0.0  # seconds


class FailureInjector:
    """Simulates various failure modes for robotics."""

    def __init__(self):
        self.state = FailureState()
        self.logger = structlog.get_logger(component="failure_injection")
        self.failure_log: List[Dict] = []

    def reset(self):
        """Reset all failure states."""
        self.state = FailureState()
        self.failure_log = []

    def drain_battery(self, dt: float, drain_rate: float = 0.001) -> float:
        """Simulate battery drain over time."""
        drain = drain_rate * dt
        self.state.battery_level = max(0.0, self.state.battery_level - drain)

        if self.state.battery_level < 0.2:
            self._log_failure("battery_low", f"Battery at {self.state.battery_level:.1%}")

        if self.state.battery_level < 0.05:
            self._log_failure("battery_critical", "Battery critical - shutdown imminent")

        return self.state.battery_level

    def apply_structural_damage(self, damage: float, location: str = "unknown"):
        """Apply structural damage to robot."""
        self.state.structural_integrity = max(0.0, self.state.structural_integrity - damage)
        self._log_failure("structural_damage", f"Damage at {location}: -{damage:.1%}")

        if self.state.structural_integrity < 0.5:
            affected_actuators = random.sample(list(self.state.actuator_health.keys()),
                                               k=min(2, len(self.state.actuator_health)))
            for act in affected_actuators:
                self.state.actuator_health[act] *= 0.8

        return self.state.structural_integrity

    def inject_sensor_noise(self, sensor_type: str, noise_level: float = 0.3):
        """Inject noise into a specific sensor."""
        if sensor_type in self.state.sensor_health:
            self.state.sensor_health[sensor_type] = max(0.0,
                self.state.sensor_health[sensor_type] - noise_level)
            self._log_failure("sensor_noise", f"{sensor_type} noise: +{noise_level:.1%}")

    def jam_actuator(self, actuator: str, jam_probability: float = 0.1):
        """Simulate actuator jamming."""
        if actuator in self.state.actuator_health:
            if random.random() < jam_probability:
                self.state.actuator_health[actuator] *= 0.3
                self._log_failure("actuator_jam", f"{actuator} jammed")

    def simulate_communication_loss(self, duration: float = 5.0, severity: float = 0.5):
        """Simulate communication degradation."""
        self.state.communication_quality = max(0.0, 1.0 - severity)
        self._log_failure("comm_loss", f"Communication degraded to {severity:.1%}")

    def simulate_overheat(self, rate: float = 0.1):
        """Simulate overheating."""
        self.state.temperature += rate
        if self.state.temperature > 60:
            self._log_failure("overheat", f"Temperature: {self.state.temperature:.1f}°C")
            for sensor in self.state.sensor_health:
                self.state.sensor_health[sensor] *= 0.95

    def get_actuator_degradation(self, actuator: str) -> float:
        """Get actuator degradation factor (1.0 = perfect, 0.0 = failed)."""
        return self.state.actuator_health.get(actuator, 1.0)

    def get_sensor_degradation(self, sensor: str) -> float:
        """Get sensor degradation factor."""
        return self.state.sensor_health.get(sensor, 1.0)

    def is_operational(self) -> bool:
        """Check if robot is still operational."""
        return (self.state.battery_level > 0.0 and
                self.state.structural_integrity > 0.1 and
                self.state.communication_quality > 0.0)

    def get_status(self) -> Dict:
        """Get current failure state."""
        return {
            "battery": self.state.battery_level,
            "structural": self.state.structural_integrity,
            "sensors": dict(self.state.sensor_health),
            "actuators": dict(self.state.actuator_health),
            "communication": self.state.communication_quality,
            "temperature": self.state.temperature,
            "operational": self.is_operational(),
        }

    def _log_failure(self, failure_type: str, description: str):
        self.failure_log.append({
            "type": failure_type,
            "description": description,
            "state": self.get_status(),
        })

    def to_context(self) -> str:
        return (f"Failure State: battery={self.state.battery_level:.0%}, "
                f"structural={self.state.structural_integrity:.0%}, "
                f"comm={self.state.communication_quality:.0%}, "
                f"temp={self.state.temperature:.0f}°C")
