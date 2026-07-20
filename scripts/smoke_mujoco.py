"""Smoke-test a running Ontogeny MuJoCo WebSocket endpoint."""

import argparse
import asyncio
import json
import math

import websockets


async def receive_type(socket, message_type: str) -> dict:
    while True:
        message = json.loads(await socket.recv())
        if message.get("type") == message_type:
            return message


async def smoke(port: int) -> None:
    async with websockets.connect(f"ws://127.0.0.1:{port}") as socket:
        await socket.send(json.dumps({"type": "command", "command": "health"}))
        health = await receive_type(socket, "health")
        assert health["model_loaded"]
        assert health["render_error"] is None
        initial_position = health["body"]["pos"]

        await socket.send(json.dumps({"type": "command", "command": "demo_start"}))
        stages: list[str] = []
        saw_frame = False
        walking_target_seen = False
        stop_position = initial_position
        while len(stages) < 3:
            message = json.loads(await socket.recv())
            if message.get("type") == "frame":
                saw_frame = len(message.get("data", "")) > 1000
            elif message.get("type") == "telemetry":
                stage = message["demo"]["stage"]
                if stage == "walk_out":
                    walking_target_seen = any(
                        abs(joint["target"] - joint["pos"]) > 0.01
                        for joint in message["joints"].values()
                    )
                elif stage == "stop":
                    stop_position = message["body"]["pos"]
                if stage not in stages:
                    stages.append(stage)
        assert saw_frame
        assert walking_target_seen
        assert stages[:3] == ["initialize", "walk_out", "stop"]
        displacement = math.dist(initial_position[:2], stop_position[:2])
        assert displacement > 0.01

        await socket.send(json.dumps({"type": "command", "command": "freeze"}))
        await socket.send(json.dumps({"type": "command", "command": "health"}))
        frozen = await receive_type(socket, "health")
        await asyncio.sleep(0.3)
        await socket.send(json.dumps({"type": "command", "command": "health"}))
        still_frozen = await receive_type(socket, "health")
        assert still_frozen["sim_time"] == frozen["sim_time"]

        await socket.send(json.dumps({"type": "command", "command": "reset"}))
        await socket.send(json.dumps({"type": "command", "command": "health"}))
        reset = await receive_type(socket, "health")
        assert reset["controller"]["mode"] == "stand"
        assert reset["sim_time"] == 0.0
        assert reset["demo"]["stage"] == "idle"
        print(
            f"MuJoCo smoke passed: model={reset['robot_model']} "
            f"stages={','.join(stages)} displacement={displacement:.3f}m "
            "frame=real freeze=immediate reset=deterministic"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8768)
    asyncio.run(smoke(parser.parse_args().port))
