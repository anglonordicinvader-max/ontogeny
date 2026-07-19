"""Smoke tests for Blender simulation module.

Tests the parts of blender_simulation.py that don't require
a running Blender instance (data structures, imports, helpers).
"""

import ast
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

        assert len(PRACTICAL_WORLDS) == 9
        assert len(ALL_SURVIVAL_WORLDS) == 30

    def test_no_sqlalchemy_import_from_blender_worlds(self):
        """blender_worlds.py must not import sqlalchemy or cognitive stack."""
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "blender_worlds.py")
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        # Check for actual import statements, not comments or docstrings
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            if stripped.startswith("import ") or stripped.startswith("from "):
                assert "sqlalchemy" not in stripped.lower(), f"Found sqlalchemy import: {stripped}"
                assert "crawler_agent.cognitive" not in stripped, (
                    f"Found cognitive stack import: {stripped}"
                )
