"""Goal-directed research planner for the Knowledge Acquisition System.

Every acquisition should originate from:
- a planning goal
- a reasoning objective
- memory reinforcement
- a knowledge gap
- a curiosity objective
- a robotics task
- software research

Every acquisition begins with:
- research objective
- expected evidence
- preferred source categories
- maximum acquisition budget
- stop conditions
- confidence target
- memory relevance

The planner determines:
- which sources to query
- query order
- acquisition depth
- expected usefulness
- termination criteria
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

import structlog


class ObjectiveStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


class StopCondition(StrEnum):
    CONFIDENCE_REACHED = "confidence_reached"
    BUDGET_EXHAUSTED = "budget_exhausted"
    ALL_SOURCES_EXHAUSTED = "all_sources_exhausted"
    MAX_DEPTH_REACHED = "max_depth_reached"
    CONTRADICTION_FOUND = "contradiction_found"
    MANUAL_STOP = "manual_stop"


@dataclass
class ResearchObjective:
    """A single research objective within a plan."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    query: str = ""
    expected_evidence_types: list[str] = field(default_factory=list)
    preferred_categories: list[str] = field(default_factory=list)
    excluded_domains: list[str] = field(default_factory=list)
    confidence_target: float = 0.7
    max_budget: int = 50
    max_depth: int = 2
    status: ObjectiveStatus = ObjectiveStatus.PENDING
    documents_found: int = 0
    confidence_achieved: float = 0.0
    queries_issued: int = 0
    stop_reason: str = ""
    memory_relevance: float = 0.5  # 0-1: how relevant to current memory state
    reasoning: str = ""  # why this objective was created
    priority: int = 0  # higher = more urgent
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResearchPlan:
    """A complete research plan with ordered objectives."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    objective: str = ""  # high-level research goal
    description: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    objectives: list[ResearchObjective] = field(default_factory=list)
    total_budget: int = 200
    budget_used: int = 0
    status: str = "pending"  # pending, active, completed, failed
    completion_percentage: float = 0.0
    sources_queried: list[str] = field(default_factory=list)
    evidence_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class ResearchPlanner:
    """Generates goal-directed research plans.

    Ontogeny should generate research plans, not crawl blindly.
    Every crawl begins with a plan.
    """

    def __init__(self):
        self.plans: dict[str, ResearchPlan] = {}
        self.logger = structlog.get_logger()

    def create_plan(
        self,
        objective: str,
        description: str = "",
        total_budget: int = 200,
        sub_objectives: list[dict[str, Any]] | None = None,
    ) -> ResearchPlan:
        """Create a new research plan."""
        plan = ResearchPlan(
            objective=objective,
            description=description,
            total_budget=total_budget,
        )

        if sub_objectives:
            for i, obj_data in enumerate(sub_objectives):
                obj = ResearchObjective(
                    description=obj_data.get("description", ""),
                    query=obj_data.get("query", ""),
                    expected_evidence_types=obj_data.get("evidence_types", []),
                    preferred_categories=obj_data.get("categories", []),
                    excluded_domains=obj_data.get("excluded", []),
                    confidence_target=obj_data.get("confidence_target", 0.7),
                    max_budget=obj_data.get("budget", 50),
                    max_depth=obj_data.get("max_depth", 2),
                    memory_relevance=obj_data.get("memory_relevance", 0.5),
                    reasoning=obj_data.get("reasoning", ""),
                    priority=obj_data.get("priority", 0),
                )
                plan.objectives.append(obj)

        self.plans[plan.id] = plan
        self.logger.info(
            "research_plan_created",
            plan_id=plan.id,
            objective=objective,
            num_objectives=len(plan.objectives),
        )
        return plan

    def create_plan_from_goal(
        self,
        goal_description: str,
        context: dict[str, Any] | None = None,
        memory_relevant_facts: list[str] | None = None,
    ) -> ResearchPlan:
        """Create a research plan from a high-level cognitive goal.

        This is the primary interface for Ontogeny's cognitive pipeline.
        The planner generates sub-objectives based on the goal.
        """
        # Auto-generate sub-objectives based on the goal
        sub_objectives = self._generate_objectives(goal_description, context)
        plan = self.create_plan(
            objective=goal_description,
            description=f"Research plan for: {goal_description}",
            sub_objectives=sub_objectives,
        )
        if memory_relevant_facts:
            plan.metadata["memory_context"] = memory_relevant_facts
        return plan

    def _generate_objectives(
        self, goal: str, context: dict[str, Any] | None
    ) -> list[dict[str, Any]]:
        """Generate research sub-objectives from a high-level goal.

        Uses heuristic rules to break down goals into actionable queries.
        """
        objectives = []
        goal_lower = goal.lower()

        # Knowledge gap objectives
        objectives.append({
            "description": f"Find authoritative sources about: {goal}",
            "query": goal,
            "evidence_types": ["documentation", "academic", "official"],
            "categories": ["official_docs", "academic", "tech_docs"],
            "confidence_target": 0.7,
            "budget": 50,
            "priority": 10,
            "reasoning": "Primary knowledge acquisition",
        })

        # Contradiction checking
        objectives.append({
            "description": f"Find contradictory or alternative views on: {goal}",
            "query": f"{goal} vs alternatives comparison",
            "evidence_types": ["discussion", "forum", "news"],
            "categories": ["forum", "community", "reputable_news"],
            "confidence_target": 0.5,
            "budget": 30,
            "priority": 5,
            "reasoning": "Contradiction detection for robustness",
        })

        # Recent developments
        objectives.append({
            "description": f"Find recent developments related to: {goal}",
            "query": f"{goal} latest developments 2024 2025",
            "evidence_types": ["news", "blog", "release"],
            "categories": ["reputable_news", "blog", "tech_docs"],
            "confidence_target": 0.6,
            "budget": 30,
            "priority": 7,
            "reasoning": "Ensure knowledge is current",
        })

        # Practical examples
        objectives.append({
            "description": f"Find practical examples and implementations of: {goal}",
            "query": f"{goal} implementation example tutorial",
            "evidence_types": ["code", "documentation", "tutorial"],
            "categories": ["tech_docs", "community"],
            "confidence_target": 0.6,
            "budget": 40,
            "priority": 6,
            "reasoning": "Practical grounding for understanding",
        })

        # Domain-specific adjustments
        if any(kw in goal_lower for kw in ["library", "package", "framework", "tool"]):
            objectives.append({
                "description": f"Check package registries for: {goal}",
                "query": goal,
                "evidence_types": ["package", "repository"],
                "categories": ["official_api", "tech_docs"],
                "confidence_target": 0.8,
                "budget": 20,
                "priority": 9,
                "reasoning": "Package registry verification",
            })

        if any(kw in goal_lower for kw in ["research", "paper", "study", "theory"]):
            objectives.append({
                "description": f"Find academic papers on: {goal}",
                "query": goal,
                "evidence_types": ["paper", "academic"],
                "categories": ["academic"],
                "confidence_target": 0.8,
                "budget": 40,
                "priority": 8,
                "reasoning": "Academic grounding",
            })

        return objectives

    def get_next_objective(self, plan: ResearchPlan) -> ResearchObjective | None:
        """Get the next objective to execute in a plan."""
        pending = [
            o for o in plan.objectives
            if o.status == ObjectiveStatus.PENDING
        ]
        if not pending:
            return None
        # Sort by priority (descending)
        pending.sort(key=lambda o: o.priority, reverse=True)
        return pending[0]

    def update_objective(
        self,
        plan_id: str,
        objective_id: str,
        status: ObjectiveStatus,
        documents_found: int = 0,
        confidence: float = 0.0,
        stop_reason: str = "",
    ):
        """Update an objective's status."""
        plan = self.plans.get(plan_id)
        if not plan:
            return
        for obj in plan.objectives:
            if obj.id == objective_id:
                obj.status = status
                obj.documents_found += documents_found
                obj.confidence_achieved = max(obj.confidence_achieved, confidence)
                if stop_reason:
                    obj.stop_reason = stop_reason
                break

        # Update plan completion
        completed = sum(
            1 for o in plan.objectives
            if o.status in (ObjectiveStatus.COMPLETED, ObjectiveStatus.FAILED, ObjectiveStatus.ABANDONED)
        )
        plan.completion_percentage = (completed / max(1, len(plan.objectives))) * 100
        if completed == len(plan.objectives):
            plan.status = "completed"

    def should_stop(self, plan: ResearchPlan) -> tuple[bool, str]:
        """Check if the plan should be stopped."""
        if plan.budget_used >= plan.total_budget:
            return True, StopCondition.BUDGET_EXHAUSTED.value

        active = [
            o for o in plan.objectives
            if o.status == ObjectiveStatus.IN_PROGRESS
        ]
        pending = [
            o for o in plan.objectives
            if o.status == ObjectiveStatus.PENDING
        ]

        if not active and not pending:
            return True, StopCondition.ALL_SOURCES_EXHAUSTED.value

        # Check if any objective reached its confidence target
        for obj in plan.objectives:
            if (
                obj.status == ObjectiveStatus.IN_PROGRESS
                and obj.confidence_achieved >= obj.confidence_target
            ):
                return True, StopCondition.CONFIDENCE_REACHED.value

        return False, ""

    def get_plan_summary(self, plan: ResearchPlan) -> dict[str, Any]:
        return {
            "id": plan.id,
            "objective": plan.objective,
            "status": plan.status,
            "completion": plan.completion_percentage,
            "budget_used": plan.budget_used,
            "budget_total": plan.total_budget,
            "evidence_count": plan.evidence_count,
            "objectives": [
                {
                    "id": o.id,
                    "description": o.description,
                    "status": o.status.value,
                    "confidence": o.confidence_achieved,
                    "documents": o.documents_found,
                }
                for o in plan.objectives
            ],
        }
