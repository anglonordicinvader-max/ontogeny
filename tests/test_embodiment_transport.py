"""Focused contract tests for the backend-authoritative embodiment transport."""

import asyncio
import json

import pytest

from backend.embodiment_transport import EmbodimentTransportService


class FakeSocket:
    def __init__(self, service, channel):
        self.service = service
        self.channel = channel
        self.messages = []

    async def send(self, raw):
        message = json.loads(raw)
        self.messages.append(message)
        request_id = message.get("request_id")
        if request_id:
            asyncio.get_running_loop().call_soon(
                self.service._handle_message,
                self.channel,
                {
                    "type": "command_result",
                    "request_id": request_id,
                    "success": True,
                    "command": message["command"],
                },
            )


@pytest.mark.asyncio
async def test_command_is_allowlisted_and_correlated():
    service = EmbodimentTransportService(8766, 8767)
    channel = service.channels["mujoco"]
    channel.connected = True
    channel.socket = FakeSocket(service, channel)

    result = await service.send_action("mujoco", "walk")

    assert result["success"] is True
    assert result["command"] == "walk"
    assert channel.pending == {}


@pytest.mark.asyncio
async def test_unknown_commands_never_reach_simulator():
    service = EmbodimentTransportService(8766, 8767)
    channel = service.channels["blender"]
    channel.connected = True
    channel.socket = FakeSocket(service, channel)

    result = await service.send_action("blender", "arbitrary-python")

    assert result["success"] is False
    assert channel.socket.messages == []


def test_snapshot_reflects_genuine_telemetry():
    service = EmbodimentTransportService(8766, 8767)
    channel = service.channels["mujoco"]
    channel.connected = True
    service._handle_message(
        channel,
        {"type": "telemetry", "controller": {"mode": "walk"}, "frame": 12},
    )

    snapshot = service.snapshot("mujoco")
    assert snapshot["available"] is True
    assert snapshot["lifecycle"] == "running"
    assert snapshot["telemetry"]["frame"] == 12
