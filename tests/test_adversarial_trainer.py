"""Tests for Adversarial Trainer — attempt + critique + counter-example generation."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.crawler_agent.cognitive.adversarial_trainer import (
    AdversarialExample,
    AdversarialTrainer,
)
from src.crawler_agent.cognitive.backend import CognitiveBackend, CognitiveResponse
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
    mm = ModificationMemory(storage_path=str(tmp_storage))
    for i in range(10):
        mm.record(
            ModificationRecord(
                id=f"rec-{i}",
                timestamp="2026-01-01T00:00:00",
                source_module="self_modify",
                target_file="orchestrator.py" if i % 2 == 0 else "planner.py",
                task_type="code_rewrite"
                if i % 3 == 0
                else "optimization"
                if i % 3 == 1
                else "bug_fix",
                description=f"Test modification {i}",
                original_code=f"import os\nimport sys\n# Original {i}",
                modified_code=f"# Modified code for test {i}\nimport os\nimport sys",
                success=True,
                quality_score=0.5 + (i * 0.05),
            )
        )
    return mm


@pytest.fixture
def mock_backend():
    """Create a mock CognitiveBackend."""
    backend = AsyncMock(spec=CognitiveBackend)
    # Mock responses for the three phases
    responses = [
        # Phase 1: Generate attempt
        CognitiveResponse(
            content=json.dumps(
                {
                    "code": "# Modified code\nimport os\nimport sys\nimport json",
                    "quality": 0.6,
                    "approach": "Added json import",
                }
            ),
            confidence=0.6,
        ),
        # Phase 2: Critique attempt
        CognitiveResponse(
            content=json.dumps(
                {
                    "critique": "The code adds json import but doesn't use it, creating an unused import.",
                    "flaw_categories": ["unused_import", "code_smell"],
                    "quality": 0.7,
                    "severity": "low",
                }
            ),
            confidence=0.7,
        ),
        # Phase 3: Generate counter-example
        CognitiveResponse(
            content=json.dumps(
                {
                    "code": "# Corrected code\nimport os\nimport sys",
                    "improvements": ["Removed unused json import"],
                }
            ),
            confidence=0.7,
        ),
    ]
    backend.complete = AsyncMock(side_effect=responses)
    return backend


@pytest.fixture
def trainer(mock_backend, memory, tmp_path):
    """Create an AdversarialTrainer with temp storage."""
    return AdversarialTrainer(
        backend=mock_backend,
        modification_memory=memory,
        min_quality=0.5,
        max_examples_per_cycle=2,
    )


class TestAdversarialExample:
    """Tests for AdversarialExample."""

    def test_default_example(self):
        """Test default example values."""
        example = AdversarialExample()
        assert example.id == ""
        assert example.attempt == ""
        assert example.critique == ""
        assert example.counter_example == ""
        assert example.flaw_categories == []
        assert example.quality_score == 0.0


class TestAdversarialTrainer:
    """Tests for the AdversarialTrainer."""

    def test_init(self, trainer):
        """Test trainer initialization."""
        assert trainer.backend is not None
        assert trainer.memory is not None
        assert trainer.min_quality == 0.5
        assert trainer.max_examples_per_cycle == 2

    def test_select_source_records(self, trainer):
        """Test source record selection."""
        records = trainer._select_source_records()
        # Should select some records (moderate quality, successful)
        assert isinstance(records, list)

    def test_stats(self, trainer):
        """Test stats generation."""
        stats = trainer.get_stats()
        assert "total_generated" in stats
        assert "attempts_generated" in stats
        assert "critiques_generated" in stats
        assert "counter_examples_generated" in stats
        assert "tasks_rejected" in stats
        assert "flaw_categories" in stats
        assert stats["total_generated"] == 0

    def test_to_context(self, trainer):
        """Test context string generation."""
        context = trainer.to_context()
        assert "Adversarial Trainer" in context
        assert "Total Generated" in context
