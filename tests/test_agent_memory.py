"""Smoke tests for agent manager and memory system.

Verifies agent manager singleton, memory system initialization,
and emotional processor basic functionality.
"""

import os
import sys
from types import SimpleNamespace

import networkx as nx
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestAgentManager:
    """Test AgentManager singleton and basic operations."""

    def test_import_agent_manager(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from agent_manager import AgentManager

        assert AgentManager is not None

    def test_singleton_pattern(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from agent_manager import AgentManager

        a = AgentManager()
        b = AgentManager()
        assert a is b

    @pytest.mark.asyncio
    async def test_refresh_status_awaits_orchestrator_and_maps_live_state(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from agent_manager import AgentManager

        graph = nx.DiGraph()
        graph.add_edge("core", "body", relation_type="embodies", weight=0.8)
        concept = SimpleNamespace(id="core", name="Ontogeny Core", strength=1.0)

        async def get_status():
            return {
                "state": "planning",
                "iteration": 4,
                "uptime_seconds": 8,
                "goals": {"drives": {"curiosity": 0.7}},
                "memory": {"semantic_count": 3},
                "knowledge_graph": {"concepts": 1, "relations": 1},
                "maldoror": {"current_version": "v3", "avg_loss": 0.2},
                "backend": {"modifier_backend": "maldoror"},
                "embodiment": {"blender": True, "mujoco": True},
            }

        manager = AgentManager()
        manager._status_cache = None
        manager._agent = SimpleNamespace(
            get_status=get_status,
            knowledge_graph=SimpleNamespace(concepts={"core": concept}, graph=graph),
        )

        status = await manager.refresh_status()

        assert status["state"] == "planning"
        assert status["memory"]["semantic"] == 3
        assert status["maldoror"]["version"] == "v3"
        assert status["embodiment"] == {"blender": True, "mujoco": True}
        assert status["knowledgeGraph"]["nodes"][0]["name"] == "Ontogeny Core"
        assert status["knowledgeGraph"]["edges"][0]["type"] == "embodies"

    @pytest.mark.asyncio
    async def test_goal_serialization_awaits_goal_manager(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from agent_manager import AgentManager

        from crawler_agent.cognitive.goals import GoalPriority, GoalStatus

        async def active_goals():
            return [
                SimpleNamespace(
                    id="g1",
                    description="Validate embodiment",
                    status=GoalStatus.ACTIVE,
                    progress=0.5,
                    priority=GoalPriority.HIGH,
                )
            ]

        manager = AgentManager()
        manager._agent = SimpleNamespace(goals=SimpleNamespace(get_active_goals=active_goals))

        goals = await manager.get_goals()

        assert goals == [
            {
                "id": "g1",
                "description": "Validate embodiment",
                "status": "active",
                "progress": 0.5,
                "priority": "high",
            }
        ]


class TestMemorySystem:
    """Test memory system initialization."""

    def test_import_memory(self):
        from crawler_agent.cognitive.memory import MemorySystem

        assert MemorySystem is not None

    def test_memory_initialization(self):
        from crawler_agent.cognitive.memory import MemorySystem

        mem = MemorySystem(database_url="sqlite+aiosqlite:///:memory:")
        assert mem is not None


class TestEmotionalProcessor:
    """Test emotional processor basic functionality."""

    def test_import_emotional(self):
        from crawler_agent.cognitive.emotional import EmotionalProcessor, EmotionalState

        assert EmotionalProcessor is not None

    def test_emotional_state_creation(self):
        from crawler_agent.cognitive.emotional import EmotionalState

        state = EmotionalState()
        assert state is not None


class TestGoalManager:
    """Test goal manager initialization."""

    def test_import_goals(self):
        from crawler_agent.cognitive.goals import GoalManager

        assert GoalManager is not None

    def test_goal_manager_initialization(self):
        from crawler_agent.cognitive.goals import GoalManager

        gm = GoalManager()
        assert gm is not None


class TestKnowledgeGraph:
    """Test knowledge graph initialization."""

    def test_import_knowledge_graph(self):
        from crawler_agent.cognitive.knowledge_graph import KnowledgeGraph

        assert KnowledgeGraph is not None

    def test_knowledge_graph_import(self):
        from crawler_agent.cognitive.knowledge_graph import KnowledgeGraph

        kg = KnowledgeGraph(backend="memory")
        assert kg is not None
