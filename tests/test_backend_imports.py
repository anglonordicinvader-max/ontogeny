"""Smoke tests for backend imports and initialization.

Verifies that critical modules can be imported and basic
initialization works without external dependencies.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestBackendImports:
    """Verify critical backend modules can be imported."""

    def test_import_memory_system(self):
        from crawler_agent.cognitive.memory import MemorySystem

        assert MemorySystem is not None

    def test_import_emotional_processor(self):
        from crawler_agent.cognitive.emotional import EmotionalProcessor, EmotionalState

        assert EmotionalProcessor is not None
        assert EmotionalState is not None

    def test_import_goal_manager(self):
        from crawler_agent.cognitive.goals import Goal, GoalManager

        assert GoalManager is not None

    def test_import_self_modifier(self):
        from crawler_agent.cognitive.self_modify import SelfModifier

        assert SelfModifier is not None

    def test_import_knowledge_graph(self):
        from crawler_agent.cognitive.knowledge_graph import KnowledgeGraph

        assert KnowledgeGraph is not None

    def test_import_blender_sandbox(self):
        from crawler_agent.cognitive.blender_sandbox import BlenderSandbox, SimulationSpec

        assert BlenderSandbox is not None

    def test_import_cognitive_backend(self):
        from crawler_agent.cognitive.backend import CognitiveBackend

        assert CognitiveBackend is not None

    def test_import_practical_worlds(self):
        from crawler_agent.cognitive.practical_worlds import PRACTICAL_WORLDS

        assert len(PRACTICAL_WORLDS) > 0

    def test_import_survival_worlds(self):
        from crawler_agent.cognitive.survival_worlds import ALL_SURVIVAL_WORLDS

        assert len(ALL_SURVIVAL_WORLDS) > 0

    def test_import_world_selector(self):
        from crawler_agent.cognitive.world_selector import WorldSelector

        ws = WorldSelector()
        assert ws is not None

    def test_import_orchestrator_simulation_types(self):
        from crawler_agent.cognitive.orchestrator import BlenderSimulationType, SimulationType

        assert hasattr(SimulationType, "PLANNING")
        assert hasattr(BlenderSimulationType, "RIGID_BODY")


class TestSimulationTypeSeparation:
    """Verify the two SimulationType enums don't collide."""

    def test_simulator_simulation_type(self):
        from crawler_agent.cognitive.simulator import SimulationType

        members = [m.name for m in SimulationType]
        assert "PLANNING" in members
        assert "DREAM" in members
        assert "RIGID_BODY" not in members

    def test_blender_simulation_type(self):
        from crawler_agent.cognitive.blender_sandbox import SimulationType

        members = [m.name for m in SimulationType]
        assert "RIGID_BODY" in members
        assert "EMOTION" in members
        assert "PLANNING" not in members
