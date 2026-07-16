"""Maldoror custom model lifecycle management."""
import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog

from .model_trainer import ModelTrainer, TrainingRun


@dataclass
class ModelState:
    name: str
    version: str
    adapter_path: str
    active: bool = False
    benchmark_score: float = 0.0
    timestamp: float = 0.0


class CustomModelManager:
    """Manages the Maldoror model lifecycle: train, deploy via Ollama, switch, A/B test."""

    MODELFILE = """FROM {base_model}
ADAPTER {adapter_path}
PARAMETER temperature 0.3
PARAMETER top_p 0.9
SYSTEM You are Maldoror, a specialized AI for recursive self-modification of cognitive agents. You analyze code, identify improvements, and generate precise modifications. Maintain backward compatibility and prioritize safety.
TEMPLATE {template}
"""

    TEMPLATE_QWEN = """{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}<|im_start|>user
{{ .Prompt }}<|im_end|>
<|im_start|>assistant
"""

    def __init__(self, model_trainer: ModelTrainer, ollama_host: str = "http://localhost:11434"):
        self.trainer = model_trainer
        self.ollama_host = ollama_host
        self.logger = structlog.get_logger()
        self.models: list[ModelState] = []
        self.active_model: ModelState | None = None
        self._load_state()

    def _state_path(self) -> Path:
        return self.trainer.output_dir / "models.json"

    def _load_state(self) -> None:
        path = self._state_path()
        if path.exists():
            try:
                data = json.loads(path.read_text())
                self.models = [ModelState(**m) for m in data.get("models", [])]
                for m in self.models:
                    if m.active:
                        self.active_model = m
            except Exception as e:
                self.logger.warning("state_load_failed", error=str(e))

    def _save_state(self) -> None:
        self._state_path().write_text(json.dumps(
            {"models": [m.__dict__ for m in self.models]}, indent=2, default=str
        ))

    async def deploy(self, run: TrainingRun, model_name: str | None = None) -> ModelState | None:
        """Deploy a trained adapter as an Ollama model."""
        if not run.success or not run.adapter_path:
            self.logger.error("cannot_deploy_failed_run")
            return None

        adapter_path = Path(run.adapter_path)
        if not adapter_path.exists():
            self.logger.error("adapter_path_not_found", path=run.adapter_path)
            return None

        version = run.version
        name = model_name or f"maldoror:{version}"
        modelfile = self.MODELFILE.format(
            base_model=run.base_model,
            adapter_path=str(adapter_path.absolute()),
            template=self.TEMPLATE_QWEN,
        )

        modelfile_path = adapter_path / "Modelfile"
        modelfile_path.write_text(modelfile)

        try:
            proc = await asyncio.create_subprocess_exec(
                "ollama", "create", name, "-f", str(modelfile_path),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

            if proc.returncode != 0:
                self.logger.error("ollama_create_failed", error=stderr.decode())
                return None

            state = ModelState(
                name=name, version=version,
                adapter_path=run.adapter_path, timestamp=time.time(),
            )
            self.models.append(state)
            self._save_state()
            self.logger.info("model_deployed", name=name)
            return state

        except asyncio.TimeoutError:
            self.logger.error("ollama_create_timeout")
            return None
        except FileNotFoundError:
            self.logger.error("ollama_not_found_install_ollama")
            return None

    async def switch_to(self, version: str) -> bool:
        """Switch active model to a specific version."""
        for m in self.models:
            if m.version == version:
                if self.active_model:
                    self.active_model.active = False
                m.active = True
                self.active_model = m
                self._save_state()
                self.logger.info("switched_model", version=version, name=m.name)
                return True
        self.logger.error("version_not_found", version=version)
        return False

    async def ab_test(
        self, prompt: str, version_a: str | None = None, version_b: str | None = None
    ) -> dict[str, Any]:
        """A/B test two model versions on a prompt."""
        a = version_a or (self.active_model.version if self.active_model else None)
        b = version_b or self._find_candidate()

        if not a or not b:
            return {"error": "need at least one active model and one candidate"}

        results = {}
        for label, v in [("model_a", a), ("model_b", b)]:
            resp = await self._query_model(f"maldoror:{v}", prompt)
            results[label] = {"version": v, "response": resp}

        return {
            "prompt": prompt[:200],
            "model_a_version": a,
            "model_b_version": b,
            "results": results,
        }

    def _find_candidate(self) -> str | None:
        """Find a non-active model for A/B testing."""
        for m in self.models:
            if not m.active:
                return m.version
        return None

    async def _query_model(self, model: str, prompt: str) -> str:
        try:
            proc = await asyncio.create_subprocess_exec(
                "ollama", "run", model, prompt,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            if proc.returncode == 0:
                return stdout.decode().strip()
            return f"error: {stderr.decode()[:200]}"
        except Exception as e:
            return f"error: {str(e)}"

    async def list_models(self) -> list[dict[str, Any]]:
        """List available Ollama models matching maldoror."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "ollama", "list",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
            lines = stdout.decode().strip().split("\n")[1:]
            return [
                {"name": parts[0], "size": parts[2] if len(parts) > 2 else "?"}
                for parts in (l.split() for l in lines)
                if parts and "maldoror" in parts[0]
            ]
        except (FileNotFoundError, asyncio.TimeoutError):
            return []

    def get_stats(self) -> dict[str, Any]:
        return {
            "deployed_models": len(self.models),
            "active_model": self.active_model.name if self.active_model else None,
            "versions": [m.version for m in self.models],
        }

    def to_context(self) -> str:
        stats = self.get_stats()
        lines = [
            "Custom Model Manager:",
            f"  Deployed Models: {stats['deployed_models']}",
            f"  Active: {stats['active_model'] or 'None'}",
        ]
        if stats["versions"]:
            lines.append(f"  Versions: {', '.join(stats['versions'])}")
        return "\n".join(lines)
