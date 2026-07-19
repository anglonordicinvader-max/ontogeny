import asyncio
import os
import sys
import time
from typing import Any, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class AgentManager:
    _instance: Optional["AgentManager"] = None
    _agent: Any = None
    _running: bool = False
    _task: asyncio.Task | None = None
    _stop_event: asyncio.Event | None = None
    _cycle_results: list = []
    _start_time: float = 0
    _initialized: bool = False

    def __new__(cls) -> "AgentManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _get_orchestrator_class(self):
        from crawler_agent.cognitive.orchestrator import CognitiveOrchestrator

        return CognitiveOrchestrator

    async def start(self, max_cycles: int | None = None) -> dict:
        if self._running:
            return {"status": "already_running"}

        try:
            OrchestratorClass = self._get_orchestrator_class()
            self._agent = OrchestratorClass()
            await self._agent.initialize()
            self._running = True
            self._stop_event = asyncio.Event()
            self._start_time = time.time()
            self._cycle_results = []
            self._task = asyncio.create_task(self._loop(max_cycles))
            self._initialized = True
            return {"status": "started"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def stop(self) -> dict:
        if not self._running:
            return {"status": "not_running"}

        self._running = False
        if self._stop_event:
            self._stop_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._agent:
            await self._agent.close()
            self._agent = None
        return {"status": "stopped"}

    async def run_single_cycle(self) -> dict | None:
        if not self._agent:
            return None
        try:
            result = await self._agent.run_cycle()
            self._cycle_results.append(result)
            return result
        except Exception as e:
            return {"error": str(e)}

    async def _loop(self, max_cycles: int | None):
        try:
            count = 0
            while self._running:
                if self._stop_event and self._stop_event.is_set():
                    break
                if max_cycles and count >= max_cycles:
                    break
                result = await self.run_single_cycle()
                if result:
                    count += 1
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            self._running = False

    def get_status(self) -> dict:
        if not self._agent:
            return self._idle_status()

        try:
            raw = self._agent.get_status()
            return self._map_status(raw)
        except Exception:
            return self._idle_status()

    def _idle_status(self) -> dict:
        return {
            "state": "idle" if not self._running else "running",
            "iteration": len(self._cycle_results),
            "uptime": int(time.time() - self._start_time) if self._start_time else 0,
            "mood": "neutral",
            "activeGoal": None,
            "drives": {
                "curiosity": 0.0,
                "mastery": 0.0,
                "competence": 0.0,
                "autonomy": 0.0,
                "novelty": 0.0,
            },
            "memory": {"working": 0, "episodic": 0, "semantic": 0, "procedural": 0},
            "crawlers": {"active": 0, "total": 0, "requestsToday": 0, "bandwidthUsed": 0},
            "maldoror": {
                "version": "v1.0.0",
                "qualityGate": "pending",
                "improvementPct": 0.0,
                "lastTrainingLoss": 0.0,
            },
            "production": {
                "latency": 0,
                "qualityScore": 0.0,
                "errorRate": 0.0,
                "circuitBreaker": "closed",
            },
        }

    def _map_status(self, raw: dict) -> dict:
        goals_data = raw.get("goals", {})
        drives = goals_data.get("drives", {})
        memory = raw.get("memory", {})
        mood_data = raw.get("mood", {})
        health = raw.get("health", {})
        crawlers_list = raw.get("crawlers", [])
        scheduler = raw.get("scheduler", {})
        sm_stats = raw.get("self_modification", {})
        rm_stats = raw.get("recursive_modification", {})

        return {
            "state": raw.get("state", "idle"),
            "iteration": raw.get("iteration", 0),
            "uptime": int(raw.get("uptime_seconds", 0)),
            "mood": mood_data.get("current_mood", "neutral")
            if isinstance(mood_data, dict)
            else str(mood_data),
            "activeGoal": raw.get("current_plan", {}).get("goal", {}).get("description")
            if raw.get("current_plan")
            else None,
            "drives": {
                "curiosity": drives.get("curiosity", 0.0),
                "mastery": drives.get("mastery", 0.0),
                "competence": drives.get("competence", 0.0),
                "autonomy": drives.get("autonomy", 0.0),
                "novelty": drives.get("novelty", 0.0),
            },
            "memory": {
                "working": memory.get("working_memory_size", 0),
                "episodic": memory.get("episodic_count", 0),
                "semantic": memory.get("semantic_count", 0),
                "procedural": memory.get("procedural_count", 0),
            },
            "crawlers": {
                "active": len(crawlers_list),
                "total": len(crawlers_list),
                "requestsToday": scheduler.get("requests_today", 0)
                if isinstance(scheduler, dict)
                else 0,
                "bandwidthUsed": scheduler.get("bandwidth_used", 0)
                if isinstance(scheduler, dict)
                else 0,
            },
            "maldoror": {
                "version": sm_stats.get("version", "v1.0.0")
                if isinstance(sm_stats, dict)
                else "v1.0.0",
                "qualityGate": "pass"
                if rm_stats and isinstance(rm_stats, dict) and rm_stats.get("applied")
                else "pending",
                "improvementPct": rm_stats.get("performance_delta", 0.0) * 100
                if isinstance(rm_stats, dict)
                else 0.0,
                "lastTrainingLoss": sm_stats.get("last_loss", 0.0)
                if isinstance(sm_stats, dict)
                else 0.0,
            },
            "production": {
                "latency": 0,
                "qualityScore": 0.95,
                "errorRate": 0.01,
                "circuitBreaker": health.get("circuit_breakers", {}).get("default", "closed")
                if isinstance(health, dict)
                else "closed",
            },
            "knowledge": {
                "nodes": raw.get("knowledge_graph", {}).get("concept_count", 0)
                if isinstance(raw.get("knowledge_graph"), dict)
                else 0,
                "edges": raw.get("knowledge_graph", {}).get("relation_count", 0)
                if isinstance(raw.get("knowledge_graph"), dict)
                else 0,
            },
            "selfReflection": raw.get("self_reflection", {}),
            "rlAgent": raw.get("rl_agent", {}),
            "curiosity": raw.get("curiosity", {}),
            "metacognition": raw.get("metacognition", {}),
        }

    def get_recent_events(self, limit: int = 50) -> list:
        events = []
        for result in self._cycle_results[-limit:]:
            iteration = result.get("iteration", 0)
            ts = int(time.time() * 1000) - (limit - len(events)) * 1000

            for action in result.get("actions", []):
                events.append(
                    {
                        "id": f"{iteration}-action-{len(events)}",
                        "timestamp": ts,
                        "type": "action",
                        "message": action.get("action", action.get("step", "Unknown action")),
                    }
                )

            for learning in result.get("learnings", []):
                events.append(
                    {
                        "id": f"{iteration}-learning-{len(events)}",
                        "timestamp": ts,
                        "type": "learning",
                        "message": str(learning)[:200],
                    }
                )

            if result.get("recursive_modification"):
                mod = result["recursive_modification"]
                events.append(
                    {
                        "id": f"{iteration}-mod-{len(events)}",
                        "timestamp": ts,
                        "type": "modification",
                        "message": mod.get("description", "Self-modification applied"),
                    }
                )

            if result.get("error"):
                events.append(
                    {
                        "id": f"{iteration}-error-{len(events)}",
                        "timestamp": ts,
                        "type": "error",
                        "message": result["error"],
                    }
                )

            if result.get("maldoror_training"):
                training = result["maldoror_training"]
                events.append(
                    {
                        "id": f"{iteration}-training-{len(events)}",
                        "timestamp": ts,
                        "type": "training",
                        "message": f"Maldoror v{training.get('version', '?')} trained, loss={training.get('loss', '?')}",
                    }
                )

        return events[-limit:]

    def get_goals(self) -> list:
        if not self._agent:
            return []
        try:
            goals_mgr = self._agent.goals
            active = goals_mgr.get_active_goals() if hasattr(goals_mgr, "get_active_goals") else []
            return [
                {
                    "id": str(getattr(g, "id", i)),
                    "description": getattr(g, "description", str(g)),
                    "status": getattr(g, "status", "active").lower()
                    if hasattr(g, "status")
                    else "active",
                    "progress": getattr(g, "progress", 0.0),
                    "priority": getattr(g, "priority", "medium").lower()
                    if hasattr(g, "priority")
                    else "medium",
                }
                for i, g in enumerate(active)
            ]
        except Exception:
            return []

    def get_knowledge_graph(self) -> dict:
        if not self._agent:
            return {"nodes": [], "edges": []}
        try:
            kg = self._agent.knowledge_graph
            if hasattr(kg, "concepts") and hasattr(kg, "relations"):
                nodes = [
                    {
                        "id": c.get("id", str(i)),
                        "name": c.get("name", "?"),
                        "type": "concept",
                        "connections": 0,
                        "strength": c.get("strength", 0.0),
                    }
                    for i, c in enumerate(
                        list(kg.concepts.values())[:50] if isinstance(kg.concepts, dict) else []
                    )
                ]
                edges = [
                    {
                        "source": r.get("source_id", ""),
                        "target": r.get("target_id", ""),
                        "type": r.get("relation_type", ""),
                        "weight": r.get("weight", 1.0),
                    }
                    for r in (
                        list(kg.relations.values())[:100] if isinstance(kg.relations, dict) else []
                    )
                ]
                return {"nodes": nodes, "edges": edges}
        except Exception:
            pass
        return {"nodes": [], "edges": []}

    async def ask(self, question: str) -> str:
        if not self._agent:
            return "Agent not initialized"
        try:
            return await self._agent.handle_user_input(question)
        except Exception as e:
            return f"Error: {e}"


manager = AgentManager()
