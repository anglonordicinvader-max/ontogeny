"""Contrastive Trainer — trains maldoror on both successful and failed modifications.

The key insight: instead of just learning from what worked, the model also
learns from what DIDN'T work. This builds intuition about what makes a
modification good or bad, not just copying successful examples.

Training format:
- "Given this modification, predict whether it will succeed or fail"
- "Why did this modification fail? What should have been done instead?"
- "Compare these two approaches. Which one is correct and why?"
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
class ContrastiveExample:
    """A single contrastive training example."""
    id: str = ""
    example_type: str = ""  # prediction, diagnosis, comparison
    instruction: str = ""
    output: str = ""
    quality_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class ContrastiveTrainer:
    """Generates contrastive training data from successful and failed modifications.

    Three types of contrastive examples:
    1. Prediction: "Will this modification succeed?" (binary classification)
    2. Diagnosis: "Why did this modification fail?" (error analysis)
    3. Comparison: "Which of these two approaches is correct?" (ranking)
    """

    def __init__(
        self,
        backend: CognitiveBackend,
        modification_memory: ModificationMemory,
        min_quality: float = 0.5,
    ):
        self.backend = backend
        self.memory = modification_memory
        self.min_quality = min_quality
        self.logger = structlog.get_logger()
        self.stats = {
            "total_generated": 0,
            "predictions": 0,
            "diagnoses": 0,
            "comparisons": 0,
            "rejected": 0,
        }

    async def generate_contrastive_data(self) -> list[ContrastiveExample]:
        """Generate all contrastive training examples from current memory.

        This is the main entry point. It generates:
        - Prediction examples from failed modifications
        - Diagnosis examples from failed modifications with context
        - Comparison examples from matched success/failure pairs
        """
        examples: list[ContrastiveExample] = []

        failed = self.memory.get_failed_records()
        pairs = self.memory.get_contrastive_pairs()

        # 1. Prediction examples: given a modification, predict success/failure
        predictions = await self._generate_predictions(failed)
        examples.extend(predictions)

        # 2. Diagnosis examples: explain why a modification failed
        diagnoses = await self._generate_diagnoses(failed)
        examples.extend(diagnoses)

        # 3. Comparison examples: compare successful vs failed approaches
        comparisons = await self._generate_comparisons(pairs)
        examples.extend(comparisons)

        # Score and filter
        valid = [e for e in examples if e.quality_score >= self.min_quality]
        rejected = len(examples) - len(valid)

        # Add valid examples to memory
        for example in valid:
            self._add_to_memory(example)

        # Update stats
        self.stats["total_generated"] += len(valid)
        self.stats["predictions"] += len(predictions)
        self.stats["diagnoses"] += len(diagnoses)
        self.stats["comparisons"] += len(comparisons)
        self.stats["rejected"] += rejected

        self.logger.info(
            "contrastive_data_generated",
            total=len(valid),
            predictions=len(predictions),
            diagnoses=len(diagnoses),
            comparisons=len(comparisons),
            rejected=rejected,
        )

        return valid

    async def _generate_predictions(
        self,
        failed_records: list[ModificationRecord],
    ) -> list[ContrastiveExample]:
        """Generate prediction examples: will this modification succeed?"""
        if not failed_records:
            return []

        # Take up to 5 failed records for prediction generation
        samples = failed_records[:5]

        system_prompt = (
            "You are a code modification expert. Given a failed code modification, "
            "explain why it would fail and predict the outcome. "
            "Return JSON: {\"prediction\": \"fail\", \"reason\": \"explanation\", "
            "\"confidence\": 0.0-1.0, \"warning_signs\": [\"sign1\", ...]}"
        )

        examples = []
        for record in samples:
            if not record.modified_code or len(record.modified_code) < 20:
                continue

            prompt = f"""Analyze this code modification and predict its outcome:

Target file: {record.target_file}
Task type: {record.task_type}
Description: {record.description}
Original code (first 500 chars):
```python
{record.original_code[:500] if record.original_code else "# No original code"}
```

Proposed modification (first 500 chars):
```python
{record.modified_code[:500]}
```

Will this modification succeed or fail? Why?"""

            response = await self.backend.complete(
                prompt=prompt,
                system=system_prompt,
                max_tokens=1000,
                temperature=0.5,
            )

            parsed = response.parsed_json
            prediction = parsed.get("prediction", "unknown")
            reason = parsed.get("reason", "")
            warning_signs = parsed.get("warning_signs", [])

            if not reason or len(reason) < 20:
                continue

            instruction = (
                f"Analyze the following code modification and predict whether it will succeed or fail.\n\n"
                f"Target file: {record.target_file}\n"
                f"Task: {record.description}\n"
                f"Proposed code:\n```python\n{record.modified_code[:1500]}\n```"
            )

            output = (
                f"Prediction: {prediction}\n"
                f"Reason: {reason}\n"
                f"Warning signs: {', '.join(warning_signs) if warning_signs else 'None identified'}"
            )

            examples.append(ContrastiveExample(
                id=str(uuid.uuid4()),
                example_type="prediction",
                instruction=instruction,
                output=output,
                quality_score=0.7,
                metadata={
                    "actual_outcome": "fail",
                    "predicted_outcome": prediction,
                    "warning_signs": warning_signs,
                },
            ))

        return examples

    async def _generate_diagnoses(
        self,
        failed_records: list[ModificationRecord],
    ) -> list[ContrastiveExample]:
        """Generate diagnosis examples: why did this fail?"""
        if not failed_records:
            return []

        samples = failed_records[:5]

        system_prompt = (
            "You are a code debugging expert. Given a failed code modification, "
            "diagnose the root cause and suggest the correct fix. "
            "Return JSON: {\"root_cause\": \"explanation\", \"correct_approach\": \"description\", "
            "\"fixed_code\": \"python code\", \"lessons\": [\"lesson1\", ...]}"
        )

        examples = []
        for record in samples:
            if not record.modified_code or len(record.modified_code) < 20:
                continue

            prompt = f"""This code modification failed. Diagnose why and provide the correct fix:

Target file: {record.target_file}
Task type: {record.task_type}
Description: {record.description}
Original code (first 500 chars):
```python
{record.original_code[:500] if record.original_code else "# No original code"}
```

Failed modification (first 500 chars):
```python
{record.modified_code[:500]}
```

What went wrong? What's the correct approach?"""

            response = await self.backend.complete(
                prompt=prompt,
                system=system_prompt,
                max_tokens=1500,
                temperature=0.5,
            )

            parsed = response.parsed_json
            root_cause = parsed.get("root_cause", "")
            correct_approach = parsed.get("correct_approach", "")
            fixed_code = parsed.get("fixed_code", "")

            if not root_cause or len(root_cause) < 20:
                continue

            instruction = (
                f"The following code modification to '{record.target_file}' failed.\n"
                f"Task: {record.description}\n\n"
                f"Failed code:\n```python\n{record.modified_code[:1500]}\n```\n\n"
                f"Diagnose the root cause and provide the correct fix."
            )

            output = (
                f"Root cause: {root_cause}\n\n"
                f"Correct approach: {correct_approach}\n\n"
                f"Fixed code:\n```python\n{fixed_code[:2000] if fixed_code else record.original_code[:2000]}\n```"
            )

            examples.append(ContrastiveExample(
                id=str(uuid.uuid4()),
                example_type="diagnosis",
                instruction=instruction,
                output=output,
                quality_score=0.75,
                metadata={
                    "root_cause": root_cause,
                    "correct_approach": correct_approach,
                },
            ))

        return examples

    async def _generate_comparisons(
        self,
        pairs: list[tuple[ModificationRecord, ModificationRecord | None]],
    ) -> list[ContrastiveExample]:
        """Generate comparison examples: which approach is correct?"""
        # Only use pairs where we have both success and failure
        valid_pairs = [(s, f) for s, f in pairs if f is not None]

        if not valid_pairs:
            return []

        samples = valid_pairs[:5]

        system_prompt = (
            "You are a code review expert. Given two approaches to the same problem "
            "(one successful, one failed), explain which is correct and why. "
            "Return JSON: {\"correct\": \"A\" or \"B\", \"explanation\": \"why\", "
            "\"key_difference\": \"what matters\", \"takeaway\": \"general lesson\"}"
        )

        examples = []
        for success, failure in samples:
            if (not success.modified_code or len(success.modified_code) < 20 or
                not failure.modified_code or len(failure.modified_code) < 20):
                continue

            prompt = f"""Two approaches to the same problem. One succeeded, one failed.

Problem: {success.description}

Approach A (succeeded):
```python
{success.modified_code[:500]}
```

Approach B (failed):
```python
{failure.modified_code[:500]}
```

Which approach is correct? What's the key difference?"""

            response = await self.backend.complete(
                prompt=prompt,
                system=system_prompt,
                max_tokens=1000,
                temperature=0.5,
            )

            parsed = response.parsed_json
            correct = parsed.get("correct", "unknown")
            explanation = parsed.get("explanation", "")
            key_difference = parsed.get("key_difference", "")
            takeaway = parsed.get("takeaway", "")

            if not explanation or len(explanation) < 20:
                continue

            instruction = (
                f"Compare these two approaches to: {success.description}\n\n"
                f"Approach A:\n```python\n{success.modified_code[:1000]}\n```\n\n"
                f"Approach B:\n```python\n{failure.modified_code[:1000]}\n```\n\n"
                f"Which approach is correct and why?"
            )

            output = (
                f"Correct approach: {correct}\n\n"
                f"Explanation: {explanation}\n\n"
                f"Key difference: {key_difference}\n\n"
                f"Takeaway: {takeaway}"
            )

            examples.append(ContrastiveExample(
                id=str(uuid.uuid4()),
                example_type="comparison",
                instruction=instruction,
                output=output,
                quality_score=0.8,
                metadata={
                    "correct_approach": correct,
                    "key_difference": key_difference,
                    "takeaway": takeaway,
                },
            ))

        return examples

    def _add_to_memory(self, example: ContrastiveExample) -> None:
        """Add a contrastive example to modification memory."""
        record = ModificationRecord(
            id=example.id,
            timestamp=datetime.utcnow().isoformat(),
            source_module="contrastive_training",
            target_file="",
            task_type=example.example_type,
            description=f"[contrastive:{example.example_type}] Generated contrastive training example",
            reasoning=example.instruction,
            modified_code=example.output,
            success=True,  # The training example itself is valid
            quality_score=example.quality_score,
            metadata={
                "example_type": example.example_type,
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
            "Contrastive Trainer:",
            f"  Total Generated: {stats['total_generated']}",
            f"  Predictions: {stats['predictions']}",
            f"  Diagnoses: {stats['diagnoses']}",
            f"  Comparisons: {stats['comparisons']}",
            f"  Rejected: {stats['rejected']}",
            f"  Memory: {stats['memory_successful']} success, {stats['memory_failed']} failed",
        ]
        return "\n".join(lines)
