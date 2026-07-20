"""Smoke tests for MuJoCo simulation module.

Tests the parts of mujoco_simulation.py that don't require
a running MuJoCo instance (data structures, imports, helpers).
"""

import ast
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestMuJoCoSimulationSyntax:
    """Verify mujoco_simulation.py has valid Python syntax."""

    def test_syntax_valid(self):
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "mujoco_simulation.py")
        with open(path, encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
        assert tree is not None

    def test_has_main_class(self):
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "mujoco_simulation.py")
        with open(path, encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
        class_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        assert "MuJoCoSimulation" in class_names

    def test_has_controllers(self):
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "mujoco_simulation.py")
        with open(path, encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
        class_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        assert "TocabiController" in class_names
        assert "G1Controller" in class_names

    def test_has_sensor_reader(self):
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "mujoco_simulation.py")
        with open(path, encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
        class_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        assert "MuJoCoSensorReader" in class_names

    def test_health_command_in_handler(self):
        """mujoco_simulation.py WebSocket handler should support 'health' command."""
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "mujoco_simulation.py")
        with open(path, encoding="utf-8") as f:
            source = f.read()
        assert 'cmd == "health"' in source or "cmd == 'health'" in source

    def test_health_response_includes_model_loaded(self):
        """Health response should include model_loaded field."""
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "mujoco_simulation.py")
        with open(path, encoding="utf-8") as f:
            source = f.read()
        assert '"model_loaded"' in source or "'model_loaded'" in source

    def test_reset_handler_exists(self):
        """mujoco_simulation.py should handle 'reset' command."""
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "mujoco_simulation.py")
        with open(path, encoding="utf-8") as f:
            source = f.read()
        assert 'cmd == "reset"' in source or "cmd == 'reset'" in source

    def test_stand_walk_freeze_commands(self):
        """mujoco_simulation.py should handle stand, walk, freeze commands."""
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "mujoco_simulation.py")
        with open(path, encoding="utf-8") as f:
            source = f.read()
        assert 'cmd == "stand"' in source
        assert 'cmd == "walk"' in source
        assert 'cmd == "freeze"' in source


class TestMuJoCoModelAssets:
    """Verify MuJoCo model files exist."""

    def test_g1_xml_exists(self):
        path = os.path.join(
            os.path.dirname(__file__), "..", "data", "mujoco", "models", "unitree_g1", "g1.xml"
        )
        assert os.path.exists(path), f"G1 MJCF not found at {path}"

    def test_g1_assets_directory(self):
        assets_dir = os.path.join(
            os.path.dirname(__file__), "..", "data", "mujoco", "models", "unitree_g1", "assets"
        )
        assert os.path.isdir(assets_dir), f"G1 assets directory not found at {assets_dir}"
        stl_files = [f for f in os.listdir(assets_dir) if f.lower().endswith(".stl")]
        assert len(stl_files) > 0, "No STL mesh files found in G1 assets"

    def test_tocabi_urdf_exists(self):
        path = os.path.join(
            os.path.dirname(__file__), "..", "data", "blender", "models", "tocabi", "combined", "urdf", "FullBody.urdf"
        )
        assert os.path.exists(path), f"TOCABI URDF not found at {path}"


class TestMuJoCoDependencyDetection:
    """Test MuJoCo dependency detection."""

    def test_mujoco_import_check(self):
        """Verify we can detect whether mujoco is installed."""
        try:
            import mujoco
            mujoco_available = True
        except ImportError:
            mujoco_available = False
        # Just verify the detection works, don't require mujoco to be installed
        assert isinstance(mujoco_available, bool)

    def test_simulation_file_references_mujoco(self):
        """mujoco_simulation.py should reference the mujoco package."""
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "mujoco_simulation.py")
        with open(path, encoding="utf-8") as f:
            source = f.read()
        assert "import mujoco" in source


class TestMuJoCoControlBehavior:
    def test_g1_runtime_scene_adds_ground_without_modifying_asset(self):
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "mujoco_simulation.py")
        with open(path, encoding="utf-8") as f:
            source = f.read()

        assert 'name="ontogeny_ground"' in source
        assert "mjCAMERA_TRACKING" in source
        assert "trackbodyid" in source

    def test_body_velocity_uses_supported_mujoco_api(self):
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "mujoco_simulation.py")
        with open(path, encoding="utf-8") as f:
            source = f.read()

        assert "mj_objectVelocity" in source
        assert ".xvelp" not in source
        assert ".xvelr" not in source

    def test_g1_walk_targets_leave_standing_pose(self):
        from mujoco_simulation import G1Controller, G1_JOINT_NAMES, G1_STANDING_POSE

        controller = G1Controller()
        controller.set_ctrl_index_map({name: i for i, name in enumerate(G1_JOINT_NAMES)})
        controller.set_walk_cmd(controller.walk_speed, 0.0)

        targets = controller._gait_targets(len(G1_JOINT_NAMES))

        assert targets.tolist() != G1_STANDING_POSE
        assert targets[0] != G1_STANDING_POSE[0]

    def test_freeze_disables_physics_steps_without_stopping_stream(self):
        from mujoco_simulation import ControlMode, MuJoCoSimulation

        simulation = MuJoCoSimulation.__new__(MuJoCoSimulation)
        simulation.running = True
        simulation.controller = type("Controller", (), {"mode": ControlMode.FREEZE})()

        assert not simulation._should_step_physics()
        assert simulation.running

    def test_walk_command_applies_existing_default_speed(self):
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "mujoco_simulation.py")
        with open(path, encoding="utf-8") as f:
            source = f.read()

        assert "self.controller.walk_speed" in source
        assert "abs(self.controller.walk_cmd_linear) < 0.01" in source

    def test_velocity_controls_preserve_both_components(self):
        path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "desktop",
            "renderer",
            "src",
            "components",
            "MuJoCoEmbed.tsx",
        )
        with open(path, encoding="utf-8") as f:
            source = f.read()

        assert "walk_cmd:${linear},${walkAngular}" in source
        assert "walk_cmd:${walkLinear},${angular}" in source


class TestSimulatorHealthEndpoint:
    """Test the main backend simulator health endpoint."""

    def test_simulator_health_route_exists(self):
        """main.py should have a /api/simulator-health route."""
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "main.py")
        with open(path, encoding="utf-8") as f:
            source = f.read()
        assert "/api/simulator-health" in source

    def test_health_route_exists(self):
        """main.py should have a /api/health route."""
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "main.py")
        with open(path, encoding="utf-8") as f:
            source = f.read()
        assert "/api/health" in source
