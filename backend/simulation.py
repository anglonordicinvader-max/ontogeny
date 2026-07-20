import asyncio
import json
import math
import os
import random
import sys
import time

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

start_time = time.time()
connected_clients: list[WebSocket] = []

# World imports
try:
    from crawler_agent.cognitive.practical_worlds import PRACTICAL_WORLDS
    from crawler_agent.cognitive.survival_worlds import ALL_SURVIVAL_WORLDS

    ALL_WORLDS = {}
    ALL_WORLDS.update(PRACTICAL_WORLDS)
    for name, world in ALL_SURVIVAL_WORLDS.items():
        ALL_WORLDS[name] = world
except ImportError:
    PRACTICAL_WORLDS = {}
    ALL_SURVIVAL_WORLDS = {}
    ALL_WORLDS = {}

WORLD_NAMES = list(ALL_WORLDS.keys())

STATES = [
    "idle",
    "thinking",
    "planning",
    "executing",
    "learning",
    "self_modifying",
    "training",
    "running",
]
EVENT_MESSAGES = {
    "action": [
        "Crawled 15 pages from arxiv.org",
        "Indexed 23 new concepts into knowledge graph",
        "Processed 4.2MB of web data",
        "Extracted 87 entity relationships",
        "Updated semantic memory with 12 new patterns",
        "Synthesized 3 cross-domain insights",
        "Generated hypothesis about causal reasoning",
        "Validated 6 existing knowledge links",
    ],
    "learning": [
        "Curiosity drive triggered exploration of quantum computing",
        "Mastery drive increased focus on NLP techniques",
        "Novelty drive seeking alternative architectures",
        "Competence drive reinforcing successful patterns",
        "Autonomy drive experimenting with self-directed learning",
    ],
    "modification": [
        "Maldoror suggested attention head reallocation",
        "Self-modified learning rate schedule",
        "Adjusted memory consolidation threshold",
        "Refined reward shaping parameters",
        "Updated exploration-exploitation balance",
    ],
    "training": [
        "Maldoror training epoch 1/5 complete",
        "Loss decreasing: 0.2341 → 0.1987",
        "Evaluation: improvement score +2.3%",
        "Quality gate check: PASS",
        "Population member evaluated: fitness 0.87",
    ],
    "error": [
        "Crawler rate-limited by target domain",
        "Memory consolidation temporarily stalled",
        "Training batch contained anomalous data",
    ],
}


def lerp(a, b, t):
    return a + (b - a) * t


def ease_in_out(t):
    return t * t * (3 - 2 * t)


def generate_status(cycle: int, t: float) -> dict:
    state_idx = int(t / 3) % len(STATES)
    state = STATES[state_idx]

    phase = (t % 3) / 3.0
    smooth = ease_in_out(phase)

    base_drives = {
        "curiosity": 0.5 + 0.3 * math.sin(t * 0.7),
        "mastery": 0.4 + 0.25 * math.sin(t * 0.5 + 1.0),
        "competence": 0.6 + 0.2 * math.sin(t * 0.3 + 2.0),
        "autonomy": 0.3 + 0.35 * math.sin(t * 0.4 + 0.5),
        "novelty": 0.45 + 0.3 * math.sin(t * 0.6 + 1.5),
    }

    if state == "thinking":
        base_drives["curiosity"] = min(1.0, base_drives["curiosity"] + 0.3)
    elif state == "learning":
        base_drives["mastery"] = min(1.0, base_drives["mastery"] + 0.3)
        base_drives["competence"] = min(1.0, base_drives["competence"] + 0.2)
    elif state == "self_modifying":
        base_drives["novelty"] = min(1.0, base_drives["novelty"] + 0.4)
        base_drives["autonomy"] = min(1.0, base_drives["autonomy"] + 0.3)
    elif state == "training":
        base_drives["mastery"] = min(1.0, base_drives["mastery"] + 0.35)

    drives = {k: max(0.0, min(1.0, v)) for k, v in base_drives.items()}

    memory_base = min(cycle * 3, 500)
    memory = {
        "working": min(128, int(memory_base * 0.3 + 20 * math.sin(t * 0.8))),
        "episodic": min(2000, int(memory_base * 0.5 + cycle * 2)),
        "semantic": min(5000, int(memory_base * 1.2 + cycle * 5)),
        "procedural": min(1000, int(memory_base * 0.4 + cycle)),
    }

    crawler_active = max(0, min(35, int(12 + 8 * math.sin(t * 0.3))))
    requests_today = min(10000, cycle * 47 + int(200 * smooth))
    bandwidth = min(100 * 1024 * 1024, cycle * 1024 * 1024 + int(5 * 1024 * 1024 * smooth))

    latency = max(15, min(350, int(85 + 60 * math.sin(t * 1.2) + random.gauss(0, 15))))
    quality = max(0.7, min(1.0, 0.92 + 0.06 * math.sin(t * 0.4) + random.gauss(0, 0.01)))
    error_rate = max(0.0, min(0.15, 0.02 + 0.03 * math.sin(t * 0.9) + random.gauss(0, 0.005)))

    if error_rate > 0.1:
        circuit = "open"
    elif error_rate > 0.05:
        circuit = "half-open"
    else:
        circuit = "closed"

    goals = [
        "Explore emergent reasoning patterns in transformer architectures",
        "Build causal inference graph from cross-domain knowledge",
        "Optimize memory consolidation for long-term retention",
        "Develop novel attention mechanisms for multi-modal reasoning",
        "Synthesize insights from disparate knowledge domains",
        "Refine self-modification safety constraints",
    ]
    active_goal = goals[cycle % len(goals)] if state != "idle" else None

    moods = ["focused", "curious", "analytical", "contemplative", "determined", "exploratory"]
    mood = moods[cycle % len(moods)]

    maldoror_loss = max(0.05, 0.25 - cycle * 0.008 + random.gauss(0, 0.01))
    improvement = min(15.0, cycle * 0.5 + random.gauss(0, 0.2))

    knowledge_nodes = min(800, cycle * 12 + int(30 * smooth))
    knowledge_edges = min(2400, cycle * 36 + int(90 * smooth))

    # Select world based on state and drives
    current_world = None
    if WORLD_NAMES and state != "idle":
        # Map states to world preferences
        state_world_map = {
            "thinking": ["indoor_maze", "office_building", "small_house"],
            "planning": ["robot_obstacle_course", "parkour_course", "construction_site"],
            "executing": ["warehouse", "truck_loading", "stair_climb"],
            "learning": ["small_house", "office_building", "indoor_maze"],
            "perceiving": ["construction_site", "parkour_course", "robot_obstacle_course"],
        }
        preferred = state_world_map.get(state, [])
        for w in preferred:
            if w in ALL_WORLDS:
                current_world = w
                break
        if not current_world and WORLD_NAMES:
            current_world = WORLD_NAMES[cycle % len(WORLD_NAMES)]

    world_info = None
    if current_world and current_world in ALL_WORLDS:
        w = ALL_WORLDS[current_world]
        world_info = {
            "name": current_world,
            "description": w.description if hasattr(w, "description") else "",
            "difficulty": w.difficulty
            if hasattr(w, "difficulty")
            else w.tier / 4.0
            if hasattr(w, "tier")
            else 0.5,
            "tags": w.tags if hasattr(w, "tags") else [],
            "type": w.world_type.value if hasattr(w, "world_type") else "unknown",
            "num_objects": len(w.objects) if hasattr(w, "objects") else 0,
            "num_interactive": len(w.interactive) if hasattr(w, "interactive") else 0,
        }

    return {
        "state": state,
        "iteration": cycle,
        "uptime": int(time.time() - start_time),
        "mood": mood,
        "activeGoal": active_goal,
        "drives": drives,
        "memory": memory,
        "crawlers": {
            "active": crawler_active,
            "total": 35,
            "requestsToday": requests_today,
            "bandwidthUsed": bandwidth,
        },
        "maldoror": {
            "version": "v1.0.0",
            "qualityGate": "pass" if improvement > 5.0 else "pending",
            "improvementPct": round(improvement, 1),
            "lastTrainingLoss": round(maldoror_loss, 4),
        },
        "production": {
            "latency": latency,
            "qualityScore": round(quality, 3),
            "errorRate": round(error_rate, 4),
            "circuitBreaker": circuit,
        },
        "knowledge": {
            "nodes": knowledge_nodes,
            "edges": knowledge_edges,
        },
        "selfReflection": {
            "lastReflection": f"Observed {state} state with {mood} mood. Drives balanced toward {max(drives, key=drives.get)} focus.",
            "insightsCount": cycle * 3,
        },
        "rlAgent": {
            "episodes": cycle,
            "avgReward": round(0.5 + 0.3 * math.sin(t * 0.2), 3),
        },
        "curiosity": {
            "explorationRate": round(0.3 + 0.2 * math.sin(t * 0.5), 3),
            "infoGain": round(0.1 + 0.15 * math.sin(t * 0.7), 3),
        },
        "metacognition": {
            "confidence": round(0.7 + 0.2 * math.sin(t * 0.3), 3),
            "uncertainty": round(0.2 + 0.1 * math.sin(t * 0.6), 3),
        },
        "world": world_info,
    }


def generate_event(cycle: int, t: float) -> dict:
    event_type = random.choices(
        ["action", "learning", "modification", "training", "error"], weights=[40, 25, 15, 15, 5]
    )[0]
    messages = EVENT_MESSAGES[event_type]
    message = messages[cycle % len(messages)]

    return {
        "id": f"{cycle}-{event_type}-{random.randint(0, 999)}",
        "timestamp": int(time.time() * 1000),
        "type": event_type,
        "message": message,
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    print(f"[SIM] Client connected ({len(connected_clients)} total)")

    cycle = 0
    t = 0.0
    last_event_time = 0

    try:
        while True:
            status = generate_status(cycle, t)
            await websocket.send_json({"type": "status", "payload": status})

            if t - last_event_time > 1.5 + random.random() * 2:
                event = generate_event(cycle, t)
                await websocket.send_json({"type": "event", "payload": event})
                last_event_time = t

            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                msg = json.loads(data)
                if msg.get("type") == "command":
                    await websocket.send_json(
                        {
                            "type": "command_result",
                            "payload": {
                                "status": "started",
                                "command": msg["payload"].get("command", "unknown"),
                            },
                        }
                    )
            except TimeoutError:
                pass

            cycle += 1
            t += 1.0

    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        print(f"[SIM] Client disconnected ({len(connected_clients)} total)")
    except Exception as e:
        print(f"[SIM] Error: {e}")
        if websocket in connected_clients:
            connected_clients.remove(websocket)


@app.get("/")
async def root():
    return {"status": "simulation server running", "clients": len(connected_clients)}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/status")
async def status():
    cycle = int(time.time() - start_time)
    t = time.time() - start_time
    return generate_status(cycle, t)


if __name__ == "__main__":
    import uvicorn

    print("[SIM] Starting simulation server on port 8765...")
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")
