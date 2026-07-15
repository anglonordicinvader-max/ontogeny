"""Cognitive architecture modules."""

from .memory import MemorySystem, Memory, MemoryType
from .metacognition import MetaCognition, ReasoningTrace, ConfidenceLevel
from .goals import GoalManager, Goal, GoalSource, GoalPriority, GoalStatus
from .self_modify import SelfModifier, Modification, ModificationType, SafetyLevel
from .recursive_modify import RecursiveSelfModifier, RecursiveModification, ModificationTarget
from .planning import Planner, Plan, PlanStep, PlanStatus
from .learning import FocusedLearner, LearningMode
from .scheduler import AdaptiveScheduler, CrawlOrchestrator, CrawlIntensity

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

__all__ = [
    # Core
    "MemorySystem", "Memory", "MemoryType",
    "MetaCognition", "ReasoningTrace", "ConfidenceLevel",
    "GoalManager", "Goal", "GoalSource", "GoalPriority", "GoalStatus",
    "SelfModifier", "Modification", "ModificationType", "SafetyLevel",
    "Planner", "Plan", "PlanStep", "PlanStatus",
    "FocusedLearner", "LearningMode",
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
]
