"""Smoke tests for Blender simulation module.

Tests the parts of blender_simulation.py that don't require
a running Blender instance (data structures, imports, helpers).
"""

import ast
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestBlenderSimulationSyntax:
    """Verify blender_simulation.py has valid Python syntax."""

    def test_syntax_valid(self):
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "blender_simulation.py")
        with open(path, encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
        assert tree is not None

    def test_has_main_class(self):
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "blender_simulation.py")
        with open(path, encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
        class_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        assert "BlenderSimulation" in class_names

    def test_has_required_methods(self):
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "blender_simulation.py")
        with open(path, encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "BlenderSimulation":
                method_names = [
                    n.name
                    for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                assert "_setup_scene" in method_names
                assert "_build_anatomy_scene" in method_names
                assert "_build_sphere_scene" in method_names
                assert "animate" in method_names
                assert "run" in method_names
                return
        pytest.fail("BlenderSimulation class not found")

    def test_health_command_in_handler(self):
        """blender_simulation.py WebSocket handler should support 'health' command."""
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "blender_simulation.py")
        with open(path, encoding="utf-8") as f:
            source = f.read()
        assert 'cmd == "health"' in source or "cmd == 'health'" in source

    def test_health_response_contains_required_fields(self):
        """Health response should include status, mode, world, emotion, frame, running."""
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "blender_simulation.py")
        with open(path, encoding="utf-8") as f:
            source = f.read()
        for field in ["status", "mode", "world", "emotion", "frame", "running"]:
            assert f'"{field}"' in source or f"'{field}'" in source, f"Missing field: {field}"

    def test_real_renderer_has_single_blender_thread_owner(self):
        """bpy rendering must not be delegated while the scene is mutated by async tasks."""
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "blender_simulation.py")
        with open(path, encoding="utf-8") as f:
            source = f.read()
        assert "ThreadPoolExecutor" not in source
        assert "_render_executor" not in source
        assert "self._render_to_file()" in source

    def test_renderer_never_generates_placeholder_frames(self):
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "blender_simulation.py")
        with open(path, encoding="utf-8") as f:
            source = f.read()
        assert "_generate_placeholder_frame" not in source

    def test_blender_frontend_owns_the_supplied_service_port(self):
        """App supplies backend + 1; BlenderEmbed must not offset it into MuJoCo's port."""
        path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "desktop",
            "renderer",
            "src",
            "components",
            "BlenderEmbed.tsx",
        )
        with open(path, encoding="utf-8") as f:
            source = f.read()
        assert "useState<number>(backendPort);" in source
        assert "useState<number>(backendPort + 1);" not in source

    def test_world_manager_protocol_preserves_manual_ownership(self):
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "blender_simulation.py")
        with open(path, encoding="utf-8") as f:
            source = f.read()
        assert 'cmd == "worlds"' in source
        assert '"type": "world_catalog"' in source
        assert '"type": "world_changed"' in source
        assert 'self.world_source = "manual"' in source
        assert 'self.world_source == "autonomous"' in source


class TestBlenderSimulationImportChain:
    """Verify the import chain in blender_simulation.py doesn't crash."""

    def test_blender_worlds_imports(self):
        from blender_worlds import (
            ALL_SURVIVAL_WORLDS,
            PRACTICAL_WORLDS,
            PracticalWorld,
            SelectionCriteria,
            SurvivalChallenge,
            WorldSelector,
            WorldType,
        )

        assert len(PRACTICAL_WORLDS) == 12
        assert len(ALL_SURVIVAL_WORLDS) == 30

    def test_curated_workspace_worlds_use_canonical_registry(self):
        from blender_worlds import PRACTICAL_WORLDS, list_workspace_worlds

        catalog = list_workspace_worlds()
        assert [entry["id"] for entry in catalog] == [
            "research_lab",
            "small_house",
            "warehouse",
            "outdoor_test_area",
            "procedural_sandbox",
        ]
        assert all(entry["available"] for entry in catalog)
        assert all(entry["id"] in PRACTICAL_WORLDS for entry in catalog)

    def test_no_sqlalchemy_import_from_blender_worlds(self):
        """blender_worlds.py must not import sqlalchemy or cognitive stack."""
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "blender_worlds.py")
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            if stripped.startswith("import ") or stripped.startswith("from "):
                assert "sqlalchemy" not in stripped.lower(), f"Found sqlalchemy import: {stripped}"
                assert "crawler_agent.cognitive" not in stripped, (
                    f"Found cognitive stack import: {stripped}"
                )
