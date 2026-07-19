"""Planning engine for goal decomposition and execution."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, StrEnum
from typing import Any

import structlog

from .backend import CognitiveBackend
from .backend import extract_json as _extract_json


class PlanStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REPLAN = "needs_replan"


class StepStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PlanStep:
    """A step in a plan."""

    id: str
    description: str
    action: str
    parameters: dict[str, Any] = field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    dependencies: list[str] = field(default_factory=list)
    estimated_duration: float = 0.0  # seconds
    actual_duration: float = 0.0
    result: Any = None
    error: str | None = None
    confidence: float = 0.5

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "action": self.action,
            "status": self.status.value,
            "confidence": self.confidence,
        }


@dataclass
class Plan:
    """A plan for achieving a goal."""

    id: str
    goal_id: str
    goal_description: str
    steps: list[PlanStep] = field(default_factory=list)
    status: PlanStatus = PlanStatus.DRAFT
    current_step: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    estimated_total_time: float = 0.0
    actual_total_time: float = 0.0
    success_probability: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_next_step(self) -> PlanStep | None:
        """Get next executable step."""
        for step in self.steps:
            if step.status == StepStatus.PENDING:
                deps_met = all(
                    any(s.id == dep and s.status == StepStatus.COMPLETED for s in self.steps)
                    for dep in step.dependencies
                )
                if deps_met:
                    return step
        return None

    def to_context(self) -> str:
        steps_str = "\n".join(
            f"  {i + 1}. [{s.status.value}] {s.description} (action: {s.action})"
            for i, s in enumerate(self.steps)
        )
        return f"""Plan: {self.goal_description}
Status: {self.status.value}
Success Probability: {self.success_probability:.0%}
Steps:
{steps_str}"""


class Planner:
    """Planning engine for goal decomposition."""

    def __init__(self, backend: CognitiveBackend):
        self.backend = backend
        self.plans: dict[str, Plan] = {}
        self.plan_history: list[dict[str, Any]] = []
        self.available_skills: dict[str, str] = {}  # name -> code, from self-modification
        self.logger = structlog.get_logger()

    async def create_plan(
        self,
        goal_id: str,
        goal_description: str,
        context: str = "",
        available_actions: list[str] | None = None,
    ) -> Plan:
        """Create a plan for achieving a goal."""
        actions_hint = ""
        if available_actions:
            actions_hint = f"\nAvailable actions: {', '.join(available_actions)}"

        skills_hint = ""
        if self.available_skills:
            skills_hint = f"\nLearned skills you can use: {', '.join(self.available_skills.keys())}"

        system_prompt = f"""Create a detailed plan to achieve the goal. Break it into concrete steps.
Each step should have: description, action (from available actions or 'think', 'search', 'execute', 'verify'),
dependencies (step ids), estimated_duration (seconds).

Return JSON with: steps (list), estimated_total_time, success_probability, reasoning{actions_hint}"""

        user_prompt = f"""Goal: {goal_description}
Context: {context}{skills_hint}

Create a plan:"""

        response = None
        for attempt in range(2):
            response = await self.backend.complete(
                prompt=user_prompt,
                system=system_prompt,
                max_tokens=2000,
                temperature=0.3,
            )
            if response.content and response.content.strip():
                break
            self.logger.warning("empty_llm_response", attempt=attempt)

        if not response or not response.content or not response.content.strip():
            self.logger.error("planning_failed", error="LLM returned empty response after retries")
            return Plan(
                id=f"plan_{goal_id[:8]}",
                goal_id=goal_id,
                goal_description=goal_description,
                status=PlanStatus.FAILED,
            )

        result = _extract_json(response.content)

        plan = Plan(
            id=f"plan_{goal_id[:8]}",
            goal_id=goal_id,
            goal_description=goal_description,
            status=PlanStatus.DRAFT,
            estimated_total_time=result.get("estimated_total_time", 0),
            success_probability=result.get("success_probability", 0.5),
            metadata={"reasoning": result.get("reasoning", "")},
        )

        raw_steps = []
        for i, step_data in enumerate(result.get("steps", [])):
            step = PlanStep(
                id=f"step_{i}",
                description=step_data.get("description", ""),
                action=step_data.get("action", "execute"),
                parameters=step_data.get("parameters", {}),
                dependencies=step_data.get("dependencies", []),
                estimated_duration=step_data.get("estimated_duration", 10),
                confidence=step_data.get("confidence", 0.5),
            )
            plan.steps.append(step)
            raw_steps.append(step)

        # Resolve dependency labels to step IDs
        # LLM may return "Step 1", "Step 2" etc; map to "step_0", "step_1"
        for i, step in enumerate(raw_steps):
            resolved = []
            for dep in step.dependencies:
                if dep.startswith("step_"):
                    resolved.append(dep)
                else:
                    # Try "Step N" pattern -> step_{N-1}
                    import re

                    m = re.match(r"Step\s+(\d+)", dep, re.IGNORECASE)
                    if m:
                        idx = int(m.group(1)) - 1
                        if 0 <= idx < len(raw_steps):
                            resolved.append(raw_steps[idx].id)
                        else:
                            # Fallback: try matching by partial description
                            for s in raw_steps:
                                if dep.lower() in s.description.lower():
                                    resolved.append(s.id)
                                    break
                    else:
                        # Try matching by description
                        for s in raw_steps:
                            if dep.lower() in s.description.lower():
                                resolved.append(s.id)
                                break
            step.dependencies = resolved

        self.plans[plan.id] = plan
        return plan

    async def replan(
        self,
        plan: Plan,
        failure_point: PlanStep,
        error: str,
        new_context: str = "",
    ) -> Plan:
        """Create a new plan after failure."""
        completed = [s for s in plan.steps if s.status == StepStatus.COMPLETED]
        completed_str = "\n".join(f"- {s.description}: {s.result}" for s in completed)

        system_prompt = """The previous plan failed. Create a new plan considering:
1. What was already accomplished
2. What failed and why
3. Alternative approaches

Return JSON with: steps, reasoning, success_probability"""

        user_prompt = f"""Original goal: {plan.goal_description}
Completed steps: {completed_str}
Failed step: {failure_point.description}
Error: {error}
New context: {new_context}

Create new plan:"""

        response = await self.backend.complete(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=2000,
            temperature=0.3,
        )

        result = _extract_json(response.content)

        new_plan = Plan(
            id=f"plan_replan_{plan.goal_id[:8]}",
            goal_id=plan.goal_id,
            goal_description=plan.goal_description,
            status=PlanStatus.ACTIVE,
            success_probability=result.get("success_probability", 0.4),
            metadata={
                "reasoning": result.get("reasoning", ""),
                "replan_reason": error,
                "original_plan": plan.id,
            },
        )

        for i, step_data in enumerate(result.get("steps", [])):
            step = PlanStep(
                id=f"step_{i}",
                description=step_data.get("description", ""),
                action=step_data.get("action", "execute"),
                dependencies=step_data.get("dependencies", []),
                confidence=step_data.get("confidence", 0.5),
            )
            new_plan.steps.append(step)

        self.plans[new_plan.id] = new_plan
        return new_plan

    async def simulate_plan(self, plan: Plan) -> dict[str, Any]:
        """Simulate plan execution to estimate outcomes."""
        system_prompt = """Simulate executing this plan. For each step, predict:
1. Likely outcome (success/failure/partial)
2. Potential issues
3. Time estimate accuracy

Return JSON with: step_predictions, overall_success_probability, bottlenecks, suggestions"""

        user_prompt = f"""Plan to simulate:
{plan.to_context()}

Simulate execution:"""

        response = await self.backend.complete(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=1500,
            temperature=0.3,
        )

        result = _extract_json(response.content)
        return result if result else {"error": "Simulation failed"}

    async def evaluate_step(
        self,
        step: PlanStep,
        context: str,
    ) -> dict[str, Any]:
        """Evaluate a step before execution."""
        system_prompt = """Evaluate this step before execution. Consider:
1. Is the action appropriate?
2. What could go wrong?
3. Are there better alternatives?

Return JSON with: should_proceed, confidence, alternative_actions, risks"""

        user_prompt = f"""Step: {step.description}
Action: {step.action}
Context: {context}

Evaluate:"""

        response = await self.backend.complete(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=800,
            temperature=0.3,
        )

        result = _extract_json(response.content)
        return result if result else {"should_proceed": True, "confidence": 0.5}

    async def record_outcome(
        self,
        plan: Plan,
        step: PlanStep,
        success: bool,
        result: Any = None,
        actual_time: float = 0.0,
    ) -> None:
        """Record step execution outcome."""
        step.status = StepStatus.COMPLETED if success else StepStatus.FAILED
        step.result = result
        step.actual_duration = actual_time
        if not success:
            step.error = str(result) if result else "Unknown error"

        self.plan_history.append(
            {
                "plan_id": plan.id,
                "step_id": step.id,
                "success": success,
                "actual_time": actual_time,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        if not success:
            plan.status = PlanStatus.NEEDS_REPLAN
        elif all(s.status == StepStatus.COMPLETED for s in plan.steps):
            plan.status = PlanStatus.COMPLETED

        plan.updated_at = datetime.utcnow()

    def get_active_plan(self) -> Plan | None:
        """Get current active plan."""
        for plan in self.plans.values():
            if plan.status in (PlanStatus.ACTIVE, PlanStatus.EXECUTING):
                return plan
        return None

    def get_stats(self) -> dict[str, Any]:
        """Get planning statistics."""
        return {
            "total_plans": len(self.plans),
            "active": sum(1 for p in self.plans.values() if p.status == PlanStatus.ACTIVE),
            "completed": sum(1 for p in self.plans.values() if p.status == PlanStatus.COMPLETED),
            "failed": sum(1 for p in self.plans.values() if p.status == PlanStatus.FAILED),
            "history_size": len(self.plan_history),
        }
