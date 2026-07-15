"""Architecture-aware self-modification.

Provides:
- Module dependency graph
- Safe modification zones
- Impact analysis
- Rollback on failure
"""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import structlog


@dataclass
class ModuleInfo:
    name: str
    path: str
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    last_modified: datetime = field(default_factory=datetime.utcnow)
    version: int = 1
    is_stable: bool = True
    risk_level: float = 0.0  # 0.0 to 1.0


@dataclass
class ModificationPlan:
    module: str
    changes: List[Dict] = field(default_factory=list)
    affected_modules: List[str] = field(default_factory=list)
    risk_assessment: float = 0.0
    rollback_available: bool = True


class ArchitectureAwareModifier:
    """Architecture-aware self-modification with rollback."""

    def __init__(self, data_dir: str = "data/architecture"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logger = structlog.get_logger(component="architecture_modify")

        self.modules: Dict[str, ModuleInfo] = {}
        self.modification_history: List[Dict] = []
        self.backups: Dict[str, str] = {}  # module_name -> backup_content

        self._scan_architecture()

    def _scan_architecture(self):
        """Scan and catalog the codebase architecture."""
        self.modules = {
            "orchestrator": ModuleInfo("orchestrator", "orchestrator.py",
                                      dependencies=["memory", "llm", "crawlers"],
                                      risk_level=0.3),
            "memory": ModuleInfo("memory", "memory.py",
                                dependencies=["sqlite"],
                                risk_level=0.4),
            "llm": ModuleInfo("llm", "llm.py",
                             dependencies=[],
                             risk_level=0.2),
            "self_modify": ModuleInfo("self_modify", "self_modify.py",
                                     dependencies=["orchestrator"],
                                     risk_level=0.7),
            "recursive_modify": ModuleInfo("recursive_modify", "recursive_modify.py",
                                          dependencies=["self_modify", "orchestrator"],
                                          risk_level=0.8),
            "blender_sandbox": ModuleInfo("blender_sandbox", "blender_sandbox.py",
                                         dependencies=["simulation"],
                                         risk_level=0.3),
            "crawlers": ModuleInfo("crawlers", "crawlers/",
                                  dependencies=["llm"],
                                  risk_level=0.1),
            "skill_library": ModuleInfo("skill_library", "skill_library.py",
                                       dependencies=["memory"],
                                       risk_level=0.2),
            "goal_system": ModuleInfo("goal_system", "goal_system.py",
                                     dependencies=["memory"],
                                     risk_level=0.2),
        }

    def analyze_impact(self, module_name: str, changes: List[str]) -> ModificationPlan:
        """Analyze impact of proposed changes."""
        module = self.modules.get(module_name)
        if not module:
            return ModificationPlan(module=module_name)

        affected = list(module.dependents)
        risk = module.risk_level

        if "interface" in " ".join(changes).lower():
            risk += 0.3
            affected.extend(module.dependents)

        if "data" in " ".join(changes).lower():
            risk += 0.2

        return ModificationPlan(
            module=module_name,
            changes=[{"description": c} for c in changes],
            affected_modules=list(set(affected)),
            risk_assessment=min(1.0, risk),
            rollback_available=True,
        )

    def backup_module(self, module_name: str, content: str):
        """Backup module before modification."""
        self.backups[module_name] = content

    def rollback_module(self, module_name: str) -> Optional[str]:
        """Rollback a module to its backup."""
        return self.backups.get(module_name)

    def record_modification(self, module_name: str, changes: List[str], success: bool):
        """Record a modification."""
        self.modification_history.append({
            "module": module_name,
            "changes": changes,
            "success": success,
            "timestamp": datetime.utcnow().isoformat(),
        })
        if module_name in self.modules:
            self.modules[module_name].last_modified = datetime.utcnow()
            self.modules[module_name].version += 1
            if not success:
                self.modules[module_name].risk_level = min(1.0,
                    self.modules[module_name].risk_level + 0.1)

    def get_safe_modules(self) -> List[str]:
        """Get modules safe to modify (low risk)."""
        return [name for name, mod in self.modules.items() if mod.risk_level < 0.3]

    def get_risky_modules(self) -> List[str]:
        """Get high-risk modules."""
        return [name for name, mod in self.modules.items() if mod.risk_level >= 0.5]

    def to_context(self) -> str:
        safe = len(self.get_safe_modules())
        risky = len(self.get_risky_modules())
        return f"Architecture: {len(self.modules)} modules ({safe} safe, {risky} risky), {len(self.modification_history)} modifications"
