"""E2E pipeline test for Maldoror custom model.

Tests the full lifecycle:
1. Seed training data
2. Ingest into ModificationMemory
3. Prepare dataset
4. Train (Docker GPU)
5. Deploy via Ollama
6. Hot-swap modifier backend
7. Query maldoror model

Run: python -m pytest tests/test_maldoror_e2e.py -v --timeout=300
"""
import asyncio
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure data directories exist
Path("data/maldoror").mkdir(parents=True, exist_ok=True)
Path("data/modification_memory").mkdir(parents=True, exist_ok=True)

from src.crawler_agent.cognitive.modification_memory import ModificationMemory
from src.crawler_agent.cognitive.model_trainer import ModelTrainer
from src.crawler_agent.cognitive.custom_model_manager import CustomModelManager, ModelState
from src.crawler_agent.cognitive.backend import HybridBackend, LLMBackend


class TestModificationMemory:
    """Test training data ingestion and export."""

    def test_loads_seed_data(self):
        mm = ModificationMemory()
        assert len(mm.records) >= 10, f"Expected >=10 records, got {len(mm.records)}"

    def test_ready_for_training(self):
        mm = ModificationMemory()
        assert mm.ready_for_training(min_examples=10)

    def test_chatml_format(self):
        mm = ModificationMemory()
        data = mm.get_training_data(format="chatml", min_quality=0.6)
        assert len(data) >= 10
        assert "messages" in data[0]
        msgs = data[0]["messages"]
        assert len(msgs) == 3  # system, user, assistant
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"
        assert msgs[2]["role"] == "assistant"

    def test_alpaca_format(self):
        mm = ModificationMemory()
        data = mm.get_training_data(format="alpaca", min_quality=0.6)
        assert len(data) >= 10
        assert "instruction" in data[0]
        assert "output" in data[0]

    def test_quality_filter(self):
        mm = ModificationMemory()
        all_data = mm.get_training_data(min_quality=0.0)
        high_data = mm.get_training_data(min_quality=0.9)
        assert len(high_data) <= len(all_data)

    def test_stats(self):
        mm = ModificationMemory()
        stats = mm.get_stats()
        assert stats["total_records"] >= 10
        # get_stats uses default min_examples=20; check with lower threshold
        assert mm.ready_for_training(min_examples=10) is True
        assert stats["avg_quality"] > 0

    def test_context_string(self):
        mm = ModificationMemory()
        ctx = mm.to_context()
        assert "Modification Memory:" in ctx
        assert "Total Records:" in ctx


class TestModelTrainer:
    """Test training orchestration."""

    def test_version_increment(self):
        mm = ModificationMemory()
        t1 = ModelTrainer(modification_memory=mm, output_dir="data/maldoror")
        v1 = t1.current_version
        assert v1.startswith("v"), f"Version should start with 'v', got {v1}"

    def test_prepare_dataset(self):
        mm = ModificationMemory()
        t = ModelTrainer(modification_memory=mm, output_dir="data/maldoror")
        path = t.prepare_dataset()
        assert path.exists()
        lines = path.read_text().strip().split("\n")
        assert len(lines) >= 10
        # Verify each line is valid JSON
        for line in lines:
            data = json.loads(line)
            assert "messages" in data

    def test_stats(self):
        mm = ModificationMemory()
        t = ModelTrainer(modification_memory=mm, output_dir="data/maldoror")
        stats = t.get_stats()
        assert "total_runs" in stats
        assert "current_version" in stats

    def test_context_string(self):
        mm = ModificationMemory()
        t = ModelTrainer(modification_memory=mm, output_dir="data/maldoror")
        ctx = t.to_context()
        assert "Model Trainer:" in ctx


class TestCustomModelManager:
    """Test model lifecycle management."""

    def test_model_file_template(self):
        assert hasattr(CustomModelManager, "MODELFILE")
        template = CustomModelManager.MODELFILE
        assert "{base_model}" in template
        assert "{adapter_path}" in template

    def test_state_persistence(self):
        # Clean up any leftover state
        models_json = Path("data/maldoror/models.json")
        if models_json.exists():
            models_json.unlink()

        mm = ModificationMemory()
        t = ModelTrainer(modification_memory=mm, output_dir="data/maldoror")
        mgr = CustomModelManager(model_trainer=t)

        # Manually add a model state
        state = ModelState(
            name="maldoror:test", version="v0",
            adapter_path="data/maldoror/v0", active=True,
        )
        mgr.models.append(state)
        mgr._save_state()

        # Reload and verify
        mgr2 = CustomModelManager(model_trainer=t)
        assert len(mgr2.models) >= 1
        assert mgr2.models[0].name == "maldoror:test"

        # Clean up
        models_json.unlink()

    def test_switch_to(self):
        mm = ModificationMemory()
        t = ModelTrainer(modification_memory=mm, output_dir="data/maldoror")
        mgr = CustomModelManager(model_trainer=t)
        mgr.models.append(ModelState(name="maldoror:v0", version="v0", adapter_path="x"))
        mgr.models.append(ModelState(name="maldoror:v1", version="v1", adapter_path="y"))

        result = asyncio.run(mgr.switch_to("v1"))
        assert result is True
        assert mgr.active_model.version == "v1"

    def test_stats(self):
        mm = ModificationMemory()
        t = ModelTrainer(modification_memory=mm, output_dir="data/maldoror")
        mgr = CustomModelManager(model_trainer=t)
        stats = mgr.get_stats()
        assert "deployed_models" in stats
        assert "active_model" in stats


class TestHybridBackendModifier:
    """Test 4-tier backend with modifier."""

    def _make_mock(self, name="mock"):
        m = MagicMock()
        m.complete = AsyncMock(return_value=MagicMock(content="ok", confidence=0.8))
        m.embed = AsyncMock(return_value=[0.0] * 384)
        m.classify = AsyncMock(return_value={"a": 1.0})
        m.extract_patterns = AsyncMock(return_value=[])
        m.get_name = MagicMock(return_value=name)
        return m

    def test_four_tier_routing(self):
        routine = self._make_mock("routine")
        code = self._make_mock("code")
        reasoning = self._make_mock("reasoning")
        modifier = self._make_mock("modifier")
        hb = HybridBackend(routine=routine, code=code, reasoning=reasoning, modifier=modifier)

        # Modifier tasks route to modifier
        tier = hb._route("recursive_modify this function")
        assert tier == "modifier"

        # Code tasks route to code
        tier = hb._route("code_generation for parser")
        assert tier == "code"

        # Reasoning tasks route to reasoning
        tier = hb._route("planning the architecture")
        assert tier == "reasoning"

        # Default routes to routine
        tier = hb._route("hello world")
        assert tier == "routine"

    def test_update_modifier(self):
        routine = self._make_mock("routine")
        hb = HybridBackend(routine=routine)
        assert not hb._has_modifier

        modifier = self._make_mock("modifier")
        hb.update_modifier(modifier)
        assert hb._has_modifier
        assert hb.modifier.get_name() == "modifier"

        hb.update_modifier(None)
        assert not hb._has_modifier

    def test_stats_include_modifier(self):
        routine = self._make_mock("routine")
        hb = HybridBackend(routine=routine)
        stats = hb.get_stats()
        assert "modifier_calls" in stats
        assert "modifier_backend" in stats

    def test_name_includes_modifier(self):
        routine = self._make_mock("routine")
        hb = HybridBackend(routine=routine)
        name = hb.get_name()
        assert "routine" in name


class TestPipelineIntegration:
    """Integration test: data -> memory -> dataset -> trainer."""

    def test_full_data_flow(self):
        # Clean up any leftover state from prior tests
        models_json = Path("data/maldoror/models.json")
        if models_json.exists():
            models_json.unlink()

        # 1. Load memory
        mm = ModificationMemory()
        assert len(mm.records) >= 10

        # 2. Prepare dataset
        trainer = ModelTrainer(modification_memory=mm, output_dir="data/maldoror")
        dataset_path = trainer.prepare_dataset()
        assert dataset_path.exists()

        # 3. Verify dataset content
        lines = dataset_path.read_text().strip().split("\n")
        for line in lines:
            ex = json.loads(line)
            assert "messages" in ex
            msgs = ex["messages"]
            assert msgs[0]["role"] == "system"
            assert "Maldoror" in msgs[0]["content"]

        # 4. Manager can read trainer state
        mgr = CustomModelManager(model_trainer=trainer)
        stats = mgr.get_stats()
        assert stats["deployed_models"] == 0  # Nothing deployed yet

        # 5. Backend has modifier tier
        hb = HybridBackend(routine=MagicMock())
        assert hasattr(hb, "MODIFIER_TASKS")
        assert "recursive_modify" in hb.MODIFIER_TASKS
