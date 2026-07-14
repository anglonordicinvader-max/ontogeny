"""Planning engine for goal decomposition and execution."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import structlog
from openai import AsyncOpenAI


class PlanStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REPLAN = "needs_replan"


class StepStatus(str, Enum):
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
                # Check dependencies
                deps_met = all(
                    any(s.id == dep and s.status == StepStatus.COMPLETED for s in self.steps)
                    for dep in step.dependencies
                )
                if deps_met:
                    return step
        return None

    def to_context(self) -> str:
        steps_str = "\n".join(
            f"  {i+1}. [{s.status.value}] {s.description} (action: {s.action})"
            for i, s in enumerate(self.steps)
        )
        return f"""Plan: {self.goal_description}
Status: {self.status.value}
Success Probability: {self.success_probability:.0%}
Steps:
{steps_str}"""


class Planner:
    """Planning engine for goal decomposition."""

    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview", api_base: str | None = None):
        self.client = AsyncOpenAI(api_key=api_key or "ollama", base_url=api_base)
        self.model = model
        self.plans: dict[str, Plan] = {}
        self.plan_history: list[dict[str, Any]] = []
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

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": f"""Create a detailed plan to achieve the goal. Break it into concrete steps.
Each step should have: description, action (from available actions or 'think', 'search', 'execute', 'verify'), 
dependencies (step ids), estimated_duration (seconds).

Return JSON with: steps (list), estimated_total_time, success_probability, reasoning{actions_hint}""",
                },
                {
                    "role": "user",
                    "content": f"""Goal: {goal_description}
Context: {context}

Create a plan:""",
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=2000,
        )

        try:
            result = json.loads(response.choices[0].message.content or "{}")

            plan = Plan(
                id=f"plan_{goal_id[:8]}",
                goal_id=goal_id,
                goal_description=goal_description,
                status=PlanStatus.DRAFT,
                estimated_total_time=result.get("estimated_total_time", 0),
                success_probability=result.get("success_probability", 0.5),
                metadata={"reasoning": result.get("reasoning", "")},
            )

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

            self.plans[plan.id] = plan
            return plan

        except Exception as e:
            self.logger.error("planning_failed", error=str(e))
            return Plan(
                id=f"plan_{goal_id[:8]}",
                goal_id=goal_id,
                goal_description=goal_description,
                status=PlanStatus.FAILED,
            )

    async def replan(
        self,
        plan: Plan,
        failure_point: PlanStep,
        error: str,
        new_context: str = "",
    ) -> Plan:
        """Create a new plan after failure."""
        # Get completed steps for context
        completed = [s for s in plan.steps if s.status == StepStatus.COMPLETED]
        completed_str = "\n".join(f"- {s.description}: {s.result}" for s in completed)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """The previous plan failed. Create a new plan considering:
1. What was already accomplished
2. What failed and why
3. Alternative approaches

Return JSON with: steps, reasoning, success_probability""",
                },
                {
                    "role": "user",
                    "content": f"""Original goal: {plan.goal_description}
Completed steps: {completed_str}
Failed step: {failure_point.description}
Error: {error}
New context: {new_context}

Create new plan:""",
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=2000,
        )

        try:
            result = json.loads(response.choices[0].message.content or "{}")

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

        except Exception as e:
            self.logger.error("replan_failed", error=str(e))
            plan.status = PlanStatus.FAILED
            return plan

    async def simulate_plan(self, plan: Plan) -> dict[str, Any]:
        """Simulate plan execution to estimate outcomes."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """Simulate executing this plan. For each step, predict:
1. Likely outcome (success/failure/partial)
2. Potential issues
3. Time estimate accuracy

Return JSON with: step_predictions, overall_success_probability, bottlenecks, suggestions""",
                },
                {
                    "role": "user",
                    "content": f"""Plan to simulate:
{plan.to_context()}

Simulate execution:""",
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=1500,
        )

        try:
            return json.loads(response.choices[0].message.content or "{}")
        except Exception:
            return {"error": "Simulation failed"}

    async def evaluate_step(
        self,
        step: PlanStep,
        context: str,
    ) -> dict[str, Any]:
        """Evaluate a step before execution."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """Evaluate this step before execution. Consider:
1. Is the action appropriate?
2. What could go wrong?
3. Are there better alternatives?

Return JSON with: should_proceed, confidence, alternative_actions, risks""",
                },
                {
                    "role": "user",
                    "content": f"""Step: {step.description}
Action: {step.action}
Context: {context}

Evaluate:""",
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=800,
        )

        try:
            return json.loads(response.choices[0].message.content or "{}")
        except Exception:
            return {"should_proceed": True, "confidence": 0.5}

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

        self.plan_history.append({
            "plan_id": plan.id,
            "step_id": step.id,
            "success": success,
            "actual_time": actual_time,
            "timestamp": datetime.utcnow().isoformat(),
        })

        # Update plan status
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
