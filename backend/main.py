import argparse
import asyncio
import json
import os
import socket
import sys
import time
from typing import Set

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(__file__))
from agent_manager import manager
from demo_fixtures import demo_session
from embodiment_transport import EmbodimentTransportService

app = FastAPI(title="Ontogeny Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

connected_clients: set[WebSocket] = set()
embodiment_transport = EmbodimentTransportService(
    blender_port=int(os.environ.get("ONTOGENY_BLENDER_PORT", "8766")),
    mujoco_port=int(os.environ.get("ONTOGENY_MUJOCO_PORT", "8767")),
)
manager.set_embodiment_transport(embodiment_transport)


def find_available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def broadcast(message: dict):
    disconnected = set()
    for client in connected_clients:
        try:
            await client.send_json(message)
        except Exception:
            disconnected.add(client)
    connected_clients.difference_update(disconnected)


async def status_broadcast_loop():
    while True:
        try:
            if demo_session.active:
                status = _demo_full_status()
            else:
                status = await manager.refresh_status()
            await broadcast({"type": "status", "payload": status})
        except Exception as exc:
            print(f"[MAIN] status broadcast failed: {exc}")
        await asyncio.sleep(1)


async def event_broadcast_loop():
    seen_event_ids: set[str] = set()
    while True:
        try:
            events = manager.get_recent_events(limit=100)
            for event in events:
                if event["id"] in seen_event_ids:
                    continue
                await broadcast({"type": "event", "payload": event})
                seen_event_ids.add(event["id"])
            current_ids = {event["id"] for event in events}
            seen_event_ids.intersection_update(current_ids)
        except Exception as exc:
            print(f"[MAIN] event broadcast failed: {exc}")
        await asyncio.sleep(1)


@app.on_event("startup")
async def startup():
    await embodiment_transport.start()
    asyncio.create_task(status_broadcast_loop())
    asyncio.create_task(event_broadcast_loop())


@app.on_event("shutdown")
async def shutdown():
    await embodiment_transport.stop()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await handle_message(message, websocket)
    except WebSocketDisconnect:
        connected_clients.discard(websocket)


async def handle_message(message: dict, websocket: WebSocket):
    msg_type = message.get("type")
    payload = message.get("payload", {})

    if msg_type == "command":
        cmd = payload.get("command")
        if cmd == "start_agent":
            result = await manager.start(payload.get("max_cycles"))
            await websocket.send_json({"type": "command_result", "payload": result})
        elif cmd == "stop_agent":
            result = await manager.stop()
            await websocket.send_json({"type": "command_result", "payload": result})
        elif cmd == "run_cycle":
            result = await manager.run_single_cycle()
            await websocket.send_json({"type": "command_result", "payload": result})
        elif cmd == "set_intensity":
            await broadcast(
                {
                    "type": "event",
                    "payload": {
                        "id": str(int(time.time() * 1000)),
                        "timestamp": int(time.time() * 1000),
                        "type": "action",
                        "message": f"Acquisition intensity set to {payload.get('level', 'moderate')}",
                    },
                }
            )
        elif cmd == "demo_start":
            result = demo_session.start()
            await websocket.send_json({"type": "command_result", "payload": result})
            await broadcast({"type": "status", "payload": _demo_full_status()})
            await broadcast(
                {
                    "type": "event",
                    "payload": {
                        "id": str(int(time.time() * 1000)),
                        "timestamp": int(time.time() * 1000),
                        "type": "demo",
                        "message": "Demo Mode started",
                    },
                }
            )
        elif cmd == "demo_advance":
            result = demo_session.advance()
            await websocket.send_json({"type": "command_result", "payload": result})
            await broadcast({"type": "status", "payload": _demo_full_status()})
            step_name = result.get("stepName", "Unknown")
            await broadcast(
                {
                    "type": "event",
                    "payload": {
                        "id": str(int(time.time() * 1000)),
                        "timestamp": int(time.time() * 1000),
                        "type": "demo",
                        "message": f"Demo step: {step_name}",
                    },
                }
            )
        elif cmd == "demo_reset":
            result = demo_session.reset()
            await websocket.send_json({"type": "command_result", "payload": result})
            await broadcast({"type": "status", "payload": _demo_full_status()})
        elif cmd == "embodiment_command":
            result = await embodiment_transport.send_action(
                str(payload.get("embodiment", "")), str(payload.get("action", ""))
            )
            await websocket.send_json({"type": "command_result", "payload": result})
            if result.get("success"):
                await broadcast(
                    {
                        "type": "event",
                        "payload": {
                            "id": result.get("request_id", str(int(time.time() * 1000))),
                            "timestamp": int(time.time() * 1000),
                            "type": "embodiment",
                            "message": (
                                f"{payload.get('embodiment')} embodiment: {payload.get('action')}"
                            ),
                        },
                    }
                )

    elif msg_type == "action":
        action = payload.get("action")
        await broadcast(
            {
                "type": "event",
                "payload": {
                    "id": str(int(time.time() * 1000)),
                    "timestamp": int(time.time() * 1000),
                    "type": "action",
                    "message": f"Action triggered: {action}",
                },
            }
        )


class AskRequest(BaseModel):
    question: str


@app.get("/api/status")
async def get_status():
    return await manager.refresh_status()


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "agent_running": manager._running,
        "embodiment_transport": embodiment_transport.snapshots(),
    }


@app.get("/api/simulator-health")
async def simulator_health():
    """Check if simulator ports are reachable."""

    async def reachable(port: int) -> bool:
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection("127.0.0.1", port), timeout=0.25
            )
            writer.close()
            await writer.wait_closed()
            return True
        except (TimeoutError, OSError):
            return False

    blender_port = int(os.environ.get("ONTOGENY_BLENDER_PORT", "8766"))
    mujoco_port = int(os.environ.get("ONTOGENY_MUJOCO_PORT", "8767"))
    blender, mujoco = await asyncio.gather(reachable(blender_port), reachable(mujoco_port))
    return {
        "blender": {"available": blender, "port": blender_port},
        "mujoco": {"available": mujoco, "port": mujoco_port},
    }


@app.post("/api/agent/start")
async def start_agent(max_cycles: int = Query(None)):
    return await manager.start(max_cycles)


@app.post("/api/agent/stop")
async def stop_agent():
    return await manager.stop()


@app.post("/api/agent/cycle")
async def run_cycle():
    return await manager.run_single_cycle()


@app.post("/api/agent/ask")
async def ask_agent(req: AskRequest):
    answer = await manager.ask(req.question)
    return {"answer": answer}


@app.get("/api/goals")
async def get_goals():
    return await manager.get_goals()


@app.get("/api/knowledge")
async def get_knowledge():
    return manager.get_knowledge_graph()


@app.get("/api/events")
async def get_events(limit: int = Query(50)):
    return manager.get_recent_events(limit)


@app.post("/api/demo/start")
async def demo_start():
    result = demo_session.start()
    await broadcast(
        {
            "type": "event",
            "payload": {
                "id": str(int(time.time() * 1000)),
                "timestamp": int(time.time() * 1000),
                "type": "demo",
                "message": "Demo Mode started",
            },
        }
    )
    return result


@app.post("/api/demo/advance")
async def demo_advance():
    result = demo_session.advance()
    await broadcast({"type": "status", "payload": _demo_full_status()})
    step_name = result.get("stepName", "")
    await broadcast(
        {
            "type": "event",
            "payload": {
                "id": str(int(time.time() * 1000)),
                "timestamp": int(time.time() * 1000),
                "type": "demo",
                "message": f"Demo step: {step_name}",
            },
        }
    )
    return result


@app.post("/api/demo/reset")
async def demo_reset():
    result = demo_session.reset()
    await broadcast(
        {
            "type": "event",
            "payload": {
                "id": str(int(time.time() * 1000)),
                "timestamp": int(time.time() * 1000),
                "type": "demo",
                "message": "Demo Mode reset",
            },
        }
    )
    return result


@app.get("/api/demo/status")
async def demo_status():
    return demo_session.get_status()


@app.get("/api/demo/goal")
async def demo_goal():
    return demo_session.get_goal()


@app.get("/api/demo/plan")
async def demo_plan():
    return demo_session.get_plan()


@app.get("/api/demo/evidence")
async def demo_evidence():
    return demo_session.get_evidence()


@app.get("/api/demo/memory")
async def demo_memory():
    return demo_session.get_memory_writes()


@app.get("/api/demo/knowledge-graph")
async def demo_knowledge_graph():
    return demo_session.get_knowledge_graph()


@app.get("/api/demo/reflection")
async def demo_reflection():
    return demo_session.get_reflection()


@app.get("/api/demo/maldoror")
async def demo_maldoror():
    return demo_session.get_maldoror_proposal()


def _demo_full_status() -> dict:
    base = manager.get_status()
    base["demo"] = demo_session.get_status()
    if demo_session.active:
        base["state"] = "demo"
    return base


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()

    port = args.port or find_available_port()
    print(f"Starting Ontogeny backend on port {port}")

    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=port)
