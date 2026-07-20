"""Smoke-test a running Ontogeny Blender WebSocket endpoint."""

import argparse
import asyncio
import json

import websockets


WORLDS = (
    "research_lab",
    "small_house",
    "warehouse",
    "outdoor_test_area",
    "procedural_sandbox",
)


async def smoke(port: int) -> None:
    async with websockets.connect(f"ws://127.0.0.1:{port}", max_size=8_000_000) as socket:
        await socket.send(json.dumps({"type": "command", "command": "worlds"}))
        while True:
            catalog = json.loads(await socket.recv())
            if catalog.get("type") == "world_catalog":
                break
        available = {world["id"] for world in catalog["worlds"] if world["available"]}
        assert set(WORLDS).issubset(available)

        frame_sizes: dict[str, int] = {}
        for world in WORLDS:
            await socket.send(json.dumps({"type": "command", "command": f"world:{world}"}))
            changed = False
            while not changed or world not in frame_sizes:
                message = json.loads(await socket.recv())
                if message.get("type") == "world_changed" and message.get("active") == world:
                    changed = True
                elif message.get("type") == "frame" and changed:
                    frame_sizes[world] = len(message.get("data", ""))
            assert frame_sizes[world] > 1_000

        print(
            "Blender smoke passed: "
            + ", ".join(f"{world}={frame_sizes[world]}" for world in WORLDS)
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8766)
    asyncio.run(smoke(parser.parse_args().port))
