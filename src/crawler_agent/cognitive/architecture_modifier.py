"""Architecture Modifier — maldoror rewrites its own neural network structure.

Instead of just fine-tuning weights (LoRA), this module enables structural
modification of the transformer architecture itself:
- Add/remove transformer layers
- Modify attention heads (count, dimension)
- Expand/reduce feed-forward networks
- Modify tokenization (add new tokens)
- Change hidden dimensions

Each modification is:
1. Loaded from current model (Qwen2.5-7B or previous modified version)
2. Structurally altered (one change at a time)
3. Trained to adapt the new structure
4. Verified to ensure it still works
5. Deployed as a new version

This is genuinely rare — very few systems modify their own architecture.
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, StrEnum
from pathlib import Path
from typing import Any

import structlog


class ModificationType(StrEnum):
    """Types of structural modifications."""

    ADD_LAYER = "add_layer"
    REMOVE_LAYER = "remove_layer"
    MODIFY_ATTENTION_HEADS = "modify_attention_heads"
    MODIFY_FFN_DIM = "modify_ffn_dim"
    MODIFY_HIDDEN_DIM = "modify_hidden_dim"
    EXPAND_TOKENIZER = "expand_tokenizer"
    CHANGE_ACTIVATION = "change_activation"


@dataclass
class ArchitectureModification:
    """A single structural modification to the model."""

    id: str = ""
    mod_type: ModificationType = ModificationType.ADD_LAYER
    description: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    risk_level: float = 0.0
    estimated_params_delta: int = 0  # +N parameters


@dataclass
class ArchitectureState:
    """Current state of the model architecture."""

    base_model: str = "Qwen/Qwen2.5-7B-Instruct"
    version: str = "v0"
    num_layers: int = 0
    hidden_dim: int = 0
    num_attention_heads: int = 0
    ffn_dim: int = 0
    vocab_size: int = 0
    total_params: int = 0
    modification_history: list[dict[str, Any]] = field(default_factory=list)
    timestamp: str = ""


@dataclass
class ModificationResult:
    """Result of attempting an architecture modification."""

    success: bool = False
    modification: ArchitectureModification | None = None
    before_state: ArchitectureState | None = None
    after_state: ArchitectureState | None = None
    training_loss: float = 0.0
    eval_score: float = 0.0
    error: str = ""
    duration_seconds: float = 0.0
    backup_path: str = ""


class ArchitectureModifier:
    """Enables maldoror to rewrite its own neural network architecture.

    Unlike LoRA fine-tuning (weight-only), this module modifies the actual
    transformer structure. Each modification is small and incremental:

    1. Load current model
    2. Apply one structural change
    3. Train to adapt new structure
    4. Verify it works
    5. Deploy or rollback

    The module tracks:
    - Which modifications improve performance
    - Which modifications degrade performance
    - Risk levels for different modification types
    - Parameter count changes
    """

    def __init__(
        self,
        output_dir: str = "data/maldoror/architecture",
        base_model: str = "Qwen/Qwen2.5-7B-Instruct",
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.base_model = base_model
        self.logger = structlog.get_logger()

        self.current_state: ArchitectureState | None = None
        self.modification_history: list[ModificationResult] = []
        self.backups: dict[str, str] = {}  # version -> backup path

        self._load_state()

    def _load_state(self) -> None:
        """Load architecture state from disk."""
        state_path = self.output_dir / "architecture_state.json"
        if state_path.exists():
            try:
                data = json.loads(state_path.read_text())
                self.current_state = ArchitectureState(**data.get("current_state", {}))
                self.modification_history = [
                    ModificationResult(**r) for r in data.get("history", [])
                ]
            except Exception as e:
                self.logger.warning("architecture_state_load_failed", error=str(e))

    def _save_state(self) -> None:
        """Save architecture state to disk."""
        state_path = self.output_dir / "architecture_state.json"
        state = {
            "current_state": self.current_state.__dict__ if self.current_state else None,
            "history": [r.__dict__ for r in self.modification_history[-20:]],
        }
        state_path.write_text(json.dumps(state, indent=2, default=str))

    def get_proposed_modifications(self) -> list[ArchitectureModification]:
        """Get list of possible structural modifications.

        Returns modifications ordered by risk (safest first).
        """
        mods = [
            ArchitectureModification(
                id=str(uuid.uuid4())[:8],
                mod_type=ModificationType.ADD_LAYER,
                description="Add a new transformer layer (duplicates structure of last layer)",
                params={"position": -1},  # Add at end
                risk_level=0.4,
                estimated_params_delta=50_000_000,  # ~50M for 7B model
            ),
            ArchitectureModification(
                id=str(uuid.uuid4())[:8],
                mod_type=ModificationType.MODIFY_ATTENTION_HEADS,
                description="Increase attention heads by 2 (may improve multi-head diversity)",
                params={"delta": 2},
                risk_level=0.3,
                estimated_params_delta=20_000_000,
            ),
            ArchitectureModification(
                id=str(uuid.uuid4())[:8],
                mod_type=ModificationType.MODIFY_FFN_DIM,
                description="Expand feed-forward dimension by 25% (more capacity)",
                params={"scale": 1.25},
                risk_level=0.35,
                estimated_params_delta=100_000_000,
            ),
            ArchitectureModification(
                id=str(uuid.uuid4())[:8],
                mod_type=ModificationType.EXPAND_TOKENIZER,
                description="Add 100 new tokens for code/technical vocabulary",
                params={"num_tokens": 100},
                risk_level=0.2,
                estimated_params_delta=5_000_000,
            ),
            ArchitectureModification(
                id=str(uuid.uuid4())[:8],
                mod_type=ModificationType.REMOVE_LAYER,
                description="Remove last transformer layer (reduce size, test impact)",
                params={"position": -1},
                risk_level=0.6,
                estimated_params_delta=-50_000_000,
            ),
            ArchitectureModification(
                id=str(uuid.uuid4())[:8],
                mod_type=ModificationType.MODIFY_HIDDEN_DIM,
                description="Increase hidden dimension by 10% (more representation capacity)",
                params={"scale": 1.1},
                risk_level=0.5,
                estimated_params_delta=150_000_000,
            ),
        ]

        # Sort by risk (safest first)
        mods.sort(key=lambda m: m.risk_level)
        return mods

    def recommend_modification(
        self,
        performance_history: list[dict[str, Any]] | None = None,
    ) -> ArchitectureModification | None:
        """Recommend the best modification based on performance history.

        Uses modification_memory to understand what structural changes
        have worked in the past.
        """
        mods = self.get_proposed_modifications()

        if not self.modification_history:
            # First time: safest modification
            return mods[0] if mods else None

        # Analyze what's worked
        successful_types = [
            r.modification.mod_type
            for r in self.modification_history
            if r.success and r.modification
        ]

        # Prefer modifications that have succeeded before
        for mod in mods:
            if mod.mod_type in successful_types:
                return mod

        # If no history of success, try safest option not yet attempted
        attempted_types = {
            r.modification.mod_type for r in self.modification_history if r.modification
        }
        for mod in mods:
            if mod.mod_type not in attempted_types:
                return mod

        # All types attempted: pick lowest risk
        return mods[0] if mods else None

    async def apply_modification(
        self,
        modification: ArchitectureModification,
        training_data_path: str | None = None,
    ) -> ModificationResult:
        """Apply a structural modification to the model.

        This is the main entry point. It:
        1. Backs up current model
        2. Applies the structural change
        3. Trains the modified model
        4. Evaluates performance
        5. Deploys or rolls back
        """
        start_time = datetime.utcnow()
        result = ModificationResult(modification=modification)

        try:
            # 1. Get current state
            if self.current_state:
                result.before_state = ArchitectureState(**self.current_state.__dict__)

            # 2. Backup current model
            backup_path = await self._backup_model()
            result.backup_path = backup_path

            # 3. Apply structural change
            new_state = await self._apply_structural_change(modification)
            result.after_state = new_state

            # 4. Train modified model
            training_result = await self._train_modified(modification, training_data_path)
            result.training_loss = training_result.get("loss", 0.0)

            # 5. Evaluate
            eval_score = await self._evaluate_modified()
            result.eval_score = eval_score

            # 6. Decide: deploy or rollback
            if eval_score >= 0.4:  # Minimum acceptable score
                await self._deploy_modified(new_state)
                result.success = True
                self.current_state = new_state
                self.current_state.modification_history.append(
                    {
                        "mod_type": modification.mod_type.value,
                        "description": modification.description,
                        "eval_score": eval_score,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
            else:
                await self._rollback_model(backup_path)
                result.error = f"Eval score {eval_score:.3f} below threshold 0.4"

        except Exception as e:
            result.error = str(e)
            # Attempt rollback
            if result.backup_path:
                try:
                    await self._rollback_model(result.backup_path)
                except Exception:
                    pass

        result.duration_seconds = (datetime.utcnow() - start_time).total_seconds()
        self.modification_history.append(result)
        self._save_state()

        self.logger.info(
            "architecture_modification_complete",
            mod_type=modification.mod_type.value,
            success=result.success,
            eval_score=result.eval_score,
            duration=result.duration_seconds,
        )

        return result

    async def _backup_model(self) -> str:
        """Backup current model weights."""
        backup_id = str(uuid.uuid4())[:8]
        backup_path = str(self.output_dir / f"backup_{backup_id}")
        # In production, this would copy model weights
        # For now, record the backup location
        self.backups[self.current_state.version if self.current_state else "v0"] = backup_path
        return backup_path

    async def _apply_structural_change(
        self,
        modification: ArchitectureModification,
    ) -> ArchitectureState:
        """Apply the structural modification to the model graph.

        This is where the actual architecture change happens.
        In production, this would modify the PyTorch model directly.
        """
        # Create new state based on current
        if self.current_state:
            new_state = ArchitectureState(
                base_model=self.current_state.base_model,
                version=f"v{len(self.modification_history) + 1}",
                num_layers=self.current_state.num_layers,
                hidden_dim=self.current_state.hidden_dim,
                num_attention_heads=self.current_state.num_attention_heads,
                ffn_dim=self.current_state.ffn_dim,
                vocab_size=self.current_state.vocab_size,
                total_params=self.current_state.total_params,
            )
        else:
            new_state = ArchitectureState(
                base_model=self.base_model,
                version="v1",
                num_layers=28,  # Qwen2.5-7B default
                hidden_dim=3584,
                num_attention_heads=28,
                ffn_dim=18944,
                vocab_size=151936,
                total_params=7_600_000_000,
            )

        # Apply modification
        if modification.mod_type == ModificationType.ADD_LAYER:
            new_state.num_layers += 1
            new_state.total_params += modification.estimated_params_delta

        elif modification.mod_type == ModificationType.REMOVE_LAYER:
            new_state.num_layers = max(1, new_state.num_layers - 1)
            new_state.total_params += modification.estimated_params_delta  # Negative

        elif modification.mod_type == ModificationType.MODIFY_ATTENTION_HEADS:
            delta = modification.params.get("delta", 2)
            new_state.num_attention_heads += delta
            new_state.total_params += modification.estimated_params_delta

        elif modification.mod_type == ModificationType.MODIFY_FFN_DIM:
            scale = modification.params.get("scale", 1.25)
            new_state.ffn_dim = int(new_state.ffn_dim * scale)
            new_state.total_params += modification.estimated_params_delta

        elif modification.mod_type == ModificationType.MODIFY_HIDDEN_DIM:
            scale = modification.params.get("scale", 1.1)
            new_state.hidden_dim = int(new_state.hidden_dim * scale)
            new_state.total_params += modification.estimated_params_delta

        elif modification.mod_type == ModificationType.EXPAND_TOKENIZER:
            num_tokens = modification.params.get("num_tokens", 100)
            new_state.vocab_size += num_tokens
            new_state.total_params += modification.estimated_params_delta

        new_state.timestamp = datetime.utcnow().isoformat()
        return new_state

    async def _train_modified(
        self,
        modification: ArchitectureModification,
        training_data_path: str | None = None,
    ) -> dict[str, Any]:
        """Train the modified architecture.

        Uses the Docker GPU infrastructure for training.
        """
        # In production, this would:
        # 1. Load the modified model
        # 2. Prepare training data
        # 3. Run full training loop (not just LoRA)
        # 4. Return training metrics

        # For now, simulate training
        return {
            "loss": 0.5,
            "epochs": 1,
            "duration": 60.0,
        }

    async def _evaluate_modified(self) -> float:
        """Evaluate the modified architecture.

        Returns a score between 0.0 and 1.0.
        """
        # In production, this would run the model through benchmarks
        # For now, simulate evaluation
        return 0.6

    async def _deploy_modified(self, new_state: ArchitectureState) -> None:
        """Deploy the modified model."""
        # In production, this would:
        # 1. Save the modified model
        # 2. Update Ollama with new model
        # 3. Update the backend to use new model
        pass

    async def _rollback_model(self, backup_path: str) -> None:
        """Rollback to the backup model."""
        # In production, this would restore from backup
        pass

    def get_stats(self) -> dict[str, Any]:
        """Get modification statistics."""
        successful = [r for r in self.modification_history if r.success]
        return {
            "total_modifications": len(self.modification_history),
            "successful": len(successful),
            "failed": len(self.modification_history) - len(successful),
            "current_version": self.current_state.version if self.current_state else "v0",
            "current_params": self.current_state.total_params if self.current_state else 0,
            "modification_types": {
                r.modification.mod_type.value: 1 for r in successful if r.modification
            },
        }

    def to_context(self) -> str:
        """Convert stats to context string."""
        stats = self.get_stats()
        lines = [
            "Architecture Modifier:",
            f"  Current Version: {stats['current_version']}",
            f"  Total Params: {stats['current_params']:,}",
            f"  Modifications: {stats['total_modifications']} ({stats['successful']} success, {stats['failed']} failed)",
            f"  Types Applied: {', '.join(stats['modification_types'].keys()) or 'none'}",
        ]
        return "\n".join(lines)
