"""Persistence module for saving and loading agent state."""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog


@dataclass
class AgentState:
    """Serializable agent state."""
    iteration: int = 0
    start_time: str = ""
    goals: list[dict[str, Any]] = field(default_factory=list)
    completed_goals: list[dict[str, Any]] = field(default_factory=list)
    memory_experiences: list[dict[str, Any]] = field(default_factory=list)
    knowledge_concepts: list[dict[str, Any]] = field(default_factory=list)
    knowledge_relations: list[dict[str, Any]] = field(default_factory=list)
    causal_variables: list[dict[str, Any]] = field(default_factory=list)
    causal_edges: list[dict[str, Any]] = field(default_factory=list)
    skills: list[dict[str, Any]] = field(default_factory=list)
    agent_messages: list[dict[str, Any]] = field(default_factory=list)
    execution_log: list[dict[str, Any]] = field(default_factory=list)
    custom: dict[str, Any] = field(default_factory=dict)


class StatePersistence:
    """Save and load agent state to/from disk."""

    def __init__(self, state_dir: str = "./data"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / "agent_state.json"
        self.logger = structlog.get_logger()

    async def save(self, state: AgentState) -> None:
        """Save state to disk."""
        try:
            data = asdict(state)
            data["_saved_at"] = datetime.utcnow().isoformat()
            self.state_file.write_text(json.dumps(data, indent=2, default=str))
            self.logger.info("state_saved", file=str(self.state_file))
        except Exception as e:
            self.logger.error("state_save_failed", error=str(e))

    async def load(self) -> AgentState | None:
        """Load state from disk."""
        if not self.state_file.exists():
            self.logger.info("no_saved_state")
            return None

        try:
            data = json.loads(self.state_file.read_text())
            data.pop("_saved_at", None)
            state = AgentState(**data)
            self.logger.info("state_loaded", file=str(self.state_file))
            return state
        except Exception as e:
            self.logger.error("state_load_failed", error=str(e))
            return None

    async def save_backup(self, state: AgentState) -> None:
        """Save a timestamped backup."""
        backup_dir = self.state_dir / "backups"
        backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"state_{timestamp}.json"

        try:
            data = asdict(state)
            data["_saved_at"] = datetime.utcnow().isoformat()
            backup_file.write_text(json.dumps(data, indent=2, default=str))
            self.logger.info("backup_saved", file=str(backup_file))
        except Exception as e:
            self.logger.error("backup_save_failed", error=str(e))

    def list_backups(self) -> list[str]:
        """List available backups."""
        backup_dir = self.state_dir / "backups"
        if not backup_dir.exists():
            return []
        return sorted([f.name for f in backup_dir.glob("state_*.json")])
