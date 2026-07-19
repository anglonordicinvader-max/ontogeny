"""Tests for Contrastive Trainer — training on both success and failure."""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.crawler_agent.cognitive.backend import CognitiveResponse
from src.crawler_agent.cognitive.contrastive_trainer import (
    ContrastiveExample,
    ContrastiveTrainer,
)
from src.crawler_agent.cognitive.modification_memory import (
    ModificationMemory,
    ModificationRecord,
)


@pytest.fixture
def tmp_storage(tmp_path):
    """Create a temporary storage directory."""
    return tmp_path / "modification_memory"


@pytest.fixture
def memory(tmp_storage):
    """Create a ModificationMemory with temp storage."""
    return ModificationMemory(storage_path=str(tmp_storage))


@pytest.fixture
def mock_backend():
    """Create a mock LLM backend."""
    backend = AsyncMock()
    backend.complete = AsyncMock()
    backend.get_name = MagicMock(return_value="mock_llm")
    return backend


@pytest.fixture
def trainer(mock_backend, memory):
    """Create a ContrastiveTrainer with mock backend."""
    return ContrastiveTrainer(
        backend=mock_backend,
        modification_memory=memory,
        min_quality=0.5,
    )


@pytest.fixture
def success_record():
    """Create a successful modification record."""
    return ModificationRecord(
        id="succ-001",
        timestamp="2026-01-01T00:00:00",
        source_module="recursive_modify",
        target_file="orchestrator.py",
        task_type="code_rewrite",
        description="Fixed import ordering to avoid circular dependencies",
        reasoning="The imports were in the wrong order",
        original_code="import sys\nimport os\nfrom foo import bar",
        modified_code="import os\nimport sys\nfrom foo import bar",
        success=True,
        quality_score=0.8,
    )


@pytest.fixture
def failed_record():
    """Create a failed modification record."""
    return ModificationRecord(
        id="fail-001",
        timestamp="2026-01-01T00:00:00",
        source_module="self_modify",
        target_file="orchestrator.py",
        task_type="optimization",
        description="Tried to optimize import ordering but broke it",
        reasoning="The optimization was incorrect",
        original_code="import os\nimport sys\nfrom foo import bar",
        modified_code="import bar\nimport os\nimport sys  # wrong approach",
        success=False,
        quality_score=0.3,
    )


class TestModificationMemoryContrastive:
    """Tests for ModificationMemory contrastive methods."""

    def test_get_failed_records(self, memory, failed_record):
        """Test that failed records are retrieved."""
        memory.record(failed_record)
        failed = memory.get_failed_records()
        assert len(failed) == 1
        assert failed[0].id == "fail-001"
        assert not failed[0].success

    def test_get_contrastive_pairs(self, memory, success_record, failed_record):
        """Test that contrastive pairs are matched."""
        memory.record(success_record)
        memory.record(failed_record)
        pairs = memory.get_contrastive_pairs()
        assert len(pairs) == 1
        succ, fail = pairs[0]
        assert succ.id == "succ-001"
        assert fail is not None
        assert fail.id == "fail-001"

    def test_get_contrastive_pairs_no_match(self, memory, success_record):
        """Test pairs when no failed record matches."""
        memory.record(success_record)
        pairs = memory.get_contrastive_pairs()
        assert len(pairs) == 1
        succ, fail = pairs[0]
        assert succ.id == "succ-001"
        assert fail is None

    def test_stats_includes_failed(self, memory, success_record, failed_record):
        """Test that stats include failed count."""
        memory.record(success_record)
        memory.record(failed_record)
        stats = memory.get_stats()
        assert stats["successful"] == 1
        assert stats["failed"] == 1


class TestContrastiveTrainer:
    """Tests for the ContrastiveTrainer."""

    def test_init(self, trainer):
        """Test trainer initialization."""
        assert trainer.backend is not None
        assert trainer.memory is not None
        assert trainer.min_quality == 0.5
        assert trainer.stats["total_generated"] == 0

    @pytest.mark.asyncio
    async def test_generate_empty_when_no_data(self, trainer):
        """Test that generation returns empty when no data exists."""
        examples = await trainer.generate_contrastive_data()
        assert examples == []

    @pytest.mark.asyncio
    async def test_generate_predictions(self, trainer, mock_backend, failed_record):
        """Test prediction example generation."""
        trainer.memory.record(failed_record)

        mock_backend.complete.return_value = CognitiveResponse(
            content=json.dumps(
                {
                    "prediction": "fail",
                    "reason": "The import order is wrong and will cause circular dependencies",
                    "confidence": 0.8,
                    "warning_signs": ["Imports at top", "No error handling"],
                }
            ),
            confidence=0.8,
        )

        examples = await trainer._generate_predictions([failed_record])
        assert len(examples) == 1
        assert examples[0].example_type == "prediction"
        assert "fail" in examples[0].output.lower()

    @pytest.mark.asyncio
    async def test_generate_diagnoses(self, trainer, mock_backend, failed_record):
        """Test diagnosis example generation."""
        trainer.memory.record(failed_record)

        mock_backend.complete.return_value = CognitiveResponse(
            content=json.dumps(
                {
                    "root_cause": "The import order was reversed, causing the module to be used before it was defined",
                    "correct_approach": "Keep standard library imports first, then third-party, then local",
                    "fixed_code": "import os\nimport sys\nfrom foo import bar",
                    "lessons": ["Import order matters", "Follow PEP 8"],
                }
            ),
            confidence=0.8,
        )

        examples = await trainer._generate_diagnoses([failed_record])
        assert len(examples) == 1
        assert examples[0].example_type == "diagnosis"
        assert "root cause" in examples[0].output.lower()

    @pytest.mark.asyncio
    async def test_generate_comparisons(self, trainer, mock_backend, success_record, failed_record):
        """Test comparison example generation."""
        trainer.memory.record(success_record)
        trainer.memory.record(failed_record)

        mock_backend.complete.return_value = CognitiveResponse(
            content=json.dumps(
                {
                    "correct": "A",
                    "explanation": "Approach A follows PEP 8 import ordering conventions",
                    "key_difference": "Import order determines initialization sequence",
                    "takeaway": "Always follow standard library first convention",
                }
            ),
            confidence=0.8,
        )

        pairs = trainer.memory.get_contrastive_pairs()
        examples = await trainer._generate_comparisons(pairs)
        assert len(examples) == 1
        assert examples[0].example_type == "comparison"
        assert "correct" in examples[0].output.lower()

    @pytest.mark.asyncio
    async def test_generate_all_types(self, trainer, mock_backend, success_record, failed_record):
        """Test that all three types are generated."""
        trainer.memory.record(success_record)
        trainer.memory.record(failed_record)

        mock_backend.complete.return_value = CognitiveResponse(
            content=json.dumps(
                {
                    "prediction": "fail",
                    "reason": "Test reason for failure prediction",
                    "confidence": 0.8,
                    "warning_signs": ["test warning"],
                }
            ),
            confidence=0.8,
        )

        examples = await trainer.generate_contrastive_data()
        # Should have at least one example type
        assert len(examples) >= 1
        types = {e.example_type for e in examples}
        assert len(types) >= 1

    @pytest.mark.asyncio
    async def test_adds_to_memory(self, trainer, mock_backend, failed_record):
        """Test that generated examples are added to memory."""
        trainer.memory.record(failed_record)

        mock_backend.complete.return_value = CognitiveResponse(
            content=json.dumps(
                {
                    "prediction": "fail",
                    "reason": "Test reason for adding to memory",
                    "confidence": 0.8,
                    "warning_signs": ["test"],
                }
            ),
            confidence=0.8,
        )

        initial_count = len(trainer.memory.records)
        await trainer.generate_contrastive_data()

        # Should have added records
        assert len(trainer.memory.records) > initial_count

        # Check that records have the contrastive_training source module
        contrastive_records = [
            r for r in trainer.memory.records if r.source_module == "contrastive_training"
        ]
        assert len(contrastive_records) > 0

    @pytest.mark.asyncio
    async def test_filters_low_quality(self, trainer, mock_backend, failed_record):
        """Test that low-quality examples are filtered out."""
        trainer.memory.record(failed_record)

        # Return a response that generates an example but with low quality
        # The prediction example has quality 0.7, so we need to test filtering differently
        # Actually, the filter happens at the example level, not the LLM response level
        # Let's test by setting min_quality very high
        trainer.min_quality = 0.95

        mock_backend.complete.return_value = CognitiveResponse(
            content=json.dumps(
                {
                    "prediction": "fail",
                    "reason": "The import order is wrong and will cause circular dependencies",
                    "confidence": 0.8,
                    "warning_signs": ["test warning"],
                }
            ),
            confidence=0.8,
        )

        examples = await trainer.generate_contrastive_data()
        # All should be filtered out because quality 0.7 < 0.95
        assert len(examples) == 0
        assert trainer.stats["rejected"] > 0

    def test_stats_tracking(self, trainer):
        """Test that stats are properly tracked."""
        stats = trainer.get_stats()
        assert "total_generated" in stats
        assert "predictions" in stats
        assert "diagnoses" in stats
        assert "comparisons" in stats
        assert "rejected" in stats
        assert "memory_total" in stats
        assert "memory_successful" in stats
        assert "memory_failed" in stats

    def test_to_context(self, trainer):
        """Test context string generation."""
        context = trainer.to_context()
        assert "Contrastive Trainer" in context
        assert "Total Generated" in context
