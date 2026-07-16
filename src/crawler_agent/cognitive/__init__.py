"""Cognitive architecture modules."""

from .memory import MemorySystem, Memory, MemoryType
from .metacognition import MetaCognition, ReasoningTrace, ConfidenceLevel
from .goals import GoalManager, Goal, GoalSource, GoalPriority, GoalStatus
from .self_modify import SelfModifier, Modification, ModificationType, SafetyLevel
from .recursive_modify import RecursiveSelfModifier, RecursiveModification, ModificationTarget
from .planning import Planner, Plan, PlanStep, PlanStatus
from .scheduler import AdaptiveScheduler, CrawlOrchestrator, CrawlIntensity

# Lazy imports to avoid circular dependencies
def _lazy_learning():
    from .learning import FocusedLearner, LearningMode
    return FocusedLearner, LearningMode

# Advanced cognitive modules
from .knowledge_graph import KnowledgeGraph, Concept, Relation, RelationType
from .causal_reasoning import CausalReasoner, CausalVariable, CausalEdge, Intervention, Counterfactual
from .skill_composition import SkillComposer, Skill, SkillChain, SkillType
from .uncertainty import UncertaintyTracker, UncertaintyEstimate, UncertaintyType
from .simulator import InternalSimulator, Simulation, Dream, SimulationType
from .emotional import EmotionalProcessor, EmotionalState
from .attention import AttentionMechanism
from .sleep import SleepConsolidator
from .meta_learner import MetaLearner
from .transfer import TransferLearner
from .curiosity import CuriosityEngine
from .world_model import BayesianWorldModel
from .pattern_learner import PatternLearner
from .rl_agent import RLAgent

# Verification & Learning Infrastructure
from .benchmark import BenchmarkHarness, BenchmarkTask, BenchmarkResult, BenchmarkSuite
from .patch_verifier import PatchVerifier, TestGenerator, TestCase, VerificationResult
from .skill_library import SkillLibrary, Skill
from .knowledge_distiller import KnowledgeDistiller, DistillationExample
from .ci_validator import GitHubActionsValidator, LocalCIValidator, CompositeValidator
from .reward_model import RewardModel, PatchFeatures, RewardPrediction, PatchRanker
from .memory_compression import MemoryCompressor, ContextWindowManager, MemoryConsolidator
from .backend import CognitiveBackend, LLMBackend, HybridBackend, PatternBackend, CognitiveResponse
from .blender_sandbox import BlenderSandbox, SimulationType, ExportFormat, PhysicsConfig, SensorConfig, DomainRandomizationConfig, ProceduralConfig, RobotConfig, SimulationSpec, SimulationResult
from .outcome_verifier import CompositeOutcomeVerifier, create_outcome_verifier, VerificationSpec, VerificationStatus
from .mcts_planner import MCTSPlanner, create_mcts_planner, MCTSConfig

__all__ = [
    # Core
    "MemorySystem", "Memory", "MemoryType",
    "MetaCognition", "ReasoningTrace", "ConfidenceLevel",
    "GoalManager", "Goal", "GoalSource", "GoalPriority", "GoalStatus",
    "SelfModifier", "Modification", "ModificationType", "SafetyLevel",
    "Planner", "Plan", "PlanStep", "PlanStatus",
    "AdaptiveScheduler", "CrawlOrchestrator", "CrawlIntensity",
    
    # Advanced
    "KnowledgeGraph", "Concept", "Relation", "RelationType",
    "CausalReasoner", "CausalVariable", "CausalEdge", "Intervention", "Counterfactual",
    "SkillComposer", "Skill", "SkillChain", "SkillType",
    "UncertaintyTracker", "UncertaintyEstimate", "UncertaintyType",
    "InternalSimulator", "Simulation", "Dream", "SimulationType",
    "EmotionalProcessor", "EmotionalState",
    "AttentionMechanism",
    "SleepConsolidator",
    "MetaLearner",
    "TransferLearner",
    "CuriosityEngine",
    "BayesianWorldModel",
    "PatternLearner",
    "RLAgent",
    
    # Verification & Learning Infrastructure
    "BenchmarkHarness", "BenchmarkTask", "BenchmarkResult", "BenchmarkSuite",
    "PatchVerifier", "TestGenerator", "TestCase", "VerificationResult",
    "SkillLibrary", "Skill",
    "KnowledgeDistiller", "DistillationExample",
    "GitHubActionsValidator", "LocalCIValidator", "CompositeValidator",
    "RewardModel", "PatchFeatures", "RewardPrediction", "PatchRanker",
    "MemoryCompressor", "ContextWindowManager", "MemoryConsolidator",
    "CognitiveBackend", "LLMBackend", "HybridBackend", "PatternBackend", "CognitiveResponse",
    
    # Grounding & Verification
    "BlenderSandbox", "SimulationType", "ExportFormat", "PhysicsConfig", "SensorConfig",
    "DomainRandomizationConfig", "ProceduralConfig", "RobotConfig", "SimulationSpec", "SimulationResult",
    "CompositeOutcomeVerifier", "create_outcome_verifier", "VerificationSpec", "VerificationStatus",
    "MCTSPlanner", "create_mcts_planner", "MCTSConfig",
    
    # Lazy imports (use via function calls)
    "_lazy_learning",
]
