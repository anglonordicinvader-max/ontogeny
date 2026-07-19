"""Modification Memory — accumulates successful self-modifications as training data.

Aggregates training records from:
- recursive_modify.py (source code rewrites)
- self_modify.py (skill creation, optimization)
- benchmark_runner.py (performance measurements)

Stores as JSONL for easy export to fine-tuning pipelines.
"""

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog


@dataclass
class ModificationRecord:
    """A single training record from a self-modification."""

    id: str = ""
    timestamp: str = ""
    source_module: str = ""  # recursive_modify, self_modify, etc.
    target_file: str = ""  # e.g. "orchestrator.py"
    task_type: str = ""  # code_rewrite, skill_creation, optimization, bug_fix
    description: str = ""
    reasoning: str = ""
    original_code: str = ""  # first N lines of original
    modified_code: str = ""  # the replacement code
    diff: str = ""  # unified diff
    success: bool = False
    performance_delta: float = 0.0
    benchmark_score: float = 0.0  # from benchmark_runner
    quality_score: float = 0.0  # computed quality rating
    metadata: dict[str, Any] = field(default_factory=dict)


class ModificationMemory:
    """Accumulates and manages training data from self-modifications.

    Reads from JSONL logs written by recursive_modify.py and self_modify.py,
    computes quality scores, and exports formatted data for fine-tuning.
    """

    def __init__(self, storage_path: str = "data/modification_memory"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.records: list[ModificationRecord] = []
        self.log_file = self.storage_path / "memory.jsonl"
        self.logger = structlog.get_logger()
        self._load_records()

    def _load_records(self) -> None:
        """Load existing records from disk."""
        if not self.log_file.exists():
            return

        try:
            for line in self.log_file.read_text(encoding="utf-8").strip().split("\n"):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    record = ModificationRecord(
                        **{
                            k: v
                            for k, v in data.items()
                            if k in ModificationRecord.__dataclass_fields__
                        }
                    )
                    self.records.append(record)
                except Exception as e:
                    self.logger.debug("record_parse_failed", error=str(e))
            self.logger.info("modification_memory_loaded", count=len(self.records))
        except Exception as e:
            self.logger.warning("modification_memory_load_failed", error=str(e))

    def record(self, mod_record: ModificationRecord) -> None:
        """Add a new modification record."""
        if not mod_record.timestamp:
            mod_record.timestamp = datetime.utcnow().isoformat()

        # Compute quality score if not set
        if mod_record.quality_score == 0.0:
            mod_record.quality_score = self._compute_quality(mod_record)

        self.records.append(mod_record)

        # Append to JSONL
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(mod_record)) + "\n")
        except Exception as e:
            self.logger.warning("record_write_failed", error=str(e))

    def ingest_from_training_logs(self) -> int:
        """Ingest records from recursive_modify and self_modify training logs."""
        ingested = 0

        # Ingest from recursive_modify training log
        recursive_log = Path("./data/modification_training_log.jsonl")
        if recursive_log.exists():
            for line in recursive_log.read_text(encoding="utf-8").strip().split("\n"):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if data.get("source_module") == "recursive_modify":
                        continue  # Already ingested

                    record = ModificationRecord(
                        id=data.get("id", ""),
                        timestamp=data.get("timestamp", ""),
                        source_module="recursive_modify",
                        target_file=data.get("target_file", ""),
                        task_type="code_rewrite",
                        description=data.get("description", ""),
                        reasoning=data.get("reasoning", ""),
                        original_code=data.get("original_code", ""),
                        modified_code=data.get("new_code", ""),
                        diff=data.get("diff", ""),
                        success=data.get("success", False),
                    )
                    # Check if already exists
                    if not any(r.id == record.id for r in self.records if r.id):
                        self.record(record)
                        ingested += 1
                except Exception as e:
                    self.logger.debug("record_parse_failed", error=str(e))

        # Ingest from self_modify training log
        self_modify_log = Path("./data/modification_training_log.jsonl")
        if self_modify_log.exists():
            for line in self_modify_log.read_text(encoding="utf-8").strip().split("\n"):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if data.get("source_module") == "self_modify":
                        continue

                    record = ModificationRecord(
                        id=data.get("id", ""),
                        timestamp=data.get("timestamp", ""),
                        source_module="self_modify",
                        task_type=data.get("mod_type", "unknown"),
                        description=data.get("description", ""),
                        reasoning=data.get("reasoning", ""),
                        modified_code=data.get("code", ""),
                        success=data.get("success", False),
                    )
                    if not any(r.id == record.id for r in self.records if r.id):
                        self.record(record)
                        ingested += 1
                except Exception as e:
                    self.logger.debug("record_parse_failed", error=str(e))

        if ingested > 0:
            self.logger.info("training_logs_ingested", count=ingested)

        return ingested

    def _compute_quality(self, record: ModificationRecord) -> float:
        """Compute a quality score for a modification record."""
        score = 0.5  # Base score

        # Boost for success
        if record.success:
            score += 0.2

        # Boost for positive performance delta
        if record.performance_delta > 0:
            score += min(0.2, record.performance_delta * 0.1)

        # Boost for having good reasoning
        if record.reasoning and len(record.reasoning) > 50:
            score += 0.05

        # Boost for having a diff (more precise modification)
        if record.diff and len(record.diff) > 10:
            score += 0.05

        return min(1.0, score)

    def get_successful_records(
        self,
        task_type: str | None = None,
        min_quality: float = 0.6,
    ) -> list[ModificationRecord]:
        """Get successful records filtered by type and quality."""
        return [
            r
            for r in self.records
            if r.success
            and r.quality_score >= min_quality
            and (task_type is None or r.task_type == task_type)
        ]

    def get_failed_records(
        self,
        task_type: str | None = None,
    ) -> list[ModificationRecord]:
        """Get failed records for contrastive training."""
        return [
            r
            for r in self.records
            if not r.success and (task_type is None or r.task_type == task_type)
        ]

    def get_contrastive_pairs(
        self,
        task_type: str | None = None,
    ) -> list[tuple[ModificationRecord, ModificationRecord | None]]:
        """Get matched pairs of successful and failed modifications.

        Returns pairs where both share the same target_file or task_type.
        The failed record may be None if no match exists.
        """
        successful = self.get_successful_records(task_type=task_type, min_quality=0.0)
        failed = self.get_failed_records(task_type=task_type)

        pairs = []
        used_failed = set()

        for succ in successful:
            best_match = None
            best_score = -1

            for fail in failed:
                if fail.id in used_failed:
                    continue
                # Score match quality
                score = 0
                if fail.target_file == succ.target_file:
                    score += 3
                if fail.task_type == succ.task_type:
                    score += 2
                if fail.description and succ.description:
                    # Simple word overlap
                    succ_words = set(succ.description.lower().split())
                    fail_words = set(fail.description.lower().split())
                    overlap = len(succ_words & fail_words) / max(len(succ_words | fail_words), 1)
                    score += overlap * 2

                if score > best_score:
                    best_score = score
                    best_match = fail

            if best_match and best_score > 0:
                used_failed.add(best_match.id)
            pairs.append((succ, best_match))

        return pairs

    def get_training_data(
        self,
        task_type: str | None = None,
        min_quality: float = 0.6,
        format: str = "alpaca",
    ) -> list[dict]:
        """Get training data in the specified format.

        Formats:
        - alpaca: {instruction, input, output}
        - chatml: {messages: [{role, content}]}
        - completion: {prompt, completion}
        """
        records = self.get_successful_records(task_type, min_quality)

        if format == "alpaca":
            return [
                {
                    "instruction": self._build_instruction(r),
                    "input": "",
                    "output": self._build_output(r),
                    "quality": r.quality_score,
                }
                for r in records
            ]
        elif format == "chatml":
            return [
                {
                    "messages": [
                        {"role": "system", "content": self._system_prompt()},
                        {"role": "user", "content": self._build_instruction(r)},
                        {"role": "assistant", "content": self._build_output(r)},
                    ]
                }
                for r in records
            ]
        elif format == "completion":
            return [
                {
                    "prompt": self._build_instruction(r),
                    "completion": self._build_output(r),
                    "quality": r.quality_score,
                }
                for r in records
            ]
        return []

    def _build_instruction(self, record: ModificationRecord) -> str:
        """Build instruction prompt from a record."""
        parts = [f"Improve the following Python code to fix: {record.description}"]
        if record.target_file:
            parts[0] += f"\nTarget file: {record.target_file}"
        if record.reasoning:
            parts.append(f"Context: {record.reasoning}")
        if record.original_code:
            parts.append(f"Original code:\n```python\n{record.original_code[:1500]}\n```")
        return "\n\n".join(parts)

    def _build_output(self, record: ModificationRecord) -> str:
        """Build expected output from a record."""
        if record.modified_code:
            return f"```python\n{record.modified_code[:3000]}\n```"
        if record.diff:
            return f"```diff\n{record.diff[:2000]}\n```"
        return record.description

    def _system_prompt(self) -> str:
        """System prompt for the Maldoror model."""
        return (
            "You are Maldoror, a specialized AI model for recursive self-modification "
            "of cognitive agent systems. You analyze code, identify improvements, "
            "and generate precise, tested modifications. You maintain backward "
            "compatibility and prioritize safety. Return valid Python code."
        )

    def ready_for_training(self, min_examples: int = 20) -> bool:
        """Check if enough data exists for fine-tuning."""
        return len(self.get_successful_records()) >= min_examples

    def get_stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        task_types = {}
        for r in self.records:
            task_types[r.task_type] = task_types.get(r.task_type, 0) + 1

        successful = [r for r in self.records if r.success]
        failed = [r for r in self.records if not r.success]
        avg_quality = sum(r.quality_score for r in successful) / max(len(successful), 1)

        return {
            "total_records": len(self.records),
            "successful": len(successful),
            "failed": len(failed),
            "avg_quality": avg_quality,
            "task_types": task_types,
            "ready_for_training": self.ready_for_training(),
            "sources": {
                "recursive_modify": sum(
                    1 for r in self.records if r.source_module == "recursive_modify"
                ),
                "self_modify": sum(1 for r in self.records if r.source_module == "self_modify"),
                "self_training": sum(1 for r in self.records if r.source_module == "self_training"),
            },
        }

    def to_context(self) -> str:
        """Convert memory state to context string."""
        stats = self.get_stats()
        lines = [
            "Modification Memory:",
            f"  Total Records: {stats['total_records']}",
            f"  Successful: {stats['successful']}",
            f"  Failed: {stats['failed']}",
            f"  Avg Quality: {stats['avg_quality']:.2f}",
            f"  Ready for Training: {stats['ready_for_training']}",
        ]
        if stats["task_types"]:
            lines.append("  Task Types:")
            for t, c in stats["task_types"].items():
                lines.append(f"    {t}: {c}")
        return "\n".join(lines)
