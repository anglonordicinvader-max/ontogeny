"""Maldoror model trainer - orchestrates QLoRA fine-tuning via Docker GPU."""
import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from .modification_memory import ModificationMemory, ModificationRecord


@dataclass
class TrainingRun:
    version: str
    timestamp: str = ""
    base_model: str = "Qwen/Qwen2.5-7B-Instruct"
    adapter_path: str = ""
    num_examples: int = 0
    quality_avg: float = 0.0
    loss: float = 0.0
    duration_seconds: float = 0.0
    success: bool = False
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class ModelTrainer:
    """Trains the Maldoror custom model via QLoRA in Docker GPU container."""

    def __init__(
        self,
        modification_memory: ModificationMemory,
        output_dir: str = "data/maldoror",
        docker_image: str = "ontogeny-blender",
    ):
        self.memory = modification_memory
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.docker_image = docker_image
        self.logger = structlog.get_logger()
        self.runs: list[TrainingRun] = []
        self.current_version = self._next_version()
        self._load_runs()

    def _next_version(self) -> str:
        existing = list(self.output_dir.glob("v*"))
        if not existing:
            return "v0"
        versions = sorted(
            (int(d.name[1:]) for d in existing if d.name.startswith("v") and d.name[1:].isdigit()),
            reverse=True,
        )
        return f"v{(versions[0] if versions else 0) + 1}"

    def _load_runs(self) -> None:
        runs_file = self.output_dir / "runs.json"
        if runs_file.exists():
            try:
                data = json.loads(runs_file.read_text())
                self.runs = [TrainingRun(**r) for r in data.get("runs", [])]
                if self.runs:
                    self.current_version = self._next_version()
            except Exception as e:
                self.logger.warning("runs_load_failed", error=str(e))

    def _save_runs(self) -> None:
        runs_file = self.output_dir / "runs.json"
        runs_file.write_text(json.dumps(
            {"runs": [r.__dict__ for r in self.runs]}, indent=2, default=str
        ))

    def prepare_dataset(self, min_quality: float = 0.6) -> Path:
        """Export training data in chatml format for the training script."""
        data = self.memory.get_training_data(format="chatml", min_quality=min_quality)
        if not data:
            raise ValueError("No training data available")
        dataset_path = self.output_dir / f"train_{self.current_version}.jsonl"
        with open(dataset_path, "w") as f:
            for ex in data:
                f.write(json.dumps(ex) + "\n")
        self.logger.info("dataset_prepared", path=str(dataset_path), count=len(data))
        return dataset_path

    async def train(
        self,
        base_model: str = "Qwen/Qwen2.5-7B-Instruct",
        min_quality: float = 0.6,
        max_steps: int = 200,
        timeout: int = 7200,
    ) -> TrainingRun:
        """Run QLoRA training inside Docker GPU container."""
        run = TrainingRun(
            version=self.current_version,
            timestamp=datetime.utcnow().isoformat(),
            base_model=base_model,
        )
        try:
            dataset_path = self.prepare_dataset(min_quality=min_quality)
            adapter_dir = self.output_dir / self.current_version
            adapter_dir.mkdir(parents=True, exist_ok=True)

            start = time.time()
            proc = await asyncio.create_subprocess_exec(
                "docker", "run", "--rm", "--runtime=nvidia",
                "-v", f"{dataset_path.parent}:/workspace",
                "-v", f"{adapter_dir}:/output",
                "-e", f"MALDOROR_BASE_MODEL={base_model}",
                "-e", f"MALDOROR_ADAPTER_DIR=/output",
                "-e", f"MALDOROR_DATASET=/workspace/{dataset_path.name}",
                "-e", f"MALDOROR_MAX_STEPS={max_steps}",
                self.docker_image,
                "python", "/workspace/train.py",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            duration = time.time() - start

            run.duration_seconds = duration
            run.adapter_path = str(adapter_dir)
            run.num_examples = len(self.memory.get_successful_records(min_quality=min_quality))

            if proc.returncode == 0 and any(adapter_dir.iterdir()):
                run.success = True
                run.loss = self._extract_loss(stdout.decode())
                self.logger.info("training_complete", version=self.current_version, loss=run.loss)
            else:
                run.error = stderr.decode()[:2000]
                self.logger.error("training_failed", error=run.error)

            self.runs.append(run)
            self._save_runs()
            if run.success:
                self.current_version = self._next_version()
            return run

        except asyncio.TimeoutError:
            run.error = "timeout"
            run.success = False
            self.runs.append(run)
            self._save_runs()
            return run
        except Exception as e:
            run.error = str(e)
            run.success = False
            self.runs.append(run)
            self._save_runs()
            return run

    def _extract_loss(self, output: str) -> float:
        """Extract final training loss from output."""
        import re
        matches = re.findall(r'"loss":\s*([\d.]+)', output)
        if matches:
            return float(matches[-1])
        matches = re.findall(r'loss[=:]\s*([\d.]+)', output)
        if matches:
            return float(matches[-1])
        return 0.0

    def get_latest_adapter(self) -> str | None:
        """Get path to latest successful adapter."""
        for run in reversed(self.runs):
            if run.success and run.adapter_path:
                return run.adapter_path
        return None

    def get_stats(self) -> dict[str, Any]:
        """Get training statistics."""
        successful = [r for r in self.runs if r.success]
        return {
            "total_runs": len(self.runs),
            "successful": len(successful),
            "current_version": self.current_version,
            "latest_adapter": self.get_latest_adapter(),
            "avg_loss": sum(r.loss for r in successful) / max(len(successful), 1) if successful else 0.0,
            "avg_duration": sum(r.duration_seconds for r in successful) / max(len(successful), 1) if successful else 0.0,
            "runs": [{"version": r.version, "success": r.success, "loss": r.loss} for r in self.runs[-5:]],
        }

    def to_context(self) -> str:
        """Convert trainer state to context string."""
        stats = self.get_stats()
        lines = [
            "Model Trainer:",
            f"  Total Runs: {stats['total_runs']}",
            f"  Successful: {stats['successful']}",
            f"  Current Version: {stats['current_version']}",
            f"  Latest Adapter: {stats['latest_adapter'] or 'None'}",
        ]
        if stats["avg_loss"] > 0:
            lines.append(f"  Avg Loss: {stats['avg_loss']:.4f}")
        return "\n".join(lines)
