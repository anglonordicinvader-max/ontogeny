"""Skill Composition system for combining learned skills."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

import structlog
from openai import AsyncOpenAI


class SkillType(str, Enum):
    ATOMIC = "atomic"          # Single action
    COMPOSITE = "composite"    # Combined skills
    REACTIVE = "reactive"      # Trigger-based
    PROCEDURAL = "procedural"  # Step-by-step
    ADAPTIVE = "adaptive"      # Self-modifying


class SkillStatus(str, Enum):
    LEARNED = "learned"
    REFINED = "refined"
    DEPRECATED = "deprecated"
    COMPOSING = "composing"


@dataclass
class SkillInput:
    """Input specification for a skill."""
    name: str
    type: str  # string, number, boolean, object
    required: bool = True
    default: Any = None
    description: str = ""


@dataclass
class SkillOutput:
    """Output specification for a skill."""
    name: str
    type: str
    description: str = ""


@dataclass
class Skill:
    """A learnable skill."""
    id: str
    name: str
    description: str
    skill_type: SkillType = SkillType.ATOMIC
    status: SkillStatus = SkillStatus.LEARNED

    # Interface
    inputs: list[SkillInput] = field(default_factory=list)
    outputs: list[SkillOutput] = field(default_factory=list)

    # Implementation
    code: str = ""
    procedure: list[str] = field(default_factory=list)

    # Composition
    sub_skills: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)

    # Performance
    success_rate: float = 0.5
    usage_count: int = 0
    avg_execution_time: float = 0.0

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SkillChain:
    """A chain of skills executed in sequence."""
    id: str
    name: str
    steps: list[dict[str, Any]]  # [{skill_id, input_mapping, output_mapping}]
    description: str = ""
    success_rate: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)


class SkillComposer:
    """Composes complex behaviors from simpler skills."""

    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview", api_base: str | None = None):
        self.client = AsyncOpenAI(api_key=api_key or "ollama", base_url=api_base)
        self.model = model
        self.skills: dict[str, Skill] = {}
        self.chains: dict[str, SkillChain] = {}
        self.execution_history: list[dict[str, Any]] = []
        self.logger = structlog.get_logger()

    def register_skill(self, skill: Skill) -> None:
        """Register a skill."""
        self.skills[skill.id] = skill
        self.logger.debug("skill_registered", skill_id=skill.id, name=skill.name)

    async def compose_skills(
        self,
        skill_ids: list[str],
        goal: str,
    ) -> SkillChain:
        """Compose multiple skills into a chain."""
        skills = [self.skills[sid] for sid in skill_ids if sid in self.skills]

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """Compose skills into an execution chain. Define:
1. Execution order
2. Input/output mappings between steps
3. Error handling strategy

Return JSON with: steps (list of {skill_id, description, input_mapping, output_mapping, error_handling}), overall_strategy""",
                },
                {
                    "role": "user",
                    "content": f"""Goal: {goal}
Available skills: {[{'id': s.id, 'name': s.name, 'inputs': [i.name for i in s.inputs], 'outputs': [o.name for o in s.outputs]} for s in skills]}

Create composition:""",
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=1500,
        )

        try:
            data = json.loads(response.choices[0].message.content or "{}")
            chain = SkillChain(
                id=f"chain_{len(self.chains)}",
                name=f"Chain for: {goal[:50]}",
                steps=data.get("steps", []),
                description=data.get("overall_strategy", ""),
                metadata={"goal": goal},
            )
            self.chains[chain.id] = chain
            return chain
        except Exception as e:
            self.logger.error("composition_failed", error=str(e))
            return SkillChain(id="failed", name="Failed composition", steps=[])

    async def discover_compositions(
        self,
        goal: str,
        context: str = "",
    ) -> list[SkillChain]:
        """Discover possible skill compositions for a goal."""
        available = list(self.skills.values())

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """Given available skills and a goal, suggest skill compositions.
For each composition, specify:
1. Which skills to use
2. How to combine them
3. Expected effectiveness

Return JSON with: compositions (list of {name, skills, strategy, effectiveness})""",
                },
                {
                    "role": "user",
                    "content": f"""Goal: {goal}
Context: {context}
Available skills: {[{'name': s.name, 'type': s.skill_type.value, 'success_rate': s.success_rate} for s in available[:30]]}

Suggest compositions:""",
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=1500,
        )

        try:
            data = json.loads(response.choices[0].message.content or "{}")
            chains = []
            for comp in data.get("compositions", []):
                chain = SkillChain(
                    id=f"discovered_{len(self.chains) + len(chains)}",
                    name=comp.get("name", ""),
                    steps=[{"skill_name": s} for s in comp.get("skills", [])],
                    description=comp.get("strategy", ""),
                    metadata={"effectiveness": comp.get("effectiveness", 0.5)},
                )
                chains.append(chain)
            return chains
        except Exception:
            return []

    async def refine_skill(
        self,
        skill_id: str,
        feedback: str,
        performance: float,
    ) -> Skill:
        """Refine a skill based on feedback."""
        skill = self.skills.get(skill_id)
        if not skill:
            raise ValueError(f"Skill {skill_id} not found")

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """Refine a skill based on feedback. Improve:
1. Error handling
2. Edge cases
3. Performance
4. Robustness

Return JSON with: improved_code, improvements_made, expected_improvement""",
                },
                {
                    "role": "user",
                    "content": f"""Skill: {skill.name}
Current code: {skill.code}
Procedure: {skill.procedure}
Feedback: {feedback}
Performance: {performance}

Refine:""",
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=1500,
        )

        try:
            data = json.loads(response.choices[0].message.content or "{}")
            skill.code = data.get("improved_code", skill.code)
            skill.status = SkillStatus.REFINED
            skill.success_rate = min(1.0, skill.success_rate + 0.1)
            skill.metadata["refinements"] = skill.metadata.get("refinements", 0) + 1
            skill.metadata["last_improvement"] = data.get("improvements_made", "")
            return skill
        except Exception as e:
            self.logger.error("refinement_failed", error=str(e))
            return skill

    async def auto_compose(
        self,
        goal: str,
        max_skills: int = 5,
    ) -> SkillChain:
        """Automatically compose skills for a goal."""
        compositions = await self.discover_compositions(goal)
        if compositions:
            best = max(compositions, key=lambda c: c.metadata.get("effectiveness", 0))
            return await self.compose_skills(
                [s.get("skill_name", "") for s in best.steps[:max_skills]],
                goal,
            )
        return SkillChain(id="empty", name="No composition found", steps=[])

    def record_execution(
        self,
        skill_id: str,
        success: bool,
        execution_time: float,
        output: Any = None,
    ) -> None:
        """Record skill execution."""
        skill = self.skills.get(skill_id)
        if skill:
            skill.usage_count += 1
            skill.last_used = datetime.utcnow()
            if skill.usage_count > 0:
                old_rate = skill.success_rate
                skill.success_rate = (old_rate * (skill.usage_count - 1) + (1 if success else 0)) / skill.usage_count

        self.execution_history.append({
            "skill_id": skill_id,
            "success": success,
            "execution_time": execution_time,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def get_skill_dependencies(self, skill_id: str) -> list[str]:
        """Get all skills this skill depends on."""
        skill = self.skills.get(skill_id)
        if not skill:
            return []
        return skill.dependencies

    def get_composable_skills(self) -> list[Skill]:
        """Get skills that can be composed."""
        return [
            s for s in self.skills.values()
            if s.skill_type in (SkillType.ATOMIC, SkillType.PROCEDURAL)
            and s.success_rate > 0.5
        ]

    def to_context(self) -> str:
        """Export skills as context."""
        lines = ["Available Skills:"]
        for skill in sorted(self.skills.values(), key=lambda s: s.success_rate, reverse=True)[:20]:
            lines.append(f"  {skill.name} ({skill.skill_type.value}): {skill.description[:80]}")
            lines.append(f"    Success rate: {skill.success_rate:.0%}, Used: {skill.usage_count} times")
        return "\n".join(lines)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_skills": len(self.skills),
            "by_type": {
                t.value: sum(1 for s in self.skills.values() if s.skill_type == t)
                for t in SkillType
            },
            "total_chains": len(self.chains),
            "avg_success_rate": sum(s.success_rate for s in self.skills.values()) / max(len(self.skills), 1),
            "executions": len(self.execution_history),
        }
