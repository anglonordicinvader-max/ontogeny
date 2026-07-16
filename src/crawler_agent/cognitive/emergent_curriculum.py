"""Emergent Curriculum — maldoror creates its own training curriculum.

Instead of training on random data, the agent identifies what it's weak at
and generates targeted training tasks to fill those gaps. This is a
self-directed curriculum that emerges from the agent's own performance.

How it works:
1. Analyze modification history for patterns (what task types fail most?)
2. Identify weak areas (low quality scores, frequent failures)
3. Generate training tasks targeting those weaknesses
4. Add tasks to modification_memory for the next training run
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from .backend import CognitiveBackend, CognitiveResponse
from .modification_memory import ModificationMemory, ModificationRecord


@dataclass
class CurriculumTask:
    """A generated training task targeting a specific weakness."""
    id: str = ""
    weakness_type: str = ""  # task_type, error_pattern, concept_gap
    instruction: str = ""
    output: str = ""
    quality_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WeaknessProfile:
    """Analysis of what the model is weak at."""
    task_type_failure_rates: dict[str, float] = field(default_factory=dict)
    common_error_patterns: list[str] = field(default_factory=list)
    low_quality_areas: list[str] = field(default_factory=list)
    recommendation: str = ""


class EmergentCurriculum:
    """Analyzes performance and generates targeted training tasks.

    Instead of passively training on whatever data exists, this module
    actively identifies gaps and creates curriculum items to fill them.
    """

    def __init__(
        self,
        backend: CognitiveBackend,
        modification_memory: ModificationMemory,
        min_quality: float = 0.5,
        max_tasks_per_cycle: int = 5,
    ):
        self.backend = backend
        self.memory = modification_memory
        self.min_quality = min_quality
        self.max_tasks_per_cycle = max_tasks_per_cycle
        self.logger = structlog.get_logger()
        self.stats = {
            "curriculums_generated": 0,
            "tasks_created": 0,
            "weaknesses_identified": 0,
            "tasks_rejected": 0,
        }

    async def generate_curriculum(self) -> list[CurriculumTask]:
        """Analyze weaknesses and generate targeted training tasks.

        This is the main entry point. It:
        1. Profiles current weaknesses from modification history
        2. Generates training tasks that specifically target those weaknesses
        3. Scores quality and adds valid tasks to modification_memory
        """
        # 1. Analyze weaknesses
        profile = await self._analyze_weaknesses()
        if not profile.common_error_patterns and not profile.low_quality_areas:
            self.logger.info("no_weaknesses_found")
            return []

        # 2. Generate tasks targeting weaknesses
        tasks: list[CurriculumTask] = []

        # Generate tasks for error patterns
        for pattern in profile.common_error_patterns[:3]:
            generated = await self._generate_task_for_error_pattern(pattern)
            if generated:
                tasks.extend(generated)

        # Generate tasks for low quality areas
        for area in profile.low_quality_areas[:2]:
            generated = await self._generate_task_for_weak_area(area)
            if generated:
                tasks.extend(generated)

        # Generate general remediation tasks
        if profile.recommendation:
            remediation = await self._generate_remediation_task(profile)
            if remediation:
                tasks.append(remediation)

        # Score and filter
        valid = [t for t in tasks if t.quality_score >= self.min_quality]
        rejected = len(tasks) - len(valid)

        # Add to memory
        for task in valid[:self.max_tasks_per_cycle]:
            self._add_to_memory(task)

        self.stats["curriculums_generated"] += 1
        self.stats["tasks_created"] += len(valid)
        self.stats["weaknesses_identified"] += len(profile.common_error_patterns) + len(profile.low_quality_areas)
        self.stats["tasks_rejected"] += rejected

        self.logger.info(
            "curriculum_generated",
            weaknesses=len(profile.common_error_patterns) + len(profile.low_quality_areas),
            tasks=len(valid),
            rejected=rejected,
        )

        return valid

    async def _analyze_weaknesses(self) -> WeaknessProfile:
        """Analyze modification history to find weaknesses."""
        all_records = self.memory.records
        failed = self.memory.get_failed_records()
        successful = self.memory.get_successful_records()

        # Calculate failure rates by task type
        task_type_counts: dict[str, dict[str, int]] = {}
        for r in all_records:
            if r.task_type not in task_type_counts:
                task_type_counts[r.task_type] = {"total": 0, "failed": 0}
            task_type_counts[r.task_type]["total"] += 1
            if not r.success:
                task_type_counts[r.task_type]["failed"] += 1

        failure_rates = {}
        for task_type, counts in task_type_counts.items():
            if counts["total"] >= 2:  # Only analyze types with enough data
                failure_rates[task_type] = counts["failed"] / counts["total"]

        # Find common error patterns
        error_descriptions = [r.description for r in failed if r.description]
        low_quality = [r.task_type for r in all_records if r.quality_score < 0.4]

        # Use LLM to identify patterns
        system_prompt = (
            "You are a performance analyst. Given a list of failed modifications "
            "and their descriptions, identify the most common error patterns. "
            "Return JSON: {\"patterns\": [\"pattern1\", ...], \"recommendation\": \"what to focus on\"}"
        )

        prompt = f"""Failed modification descriptions:
{json.dumps(error_descriptions[:20], indent=2)}

Failure rates by task type:
{json.dumps({k: f"{v:.1%}" for k, v in failure_rates.items()}, indent=2)}

What are the most common error patterns? What should we focus training on?"""

        response = await self.backend.complete(
            prompt=prompt,
            system=system_prompt,
            max_tokens=1500,
            temperature=0.5,
        )

        parsed = response.parsed_json
        patterns = parsed.get("patterns", [])
        recommendation = parsed.get("recommendation", "")

        # Low quality areas
        low_quality_areas = list(set(low_quality))

        return WeaknessProfile(
            task_type_failure_rates=failure_rates,
            common_error_patterns=patterns,
            low_quality_areas=low_quality_areas,
            recommendation=recommendation,
        )

    async def _generate_task_for_error_pattern(
        self,
        pattern: str,
    ) -> list[CurriculumTask]:
        """Generate training tasks that address a specific error pattern."""
        system_prompt = (
            "You are a training data generator. Given an error pattern found in "
            "failed code modifications, generate 2-3 training examples that teach "
            "the model to avoid this specific mistake. "
            "Return JSON: {\"tasks\": [{\"instruction\": \"problem\", \"output\": \"solution\", "
            "\"explanation\": \"why this works\", \"quality\": 0.0-1.0}]}"
        )

        prompt = f"""Error pattern to address: {pattern}

Generate 2-3 training examples that specifically teach how to avoid this error.
Each should present a problem where this error would naturally occur, and show the correct solution."""

        response = await self.backend.complete(
            prompt=prompt,
            system=system_prompt,
            max_tokens=2000,
            temperature=0.7,
        )

        parsed = response.parsed_json
        tasks = []
        for item in parsed.get("tasks", [])[:3]:
            instruction = item.get("instruction", "")
            output = item.get("output", "")
            if not instruction or not output or len(output) < 30:
                continue

            tasks.append(CurriculumTask(
                id=str(uuid.uuid4()),
                weakness_type="error_pattern",
                instruction=instruction,
                output=output,
                quality_score=item.get("quality", 0.6),
                metadata={
                    "pattern": pattern,
                    "explanation": item.get("explanation", ""),
                },
            ))

        return tasks

    async def _generate_task_for_weak_area(
        self,
        area: str,
    ) -> list[CurriculumTask]:
        """Generate training tasks for a weak task type."""
        system_prompt = (
            "You are a training data generator. Given a task type where the model "
            "consistently performs poorly, generate targeted training examples. "
            "Return JSON: {\"tasks\": [{\"instruction\": \"problem\", \"output\": \"solution\", "
            "\"difficulty\": \"easy|medium|hard\", \"quality\": 0.0-1.0}]}"
        )

        prompt = f"""Weak task type: {area}

Generate 2 training examples of increasing difficulty for this task type.
Start with easier cases and progress to harder ones."""

        response = await self.backend.complete(
            prompt=prompt,
            system=system_prompt,
            max_tokens=2000,
            temperature=0.7,
        )

        parsed = response.parsed_json
        tasks = []
        for item in parsed.get("tasks", [])[:2]:
            instruction = item.get("instruction", "")
            output = item.get("output", "")
            if not instruction or not output or len(output) < 30:
                continue

            difficulty = item.get("difficulty", "medium")
            quality_map = {"easy": 0.5, "medium": 0.7, "hard": 0.9}
            quality = quality_map.get(difficulty, 0.6)

            tasks.append(CurriculumTask(
                id=str(uuid.uuid4()),
                weakness_type="task_type",
                instruction=f"[{difficulty}] {instruction}",
                output=output,
                quality_score=quality,
                metadata={"area": area, "difficulty": difficulty},
            ))

        return tasks

    async def _generate_remediation_task(
        self,
        profile: WeaknessProfile,
    ) -> CurriculumTask | None:
        """Generate a comprehensive remediation task from the overall recommendation."""
        if not profile.recommendation:
            return None

        system_prompt = (
            "You are a training data generator. Given a performance recommendation, "
            "create a comprehensive training example that addresses the core issue. "
            "Return JSON: {\"instruction\": \"problem\", \"output\": \"solution\", "
            "\"quality\": 0.0-1.0}"
        )

        prompt = f"""Performance recommendation: {profile.recommendation}

Create a comprehensive training example that addresses this core issue.
The example should be realistic and show both the problem and the correct solution."""

        response = await self.backend.complete(
            prompt=prompt,
            system=system_prompt,
            max_tokens=1500,
            temperature=0.6,
        )

        parsed = response.parsed_json
        instruction = parsed.get("instruction", "")
        output = parsed.get("output", "")

        if not instruction or not output or len(output) < 30:
            return None

        return CurriculumTask(
            id=str(uuid.uuid4()),
            weakness_type="remediation",
            instruction=instruction,
            output=output,
            quality_score=parsed.get("quality", 0.6),
            metadata={
                "recommendation": profile.recommendation,
                "failure_rates": profile.task_type_failure_rates,
            },
        )

    def _add_to_memory(self, task: CurriculumTask) -> None:
        """Add a curriculum task to modification memory."""
        record = ModificationRecord(
            id=task.id,
            timestamp=datetime.utcnow().isoformat(),
            source_module="emergent_curriculum",
            target_file="",
            task_type=task.weakness_type,
            description=f"[curriculum:{task.weakness_type}] {task.instruction[:100]}",
            reasoning=task.instruction,
            modified_code=task.output,
            success=True,
            quality_score=task.quality_score,
            metadata={
                "weakness_type": task.weakness_type,
                **task.metadata,
            },
        )
        self.memory.record(record)

    def get_stats(self) -> dict[str, Any]:
        """Get curriculum statistics."""
        return {
            **self.stats,
            "memory_total": len(self.memory.records),
            "memory_successful": len(self.memory.get_successful_records()),
            "memory_failed": len(self.memory.get_failed_records()),
        }

    def to_context(self) -> str:
        """Convert stats to context string."""
        stats = self.get_stats()
        lines = [
            "Emergent Curriculum:",
            f"  Curriculums Generated: {stats['curriculums_generated']}",
            f"  Tasks Created: {stats['tasks_created']}",
            f"  Weaknesses Identified: {stats['weaknesses_identified']}",
            f"  Tasks Rejected: {stats['tasks_rejected']}",
            f"  Memory: {stats['memory_successful']} success, {stats['memory_failed']} failed",
        ]
        return "\n".join(lines)
