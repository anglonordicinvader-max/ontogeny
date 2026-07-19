"""NeoCorpus embodiment abstraction layer.

Thin internal abstraction between cognition and simulators/robots.
Not a public API — just the minimum required to add MuJoCo without
duplicating Blender's wiring.
"""

from abc import ABC, abstractmethod
from enum import Enum, StrEnum
from typing import Any


class EmbodimentType(StrEnum):
    BLENDER = "blender"
    MUJOCO = "mujoco"
    ROS2 = "ros2"
    PHYSICAL = "physical"


class EmbodimentAdapter(ABC):
    """Minimal interface every simulator/robot adapter must expose."""

    @property
    @abstractmethod
    def embodiment_type(self) -> EmbodimentType: ...

    @property
    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    async def observe(self) -> dict[str, Any]: ...

    @abstractmethod
    async def send_action(self, action: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    async def reset_environment(self) -> None: ...

    @abstractmethod
    def get_joint_state(self) -> dict[str, Any]: ...

    @abstractmethod
    def get_sensor_data(self) -> dict[str, Any]: ...


class EmbodimentRegistry:
    """Registry of available embodiment adapters.

    Kept intentionally minimal — no discovery, no lifecycle management.
    Adapters register themselves; the orchestrator looks them up by type.
    """

    def __init__(self) -> None:
        self._adapters: dict[EmbodimentType, EmbodimentAdapter] = {}

    def register(self, adapter: EmbodimentAdapter) -> None:
        self._adapters[adapter.embodiment_type] = adapter

    def get(self, etype: EmbodimentType) -> EmbodimentAdapter | None:
        return self._adapters.get(etype)

    def available(self) -> list[EmbodimentType]:
        return [t for t, a in self._adapters.items() if a.is_available]

    def all_types(self) -> list[EmbodimentType]:
        return list(self._adapters.keys())
