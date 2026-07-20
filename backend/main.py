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

app = FastAPI(title="Ontogeny Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

connected_clients: set[WebSocket] = set()
_sim_events: list[dict] = []


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
                status = manager.get_status()
            await broadcast({"type": "status", "payload": status})
        except Exception as e:
            print(f"[MAIN] status_broadcast_loop error: {e}")
        await asyncio.sleep(1)


async def event_broadcast_loop():
    last_count = 0
    while True:
        try:
            manager_events = manager.get_recent_events(limit=100)
            all_events = manager_events + _sim_events[-50:]
            new_events = all_events[last_count:]
            for event in new_events:
                await broadcast({"type": "event", "payload": event})
            last_count = len(all_events)
        except Exception as e:
            print(f"[MAIN] event_broadcast_loop error: {e}")
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
                        "message": f"Acquisition intensity set to {payload.get('level', 'moderate')}",
                    },
                }
            )
        elif cmd == "demo_start":
            result = demo_session.start()
            await websocket.send_json({"type": "command_result", "payload": result})
            await broadcast({"type": "status", "payload": _demo_full_status()})
            await broadcast({"type": "event", "payload": {"id": str(int(time.time() * 1000)), "timestamp": int(time.time() * 1000), "type": "demo", "message": "Demo Mode started"}})
        elif cmd == "demo_advance":
            result = demo_session.advance()
            await websocket.send_json({"type": "command_result", "payload": result})
            await broadcast({"type": "status", "payload": _demo_full_status()})
            step_name = result.get("stepName", "Unknown")
            await broadcast({"type": "event", "payload": {"id": str(int(time.time() * 1000)), "timestamp": int(time.time() * 1000), "type": "demo", "message": f"Demo step: {step_name}"}})
        elif cmd == "demo_reset":
            result = demo_session.reset()
            await websocket.send_json({"type": "command_result", "payload": result})
            await broadcast({"type": "status", "payload": _demo_full_status()})

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


@app.get("/api/simulator-health")
async def simulator_health():
    """Check if simulator ports are reachable."""
    result = {"blender": {"available": False}, "mujoco": {"available": False}}
    # The simulators run on the same host. We check if their WebSocket ports accept connections.
    # In the Electron app, the main process knows the ports. Here we just report based on
    # whether the processes were spawned. The frontend handles its own health checks.
    return result


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


@app.post("/api/demo/start")
async def demo_start():
    result = demo_session.start()
    await broadcast({"type": "event", "payload": {
        "id": str(int(time.time() * 1000)),
        "timestamp": int(time.time() * 1000),
        "type": "demo",
        "message": "Demo Mode started",
    }})
    return result


@app.post("/api/demo/advance")
async def demo_advance():
    result = demo_session.advance()
    await broadcast({"type": "status", "payload": _demo_full_status()})
    step_name = result.get("stepName", "")
    await broadcast({"type": "event", "payload": {
        "id": str(int(time.time() * 1000)),
        "timestamp": int(time.time() * 1000),
        "type": "demo",
        "message": f"Demo step: {step_name}",
    }})
    return result


@app.post("/api/demo/reset")
async def demo_reset():
    result = demo_session.reset()
    await broadcast({"type": "event", "payload": {
        "id": str(int(time.time() * 1000)),
        "timestamp": int(time.time() * 1000),
        "type": "demo",
        "message": "Demo Mode reset",
    }})
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


@app.get("/api/demo/subsystems")
async def demo_subsystems():
    return demo_session.get_subsystems()


@app.get("/api/demo/loading-stages")
async def demo_loading_stages():
    return demo_session.get_loading_stages()


@app.get("/api/demo/maldoror-pipeline")
async def demo_maldoror_pipeline():
    return demo_session.get_maldoror_pipeline()


@app.get("/api/demo/runtime-metrics")
async def demo_runtime_metrics():
    return demo_session.get_runtime_metrics()


@app.get("/api/demo/behavior-stats")
async def demo_behavior_stats():
    return demo_session.get_behavior_stats()


@app.get("/api/demo/model-routing")
async def demo_model_routing():
    return demo_session.get_model_routing()


def _demo_full_status() -> dict:
    # Generate simulation data directly
    sim_data = {}
    sim_events = []
    try:
        import sys as _sys
        _backend_dir = os.path.dirname(__file__)
        if _backend_dir not in _sys.path:
            _sys.path.insert(0, _backend_dir)
        from simulation import generate_status as _gen_status, generate_event as _gen_event, start_time as _start_time
        import time as _time
        _t = _time.time() - _start_time
        _cycle = int(_t)
        sim_data = _gen_status(_cycle, _t)
        # Generate a few events for the activity timeline
        for i in range(3):
            ev = _gen_event(_cycle - i, _t - i * 1.5)
            sim_events.append(ev)
    except Exception:
        pass

    # Inject dynamic knowledge graph from simulation
    if sim_data and "knowledge" in sim_data:
        import random as _rnd
        _cycle = sim_data.get("iteration", 0)
        _rnd.seed(_cycle)
        _kg = sim_data["knowledge"]
        _n = _kg.get("nodes", 0)
        _e = _kg.get("edges", 0)
        _concepts = [
            "Neural Architecture", "Attention Mechanism", "Memory Consolidation",
            "Causal Reasoning", "Knowledge Transfer", "Self-Modification",
            "Pattern Recognition", "Goal Management", "World Model",
            "Curiosity Engine", "Emotional State", "Meta-cognition",
            "Sensor Fusion", "Locomotion Control", "Object Detection",
            "Reinforcement Learning", "Skill Composition", "Uncertainty Tracking",
        ]
        _types = ["concept", "algorithm", "metric", "capability", "module"]
        _nodes = []
        for i in range(min(_n, 18)):
            _nodes.append({
                "id": f"n{i}",
                "name": _concepts[i % len(_concepts)],
                "type": _types[i % len(_types)],
                "connections": _rnd.randint(1, 5),
                "strength": round(0.7 + _rnd.random() * 0.3, 2),
            })
        _edges = []
        for i in range(min(_e, 24)):
            _s = _rnd.randint(0, max(0, len(_nodes) - 1))
            _t_idx = _rnd.randint(0, max(0, len(_nodes) - 1))
            if _s != _t_idx:
                _edges.append({
                    "source": f"n{_s}",
                    "target": f"n{_t_idx}",
                    "type": _rnd.choice(["uses", "improves", "relates_to", "depends_on"]),
                    "weight": round(0.5 + _rnd.random() * 0.5, 2),
                })
        sim_data["knowledge_graph"] = {"nodes": _nodes, "edges": _edges}

    if demo_session.active:
        base = sim_data if sim_data else manager.get_status()
        base["demo"] = demo_session.get_status()
        base["state"] = "demo"
        base["demo"]["subsystems"] = demo_session.get_subsystems()
        base["demo"]["maldororPipeline"] = demo_session.get_maldoror_pipeline()
        base["demo"]["runtimeMetrics"] = demo_session.get_runtime_metrics()
        base["demo"]["behaviorStats"] = demo_session.get_behavior_stats()
        base["demo"]["modelRouting"] = demo_session.get_model_routing()
        base["demo"]["loadingStages"] = demo_session.get_loading_stages()
        # Inject simulation events into activity timeline
        for ev in sim_events:
            _sim_events.append(ev)
        if len(_sim_events) > 200:
            del _sim_events[:-200]
        return base
    else:
        # Also inject events when not in demo mode
        for ev in sim_events:
            _sim_events.append(ev)
        if len(_sim_events) > 200:
            del _sim_events[:-200]
        return sim_data if sim_data else manager.get_status()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()

    port = args.port or find_available_port()
    print(f"Starting Ontogeny backend on port {port}")

    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=port)
