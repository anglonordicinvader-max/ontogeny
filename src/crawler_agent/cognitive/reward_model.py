"""Reward model for predicting patch quality before application."""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .backend import CognitiveBackend, CognitiveResponse


@dataclass
class PatchFeatures:
    """Features extracted from a patch for reward prediction."""
    lines_added: int
    lines_removed: int
    files_changed: int
    complexity_delta: float  # cyclomatic complexity change
    has_tests: bool
    has_docstrings: bool
    uses_existing_apis: bool
    introduces_new_deps: bool
    modifies_core_module: bool
    test_coverage_estimate: float
    semantic_similarity: float  # to existing code patterns


@dataclass
class RewardPrediction:
    """Predicted quality of a patch."""
    score: float  # 0-1
    confidence: float  # 0-1
    breakdown: dict[str, float]
    risks: list[str]
    reasoning: str


class RewardModel:
    """Predicts patch quality using LLM + learned features."""

    def __init__(
        self,
        backend: CognitiveBackend,
        model_path: str = "data/reward_model",
    ):
        self.backend = backend
        self.model_path = Path(model_path)
        self.model_path.mkdir(parents=True, exist_ok=True)

        # Training data for online learning
        self.training_data: list[dict[str, Any]] = []
        self._load_training_data()

    def _load_training_data(self) -> None:
        train_file = self.model_path / "training_data.jsonl"
        if train_file.exists():
            for line in train_file.read_text().strip().split("\n"):
                if line:
                    try:
                        self.training_data.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

    def _save_training_example(self, features: PatchFeatures, actual_quality: float) -> None:
        train_file = self.model_path / "training_data.jsonl"
        example = {
            "features": features.__dict__,
            "quality": actual_quality,
            "timestamp": time.time(),
        }
        train_file.write_text(
            train_file.read_text() + json.dumps(example) + "\n" if train_file.exists() else json.dumps(example) + "\n"
        )

    def extract_features(
        self,
        original_code: str,
        patched_code: str,
        file_path: str,
    ) -> PatchFeatures:
        """Extract features from a patch."""
        import difflib

        orig_lines = original_code.split("\n")
        patch_lines = patched_code.split("\n")
        diff = list(difflib.unified_diff(orig_lines, patch_lines, lineterm=""))

        lines_added = sum(1 for d in diff if d.startswith("+") and not d.startswith("+++"))
        lines_removed = sum(1 for d in diff if d.startswith("-") and not d.startswith("---"))

        # Simple complexity estimate
        orig_complexity = self._estimate_complexity(original_code)
        patch_complexity = self._estimate_complexity(patched_code)

        return PatchFeatures(
            lines_added=lines_added,
            lines_removed=lines_removed,
            files_changed=1,
            complexity_delta=patch_complexity - orig_complexity,
            has_tests="test" in patched_code.lower() or "assert" in patched_code,
            has_docstrings='"""' in patched_code or "'''" in patched_code,
            uses_existing_apis=self._check_existing_apis(patched_code),
            introduces_new_deps=self._check_new_imports(original_code, patched_code),
            modifies_core_module="cognitive" in file_path or "orchestrator" in file_path,
            test_coverage_estimate=0.0,
            semantic_similarity=0.0,
        )

    def _estimate_complexity(self, code: str) -> float:
        """Rough cyclomatic complexity."""
        import ast
        try:
            tree = ast.parse(code)
            complexity = 1
            for node in ast.walk(tree):
                if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                    complexity += 1
                elif isinstance(node, ast.BoolOp):
                    complexity += len(node.values) - 1
            return float(complexity)
        except Exception:
            return 1.0

    def _check_existing_apis(self, code: str) -> bool:
        """Check if code uses existing project APIs."""
        project_apis = ["self.memory", "self.backend", "self.crawlers", "self.goals"]
        return any(api in code for api in project_apis)

    def _check_new_imports(self, original: str, patched: str) -> bool:
        """Check if patch adds new imports."""
        import re
        orig_imports = set(re.findall(r"^(?:from|import)\s+(\S+)", original, re.MULTILINE))
        patch_imports = set(re.findall(r"^(?:from|import)\s+(\S+)", patched, re.MULTILINE))
        return len(patch_imports - orig_imports) > 0

    async def predict(
        self,
        original_code: str,
        patched_code: str,
        file_path: str,
        issue_description: str = "",
    ) -> RewardPrediction:
        """Predict patch quality."""
        features = self.extract_features(original_code, patched_code, file_path)

        # LLM-based evaluation
        prompt = f"""Evaluate this code patch quality.

File: {file_path}
Issue: {issue_description}

Original:
```python
{original_code[-2000:]}
```

Patched:
```python
{patched_code[-2000:]}
```

Assess:
1. Correctness - fixes the issue?
2. Safety - no regressions?
3. Style - follows project patterns?
4. Completeness - handles edge cases?
5. Minimalism - smallest necessary change?

Return JSON:
{{
  "score": 0.0-1.0,
  "confidence": 0.0-1.0,
  "breakdown": {{"correctness": 0.8, "safety": 0.9, "style": 0.7, "completeness": 0.6, "minimalism": 0.8}},
  "risks": ["risk1", "risk2"],
  "reasoning": "explanation"
}}"""

        response = await self.backend.complete(prompt, temperature=0.1, max_tokens=1500)

        try:
            data = json.loads(response.content)
            return RewardPrediction(
                score=data.get("score", 0.5),
                confidence=data.get("confidence", 0.5),
                breakdown=data.get("breakdown", {}),
                risks=data.get("risks", []),
                reasoning=data.get("reasoning", ""),
            )
        except json.JSONDecodeError:
            return RewardPrediction(
                score=0.5,
                confidence=0.1,
                breakdown={},
                risks=["parse_error"],
                reasoning="Failed to parse reward prediction",
            )

    def record_outcome(
        self,
        features: PatchFeatures,
        actual_quality: float,
    ) -> None:
        """Record actual outcome for training."""
        self.training_data.append({
            "features": features.__dict__,
            "quality": actual_quality,
            "timestamp": time.time(),
        })
        self._save_training_example(features, actual_quality)

    def get_stats(self) -> dict[str, Any]:
        return {
            "training_examples": len(self.training_data),
            "model_path": str(self.model_path),
        }


class PatchRanker:
    """Ranks multiple patch candidates using reward model."""

    def __init__(self, reward_model: RewardModel):
        self.reward_model = reward_model

    async def rank_patches(
        self,
        original_code: str,
        patches: list[tuple[str, str]],  # (patched_code, description)
        file_path: str,
        issue: str = "",
    ) -> list[tuple[RewardPrediction, str]]:
        """Rank patches by predicted quality."""
        results = []
        for patched_code, desc in patches:
            pred = await self.reward_model.predict(
                original_code, patched_code, file_path, issue
            )
            results.append((pred, desc))

        # Sort by score descending
        results.sort(key=lambda x: x[0].score, reverse=True)
        return results

    async def select_best(
        self,
        original_code: str,
        patches: list[tuple[str, str]],
        file_path: str,
        issue: str = "",
        min_score: float = 0.6,
    ) -> tuple[str, RewardPrediction] | None:
        """Select best patch above threshold."""
        ranked = await self.rank_patches(original_code, patches, file_path, issue)
        if ranked and ranked[0][0].score >= min_score:
            return ranked[0]
        return None