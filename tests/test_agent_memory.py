"""Smoke tests for agent manager and memory system.

Verifies agent manager singleton, memory system initialization,
and emotional processor basic functionality.
"""

import os
import sys

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
