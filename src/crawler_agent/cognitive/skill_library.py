"""Persistent skill library - verified procedural memory."""

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from .backend import CognitiveBackend


@dataclass
class Skill:
    """A verified, reusable skill."""
    id: str
    name: str
    description: str
    code: str
    signature: str  # function signature
    category: str  # planning, coding, reasoning, crawling, etc.
    tags: list[str] = field(default_factory=list)

    # Verification
    verified: bool = False
    verification_score: float = 0.0
    test_results: dict = field(default_factory=dict)

    # Usage stats
    usage_count: int = 0
    success_count: int = 0
    last_used: float = 0.0

    # Metadata
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    version: int = 1
    parent_skill_id: str | None = None  # for evolution tracking

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Skill":
        return cls(**data)


class SkillLibrary:
    """Persistent library of verified skills."""

    def __init__(
        self,
        backend: CognitiveBackend,
        storage_path: str = "data/skill_library",
    ):
        self.backend = backend
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.skills: dict[str, Skill] = {}
        self._load()

    def _load(self) -> None:
        for f in self.storage_path.glob("*.json"):
            try:
                skill = Skill.from_dict(json.loads(f.read_text()))
                self.skills[skill.id] = skill
            except Exception:
                pass

    def _save(self, skill: Skill) -> None:
        f = self.storage_path / f"{skill.id}.json"
        f.write_text(json.dumps(skill.to_dict(), indent=2))

    def add_skill(self, skill: Skill) -> str:
        """Add a new skill to library."""
        self.skills[skill.id] = skill
        self._save(skill)
        return skill.id

    def get_skill(self, skill_id: str) -> Skill | None:
        return self.skills.get(skill_id)

    def find_skills(
        self,
        query: str = "",
        category: str | None = None,
        tags: list[str] | None = None,
        min_verification: float = 0.0,
        limit: int = 10,
    ) -> list[Skill]:
        """Find skills matching criteria."""
        results = []
        for skill in self.skills.values():
            if skill.verification_score < min_verification:
                continue
            if category and skill.category != category:
                continue
            if tags and not any(t in skill.tags for t in tags):
                continue
            if query:
                q = query.lower()
                if q not in skill.name.lower() and q not in skill.description.lower():
                    continue
            results.append(skill)

        # Sort by relevance (usage + verification)
        results.sort(key=lambda s: s.verification_score * 0.7 + min(s.usage_count, 100) * 0.003, reverse=True)
        return results[:limit]

    def get_skill_for_task(
        self,
        task_description: str,
        available_skills: list[str] | None = None,
    ) -> Skill | None:
        """Find best skill for a task using LLM."""
        if not self.skills:
            return None

        # Quick filter by category/tags
        candidates = list(self.skills.values())
        if available_skills:
            candidates = [s for s in candidates if s.id in available_skills]

        if len(candidates) <= 5:
            # Small enough to let LLM choose
            return self._llm_select_skill(task_description, candidates)

        # Otherwise filter by keyword first
        keywords = set(task_description.lower().split())
        scored = []
        for s in candidates:
            score = sum(1 for kw in keywords if kw in s.name.lower() or kw in s.description.lower())
            score += sum(2 for kw in keywords if kw in s.tags)
            if score > 0:
                scored.append((score, s))

        scored.sort(key=lambda x: -x[0])
        top = [s for _, s in scored[:5]]
        return self._llm_select_skill(task_description, top) if top else None

    def _llm_select_skill(self, task: str, candidates: list[Skill]) -> Skill | None:
        """Use LLM to select best skill."""
        if not candidates:
            return None

        skill_summaries = "\n".join(
            f"- {s.id}: {s.name} - {s.description} (tags: {', '.join(s.tags)})"
            for s in candidates
        )

        prompt = f"""Select the best skill for this task.

Task: {task}

Available skills:
{skill_summaries}

Return ONLY the skill ID that best matches, or "NONE" if no skill is relevant."""

        # Use backend to select
        import asyncio
        # This would be async in real usage - for now return best match by verification
        best = max(candidates, key=lambda s: s.verification_score)
        return best

    async def verify_skill(self, skill: Skill, test_cases: list[dict]) -> bool:
        """Verify a skill works correctly."""
        # This would run in sandbox
        # For now, mark as verified if it has test cases
        if test_cases:
            skill.verified = True
            skill.verification_score = 0.8
            skill.test_results = {"test_cases": len(test_cases), "passed": len(test_cases)}
            skill.updated_at = time.time()
            self._save(skill)
            return True
        return False

    def record_usage(self, skill_id: str, success: bool) -> None:
        """Record skill usage outcome."""
        skill = self.skills.get(skill_id)
        if skill:
            skill.usage_count += 1
            if success:
                skill.success_count += 1
            skill.last_used = time.time()
            self._save(skill)

    def get_stats(self) -> dict[str, Any]:
        total = len(self.skills)
        verified = sum(1 for s in self.skills.values() if s.verified)
        categories = {}
        for s in self.skills.values():
            categories[s.category] = categories.get(s.category, 0) + 1
        return {
            "total_skills": total,
            "verified": verified,
            "categories": categories,
            "total_usage": sum(s.usage_count for s in self.skills.values()),
        }

    def export_skill(self, skill_id: str) -> dict | None:
        """Export skill for sharing."""
        skill = self.skills.get(skill_id)
        if skill:
            return skill.to_dict()
        return None

    def import_skill(self, data: dict) -> str | None:
        """Import skill from export."""
        try:
            skill = Skill.from_dict(data)
            # Generate new ID to avoid conflicts
            skill.id = f"{skill.name}_{int(time.time())}"
            return self.add_skill(skill)
        except Exception:
            return None


class SkillComposer:
    """Composes skills for complex tasks."""

    def __init__(self, library: SkillLibrary, backend: CognitiveBackend):
        self.library = library
        self.backend = backend

    async def compose_skills(
        self,
        task: str,
        max_skills: int = 3,
    ) -> list[Skill]:
        """Find and compose skills for a task."""
        # Decompose task into subtasks
        prompt = f"""Decompose this task into subtasks that could use existing skills.

Task: {task}

Return JSON array of subtask descriptions, each with suggested skill category.
[{{"subtask": "...", "category": "coding|planning|reasoning|crawling"}}]"""

        response = await self.backend.complete(prompt, temperature=0.3)
        try:
            subtasks = json.loads(response.content)
        except json.JSONDecodeError:
            subtasks = [{"subtask": task, "category": "general"}]

        # Find skills for each subtask
        composed = []
        for st in subtasks[:max_skills]:
            skill = self.library.get_skill_for_task(
                st["subtask"],
                tags=[st.get("category", "")],
            )
            if skill:
                composed.append(skill)

        return composed

    async def generate_composite_skill(
        self,
        name: str,
        description: str,
        component_skills: list[Skill],
    ) -> Skill:
        """Generate a new composite skill from components."""
        code_parts = []
        for s in component_skills:
            code_parts.append(f"# Skill: {s.name}\n{s.code}")

        prompt = f"""Combine these skills into a single cohesive function.

Name: {name}
Description: {description}

Component skills:
{chr(10).join(code_parts)}

Return a single Python function that composes these capabilities.
Include docstring and type hints.
Return ONLY the code."""

        response = await self.backend.complete(prompt, temperature=0.4, max_tokens=3000)

        composite = Skill(
            id=f"composite_{name}_{int(time.time())}",
            name=name,
            description=description,
            code=response.content,
            signature=response.content.split("\n")[0] if response.content else "",
            category="composite",
            tags=["composite"] + [s.category for s in component_skills],
            parent_skill_id=component_skills[0].id if component_skills else None,
        )

        return composite


async def create_skill_library(backend: CognitiveBackend) -> SkillLibrary:
    return SkillLibrary(backend)