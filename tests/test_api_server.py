"""Smoke tests for simulation server and backend API.

Verifies FastAPI endpoints and WebSocket handler can be
imported and basic routes exist.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestSimulationServer:
    """Test simulation server can be imported and has expected routes."""

    def test_import_simulation_app(self):
        from simulation import app

        assert app is not None

    def test_simulation_has_routes(self):
        from simulation import app

        routes = [r.path for r in app.routes]
        assert "/ws" in routes
        assert "/" in routes
        assert "/health" in routes

    def test_generate_status(self):
        from simulation import generate_status

        status = generate_status(cycle=0, t=0.0)
        assert "state" in status
        assert "drives" in status
        assert "memory" in status
        assert "crawlers" in status

    def test_generate_event(self):
        from simulation import generate_event

        event = generate_event(cycle=0, t=0.0)
        assert "id" in event
        assert "type" in event
        assert "message" in event


class TestBlenderWorlds:
    """Test standalone blender_worlds module."""

    def test_import_practical_worlds(self):
        from blender_worlds import PRACTICAL_WORLDS

        assert len(PRACTICAL_WORLDS) == 9

    def test_import_survival_worlds(self):
        from blender_worlds import ALL_SURVIVAL_WORLDS

        assert len(ALL_SURVIVAL_WORLDS) == 30

    def test_world_selector_select(self):
        from blender_worlds import SelectionCriteria, WorldSelector

        ws = WorldSelector()
        result = ws.select(SelectionCriteria())
        assert result is not None
        assert result.world is not None

    def test_practical_world_has_required_fields(self):
        from blender_worlds import PRACTICAL_WORLDS

        for _name, world in PRACTICAL_WORLDS.items():
            assert hasattr(world, "name")
            assert hasattr(world, "description")
            assert hasattr(world, "objects")
            assert hasattr(world, "difficulty")
