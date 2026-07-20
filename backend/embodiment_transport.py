"""Backend-authoritative live transport for NeoCorpus embodiments."""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import websockets

ALLOWED_COMMANDS = {
    "blender": {"health", "worlds", "reset", "pause", "resume"},
    "mujoco": {
        "health",
        "telemetry",
        "stand",
        "walk",
        "freeze",
        "reset",
        "demo_start",
        "demo_stop",
        "pause",
        "resume",
    },
}
ALLOWED_PREFIXES = {
    "blender": ("world:", "mode:", "emotion:"),
    "mujoco": ("walk_cmd:", "mode:", "emotion:", "world:"),
}


@dataclass
class TransportChannel:
    name: str
    uri: str
    connected: bool = False
    lifecycle: str = "unavailable"
    state: dict[str, Any] = field(default_factory=dict)
    last_error: str | None = None
    updated_at: float = 0.0
    socket: Any = None
    send_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    pending: dict[str, asyncio.Future] = field(default_factory=dict)


class EmbodimentTransportService:
    """Maintains state-only simulator connections and correlated commands."""

    def __init__(self, blender_port: int, mujoco_port: int):
        self.channels = {
            "blender": TransportChannel("blender", f"ws://127.0.0.1:{blender_port}"),
            "mujoco": TransportChannel("mujoco", f"ws://127.0.0.1:{mujoco_port}"),
        }
        self._tasks: list[asyncio.Task] = []
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._tasks = [
            asyncio.create_task(self._connection_loop(channel))
            for channel in self.channels.values()
        ]

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self._tasks.clear()

    def snapshot(self, embodiment: str) -> dict[str, Any]:
        channel = self.channels.get(embodiment)
        if not channel:
            return {"available": False, "lifecycle": "unavailable", "telemetry": {}}
        return {
            "available": channel.connected,
            "lifecycle": channel.lifecycle,
            "telemetry": dict(channel.state),
            "last_error": channel.last_error,
            "updated_at": channel.updated_at,
        }

    def snapshots(self) -> dict[str, dict[str, Any]]:
        return {name: self.snapshot(name) for name in self.channels}

    async def send_action(
        self, embodiment: str, command: str, timeout: float = 5.0
    ) -> dict[str, Any]:
        channel = self.channels.get(embodiment)
        if not channel:
            return {"success": False, "error": f"Unknown embodiment: {embodiment}"}
        if not self._is_allowed(embodiment, command):
            return {"success": False, "error": f"Unsupported {embodiment} command"}
        if not channel.connected or channel.socket is None:
            return {"success": False, "error": f"{embodiment} transport unavailable"}

        request_id = uuid.uuid4().hex
        future = asyncio.get_running_loop().create_future()
        channel.pending[request_id] = future
        try:
            async with channel.send_lock:
                await channel.socket.send(
                    json.dumps({"type": "command", "command": command, "request_id": request_id})
                )
            return await asyncio.wait_for(future, timeout=timeout)
        except TimeoutError:
            return {"success": False, "error": f"{embodiment} command timed out"}
        finally:
            channel.pending.pop(request_id, None)

    def _is_allowed(self, embodiment: str, command: str) -> bool:
        return command in ALLOWED_COMMANDS[embodiment] or command.startswith(
            ALLOWED_PREFIXES[embodiment]
        )

    async def _connection_loop(self, channel: TransportChannel) -> None:
        while self._running:
            try:
                async with websockets.connect(
                    channel.uri, max_size=8_000_000, open_timeout=2
                ) as socket:
                    channel.socket = socket
                    channel.connected = True
                    channel.lifecycle = "ready"
                    channel.last_error = None
                    await socket.send(
                        json.dumps({"type": "command", "command": "subscribe:telemetry"})
                    )
                    await socket.send(json.dumps({"type": "command", "command": "health"}))
                    async for raw_message in socket:
                        self._handle_message(channel, json.loads(raw_message))
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                channel.last_error = str(exc)
            finally:
                channel.socket = None
                channel.connected = False
                channel.lifecycle = "unavailable"
                for future in channel.pending.values():
                    if not future.done():
                        future.set_result(
                            {"success": False, "error": f"{channel.name} disconnected"}
                        )
                channel.pending.clear()
            if self._running:
                await asyncio.sleep(1)

    def _handle_message(self, channel: TransportChannel, message: dict[str, Any]) -> None:
        message_type = message.get("type")
        channel.updated_at = time.time()
        if message_type in {"health", "telemetry", "world_changed", "world_catalog"}:
            channel.state.update(message)
            if message_type == "telemetry":
                channel.lifecycle = (
                    "running" if message.get("controller", {}).get("mode") == "walk" else "ready"
                )
        elif message_type == "render_error":
            channel.last_error = message.get("error", "render error")
            channel.lifecycle = "error"
        elif message_type == "command_result":
            request_id = message.get("request_id")
            future = channel.pending.get(request_id)
            if future and not future.done():
                future.set_result(message)
