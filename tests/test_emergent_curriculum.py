"""Tests for Emergent Curriculum — self-directed training task generation."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.crawler_agent.cognitive.emergent_curriculum import (
    EmergentCurriculum,
    CurriculumTask,
    WeaknessProfile,
)
from src.crawler_agent.cognitive.modification_memory import (
    ModificationMemory,
    ModificationRecord,
)
from src.crawler_agent.cognitive.backend import CognitiveBackend, CognitiveResponse


@pytest.fixture
def tmp_storage(tmp_path):
    """Create a temporary storage directory."""
    return tmp_path / "modification_memory"


@pytest.fixture
def memory(tmp_storage):
    """Create a ModificationMemory with temp storage."""
    mm = ModificationMemory(storage_path=str(tmp_storage))
    for i in range(12):
        mm.record(ModificationRecord(
            id=f"rec-{i}",
            timestamp="2026-01-01T00:00:00",
            source_module="self_modify" if i < 8 else "self_training",
            target_file="orchestrator.py" if i % 2 == 0 else "planner.py",
            task_type="code_rewrite" if i % 3 == 0 else "optimization" if i % 3 == 1 else "bug_fix",
            description=f"Test modification {i}",
            modified_code=f"# Modified code for test {i}\nimport os",
            success=i < 9,  # 9 successful, 3 failed
            quality_score=0.3 + (i * 0.05),  # Some low quality ones
        ))
    return mm


@pytest.fixture
def mock_backend():
    """Create a mock CognitiveBackend."""
    backend = AsyncMock(spec=CognitiveBackend)
    # Mock weakness analysis response
    backend.complete = AsyncMock(return_value=CognitiveResponse(
        content=json.dumps({
            "patterns": ["import ordering", "missing error handling"],
            "recommendation": "Focus on error handling patterns in async code",
        }),
        confidence=0.8,
    ))
    return backend


@pytest.fixture
def curriculum(mock_backend, memory, tmp_path):
    """Create an EmergentCurriculum with temp storage."""
    return EmergentCurriculum(
        backend=mock_backend,
        modification_memory=memory,
        min_quality=0.5,
        max_tasks_per_cycle=3,
    )


class TestWeaknessProfile:
    """Tests for WeaknessProfile."""

    def test_default_profile(self):
        """Test default profile values."""
        profile = WeaknessProfile()
        assert profile.task_type_failure_rates == {}
        assert profile.common_error_patterns == []
        assert profile.low_quality_areas == []
        assert profile.recommendation == ""


class TestCurriculumTask:
    """Tests for CurriculumTask."""

    def test_default_task(self):
        """Test default task values."""
        task = CurriculumTask()
        assert task.id == ""
        assert task.weakness_type == ""
        assert task.quality_score == 0.0


class TestEmergentCurriculum:
    """Tests for the EmergentCurriculum."""

    def test_init(self, curriculum):
        """Test curriculum initialization."""
        assert curriculum.backend is not None
        assert curriculum.memory is not None
        assert curriculum.min_quality == 0.5
        assert curriculum.max_tasks_per_cycle == 3

    @pytest.mark.asyncio
    async def test_analyze_weaknesses(self, curriculum):
        """Test weakness analysis from modification history."""
        profile = await curriculum._analyze_weaknesses()
        # Should return a profile (may be empty if not enough data)
        assert isinstance(profile, WeaknessProfile)

    def test_stats(self, curriculum):
        """Test stats generation."""
        stats = curriculum.get_stats()
        assert "curriculums_generated" in stats
        assert "tasks_created" in stats
        assert "weaknesses_identified" in stats
        assert "tasks_rejected" in stats
        assert stats["curriculums_generated"] == 0

    def test_to_context(self, curriculum):
        """Test context string generation."""
        context = curriculum.to_context()
        assert "Emergent Curriculum" in context
        assert "Curriculums Generated" in context
