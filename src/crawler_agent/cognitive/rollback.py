"""Rollback and versioning system.

Provides:
- Automatic rollback on failure
- Version tracking
- Regression testing
- Health monitoring
"""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog


@dataclass
class Version:
    version_id: str
    module: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    changes: list[str] = field(default_factory=list)
    health_before: float = 1.0
    health_after: float = 1.0
    rolled_back: bool = False

    def to_dict(self) -> dict:
        return {
            "version_id": self.version_id,
            "module": self.module,
            "timestamp": self.timestamp.isoformat(),
            "changes": self.changes,
            "health_before": self.health_before,
            "health_after": self.health_after,
            "rolled_back": self.rolled_back,
        }


class RollbackManager:
    """Automatic rollback and versioning system."""

    def __init__(self, data_dir: str = "data/rollback"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logger = structlog.get_logger(component="rollback")

        self.versions: list[Version] = []
        self.backups: dict[str, str] = {}
        self.health_history: list[dict] = []

        self._load()

    def _load(self):
        versions_file = self.data_dir / "versions.json"
        if versions_file.exists():
            try:
                data = json.loads(versions_file.read_text())
                for v_data in data.get("versions", []):
                    v = Version(
                        version_id=v_data["version_id"],
                        module=v_data["module"],
                        changes=v_data.get("changes", []),
                        health_before=v_data.get("health_before", 1.0),
                        health_after=v_data.get("health_after", 1.0),
                        rolled_back=v_data.get("rolled_back", False),
                    )
                    if "timestamp" in v_data:
                        v.timestamp = datetime.fromisoformat(v_data["timestamp"])
                    self.versions.append(v)
            except Exception as e:
                self.logger.warning("versions_load_failed", error=str(e))

    def _save(self):
        versions_file = self.data_dir / "versions.json"
        versions_file.write_text(
            json.dumps(
                {
                    "versions": [v.to_dict() for v in self.versions[-200:]],
                },
                indent=2,
            )
        )

    def create_version(
        self,
        module: str,
        changes: list[str],
        content: str,
        health_before: float = 1.0,
    ) -> Version:
        """Create a new version before modification."""
        import uuid

        version = Version(
            version_id=str(uuid.uuid4())[:8],
            module=module,
            changes=changes,
            health_before=health_before,
        )
        self.backups[version.version_id] = content
        self.versions.append(version)
        self._save()
        return version

    def record_health(self, version_id: str, health_after: float):
        """Record health after modification."""
        for v in self.versions:
            if v.version_id == version_id:
                v.health_after = health_after
                self._save()
                break

    def should_rollback(self, version_id: str, threshold: float = 0.5) -> bool:
        """Check if rollback is needed based on health drop."""
        for v in self.versions:
            if v.version_id == version_id:
                drop = v.health_before - v.health_after
                return drop > threshold
        return False

    def rollback(self, version_id: str) -> str | None:
        """Rollback to a previous version."""
        for v in self.versions:
            if v.version_id == version_id:
                v.rolled_back = True
                self._save()
                return self.backups.get(version_id)
        return None

    def get_version_history(self, module: str | None = None, limit: int = 10) -> list[Version]:
        """Get version history."""
        versions = self.versions
        if module:
            versions = [v for v in versions if v.module == module]
        return versions[-limit:]

    def to_context(self) -> str:
        rolled_back = sum(1 for v in self.versions if v.rolled_back)
        return f"Rollback: {len(self.versions)} versions ({rolled_back} rolled back), {len(self.backups)} backups"
