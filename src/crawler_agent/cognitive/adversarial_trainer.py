"""Adversarial Trainer — maldoror critiques its own outputs.

Instead of just learning from successes, the model generates its own
outputs and then critiques them, creating counter-examples. This builds
self-criticism ability and teaches the model to identify flaws in its
own reasoning.

How it works:
1. Generate a modification attempt (prediction)
2. Critique the attempt (identify flaws)
3. Generate a counter-example (what the critique suggests instead)
4. Add all three to training data: attempt, critique, counter-example
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
class AdversarialExample:
    """A training example with attempt, critique, and counter-example."""

    id: str = ""
    attempt: str = ""
    critique: str = ""
    counter_example: str = ""
    flaw_categories: list[str] = field(default_factory=list)
    quality_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class AdversarialTrainer:
    """Generates adversarial training data from the model's own attempts.

    Three phases per example:
    1. Attempt: generate a modification (simulating the model's output)
    2. Critique: identify flaws in the attempt
    3. Counter-example: generate the correct version

    This teaches self-criticism: the model learns to spot its own mistakes
    before they get applied.
    """

    def __init__(
        self,
        backend: CognitiveBackend,
        modification_memory: ModificationMemory,
        min_quality: float = 0.5,
        max_examples_per_cycle: int = 5,
    ):
        self.backend = backend
        self.memory = modification_memory
        self.min_quality = min_quality
        self.max_examples_per_cycle = max_examples_per_cycle
        self.logger = structlog.get_logger()
        self.stats = {
            "total_generated": 0,
            "attempts_generated": 0,
            "critiques_generated": 0,
            "counter_examples_generated": 0,
            "tasks_rejected": 0,
            "flaw_categories": {},
        }

    async def generate_adversarial_data(self) -> list[AdversarialExample]:
        """Generate adversarial training examples from modification history.

        This is the main entry point. It:
        1. Selects source records to build adversarial examples around
        2. For each, generates an attempt (simulated modification)
        3. Critiques the attempt
        4. Generates a counter-example
        5. Adds all three to training data
        """
        # Select records to build adversarial examples around
        records = self._select_source_records()
        if not records:
            self.logger.info("no_source_records_for_adversarial")
            return []

        examples: list[AdversarialExample] = []

        for record in records[: self.max_examples_per_cycle]:
            example = await self._generate_one_adversarial(record)
            if example:
                examples.append(example)

        # Filter by quality
        valid = [e for e in examples if e.quality_score >= self.min_quality]
        rejected = len(examples) - len(valid)

        # Add to memory
        for example in valid:
            self._add_to_memory(example)

        # Update stats
        self.stats["total_generated"] += len(valid)
        self.stats["attempts_generated"] += len(examples)
        self.stats["critiques_generated"] += len(valid)
        self.stats["counter_examples_generated"] += len(valid)
        self.stats["tasks_rejected"] += rejected

        # Count flaw categories
        for example in valid:
            for cat in example.flaw_categories:
                self.stats["flaw_categories"][cat] = self.stats["flaw_categories"].get(cat, 0) + 1

        self.logger.info(
            "adversarial_data_generated",
            total=len(valid),
            rejected=rejected,
        )

        return valid

    def _select_source_records(self) -> list[ModificationRecord]:
        """Select records to build adversarial examples around.

        Prefer recent records with moderate quality — not too good (nothing to critique)
        and not too bad (nothing useful to build around).
        """
        candidates = [
            r
            for r in self.memory.records
            if r.success and r.modified_code and len(r.modified_code) > 50
        ]

        # Prefer moderate quality (0.4-0.8) — there's room for improvement
        moderate = [r for r in candidates if 0.4 <= r.quality_score <= 0.8]
        if len(moderate) >= 3:
            return moderate[-5:]  # Most recent 5

        # Fall back to any successful record
        return candidates[-5:] if candidates else []

    async def _generate_one_adversarial(
        self,
        record: ModificationRecord,
    ) -> AdversarialExample | None:
        """Generate one complete adversarial example from a source record."""
        # Phase 1: Generate a simulated attempt
        attempt = await self._generate_attempt(record)
        if not attempt:
            return None

        # Phase 2: Critique the attempt
        critique_result = await self._critique_attempt(attempt, record)
        if not critique_result:
            return None

        # Phase 3: Generate counter-example
        counter = await self._generate_counter_example(record, critique_result)
        if not counter:
            return None

        # Combine flaw categories
        flaw_categories = critique_result.get("flaw_categories", [])

        return AdversarialExample(
            id=str(uuid.uuid4()),
            attempt=attempt.get("code", ""),
            critique=critique_result.get("critique", ""),
            counter_example=counter,
            flaw_categories=flaw_categories,
            quality_score=critique_result.get("quality", 0.6),
            metadata={
                "source_record_id": record.id,
                "source_description": record.description,
                "attempt_quality": attempt.get("quality", 0.5),
            },
        )

    async def _generate_attempt(
        self,
        record: ModificationRecord,
    ) -> dict[str, Any] | None:
        """Generate a simulated modification attempt (possibly flawed)."""
        system_prompt = (
            "You are a code modification assistant. Given a task description and "
            "original code, generate a code modification attempt. The attempt "
            "should be plausible but may contain subtle flaws. "
            'Return JSON: {"code": "python code", "quality": 0.0-1.0, '
            '"approach": "description of approach"}'
        )

        prompt = f"""Task: {record.description}
Target file: {record.target_file}

Original code (first 800 chars):
```python
{record.original_code[:800] if record.original_code else "# No original code"}
```

Generate a modification attempt for this task. Make it plausible but not perfect."""

        response = await self.backend.complete(
            prompt=prompt,
            system=system_prompt,
            max_tokens=1500,
            temperature=0.8,
        )

        parsed = response.parsed_json
        code = parsed.get("code", "")
        if not code or len(code) < 20:
            return None

        return {
            "code": code,
            "quality": parsed.get("quality", 0.5),
            "approach": parsed.get("approach", ""),
        }

    async def _critique_attempt(
        self,
        attempt: dict[str, Any],
        record: ModificationRecord,
    ) -> dict[str, Any] | None:
        """Critique the modification attempt, identifying flaws."""
        system_prompt = (
            "You are a senior code reviewer. Given a code modification attempt, "
            "critically analyze it for flaws, bugs, anti-patterns, and areas "
            "for improvement. Be specific and constructive. "
            'Return JSON: {"critique": "detailed critique", '
            '"flaw_categories": ["category1", ...], "quality": 0.0-1.0, '
            '"severity": "low|medium|high"}'
        )

        prompt = f"""Original task: {record.description}

Original code (first 800 chars):
```python
{record.original_code[:800] if record.original_code else "# No original code"}
```

Modification attempt:
```python
{attempt["code"][:800]}
```

Critically analyze this modification attempt. What are the flaws? Be specific."""

        response = await self.backend.complete(
            prompt=prompt,
            system=system_prompt,
            max_tokens=1500,
            temperature=0.5,
        )

        parsed = response.parsed_json
        critique = parsed.get("critique", "")
        flaw_categories = parsed.get("flaw_categories", [])

        if not critique or len(critique) < 20:
            return None

        return {
            "critique": critique,
            "flaw_categories": flaw_categories,
            "quality": parsed.get("quality", 0.6),
            "severity": parsed.get("severity", "medium"),
        }

    async def _generate_counter_example(
        self,
        record: ModificationRecord,
        critique_result: dict[str, Any],
    ) -> str | None:
        """Generate the correct version based on the critique."""
        system_prompt = (
            "You are a code improvement expert. Given an original task, a flawed "
            "attempt, and a critique of that attempt, generate the correct, "
            "high-quality solution. The solution should address every flaw "
            "mentioned in the critique. "
            'Return JSON: {"code": "corrected python code", '
            '"improvements": ["what was fixed", ...]}'
        )

        prompt = f"""Task: {record.description}

Original code (first 800 chars):
```python
{record.original_code[:800] if record.original_code else "# No original code"}
```

Flawed attempt was critiqued:
{critique_result["critique"][:500]}

Generate the correct solution that addresses all flaws mentioned in the critique."""

        response = await self.backend.complete(
            prompt=prompt,
            system=system_prompt,
            max_tokens=1500,
            temperature=0.6,
        )

        parsed = response.parsed_json
        code = parsed.get("code", "")

        if not code or len(code) < 30:
            return None

        return code

    def _add_to_memory(self, example: AdversarialExample) -> None:
        """Add an adversarial example to modification memory."""
        record = ModificationRecord(
            id=example.id,
            timestamp=datetime.utcnow().isoformat(),
            source_module="adversarial_training",
            target_file="",
            task_type="adversarial",
            description=f"[adversarial] {example.critique[:100]}",
            reasoning=example.critique,
            original_code=example.attempt,
            modified_code=example.counter_example,
            success=True,
            quality_score=example.quality_score,
            metadata={
                "flaw_categories": example.flaw_categories,
                **example.metadata,
            },
        )
        self.memory.record(record)

    def get_stats(self) -> dict[str, Any]:
        """Get training statistics."""
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
            "Adversarial Trainer:",
            f"  Total Generated: {stats['total_generated']}",
            f"  Attempts Generated: {stats['attempts_generated']}",
            f"  Critiques Generated: {stats['critiques_generated']}",
            f"  Counter Examples: {stats['counter_examples_generated']}",
            f"  Rejected: {stats['tasks_rejected']}",
            f"  Flaw Categories: {stats['flaw_categories']}",
            f"  Memory: {stats['memory_successful']} success, {stats['memory_failed']} failed",
        ]
        return "\n".join(lines)
