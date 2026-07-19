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

app = FastAPI(title="Ontogeny Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

connected_clients: set[WebSocket] = set()


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
        status = manager.get_status()
        await broadcast({"type": "status", "payload": status})
        await asyncio.sleep(1)


async def event_broadcast_loop():
    last_count = 0
    while True:
        events = manager.get_recent_events(limit=100)
        new_events = events[last_count:]
        for event in new_events:
            await broadcast({"type": "event", "payload": event})
        last_count = len(events)
        await asyncio.sleep(1)


@app.on_event("startup")
async def startup():
    asyncio.create_task(status_broadcast_loop())
    asyncio.create_task(event_broadcast_loop())


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
                        "message": f"Crawl intensity set to {payload.get('level', 'moderate')}",
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
    return manager.get_status()


@app.get("/api/health")
async def health():
    return {"status": "ok", "agent_running": manager._running}


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
    return manager.get_goals()


@app.get("/api/knowledge")
async def get_knowledge():
    return manager.get_knowledge_graph()


@app.get("/api/events")
async def get_events(limit: int = Query(50)):
    return manager.get_recent_events(limit)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()

    port = args.port or find_available_port()
    print(f"Starting Ontogeny backend on port {port}")

    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=port)
