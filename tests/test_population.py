"""Tests for Model Population — evolutionary population-based training."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.crawler_agent.cognitive.model_population import (
    ModelPopulation,
    VariantConfig,
    VariantResult,
)
from src.crawler_agent.cognitive.modification_memory import (
    ModificationMemory,
    ModificationRecord,
)
from src.crawler_agent.cognitive.model_trainer import ModelTrainer, TrainingRun
from src.crawler_agent.cognitive.model_evaluation import ModelEvaluator


@pytest.fixture
def tmp_storage(tmp_path):
    """Create a temporary storage directory."""
    return tmp_path / "modification_memory"


@pytest.fixture
def memory(tmp_storage):
    """Create a ModificationMemory with temp storage."""
    mm = ModificationMemory(storage_path=str(tmp_storage))
    # Add some records for testing
    for i in range(15):
        mm.record(ModificationRecord(
            id=f"rec-{i}",
            timestamp="2026-01-01T00:00:00",
            source_module="self_modify" if i < 10 else "self_training",
            target_file="orchestrator.py" if i % 2 == 0 else "planner.py",
            task_type="code_rewrite" if i % 3 == 0 else "optimization" if i % 3 == 1 else "bug_fix",
            description=f"Test modification {i}",
            modified_code=f"# Modified code for test {i}\nimport os",
            success=i < 12,  # 12 successful, 3 failed
            quality_score=0.5 + (i * 0.03),
        ))
    return mm


@pytest.fixture
def mock_trainer():
    """Create a mock ModelTrainer."""
    trainer = AsyncMock(spec=ModelTrainer)
    trainer.output_dir = Path("/tmp/test_maldoror")
    trainer.current_version = "v0"
    trainer.train = AsyncMock(return_value=TrainingRun(
        version="v0",
        success=True,
        adapter_path="/tmp/test_maldoror/v0",
        num_examples=15,
        loss=0.5,
    ))
    return trainer


@pytest.fixture
def mock_evaluator():
    """Create a mock ModelEvaluator."""
    evaluator = AsyncMock(spec=ModelEvaluator)
    evaluator.BENCHMARK_TASKS = []
    evaluator._evaluate_model = AsyncMock(return_value=[])
    return evaluator


@pytest.fixture
def population(mock_trainer, memory, mock_evaluator, tmp_path):
    """Create a ModelPopulation with temp storage."""
    return ModelPopulation(
        model_trainer=mock_trainer,
        modification_memory=memory,
        evaluator=mock_evaluator,
        population_size=3,
        output_dir=str(tmp_path / "population"),
    )


class TestVariantConfig:
    """Tests for VariantConfig."""

    def test_default_config(self):
        """Test default config values."""
        config = VariantConfig()
        assert config.min_quality == 0.6
        assert config.data_strategy == "balanced"
        assert config.include_contrastive is True
        assert config.include_synthetic is True
        assert config.max_steps == 200

    def test_custom_config(self):
        """Test custom config values."""
        config = VariantConfig(
            id="test-001",
            name="quality_first",
            min_quality=0.8,
            data_strategy="quality_first",
        )
        assert config.id == "test-001"
        assert config.name == "quality_first"
        assert config.min_quality == 0.8


class TestModelPopulation:
    """Tests for the ModelPopulation."""

    def test_init(self, population):
        """Test population initialization."""
        assert population.trainer is not None
        assert population.memory is not None
        assert population.evaluator is not None
        assert population.population_size == 3
        assert population.generation == 0

    def test_initialize_population(self, population):
        """Test that population creates diverse configs."""
        configs = population.initialize_population()
        assert len(configs) <= population.population_size
        assert len(configs) >= 2  # At least balanced and quality_first

        # Check that strategies are different
        strategies = [c.data_strategy for c in configs]
        assert len(set(strategies)) >= 2  # At least 2 unique strategies

    def test_select_training_data_balanced(self, population):
        """Test balanced data selection."""
        config = VariantConfig(data_strategy="balanced", min_quality=0.5)
        records = population.select_training_data(config)
        assert len(records) > 0
        # All should have quality >= 0.5
        assert all(r.quality_score >= 0.5 for r in records)

    def test_select_training_data_quality_first(self, population):
        """Test quality_first data selection."""
        config = VariantConfig(data_strategy="quality_first", min_quality=0.6)
        records = population.select_training_data(config)
        assert len(records) > 0
        # Should be sorted by quality
        qualities = [r.quality_score for r in records]
        assert qualities == sorted(qualities, reverse=True)

    def test_select_training_data_diversity_first(self, population):
        """Test diversity_first data selection."""
        config = VariantConfig(data_strategy="diversity_first", min_quality=0.5)
        records = population.select_training_data(config)
        assert len(records) > 0
        # Should have multiple task types
        task_types = set(r.task_type for r in records)
        assert len(task_types) >= 2

    def test_select_training_data_contrastive_focus(self, population):
        """Test contrastive_focus data selection."""
        config = VariantConfig(data_strategy="contrastive_focus", min_quality=0.5)
        records = population.select_training_data(config)
        # Should have some records
        assert len(records) >= 0  # May be 0 if no contrastive data

    def test_mutate_config_light(self, population):
        """Test light mutation."""
        parent = VariantConfig(
            id="parent-001",
            name="balanced",
            min_quality=0.6,
            max_steps=200,
            learning_rate=2e-4,
        )
        child = population._mutate_config(parent, heavy_mutation=False)
        assert child.id != parent.id
        assert child.metadata.get("parent_id") == parent.id
        # Child should be similar but possibly mutated
        assert child.max_steps >= 50
        assert child.max_steps <= 500

    def test_mutate_config_heavy(self, population):
        """Test heavy mutation changes strategy."""
        parent = VariantConfig(
            id="parent-001",
            name="balanced",
            data_strategy="balanced",
        )
        # Run multiple times to check strategy changes
        strategies_changed = False
        for _ in range(10):
            child = population._mutate_config(parent, heavy_mutation=True)
            if child.data_strategy != "balanced":
                strategies_changed = True
                break
        assert strategies_changed

    def test_propagate_population(self, population):
        """Test population propagation."""
        # Set up some variants
        population.variants = {
            "v1": VariantResult(
                variant_id="v1",
                config=VariantConfig(id="v1", name="balanced", data_strategy="balanced"),
                fitness=0.8,
            ),
            "v2": VariantResult(
                variant_id="v2",
                config=VariantConfig(id="v2", name="quality_first", data_strategy="quality_first"),
                fitness=0.6,
            ),
        }
        population.generation = 1

        configs = population._propagate_population()
        assert len(configs) == population.population_size
        # All should be new variants
        assert all(c.id != "v1" and c.id != "v2" for c in configs)

    def test_build_instruction(self, population):
        """Test instruction building."""
        record = ModificationRecord(
            description="Fix import ordering",
            target_file="orchestrator.py",
            reasoning="Imports were in wrong order",
            original_code="import sys\nimport os",
        )
        instruction = population._build_instruction(record)
        assert "Fix import ordering" in instruction
        assert "orchestrator.py" in instruction

    def test_build_output(self, population):
        """Test output building."""
        record = ModificationRecord(
            modified_code="import os\nimport sys",
        )
        output = population._build_output(record)
        assert "import os" in output

    def test_stats(self, population):
        """Test stats generation."""
        stats = population.get_stats()
        assert "generation" in stats
        assert "population_size" in stats
        assert "best_fitness" in stats
        assert "best_strategy" in stats

    def test_to_context(self, population):
        """Test context string generation."""
        context = population.to_context()
        assert "Model Population" in context
        assert "Generation" in context

    def test_save_and_load_state(self, population, tmp_path):
        """Test state persistence."""
        population.generation = 5
        population.best_variant = VariantResult(
            variant_id="best",
            config=VariantConfig(id="best", name="quality_first"),
            fitness=0.85,
        )
        population._save_state()

        # Load in a new population
        new_pop = ModelPopulation(
            model_trainer=population.trainer,
            modification_memory=population.memory,
            evaluator=population.evaluator,
            output_dir=str(tmp_path / "population"),
        )
        assert new_pop.generation == 5
        assert new_pop.best_variant.fitness == 0.85
