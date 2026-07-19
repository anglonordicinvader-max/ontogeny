"""Smoke tests for all cognitive modules.

These tests verify that every module can be imported, instantiated,
and run basic operations. They serve as the foundation for the
verification pipeline — patches that break these tests are rejected.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


class TestCoreImports:
    """Verify all cognitive modules can be imported."""

    def test_import_memory(self):
        from crawler_agent.cognitive.memory import MemorySystem

    def test_import_metacognition(self):
        from crawler_agent.cognitive.metacognition import MetaCognition

    def test_import_goals(self):
        from crawler_agent.cognitive.goals import GoalManager

    def test_import_self_modify(self):
        from crawler_agent.cognitive.self_modify import SelfModifier

    def test_import_recursive_modify(self):
        from crawler_agent.cognitive.recursive_modify import RecursiveSelfModifier

    def test_import_planning(self):
        from crawler_agent.cognitive.planning import Planner

    def test_import_learning(self):
        from crawler_agent.cognitive.learning import FocusedLearner

    def test_import_knowledge_graph(self):
        from crawler_agent.cognitive.knowledge_graph import KnowledgeGraph

    def test_import_causal_reasoning(self):
        from crawler_agent.cognitive.causal_reasoning import CausalReasoner

    def test_import_skill_composition(self):
        from crawler_agent.cognitive.skill_composition import SkillComposer

    def test_import_uncertainty(self):
        from crawler_agent.cognitive.uncertainty import UncertaintyTracker

    def test_import_simulator(self):
        from crawler_agent.cognitive.simulator import InternalSimulator

    def test_import_backend(self):
        from crawler_agent.cognitive.backend import CognitiveBackend, HybridBackend, LLMBackend

    def test_import_pattern_learner(self):
        from crawler_agent.cognitive.pattern_learner import PatternLearner

    def test_import_rl_agent(self):
        from crawler_agent.cognitive.rl_agent import RLAgent

    def test_import_curiosity(self):
        from crawler_agent.cognitive.curiosity import CuriosityEngine

    def test_import_world_model(self):
        from crawler_agent.cognitive.world_model import BayesianWorldModel

    def test_import_meta_learner(self):
        from crawler_agent.cognitive.meta_learner import MetaLearner

    def test_import_sleep(self):
        from crawler_agent.cognitive.sleep import SleepConsolidator

    def test_import_attention(self):
        from crawler_agent.cognitive.attention import AttentionMechanism

    def test_import_emotional(self):
        from crawler_agent.cognitive.emotional import EmotionalProcessor

    def test_import_transfer(self):
        from crawler_agent.cognitive.transfer import TransferLearner

    def test_import_self_reflection(self):
        from crawler_agent.cognitive.self_reflection import SelfReflectionEngine

    def test_import_evo_architecture(self):
        from crawler_agent.cognitive.evo_architecture import EvoArchitecture

    def test_import_blender_sandbox(self):
        from crawler_agent.cognitive.blender_sandbox import BlenderSandbox

    def test_import_mcts_planner(self):
        from crawler_agent.cognitive.mcts_planner import MCTSPlanner

    def test_import_self_audit(self):
        from crawler_agent.cognitive.self_audit import SelfAuditor

    def test_import_multimodal(self):
        from crawler_agent.cognitive.multimodal import MultimodalProcessor

    def test_import_agent_variety(self):
        from crawler_agent.cognitive.agent_variety import AgentPopulation

    def test_import_skill_export(self):
        from crawler_agent.cognitive.skill_export import SkillExporter

    def test_import_world_selector(self):
        from crawler_agent.cognitive.world_selector import WorldSelector

    def test_import_sensor_sim(self):
        from crawler_agent.cognitive.sensor_sim import SensorArray

    def test_import_failure_injection(self):
        from crawler_agent.cognitive.failure_injection import FailureInjector

    def test_import_navigation(self):
        from crawler_agent.cognitive.navigation import ObstacleAvoidance, PathPlanner

    def test_import_weather(self):
        from crawler_agent.cognitive.weather import WeatherSystem

    def test_import_locomotion(self):
        from crawler_agent.cognitive.locomotion import LocomotionController

    def test_import_manipulation(self):
        from crawler_agent.cognitive.manipulation_tasks import ManipulationController

    def test_import_social_sim(self):
        from crawler_agent.cognitive.social_sim import SocialSimulator

    def test_import_yolo_detector(self):
        from crawler_agent.cognitive.yolo_detector import YOLODetector

    def test_import_scene_understanding(self):
        from crawler_agent.cognitive.scene_understanding import SceneUnderstanding

    def test_import_object_permanence(self):
        from crawler_agent.cognitive.object_permanence import ObjectPermanence

    def test_import_benchmarks(self):
        from crawler_agent.cognitive.benchmarks import BenchmarkSuite

    def test_import_distillation(self):
        from crawler_agent.cognitive.distillation import KnowledgeDistiller

    def test_import_skill_library(self):
        from crawler_agent.cognitive.skill_library import SkillLibrary

    def test_import_patch_verifier(self):
        from crawler_agent.cognitive.patch_verifier import PatchVerifier, TestGenerator

    def test_import_persistent_identity(self):
        from crawler_agent.cognitive.persistent_identity import PersistentIdentity

    def test_import_continual_learning(self):
        from crawler_agent.cognitive.continual_learning import ContinualLearner

    def test_import_cross_domain(self):
        from crawler_agent.cognitive.cross_domain import CrossDomainTransfer

    def test_import_curriculum(self):
        from crawler_agent.cognitive.curriculum import SelfGeneratedCurriculum

    def test_import_architecture_modify(self):
        from crawler_agent.cognitive.architecture_modify import ArchitectureAwareModifier

    def test_import_rollback(self):
        from crawler_agent.cognitive.rollback import RollbackManager

    def test_import_sphere_viz(self):
        from crawler_agent.cognitive.sphere_viz import SphereVisualizer

    def test_import_physics_exp(self):
        from crawler_agent.cognitive.physics_exp import PhysicsExperimenter

    def test_import_world_memory(self):
        from crawler_agent.cognitive.world_memory import PersistentWorldMemory

    def test_import_anatomy_mode(self):
        from crawler_agent.cognitive.anatomy_mode import TocabiPart


class TestModuleInstantiation:
    """Verify key modules can be instantiated without LLM backend."""

    def test_attention_mechanism(self):
        from crawler_agent.cognitive.attention import AttentionMechanism

        att = AttentionMechanism()
        assert att.current_focus is None
        assert att.switch_count == 0

    def test_curiosity_engine(self):
        from crawler_agent.cognitive.curiosity import CuriosityEngine

        cur = CuriosityEngine()
        assert len(cur.knowledge_gaps) == 0
        assert cur.total_exploration_reward == 0.0

    def test_world_model(self):
        from crawler_agent.cognitive.world_model import BayesianWorldModel

        wm = BayesianWorldModel()
        assert len(wm.beliefs) == 0
        assert len(wm.causal_links) == 0

    def test_emotional_processor(self):
        from crawler_agent.cognitive.emotional import EmotionalProcessor

        ep = EmotionalProcessor()
        assert ep.state.mood is not None

    def test_self_reflection(self):
        from crawler_agent.cognitive.self_reflection import ActionRecord, SelfReflectionEngine

        sr = SelfReflectionEngine(backend=None)
        assert sr.reflection_count == 0

    def test_evo_architecture(self):
        from crawler_agent.cognitive.evo_architecture import EvoArchitecture

        evo = EvoArchitecture(backend=None)
        assert evo.generation == 0
        assert len(evo.variants) == 0

    def test_self_modifier(self):
        from crawler_agent.cognitive.self_modify import CodeValidator, SelfModifier

        validator = CodeValidator()
        valid, msg = validator.validate_syntax("def foo(): pass")
        assert valid is True
        valid, msg = validator.validate_syntax("def foo(")
        assert valid is False

    def test_recursive_modifier(self):
        from pathlib import Path

        from crawler_agent.cognitive.recursive_modify import SourceAnalyzer

        analyzer = SourceAnalyzer(Path("."))
        assert analyzer.base_path == Path(".")

    def test_knowledge_graph(self):
        from crawler_agent.cognitive.knowledge_graph import KnowledgeGraph

        kg = KnowledgeGraph(backend=None)
        stats = kg.get_stats()
        assert "concepts" in stats

    def test_sleep_consolidator(self):
        from crawler_agent.cognitive.sleep import SleepConsolidator

        sc = SleepConsolidator()
        stats = sc.get_stats()
        assert "total_consolidations" in stats

    def test_failure_injector(self):
        from crawler_agent.cognitive.failure_injection import FailureInjector

        fi = FailureInjector()
        status = fi.get_status()
        assert "battery" in status

    def test_weather_system(self):
        from crawler_agent.cognitive.weather import WeatherSystem

        ws = WeatherSystem()
        ctx = ws.to_context()
        assert "Weather" in ctx

    def test_locomotion(self):
        from crawler_agent.cognitive.locomotion import LocomotionController

        lc = LocomotionController()
        ctx = lc.to_context()
        assert "Locomotion" in ctx


class TestCoreOperations:
    """Verify core operations work without external dependencies."""

    def test_attention_evaluate(self):
        import asyncio

        from crawler_agent.cognitive.attention import AttentionMechanism

        async def run():
            att = AttentionMechanism()
            target = await att.evaluate_attention("Debug the crawler code")
            assert 0.0 <= target.relevance <= 1.0
            assert 0.0 <= target.novelty <= 1.0
            assert target.attention_score >= 0.0

        asyncio.run(run())

    def test_curiosity_novelty(self):
        import asyncio

        from crawler_agent.cognitive.curiosity import CuriosityEngine

        async def run():
            cur = CuriosityEngine()
            signal = await cur.analyze_novelty("quantum computing advances", "physics")
            assert 0.0 <= signal.novelty_score <= 1.0
            assert signal.topic == "physics"

        asyncio.run(run())

    def test_world_model_belief_update(self):
        import asyncio

        from crawler_agent.cognitive.world_model import BayesianWorldModel

        async def run():
            wm = BayesianWorldModel()
            belief = await wm.add_belief("code quality matters", prior=0.7)
            assert belief.probability == 0.7
            belief.update_with_evidence(True, 1.5)
            assert belief.probability > 0.7

        asyncio.run(run())

    def test_self_reflection_record(self):
        import asyncio

        from crawler_agent.cognitive.self_reflection import SelfReflectionEngine

        async def run():
            sr = SelfReflectionEngine(backend=None)
            record = await sr.record_action(
                action_type="test",
                description="test action",
                intended_outcome="success",
            )
            assert record.id is not None
            assert record.action_type == "test"

        asyncio.run(run())

    def test_evo_architecture_init(self):
        import asyncio

        from crawler_agent.cognitive.evo_architecture import EvoArchitecture

        async def run():
            evo = EvoArchitecture(backend=None)
            pop = await evo.initialize_population()
            assert len(pop) == 5
            for v in pop:
                assert v.fitness == 0.0
                assert len(v.components) > 0

        asyncio.run(run())

    def test_self_modify_validate(self):
        from crawler_agent.cognitive.self_modify import CodeValidator

        v = CodeValidator()
        level, issues = v.check_safety("exec('import os; os.system(\"rm -rf /\")')")
        assert level.value in ("high_risk", "critical")
        level, issues = v.check_safety("def add(a, b): return a + b")
        assert level.value == "safe"

    def test_recursive_analyzer_scan(self):
        from pathlib import Path

        from crawler_agent.cognitive.recursive_modify import SourceAnalyzer

        analyzer = SourceAnalyzer(Path("."))
        files = analyzer.scan_source_files()
        assert len(files) > 0
        assert any("orchestrator" in str(f.path) for f in files.values())

    def test_attention_switch(self):
        import asyncio

        from crawler_agent.cognitive.attention import AttentionMechanism

        async def run():
            att = AttentionMechanism()
            t1 = await att.evaluate_attention("Task A")
            t2 = await att.evaluate_attention("Task B: urgent deadline")
            result = await att.decide_focus([t1, t2])
            assert result is not None

        asyncio.run(run())

    def test_causal_reasoner_extract(self):
        from pathlib import Path

        from crawler_agent.cognitive.causal_reasoning import (
            CausalEdge,
            CausalReasoner,
            CausalRelation,
            CausalVariable,
        )

        cr = CausalReasoner(backend=None)
        var = CausalVariable(id="test_var", name="test")
        cr.add_variable(var)
        assert "test_var" in cr.variables
