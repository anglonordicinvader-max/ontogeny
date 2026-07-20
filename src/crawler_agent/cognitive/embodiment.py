"""NeoCorpus embodiment abstraction layer.

Thin internal abstraction between cognition and simulators/robots.
Not a public API — just the minimum required to add MuJoCo without
duplicating Blender's wiring.
"""

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any, Protocol


class EmbodimentType(StrEnum):
    BLENDER = "blender"
    MUJOCO = "mujoco"
    ROS2 = "ros2"
    PHYSICAL = "physical"


class EmbodimentLifecycle(StrEnum):
    UNAVAILABLE = "unavailable"
    READY = "ready"
    RUNNING = "running"
    ERROR = "error"


@dataclass(frozen=True)
class EmbodimentSnapshot:
    embodiment_type: EmbodimentType
    lifecycle: EmbodimentLifecycle
    available: bool
    telemetry: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["embodiment_type"] = self.embodiment_type.value
        value["lifecycle"] = self.lifecycle.value
        return value


class EmbodimentTransport(Protocol):
    """Transport contract implemented by the backend runtime."""

    def snapshot(self, embodiment: str) -> dict[str, Any]: ...

    async def send_action(self, embodiment: str, command: str) -> dict[str, Any]: ...


class EmbodimentAdapter(ABC):
    """Minimal interface every simulator/robot adapter must expose."""

    @property
    @abstractmethod
    def embodiment_type(self) -> EmbodimentType: ...

    @property
    @abstractmethod
    def is_available(self) -> bool: ...

    @property
    @abstractmethod
    def lifecycle(self) -> EmbodimentLifecycle: ...

    @abstractmethod
    def snapshot(self) -> EmbodimentSnapshot: ...

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

    def snapshots(self) -> dict[str, dict[str, Any]]:
        return {
            embodiment_type.value: adapter.snapshot().to_dict()
            for embodiment_type, adapter in self._adapters.items()
        }
