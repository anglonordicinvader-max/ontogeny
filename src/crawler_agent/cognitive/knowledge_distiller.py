"""Knowledge distillation - fine-tune LoRA on successful self-generated code."""

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .backend import CognitiveBackend


@dataclass
class DistillationExample:
    """A training example for distillation."""
    prompt: str
    completion: str
    metadata: dict[str, Any] = None


class KnowledgeDistiller:
    """Distills successful self-generated code into LoRA adapters."""

    def __init__(
        self,
        backend: CognitiveBackend,
        storage_path: str = "data/knowledge_distillation",
        min_examples: int = 50,
    ):
        self.backend = backend
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.min_examples = min_examples

        self.examples: list[DistillationExample] = []
        self._load()

    def _load(self) -> None:
        f = self.storage_path / "examples.jsonl"
        if f.exists():
            for line in f.read_text().strip().split("\n"):
                if line:
                    try:
                        self.examples.append(DistillationExample(**json.loads(line)))
                    except Exception:
                        pass

    def add_example(
        self,
        prompt: str,
        completion: str,
        metadata: dict | None = None,
    ) -> None:
        """Add a successful code generation as training example."""
        example = DistillationExample(
            prompt=prompt,
            completion=completion,
            metadata=metadata or {},
        )
        self.examples.append(example)
        self._save_example(example)

    def _save_example(self, example: DistillationExample) -> None:
        f = self.storage_path / "examples.jsonl"
        f.write_text(f.read_text() + json.dumps({
            "prompt": example.prompt,
            "completion": example.completion,
            "metadata": example.metadata,
        }) + "\n" if f.exists() else json.dumps({
            "prompt": example.prompt,
            "completion": example.completion,
            "metadata": example.metadata,
        }) + "\n")

    def can_distill(self) -> bool:
        return len(self.examples) >= self.min_examples

    async def generate_training_data(self) -> list[dict[str, str]]:
        """Format examples for LoRA training."""
        return [
            {"prompt": e.prompt, "completion": e.completion}
            for e in self.examples
        ]

    async def trigger_distillation(self) -> dict[str, Any]:
        """Trigger LoRA fine-tuning (placeholder for actual training)."""
        if not self.can_distill():
            return {"status": "insufficient_examples", "count": len(self.examples)}

        # In practice, this would:
        # 1. Format data for PEFT/LoRA training
        # 2. Run training on base model
        # 3. Save adapter weights
        # 4. Register with Ollama/vLLM

        training_data = await self.generate_training_data()

        return {
            "status": "distillation_triggered",
            "examples": len(training_data),
            "output_path": str(self.storage_path / "lora_adapter"),
            "note": "Actual training requires GPU cluster - this prepares data",
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_examples": len(self.examples),
            "min_for_distillation": self.min_examples,
            "can_distill": self.can_distill(),
            "storage_path": str(self.storage_path),
        }