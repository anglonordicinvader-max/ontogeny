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
]
