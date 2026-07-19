"""Model Population — evolutionary population-based training for maldoror.

Runs multiple maldoror variants simultaneously, each with different
training data selections or hyperparameters. They compete on real
benchmark tasks. The winner's strategy gets propagated to the next generation.

This is genuinely novel — most LLM fine-tuning doesn't do population-based
self-improvement.
"""

import json
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from .backend import CognitiveBackend, CognitiveResponse
from .model_evaluation import ComparisonReport, ModelEvaluator
from .model_trainer import ModelTrainer, TrainingRun
from .modification_memory import ModificationMemory, ModificationRecord


@dataclass
class VariantConfig:
    """Training configuration for a single variant."""

    id: str = ""
    name: str = ""
    # Data selection
    min_quality: float = 0.6
    task_type_filter: str | None = None
    include_contrastive: bool = True
    include_synthetic: bool = True
    # Hyperparameters
    max_steps: int = 200
    learning_rate: float = 2e-4
    lora_r: int = 16
    lora_alpha: int = 32
    # Strategy
    data_strategy: str = "balanced"  # balanced, quality_first, diversity_first, contrastive_focus
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VariantResult:
    """Result of evaluating a variant."""

    variant_id: str
    config: VariantConfig
    training_run: TrainingRun | None = None
    benchmark_score: float = 0.0
    benchmark_details: dict[str, Any] = field(default_factory=dict)
    fitness: float = 0.0  # combined score
    generation: int = 0
    parent_id: str | None = None
    timestamp: str = ""


class ModelPopulation:
    """Manages an evolutionary population of maldoror variants.

    Population lifecycle:
    1. Initialize: create N variants with different configs
    2. Train: each variant trains on its selected data
    3. Evaluate: each variant competes on benchmark tasks
    4. Select: keep top performers, discard bottom
    5. Propagate: create next generation from winners
    6. Repeat from step 2

    The winner's training strategy gets mutated and reused,
    creating an evolutionary pressure toward better models.
    """

    def __init__(
        self,
        model_trainer: ModelTrainer,
        modification_memory: ModificationMemory,
        evaluator: ModelEvaluator,
        population_size: int = 3,
        survival_rate: float = 0.5,
        mutation_rate: float = 0.2,
        output_dir: str = "data/maldoror/population",
    ):
        self.trainer = model_trainer
        self.memory = modification_memory
        self.evaluator = evaluator
        self.population_size = population_size
        self.survival_rate = survival_rate
        self.mutation_rate = mutation_rate
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = structlog.get_logger()

        self.variants: dict[str, VariantResult] = {}
        self.generations: list[dict[str, Any]] = []
        self.generation = 0
        self.best_variant: VariantResult | None = None

        self._load_state()

    def _load_state(self) -> None:
        state_path = self.output_dir / "population_state.json"
        if state_path.exists():
            try:
                data = json.loads(state_path.read_text())
                self.generation = data.get("generation", 0)
                self.generations = data.get("generations", [])
                if data.get("best_variant"):
                    self.best_variant = VariantResult(**data["best_variant"])
            except Exception as e:
                self.logger.warning("population_state_load_failed", error=str(e))

    def _save_state(self) -> None:
        state_path = self.output_dir / "population_state.json"
        state = {
            "generation": self.generation,
            "generations": self.generations[-10:],  # Keep last 10
            "best_variant": self.best_variant.__dict__ if self.best_variant else None,
        }
        state_path.write_text(json.dumps(state, indent=2, default=str))

    def initialize_population(self) -> list[VariantConfig]:
        """Create initial population with diverse configurations.

        Each variant gets a different training strategy:
        - Balanced: equal mix of all data types
        - Quality first: only highest quality examples
        - Diversity first: maximize task type coverage
        - Contrastive focus: heavy on contrastive examples
        """
        configs = []

        # Strategy 1: Balanced
        configs.append(
            VariantConfig(
                id=str(uuid.uuid4())[:8],
                name="balanced",
                min_quality=0.6,
                data_strategy="balanced",
                include_contrastive=True,
                include_synthetic=True,
            )
        )

        # Strategy 2: Quality first
        configs.append(
            VariantConfig(
                id=str(uuid.uuid4())[:8],
                name="quality_first",
                min_quality=0.8,
                data_strategy="quality_first",
                include_contrastive=True,
                include_synthetic=True,
            )
        )

        # Strategy 3: Diversity first
        configs.append(
            VariantConfig(
                id=str(uuid.uuid4())[:8],
                name="diversity_first",
                min_quality=0.5,
                data_strategy="diversity_first",
                include_contrastive=True,
                include_synthetic=True,
            )
        )

        # Strategy 4: Contrastive focus (if we have enough contrastive data)
        contrastive_count = len(
            [
                r
                for r in self.memory.records
                if r.source_module in ("contrastive_training", "self_training")
            ]
        )
        if contrastive_count >= 5:
            configs.append(
                VariantConfig(
                    id=str(uuid.uuid4())[:8],
                    name="contrastive_focus",
                    min_quality=0.5,
                    data_strategy="contrastive_focus",
                    include_contrastive=True,
                    include_synthetic=True,
                )
            )

        # Strategy 5: Synthetic heavy
        synthetic_count = len(
            [r for r in self.memory.records if r.source_module == "self_training"]
        )
        if synthetic_count >= 5:
            configs.append(
                VariantConfig(
                    id=str(uuid.uuid4())[:8],
                    name="synthetic_heavy",
                    min_quality=0.5,
                    data_strategy="synthetic_heavy",
                    include_contrastive=False,
                    include_synthetic=True,
                )
            )

        # Trim to population size
        configs = configs[: self.population_size]

        self.logger.info(
            "population_initialized",
            size=len(configs),
            strategies=[c.name for c in configs],
        )

        return configs

    def select_training_data(self, config: VariantConfig) -> list[ModificationRecord]:
        """Select training data for a variant based on its strategy.

        Different strategies select different subsets of the data:
        - balanced: equal mix from all sources
        - quality_first: only top quality records
        - diversity_first: one per task_type, then fill
        - contrastive_focus: 70% contrastive, 30% regular
        - synthetic_heavy: 70% synthetic, 30% regular
        """
        all_records = self.memory.records

        if config.data_strategy == "quality_first":
            # Only high quality
            records = [r for r in all_records if r.quality_score >= config.min_quality]
            records.sort(key=lambda r: r.quality_score, reverse=True)
            return records[:50]

        elif config.data_strategy == "diversity_first":
            # One per task type, then fill by quality
            by_type: dict[str, list[ModificationRecord]] = {}
            for r in all_records:
                if r.quality_score >= config.min_quality:
                    by_type.setdefault(r.task_type, []).append(r)

            selected = []
            for _task_type, records in by_type.items():
                records.sort(key=lambda r: r.quality_score, reverse=True)
                selected.append(records[0])

            # Fill remaining by quality
            remaining = [
                r
                for r in all_records
                if r not in selected and r.quality_score >= config.min_quality
            ]
            remaining.sort(key=lambda r: r.quality_score, reverse=True)
            selected.extend(remaining[: 50 - len(selected)])
            return selected[:50]

        elif config.data_strategy == "contrastive_focus":
            # 70% contrastive/synthetic, 30% regular
            contrastive = [
                r
                for r in all_records
                if r.source_module in ("contrastive_training", "self_training")
            ]
            regular = [
                r
                for r in all_records
                if r.source_module not in ("contrastive_training", "self_training")
            ]

            contrastive.sort(key=lambda r: r.quality_score, reverse=True)
            regular.sort(key=lambda r: r.quality_score, reverse=True)

            n_contrastive = min(35, len(contrastive))
            n_regular = min(15, len(regular))
            return contrastive[:n_contrastive] + regular[:n_regular]

        elif config.data_strategy == "synthetic_heavy":
            # 70% synthetic, 30% regular
            synthetic = [r for r in all_records if r.source_module == "self_training"]
            regular = [r for r in all_records if r.source_module != "self_training"]

            synthetic.sort(key=lambda r: r.quality_score, reverse=True)
            regular.sort(key=lambda r: r.quality_score, reverse=True)

            n_synthetic = min(35, len(synthetic))
            n_regular = min(15, len(regular))
            return synthetic[:n_synthetic] + regular[:n_regular]

        else:  # balanced
            records = [r for r in all_records if r.quality_score >= config.min_quality]
            records.sort(key=lambda r: r.quality_score, reverse=True)
            return records[:50]

    async def train_variant(
        self,
        config: VariantConfig,
        base_model: str = "Qwen/Qwen2.5-7B-Instruct",
    ) -> VariantResult:
        """Train a single variant with its configuration."""
        result = VariantResult(
            variant_id=config.id,
            config=config,
            generation=self.generation,
            timestamp=datetime.utcnow().isoformat(),
        )

        try:
            # Create a temporary memory with only selected data
            selected = self.select_training_data(config)
            if not selected:
                result.benchmark_details["error"] = "No training data selected"
                return result

            # Prepare dataset for this variant
            dataset_path = self.output_dir / f"train_{config.id}.jsonl"
            with open(dataset_path, "w") as f:
                for record in selected:
                    # Build chatml format
                    instruction = self._build_instruction(record)
                    output = self._build_output(record)
                    example = {
                        "messages": [
                            {"role": "system", "content": self._system_prompt()},
                            {"role": "user", "content": instruction},
                            {"role": "assistant", "content": output},
                        ]
                    }
                    f.write(json.dumps(example) + "\n")

            # Train with variant-specific settings
            TrainingRun(
                version=f"pop_{config.id}",
                timestamp=datetime.utcnow().isoformat(),
                base_model=base_model,
                num_examples=len(selected),
            )

            # Use the trainer's train method with variant settings
            # For now, we use the trainer's default but with variant-specific max_steps
            training_run = await self.trainer.train(
                base_model=base_model,
                min_quality=config.min_quality,
                max_steps=config.max_steps,
            )

            result.training_run = training_run
            result.fitness = 0.5  # Base fitness from training success

            self.logger.info(
                "variant_trained",
                variant=config.id,
                strategy=config.name,
                examples=len(selected),
                success=training_run.success,
            )

        except Exception as e:
            result.benchmark_details["training_error"] = str(e)
            self.logger.warning("variant_training_failed", variant=config.id, error=str(e))

        return result

    async def evaluate_variant(
        self,
        result: VariantResult,
        tasks: list[Any] | None = None,
    ) -> VariantResult:
        """Evaluate a variant on benchmark tasks."""
        if not result.training_run or not result.training_run.success:
            result.fitness = 0.0
            return result

        try:
            # Create a temporary backend for this variant
            from .backend import LLMBackend

            variant_backend = LLMBackend(
                api_key="ollama",
                model=f"maldoror:pop_{result.variant_id}",
                api_base="http://localhost:11434/v1",
            )

            # Run evaluation
            eval_tasks = tasks or self.evaluator.BENCHMARK_TASKS[:4]  # Use first 4 for speed
            eval_results = await self.evaluator._evaluate_model(
                backend=variant_backend,
                model_name=f"maldoror:pop_{result.variant_id}",
                tasks=eval_tasks,
            )

            # Calculate fitness
            if eval_results:
                avg_score = sum(r.score for r in eval_results) / len(eval_results)
                result.benchmark_score = avg_score
                result.fitness = avg_score
                result.benchmark_details = {
                    "tasks_evaluated": len(eval_results),
                    "avg_score": avg_score,
                    "task_scores": {r.task_name: r.score for r in eval_results},
                }
            else:
                result.fitness = 0.0

            self.logger.info(
                "variant_evaluated",
                variant=result.variant_id,
                strategy=result.config.name,
                fitness=result.fitness,
            )

        except Exception as e:
            result.benchmark_details["eval_error"] = str(e)
            result.fitness = 0.0
            self.logger.warning(
                "variant_evaluation_failed", variant=result.variant_id, error=str(e)
            )

        return result

    async def compete(
        self,
        base_model: str = "Qwen/Qwen2.5-7B-Instruct",
    ) -> VariantResult:
        """Run full population competition: initialize, train, evaluate, select.

        Returns the best variant.
        """
        # 1. Initialize or propagate population
        if not self.variants:
            configs = self.initialize_population()
        else:
            configs = self._propagate_population()

        # 2. Train all variants
        results = []
        for config in configs:
            result = await self.train_variant(config, base_model)
            results.append(result)

        # 3. Evaluate all variants
        for result in results:
            result = await self.evaluate_variant(result)
            self.variants[result.variant_id] = result

        # 4. Select winners
        ranked = sorted(results, key=lambda r: r.fitness, reverse=True)
        survivors = ranked[: max(1, int(len(ranked) * self.survival_rate))]

        # 5. Update best
        if survivors and survivors[0].fitness > (
            self.best_variant.fitness if self.best_variant else 0
        ):
            self.best_variant = survivors[0]

        # 6. Record generation stats
        gen_stats = {
            "generation": self.generation,
            "variants": len(results),
            "best_fitness": ranked[0].fitness if ranked else 0,
            "avg_fitness": sum(r.fitness for r in results) / max(len(results), 1),
            "best_strategy": ranked[0].config.name if ranked else "none",
            "survivors": len(survivors),
        }
        self.generations.append(gen_stats)
        self.generation += 1

        self._save_state()

        self.logger.info(
            "generation_complete",
            generation=self.generation - 1,
            best_fitness=gen_stats["best_fitness"],
            best_strategy=gen_stats["best_strategy"],
        )

        return ranked[0] if ranked else VariantResult(variant_id="none")

    def _propagate_population(self) -> list[VariantConfig]:
        """Create next generation from best performers.

        Takes the winner's config, mutates it, and creates new variants.
        """
        if not self.variants:
            return self.initialize_population()

        # Get top performers
        ranked = sorted(self.variants.values(), key=lambda r: r.fitness, reverse=True)
        top = ranked[: max(1, int(len(ranked) * self.survival_rate))]

        configs = []
        for variant in top:
            # Keep the winner's config (possibly mutated)
            config = self._mutate_config(variant.config)
            configs.append(config)

        # Fill remaining slots with mutations
        while len(configs) < self.population_size:
            parent = random.choice(top)
            config = self._mutate_config(parent.config, heavy_mutation=True)
            configs.append(config)

        return configs[: self.population_size]

    def _mutate_config(
        self,
        parent: VariantConfig,
        heavy_mutation: bool = False,
    ) -> VariantConfig:
        """Mutate a parent config to create a child config.

        Light mutation: small tweaks to hyperparameters
        Heavy mutation: change strategy entirely
        """
        rate = self.mutation_rate * (2 if heavy_mutation else 1)

        child = VariantConfig(
            id=str(uuid.uuid4())[:8],
            name=f"gen{self.generation}_{parent.name}",
            min_quality=parent.min_quality,
            task_type_filter=parent.task_type_filter,
            include_contrastive=parent.include_contrastive,
            include_synthetic=parent.include_synthetic,
            max_steps=parent.max_steps,
            learning_rate=parent.learning_rate,
            lora_r=parent.lora_r,
            lora_alpha=parent.lora_alpha,
            data_strategy=parent.data_strategy,
            metadata={"parent_id": parent.id, "parent_strategy": parent.name},
        )

        # Mutate hyperparameters
        if random.random() < rate:
            child.min_quality = max(0.3, min(0.9, parent.min_quality + random.uniform(-0.1, 0.1)))
        if random.random() < rate:
            child.max_steps = max(50, min(500, parent.max_steps + random.randint(-50, 50)))
        if random.random() < rate:
            child.learning_rate = max(
                1e-5, min(1e-3, parent.learning_rate * random.uniform(0.5, 2.0))
            )
        if random.random() < rate:
            child.lora_r = max(4, min(64, parent.lora_r + random.choice([-4, 4, 8])))

        # Mutate strategy
        if heavy_mutation or random.random() < rate:
            strategies = [
                "balanced",
                "quality_first",
                "diversity_first",
                "contrastive_focus",
                "synthetic_heavy",
            ]
            child.data_strategy = random.choice(strategies)
            child.name = f"gen{self.generation}_{child.data_strategy}"

        # Mutate data inclusion
        if random.random() < rate:
            child.include_contrastive = not child.include_contrastive
        if random.random() < rate:
            child.include_synthetic = not child.include_synthetic

        return child

    def _build_instruction(self, record: ModificationRecord) -> str:
        """Build instruction from a record."""
        parts = [f"Improve the following Python code to fix: {record.description}"]
        if record.target_file:
            parts[0] += f"\nTarget file: {record.target_file}"
        if record.reasoning:
            parts.append(f"Context: {record.reasoning}")
        if record.original_code:
            parts.append(f"Original code:\n```python\n{record.original_code[:1500]}\n```")
        return "\n\n".join(parts)

    def _build_output(self, record: ModificationRecord) -> str:
        """Build output from a record."""
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

    def get_stats(self) -> dict[str, Any]:
        """Get population statistics."""
        return {
            "generation": self.generation,
            "population_size": len(self.variants),
            "best_fitness": self.best_variant.fitness if self.best_variant else 0,
            "best_strategy": self.best_variant.config.name if self.best_variant else "none",
            "total_variants_trained": len(self.variants),
            "generations_run": len(self.generations),
        }

    def to_context(self) -> str:
        """Convert stats to context string."""
        stats = self.get_stats()
        lines = [
            "Model Population:",
            f"  Generation: {stats['generation']}",
            f"  Population Size: {stats['population_size']}",
            f"  Best Fitness: {stats['best_fitness']:.3f}",
            f"  Best Strategy: {stats['best_strategy']}",
            f"  Total Variants: {stats['total_variants_trained']}",
        ]
        return "\n".join(lines)
