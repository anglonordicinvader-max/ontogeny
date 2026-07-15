"""Knowledge distillation - LoRA fine-tuning on successful self-generated code."""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .backend import CognitiveBackend


@dataclass
class TrainingExample:
    """A training example for distillation."""
    prompt: str
    completion: str
    quality_score: float
    source: str  # self_modification, recursive_modification, skill_creation
    task_type: str  # coding, planning, reasoning
    metadata: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class DistillationConfig:
    """Configuration for LoRA distillation."""
    model_name: str = "deepseek-coder-v2:16b"
    lora_rank: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    learning_rate: float = 2e-4
    batch_size: int = 4
    max_steps: int = 100
    min_examples: int = 50
    quality_threshold: float = 0.7


class KnowledgeDistiller:
    """Collects successful generations and fine-tunes a LoRA adapter."""

    def __init__(
        self,
        backend: CognitiveBackend,
        config: DistillationConfig | None = None,
        storage_path: str = "data/distillation",
    ):
        self.backend = backend
        self.config = config or DistillationConfig()
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.examples: list[TrainingExample] = []
        self.lora_adapters: dict[str, Path] = {}  # task_type -> adapter path
        self._load_examples()

    def _load_examples(self) -> None:
        for f in self.storage_path.glob("*.jsonl"):
            for line in f.read_text().strip().split("\n"):
                if line:
                    try:
                        self.examples.append(TrainingExample(**json.loads(line)))
                    except Exception:
                        pass

    def add_example(self, example: TrainingExample) -> None:
        """Add a successful generation to training set."""
        if example.quality_score >= self.config.quality_threshold:
            self.examples.append(example)
            self._save_example(example)

    def _save_example(self, example: TrainingExample) -> None:
        f = self.storage_path / f"{example.task_type}.jsonl"
        f.write_text(f.read_text() + json.dumps(example.__dict__) + "\n" if f.exists() else json.dumps(example.__dict__) + "\n")

    def get_training_data(self, task_type: str | None = None) -> list[TrainingExample]:
        """Get training examples, optionally filtered by task type."""
        if task_type:
            return [e for e in self.examples if e.task_type == task_type]
        return self.examples

    def ready_for_training(self, task_type: str | None = None) -> bool:
        """Check if enough examples exist for training."""
        data = self.get_training_data(task_type)
        return len(data) >= self.config.min_examples

    def prepare_lora_dataset(self, task_type: str | None = None) -> list[dict]:
        """Format examples for LoRA training (Alpaca format)."""
        data = self.get_training_data(task_type)
        formatted = []
        for ex in data:
            formatted.append({
                "instruction": ex.prompt,
                "input": "",
                "output": ex.completion,
                "quality": ex.quality_score,
            })
        return formatted

    async def train_lora(
        self,
        task_type: str,
        base_model: str | None = None,
    ) -> Path | None:
        """Train LoRA adapter (requires GPU with CUDA)."""
        # This would use llama.cpp or similar for LoRA training
        # For now, return placeholder
        adapter_path = self.storage_path / f"lora_{task_type}.gguf"
        return adapter_path if adapter_path.exists() else None

    def export_training_data(self, output_path: str) -> None:
        """Export training data for external training."""
        all_data = self.prepare_lora_dataset()
        Path(output_path).write_text(json.dumps(all_data, indent=2))

    def get_stats(self) -> dict[str, Any]:
        by_type = {}
        for ex in self.examples:
            by_type[ex.task_type] = by_type.get(ex.task_type, 0) + 1

        return {
            "total_examples": len(self.examples),
            "by_type": by_type,
            "ready_for_training": {
                t: self.ready_for_training(t) for t in by_type
            },
            "adapters": list(self.lora_adapters.keys()),
        }


class PatternExtractor:
    """Extracts reusable patterns from successful code."""

    def __init__(self, backend: CognitiveBackend):
        self.backend = backend

    async def extract_patterns(
        self,
        code_samples: list[str],
        context: str = "",
    ) -> list[dict]:
        """Extract common patterns from code samples."""
        combined = "\n\n---\n\n".join(code_samples[:10])

        prompt = f"""Extract reusable code patterns from these successful samples.

Context: {context}

Code samples:
{combined[:8000]}

Identify:
1. Common function signatures
2. Error handling patterns
3. Async/concurrency patterns
4. Data processing pipelines
5. Project-specific idioms

Return JSON array of patterns:
[{{
  "name": "async_rate_limited_fetch",
  "type": "concurrency",
  "description": "...",
  "template": "async def fetch_with_limit(...): ...",
  "applicability": "high|medium|low"
}}]"""

        response = await self.backend.complete(prompt, temperature=0.3, max_tokens=3000)

        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            return []

    async def generate_skill_template(
        self,
        pattern: dict,
    ) -> str:
        """Generate a skill template from a pattern."""
        prompt = f"""Create a complete, reusable skill function from this pattern.

Pattern: {json.dumps(pattern)}

Requirements:
- Full function with type hints
- Comprehensive docstring
- Error handling
- Configurable parameters
- Follows project conventions

Return ONLY the Python code."""

        response = await self.backend.complete(prompt, temperature=0.3, max_tokens=2000)
        return response.content


class SelfPlayTrainer:
    """Generates training data through self-play."""

    def __init__(
        self,
        backend: CognitiveBackend,
        distiller: KnowledgeDistiller,
    ):
        self.backend = backend
        self.distiller = distiller

    async def generate_training_data(
        self,
        num_episodes: int = 10,
        task_types: list[str] | None = None,
    ) -> list[TrainingExample]:
        """Generate training examples via self-play."""
        task_types = task_types or ["coding", "planning", "reasoning"]
        examples = []

        for _ in range(num_episodes):
            task_type = task_type = task_types[_ % len(task_types)]

            # Generate a task
            task = await self._generate_task(task_type)
            if not task:
                continue

            # Solve it
            solution = await self._solve_task(task)
            if not solution:
                continue

            # Evaluate
            quality = await self._evaluate_solution(task, solution)
            if quality >= self.distiller.config.quality_threshold:
                examples.append(TrainingExample(
                    prompt=task,
                    completion=solution,
                    quality_score=quality,
                    source="self_play",
                    task_type=task_type,
                ))

        return examples

    async def _generate_task(self, task_type: str) -> str | None:
        """Generate a training task."""
        prompts = {
            "coding": "Create a coding task with a clear specification.",
            "planning": "Create a planning task requiring multi-step reasoning.",
            "reasoning": "Create a reasoning task requiring causal or logical analysis.",
        }

        prompt = f"{prompts.get(task_type, '')} Make it realistic and solvable. Return only the task description."

        response = await self.backend.complete(prompt, temperature=0.8)
        return response.content.strip() if response.content else None

    async def _solve_task(self, task: str) -> str | None:
        """Solve a task."""
        prompt = f"Solve this task:\n\n{task}\n\nProvide complete solution with explanation."
        response = await self.backend.complete(prompt, temperature=0.7, max_tokens=3000)
        return response.content if response.content else None

    async def _evaluate_solution(self, task: str, solution: str) -> float:
        """Evaluate solution quality."""
        prompt = f"""Rate this solution 0-1.

Task: {task}
Solution: {solution[:2000]}

Criteria: correctness, completeness, clarity, efficiency.
Return ONLY: {{"score": 0.85}}"""

        response = await self.backend.complete(prompt, temperature=0.1)
        try:
            return json.loads(response.content).get("score", 0.0)
        except Exception:
            return 0.0


async def create_knowledge_distiller(backend: CognitiveBackend) -> KnowledgeDistiller:
    return KnowledgeDistiller(backend)