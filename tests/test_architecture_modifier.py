"""Tests for Architecture Modifier — neural network structural modification."""

import json
from pathlib import Path

import pytest

from src.crawler_agent.cognitive.architecture_modifier import (
    ArchitectureModifier,
    ArchitectureModification,
    ArchitectureState,
    ModificationResult,
    ModificationType,
)


@pytest.fixture
def modifier(tmp_path):
    """Create an ArchitectureModifier with temp storage."""
    return ArchitectureModifier(
        output_dir=str(tmp_path / "architecture"),
        base_model="Qwen/Qwen2.5-7B-Instruct",
    )


class TestModificationType:
    """Tests for ModificationType enum."""

    def test_all_types_exist(self):
        """Test that all modification types are defined."""
        assert ModificationType.ADD_LAYER.value == "add_layer"
        assert ModificationType.REMOVE_LAYER.value == "remove_layer"
        assert ModificationType.MODIFY_ATTENTION_HEADS.value == "modify_attention_heads"
        assert ModificationType.MODIFY_FFN_DIM.value == "modify_ffn_dim"
        assert ModificationType.MODIFY_HIDDEN_DIM.value == "modify_hidden_dim"
        assert ModificationType.EXPAND_TOKENIZER.value == "expand_tokenizer"


class TestArchitectureModification:
    """Tests for ArchitectureModification dataclass."""

    def test_default_modification(self):
        """Test default values."""
        mod = ArchitectureModification()
        assert mod.id == ""
        assert mod.mod_type == ModificationType.ADD_LAYER
        assert mod.risk_level == 0.0


class TestArchitectureState:
    """Tests for ArchitectureState dataclass."""

    def test_default_state(self):
        """Test default values."""
        state = ArchitectureState()
        assert state.base_model == "Qwen/Qwen2.5-7B-Instruct"
        assert state.version == "v0"
        assert state.num_layers == 0


class TestArchitectureModifier:
    """Tests for the ArchitectureModifier."""

    def test_init(self, modifier):
        """Test modifier initialization."""
        assert modifier.output_dir.exists()
        assert modifier.base_model == "Qwen/Qwen2.5-7B-Instruct"
        assert modifier.current_state is None

    def test_get_proposed_modifications(self, modifier):
        """Test that modifications are proposed."""
        mods = modifier.get_proposed_modifications()
        assert len(mods) > 0
        # Should be sorted by risk (safest first)
        risks = [m.risk_level for m in mods]
        assert risks == sorted(risks)

    def test_recommendation_first_time(self, modifier):
        """Test recommendation on first use (safest option)."""
        rec = modifier.recommend_modification()
        assert rec is not None
        assert rec.mod_type == ModificationType.EXPAND_TOKENIZER  # Lowest risk

    def test_recommendation_after_success(self, modifier):
        """Test recommendation after successful modification."""
        modifier.modification_history.append(ModificationResult(
            success=True,
            modification=ArchitectureModification(
                mod_type=ModificationType.ADD_LAYER,
            ),
        ))
        rec = modifier.recommend_modification()
        assert rec is not None
        # Should prefer add_layer since it succeeded before
        assert rec.mod_type == ModificationType.ADD_LAYER

    def test_recommendation_after_failure(self, modifier):
        """Test recommendation avoids failed types."""
        modifier.modification_history.append(ModificationResult(
            success=False,
            modification=ArchitectureModification(
                mod_type=ModificationType.ADD_LAYER,
            ),
        ))
        rec = modifier.recommend_modification()
        assert rec is not None
        # Should not recommend add_layer since it failed
        assert rec.mod_type != ModificationType.ADD_LAYER

    @pytest.mark.asyncio
    async def test_apply_structural_change_add_layer(self, modifier):
        """Test adding a layer."""
        modification = ArchitectureModification(
            mod_type=ModificationType.ADD_LAYER,
            params={"position": -1},
            estimated_params_delta=50_000_000,
        )
        new_state = await modifier._apply_structural_change(modification)
        assert new_state.num_layers == 29  # 28 + 1
        assert new_state.total_params == 7_650_000_000

    @pytest.mark.asyncio
    async def test_apply_structural_change_remove_layer(self, modifier):
        """Test removing a layer."""
        modification = ArchitectureModification(
            mod_type=ModificationType.REMOVE_LAYER,
            params={"position": -1},
            estimated_params_delta=-50_000_000,
        )
        new_state = await modifier._apply_structural_change(modification)
        assert new_state.num_layers == 27  # 28 - 1
        assert new_state.total_params == 7_550_000_000

    @pytest.mark.asyncio
    async def test_apply_structural_change_modify_heads(self, modifier):
        """Test modifying attention heads."""
        modification = ArchitectureModification(
            mod_type=ModificationType.MODIFY_ATTENTION_HEADS,
            params={"delta": 4},
            estimated_params_delta=40_000_000,
        )
        new_state = await modifier._apply_structural_change(modification)
        assert new_state.num_attention_heads == 32  # 28 + 4

    @pytest.mark.asyncio
    async def test_apply_structural_change_expand_tokenizer(self, modifier):
        """Test expanding tokenizer."""
        modification = ArchitectureModification(
            mod_type=ModificationType.EXPAND_TOKENIZER,
            params={"num_tokens": 500},
            estimated_params_delta=25_000_000,
        )
        new_state = await modifier._apply_structural_change(modification)
        assert new_state.vocab_size == 152436  # 151936 + 500

    def test_stats(self, modifier):
        """Test stats generation."""
        stats = modifier.get_stats()
        assert "total_modifications" in stats
        assert "successful" in stats
        assert "current_version" in stats
        assert stats["total_modifications"] == 0

    def test_to_context(self, modifier):
        """Test context string generation."""
        context = modifier.to_context()
        assert "Architecture Modifier" in context
        assert "Current Version" in context

    def test_save_and_load_state(self, modifier, tmp_path):
        """Test state persistence."""
        modifier.current_state = ArchitectureState(
            version="v3",
            num_layers=30,
            total_params=8_000_000_000,
        )
        modifier._save_state()

        # Load in a new modifier
        new_modifier = ArchitectureModifier(
            output_dir=str(tmp_path / "architecture"),
        )
        assert new_modifier.current_state.version == "v3"
        assert new_modifier.current_state.num_layers == 30
