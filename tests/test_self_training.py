"""Tests for Self-Training Synthesizer — the self-training loop."""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.crawler_agent.cognitive.self_training import (
    SelfTrainingSynthesizer,
    SynthesizedExample,
)
from src.crawler_agent.cognitive.modification_memory import (
    ModificationMemory,
    ModificationRecord,
)
from src.crawler_agent.cognitive.backend import CognitiveResponse


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
def synthesizer(mock_backend, memory):
    """Create a SelfTrainingSynthesizer with mock backend."""
    return SelfTrainingSynthesizer(
        backend=mock_backend,
        modification_memory=memory,
        max_variations=2,
        min_quality=0.5,
    )


@pytest.fixture
def success_record():
    """Create a successful modification record for testing."""
    return ModificationRecord(
        id="test-mod-001",
        timestamp="2026-01-01T00:00:00",
        source_module="recursive_modify",
        target_file="orchestrator.py",
        task_type="code_rewrite",
        description="Fixed import ordering to avoid circular dependencies",
        reasoning="The imports were in the wrong order causing circular import errors",
        original_code="import sys\nimport os\nfrom foo import bar",
        modified_code="import os\nimport sys\nfrom foo import bar",
        diff="- import sys\n- import os\n+ import os\n+ import sys",
        success=True,
        quality_score=0.8,
    )


@pytest.fixture
def failed_record():
    """Create a failed modification record for testing."""
    return ModificationRecord(
        id="test-mod-002",
        timestamp="2026-01-01T00:00:00",
        source_module="self_modify",
        target_file="planner.py",
        task_type="optimization",
        description="Tried to optimize planning but broke it",
        success=False,
        quality_score=0.3,
    )


class TestSelfTrainingSynthesizer:
    """Tests for the SelfTrainingSynthesizer."""

    def test_init(self, synthesizer):
        """Test synthesizer initialization."""
        assert synthesizer.backend is not None
        assert synthesizer.memory is not None
        assert synthesizer.max_variations == 2
        assert synthesizer.min_quality == 0.5
        assert synthesizer.stats["total_synthesized"] == 0

    @pytest.mark.asyncio
    async def test_synthesize_from_success_returns_empty_for_failed_record(
        self, synthesizer, failed_record
    ):
        """Test that synthesis returns empty for failed records."""
        result = await synthesizer.synthesize_from_success(failed_record)
        assert result == []

    @pytest.mark.asyncio
    async def test_synthesize_from_success_generates_examples(
        self, synthesizer, mock_backend, success_record
    ):
        """Test that synthesis generates training examples from successful records."""
        # Mock LLM responses for each synthesis step
        mock_backend.complete.side_effect = [
            # Variations response
            CognitiveResponse(
                content=json.dumps({
                    "variations": [
                        {
                            "approach": "Use absolute imports",
                            "code": "import os\nimport sys\nfrom foo import bar\nimport pathlib",
                            "quality": 0.7,
                        },
                        {
                            "approach": "Use __all__ to control exports",
                            "code": "import os\nimport sys\nfrom foo import bar\n__all__ = ['bar']",
                            "quality": 0.65,
                        },
                    ]
                }),
                confidence=0.8,
            ),
            # Inverse response
            CognitiveResponse(
                content=json.dumps({
                    "mistake": "Importing before defining module",
                    "bad_code": "from mymodule import something\nimport mymodule",
                    "why_wrong": "Circular import because mymodule tries to import itself",
                }),
                confidence=0.7,
            ),
            # Reasoning chain response
            CognitiveResponse(
                content=json.dumps({
                    "chain": [
                        "Python imports execute top-to-bottom",
                        "Standard library imports should come first",
                        "Third-party imports come next",
                        "Local imports come last",
                    ],
                    "key_insight": "Import ordering follows a convention that prevents circular dependencies",
                }),
                confidence=0.75,
            ),
            # Generalization response
            CognitiveResponse(
                content=json.dumps({
                    "pattern_name": "Import Ordering",
                    "description": "Fix import ordering to prevent circular dependencies",
                    "template": "import stdlib\nimport third_party\nimport local",
                    "applicable_when": ["circular import errors", "import ordering issues"],
                }),
                confidence=0.7,
            ),
        ]

        examples = await synthesizer.synthesize_from_success(success_record)

        # Should have generated examples
        assert len(examples) >= 2  # At least some examples

        # Check that examples are SynthesizedExample instances
        for ex in examples:
            assert isinstance(ex, SynthesizedExample)
            assert ex.source_record_id == success_record.id
            assert ex.quality_score >= synthesizer.min_quality

    @pytest.mark.asyncio
    async def test_synthesize_adds_to_memory(
        self, synthesizer, mock_backend, success_record
    ):
        """Test that synthesized examples are added to modification memory."""
        mock_backend.complete.side_effect = [
            CognitiveResponse(
                content=json.dumps({"variations": []}),
                confidence=0.8,
            ),
            CognitiveResponse(
                content=json.dumps({
                    "mistake": "test mistake",
                    "bad_code": "x = 1\ny = 2",
                    "why_wrong": "test reason",
                }),
                confidence=0.7,
            ),
            CognitiveResponse(
                content=json.dumps({
                    "chain": ["step 1", "step 2"],
                    "key_insight": "test insight",
                }),
                confidence=0.75,
            ),
            CognitiveResponse(
                content=json.dumps({
                    "pattern_name": "Test Pattern",
                    "description": "test description",
                    "template": "test template code here",
                    "applicable_when": ["test condition"],
                }),
                confidence=0.7,
            ),
        ]

        initial_count = len(synthesizer.memory.records)
        await synthesizer.synthesize_from_success(success_record)

        # Should have added records to memory
        assert len(synthesizer.memory.records) > initial_count

        # Check that records have the self_training source module
        synth_records = [r for r in synthesizer.memory.records if r.source_module == "self_training"]
        assert len(synth_records) > 0

    @pytest.mark.asyncio
    async def test_synthesize_filters_low_quality(
        self, synthesizer, mock_backend, success_record
    ):
        """Test that low-quality examples are filtered out."""
        mock_backend.complete.side_effect = [
            CognitiveResponse(
                content=json.dumps({
                    "variations": [
                        {"approach": "bad", "code": "x = 1  # bad quality code here", "quality": 0.1},  # Too low
                    ]
                }),
                confidence=0.8,
            ),
            CognitiveResponse(
                content=json.dumps({}),  # Empty response
                confidence=0.5,
            ),
            CognitiveResponse(
                content=json.dumps({}),  # Empty response
                confidence=0.5,
            ),
            CognitiveResponse(
                content=json.dumps({}),  # Empty response
                confidence=0.5,
            ),
        ]

        examples = await synthesizer.synthesize_from_success(success_record)

        # All examples should be filtered out due to low quality
        assert len(examples) == 0
        assert synthesizer.stats["rejected"] > 0

    def test_stats_tracking(self, synthesizer):
        """Test that stats are properly tracked."""
        stats = synthesizer.get_stats()
        assert "total_synthesized" in stats
        assert "variations" in stats
        assert "inverses" in stats
        assert "reasoning_chains" in stats
        assert "generalizations" in stats
        assert "rejected" in stats
        assert "memory_total" in stats
        assert "memory_successful" in stats

    def test_to_context(self, synthesizer):
        """Test context string generation."""
        context = synthesizer.to_context()
        assert "Self-Training Synthesizer" in context
        assert "Total Synthesized" in context

    def test_is_substantially_different(self, synthesizer):
        """Test code difference detection."""
        code_a = "import os\nimport sys"
        code_b = "import os\nimport sys"
        assert not synthesizer._is_substantially_different(code_a, code_b)

        code_c = "import os\nimport sys\nimport pathlib"
        assert synthesizer._is_substantially_different(code_a, code_c)

    def test_build_variation_instruction(self, synthesizer, success_record):
        """Test variation instruction building."""
        instruction = synthesizer._build_variation_instruction(
            success_record, "Use absolute imports"
        )
        assert "orchestrator.py" in instruction
        assert "Use absolute imports" in instruction
        assert "Fixed import ordering" in instruction
