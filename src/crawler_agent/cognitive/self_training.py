"""Self-Training Synthesizer — generates training data from successful self-modifications.

This is the core of the self-training loop: after a successful modification,
the system generates synthetic training variations, inverse examples, and
reasoning chains, then adds them to modification_memory for the next training run.
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
class SynthesizedExample:
    """A single synthesized training example."""
    id: str = ""
    source_record_id: str = ""
    synth_type: str = ""  # variation, inverse, reasoning, generalization
    instruction: str = ""
    output: str = ""
    quality_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class SelfTrainingSynthesizer:
    """Generates training data from successful self-modifications.

    After a successful modification, this module:
    1. Generates variations (different approaches to the same problem)
    2. Generates inverse examples (what NOT to do)
    3. Extracts reasoning chains (why this modification worked)
    4. Generalizes patterns (what makes this type of modification successful)
    5. Scores quality and adds to modification_memory
    """

    def __init__(
        self,
        backend: CognitiveBackend,
        modification_memory: ModificationMemory,
        max_variations: int = 3,
        min_quality: float = 0.5,
    ):
        self.backend = backend
        self.memory = modification_memory
        self.max_variations = max_variations
        self.min_quality = min_quality
        self.logger = structlog.get_logger()
        self.stats = {
            "total_synthesized": 0,
            "variations": 0,
            "inverses": 0,
            "reasoning_chains": 0,
            "generalizations": 0,
            "rejected": 0,
        }

    async def synthesize_from_success(
        self,
        record: ModificationRecord,
    ) -> list[SynthesizedExample]:
        """Generate training examples from a successful modification.

        This is the main entry point. Given a successful modification record,
        it generates multiple synthetic training examples and adds them to
        modification_memory.
        """
        if not record.success:
            return []

        examples: list[SynthesizedExample] = []

        # 1. Generate variations
        variations = await self._generate_variations(record)
        examples.extend(variations)

        # 2. Generate inverse example
        inverse = await self._generate_inverse(record)
        if inverse:
            examples.append(inverse)

        # 3. Extract reasoning chain
        reasoning = await self._extract_reasoning_chain(record)
        if reasoning:
            examples.append(reasoning)

        # 4. Generalize the pattern
        generalization = await self._generalize_pattern(record)
        if generalization:
            examples.append(generalization)

        # Score and filter
        valid = [e for e in examples if e.quality_score >= self.min_quality]
        rejected = len(examples) - len(valid)

        # Add valid examples to modification memory
        for example in valid:
            self._add_to_memory(example, record)

        # Update stats
        self.stats["total_synthesized"] += len(valid)
        self.stats["variations"] += len(variations)
        self.stats["inverses"] += 1 if inverse else 0
        self.stats["reasoning_chains"] += 1 if reasoning else 0
        self.stats["generalizations"] += 1 if generalization else 0
        self.stats["rejected"] += rejected

        self.logger.info(
            "self_training_synthesized",
            source_record=record.id,
            total=len(valid),
            rejected=rejected,
        )

        return valid

    async def _generate_variations(
        self,
        record: ModificationRecord,
    ) -> list[SynthesizedExample]:
        """Generate alternative approaches to the same problem."""
        system_prompt = (
            "You are a code modification expert. Given a successful code modification, "
            "generate 2-3 alternative approaches that could also solve the same problem. "
            "Each variation should be a valid, working alternative. "
            "Return JSON: {\"variations\": [{\"approach\": \"description\", \"code\": \"python code\", \"quality\": 0.0-1.0}]}"
        )

        prompt = f"""A successful modification was made:

Target file: {record.target_file}
Task type: {record.task_type}
Description: {record.description}
Original code (first 500 chars):
```python
{record.original_code[:500]}
```

Modified code (first 500 chars):
```python
{record.modified_code[:500]}
```

Generate 2-3 alternative approaches to solve this same problem. Each should be a valid Python modification."""

        response = await self.backend.complete(
            prompt=prompt,
            system=system_prompt,
            max_tokens=2000,
            temperature=0.8,
        )

        examples = []
        parsed = response.parsed_json
        variations = parsed.get("variations", [])

        for i, var in enumerate(variations[:self.max_variations]):
            code = var.get("code", "")
            if not code or len(code) < 20:
                continue

            quality = var.get("quality", 0.6)
            # Boost quality if the variation is substantially different
            if self._is_substantially_different(code, record.modified_code):
                quality = min(1.0, quality + 0.1)

            examples.append(SynthesizedExample(
                id=str(uuid.uuid4()),
                source_record_id=record.id,
                synth_type="variation",
                instruction=self._build_variation_instruction(record, var.get("approach", "")),
                output=f"```python\n{code[:3000]}\n```",
                quality_score=quality,
                metadata={"approach": var.get("approach", ""), "variation_index": i},
            ))

        return examples

    async def _generate_inverse(
        self,
        record: ModificationRecord,
    ) -> SynthesizedExample | None:
        """Generate an example of what NOT to do (common mistake)."""
        system_prompt = (
            "You are a code modification expert. Given a successful code modification, "
            "generate a common mistake or anti-pattern that a less experienced developer might make "
            "when trying to solve the same problem. This is used as a negative training example. "
            "Return JSON: {\"mistake\": \"description\", \"bad_code\": \"python code\", \"why_wrong\": \"explanation\"}"
        )

        prompt = f"""A successful modification was made to fix: {record.description}

Modified code (first 500 chars):
```python
{record.modified_code[:500]}
```

Generate a common mistake or anti-pattern that someone might make when trying to solve this same problem. Show the bad code and explain why it's wrong."""

        response = await self.backend.complete(
            prompt=prompt,
            system=system_prompt,
            max_tokens=1500,
            temperature=0.7,
        )

        parsed = response.parsed_json
        bad_code = parsed.get("bad_code", "")
        mistake = parsed.get("mistake", "")
        why_wrong = parsed.get("why_wrong", "")

        if not bad_code or len(bad_code) < 20:
            return None

        instruction = (
            f"The following code attempt has a critical error. "
            f"Problem: {mistake}\n\n"
            f"Bad code:\n```python\n{bad_code[:2000]}\n```\n\n"
            f"Explain what's wrong and provide the correct fix."
        )

        output = (
            f"The code has the following issue: {why_wrong}\n\n"
            f"Here's the correct approach:\n```python\n{record.modified_code[:2000]}\n```"
        )

        return SynthesizedExample(
            id=str(uuid.uuid4()),
            source_record_id=record.id,
            synth_type="inverse",
            instruction=instruction,
            output=output,
            quality_score=0.7,
            metadata={"mistake": mistake, "why_wrong": why_wrong},
        )

    async def _extract_reasoning_chain(
        self,
        record: ModificationRecord,
    ) -> SynthesizedExample | None:
        """Extract a step-by-step reasoning chain for why this modification worked."""
        if not record.reasoning and not record.description:
            return None

        system_prompt = (
            "You are a code analysis expert. Given a successful code modification, "
            "explain the step-by-step reasoning for why this modification is correct and effective. "
            "Return JSON: {\"chain\": [\"step 1\", \"step 2\", ...], \"key_insight\": \"main insight\"}"
        )

        prompt = f"""A successful modification was made:

Description: {record.description}
Reasoning: {record.reasoning or 'Not provided'}
Original code (first 500 chars):
```python
{record.original_code[:500]}
```

Modified code (first 500 chars):
```python
{record.modified_code[:500]}
```

Explain the step-by-step reasoning for why this modification works."""

        response = await self.backend.complete(
            prompt=prompt,
            system=system_prompt,
            max_tokens=1500,
            temperature=0.5,
        )

        parsed = response.parsed_json
        chain = parsed.get("chain", [])
        key_insight = parsed.get("key_insight", "")

        if not chain or len(chain) < 2:
            return None

        instruction = (
            f"Explain the step-by-step reasoning for why the following modification to "
            f"'{record.target_file}' is correct and effective.\n\n"
            f"Task: {record.description}\n"
            f"Original code:\n```python\n{record.original_code[:1000]}\n```\n"
            f"Modified code:\n```python\n{record.modified_code[:1000]}\n```"
        )

        output = (
            f"Here's the step-by-step reasoning:\n\n"
            + "\n".join(f"{i+1}. {step}" for i, step in enumerate(chain))
            + f"\n\nKey insight: {key_insight}"
        )

        return SynthesizedExample(
            id=str(uuid.uuid4()),
            source_record_id=record.id,
            synth_type="reasoning",
            instruction=instruction,
            output=output,
            quality_score=0.75,
            metadata={"chain": chain, "key_insight": key_insight},
        )

    async def _generalize_pattern(
        self,
        record: ModificationRecord,
    ) -> SynthesizedExample | None:
        """Generalize the modification into a reusable pattern."""
        system_prompt = (
            "You are a software architecture expert. Given a successful code modification, "
            "extract a generalizable pattern that could be applied to similar problems. "
            "Return JSON: {\"pattern_name\": \"name\", \"description\": \"when to use\", "
            "\"template\": \"generic code template\", \"applicable_when\": [\"condition 1\", ...]}"
        )

        prompt = f"""A successful modification was made:

Task type: {record.task_type}
Target file: {record.target_file}
Description: {record.description}

Modified code (first 500 chars):
```python
{record.modified_code[:500]}
```

Extract a generalizable pattern from this modification. What's the reusable template?"""

        response = await self.backend.complete(
            prompt=prompt,
            system=system_prompt,
            max_tokens=1500,
            temperature=0.6,
        )

        parsed = response.parsed_json
        pattern_name = parsed.get("pattern_name", "")
        template = parsed.get("template", "")
        applicable_when = parsed.get("applicable_when", [])

        if not template or len(template) < 30:
            return None

        instruction = (
            f"Apply the '{pattern_name}' pattern to solve the following problem.\n\n"
            f"Pattern description: {parsed.get('description', '')}\n"
            f"Applicable when: {', '.join(applicable_when)}\n\n"
            f"Problem: {record.description}"
        )

        output = (
            f"Pattern: {pattern_name}\n\n"
            f"```python\n{template[:2000]}\n```\n\n"
            f"This pattern applies when: {', '.join(applicable_when)}"
        )

        return SynthesizedExample(
            id=str(uuid.uuid4()),
            source_record_id=record.id,
            synth_type="generalization",
            instruction=instruction,
            output=output,
            quality_score=0.7,
            metadata={
                "pattern_name": pattern_name,
                "applicable_when": applicable_when,
            },
        )

    def _build_variation_instruction(
        self,
        record: ModificationRecord,
        approach: str,
    ) -> str:
        """Build instruction for a variation example."""
        parts = [
            f"Improve the following Python code using an alternative approach.",
            f"Target file: {record.target_file}",
            f"Task: {record.description}",
            f"Approach: {approach}",
        ]
        if record.original_code:
            parts.append(f"Original code:\n```python\n{record.original_code[:1500]}\n```")
        return "\n\n".join(parts)

    def _is_substantially_different(self, code_a: str, code_b: str) -> bool:
        """Check if two code snippets are substantially different."""
        if not code_a or not code_b:
            return False
        # Simple line-level diff
        lines_a = set(code_a.strip().split("\n"))
        lines_b = set(code_b.strip().split("\n"))
        if not lines_a or not lines_b:
            return False
        intersection = lines_a & lines_b
        union = lines_a | lines_b
        similarity = len(intersection) / len(union) if union else 1.0
        return similarity < 0.7

    def _add_to_memory(
        self,
        example: SynthesizedExample,
        source_record: ModificationRecord,
    ) -> None:
        """Add a synthesized example to modification memory."""
        record = ModificationRecord(
            id=example.id,
            timestamp=datetime.utcnow().isoformat(),
            source_module="self_training",
            target_file=source_record.target_file,
            task_type=source_record.task_type,
            description=f"[synth:{example.synth_type}] {source_record.description}",
            reasoning=example.instruction,
            original_code=source_record.original_code,
            modified_code=example.output,
            success=True,
            quality_score=example.quality_score,
            metadata={
                "synth_type": example.synth_type,
                "source_record_id": example.source_record_id,
                **example.metadata,
            },
        )
        self.memory.record(record)

    def get_stats(self) -> dict[str, Any]:
        """Get synthesis statistics."""
        return {
            **self.stats,
            "memory_total": len(self.memory.records),
            "memory_successful": len(self.memory.get_successful_records()),
        }

    def to_context(self) -> str:
        """Convert stats to context string."""
        stats = self.get_stats()
        lines = [
            "Self-Training Synthesizer:",
            f"  Total Synthesized: {stats['total_synthesized']}",
            f"  Variations: {stats['variations']}",
            f"  Inverses: {stats['inverses']}",
            f"  Reasoning Chains: {stats['reasoning_chains']}",
            f"  Generalizations: {stats['generalizations']}",
            f"  Rejected: {stats['rejected']}",
            f"  Memory Total: {stats['memory_total']}",
        ]
        return "\n".join(lines)
