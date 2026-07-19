"""Cognitive architecture modules."""

from .goals import Goal, GoalManager, GoalPriority, GoalSource, GoalStatus
from .memory import Memory, MemorySystem, MemoryType
from .metacognition import ConfidenceLevel, MetaCognition, ReasoningTrace
from .planning import Plan, Planner, PlanStatus, PlanStep
from .recursive_modify import ModificationTarget, RecursiveModification, RecursiveSelfModifier
from .scheduler import AdaptiveScheduler, CrawlIntensity, CrawlOrchestrator
from .self_modify import Modification, ModificationType, SafetyLevel, SelfModifier


# Lazy imports to avoid circular dependencies
def _lazy_learning():
    from .learning import FocusedLearner, LearningMode

    return FocusedLearner, LearningMode


# Advanced cognitive modules
from .attention import AttentionMechanism
from .backend import CognitiveBackend, CognitiveResponse, HybridBackend, LLMBackend, PatternBackend

# Verification & Learning Infrastructure
from .benchmark import BenchmarkHarness, BenchmarkResult, BenchmarkSuite, BenchmarkTask
from .blender_sandbox import (
    BlenderSandbox,
    DomainRandomizationConfig,
    ExportFormat,
    PhysicsConfig,
    ProceduralConfig,
    RobotConfig,
    SensorConfig,
    SimulationResult,
    SimulationSpec,
)
from .causal_reasoning import (
    CausalEdge,
    CausalReasoner,
    CausalVariable,
    Counterfactual,
    Intervention,
)
from .ci_validator import CompositeValidator, GitHubActionsValidator, LocalCIValidator
from .curiosity import CuriosityEngine
from .emotional import EmotionalProcessor, EmotionalState
from .knowledge_distiller import DistillationExample, KnowledgeDistiller
from .knowledge_graph import Concept, KnowledgeGraph, Relation, RelationType
from .mcts_planner import MCTSConfig, MCTSPlanner, create_mcts_planner
from .memory_compression import ContextWindowManager, MemoryCompressor, MemoryConsolidator
from .meta_learner import MetaLearner
from .outcome_verifier import (
    CompositeOutcomeVerifier,
    VerificationSpec,
    VerificationStatus,
    create_outcome_verifier,
)
from .patch_verifier import PatchVerifier, TestCase, TestGenerator, VerificationResult
from .pattern_learner import PatternLearner
from .reward_model import PatchFeatures, PatchRanker, RewardModel, RewardPrediction
from .rl_agent import RLAgent
from .simulator import Dream, InternalSimulator, Simulation, SimulationType
from .skill_composition import Skill, SkillChain, SkillComposer, SkillType
from .skill_library import Skill, SkillLibrary
from .sleep import SleepConsolidator
from .transfer import TransferLearner
from .uncertainty import UncertaintyEstimate, UncertaintyTracker, UncertaintyType
from .world_model import BayesianWorldModel

__all__ = [
    # Core
    "MemorySystem",
    "Memory",
    "MemoryType",
    "MetaCognition",
    "ReasoningTrace",
    "ConfidenceLevel",
    "GoalManager",
    "Goal",
    "GoalSource",
    "GoalPriority",
    "GoalStatus",
    "SelfModifier",
    "Modification",
    "ModificationType",
    "SafetyLevel",
    "Planner",
    "Plan",
    "PlanStep",
    "PlanStatus",
    "AdaptiveScheduler",
    "CrawlOrchestrator",
    "CrawlIntensity",
    # Advanced
    "KnowledgeGraph",
    "Concept",
    "Relation",
    "RelationType",
    "CausalReasoner",
    "CausalVariable",
    "CausalEdge",
    "Intervention",
    "Counterfactual",
    "SkillComposer",
    "Skill",
    "SkillChain",
    "SkillType",
    "UncertaintyTracker",
    "UncertaintyEstimate",
    "UncertaintyType",
    "InternalSimulator",
    "Simulation",
    "Dream",
    "SimulationType",
    "EmotionalProcessor",
    "EmotionalState",
    "AttentionMechanism",
    "SleepConsolidator",
    "MetaLearner",
    "TransferLearner",
    "CuriosityEngine",
    "BayesianWorldModel",
    "PatternLearner",
    "RLAgent",
    # Verification & Learning Infrastructure
    "BenchmarkHarness",
    "BenchmarkTask",
    "BenchmarkResult",
    "BenchmarkSuite",
    "PatchVerifier",
    "TestGenerator",
    "TestCase",
    "VerificationResult",
    "SkillLibrary",
    "Skill",
    "KnowledgeDistiller",
    "DistillationExample",
    "GitHubActionsValidator",
    "LocalCIValidator",
    "CompositeValidator",
    "RewardModel",
    "PatchFeatures",
    "RewardPrediction",
    "PatchRanker",
    "MemoryCompressor",
    "ContextWindowManager",
    "MemoryConsolidator",
    "CognitiveBackend",
    "LLMBackend",
    "HybridBackend",
    "PatternBackend",
    "CognitiveResponse",
    # Grounding & Verification
    "BlenderSandbox",
    "ExportFormat",
    "PhysicsConfig",
    "SensorConfig",
    "DomainRandomizationConfig",
    "ProceduralConfig",
    "RobotConfig",
    "SimulationSpec",
    "SimulationResult",
    "CompositeOutcomeVerifier",
    "create_outcome_verifier",
    "VerificationSpec",
    "VerificationStatus",
    "MCTSPlanner",
    "create_mcts_planner",
    "MCTSConfig",
    # Lazy imports (use via function calls)
    "_lazy_learning",
]
