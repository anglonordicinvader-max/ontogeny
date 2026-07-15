"""Cross-domain transfer - transfer learning across skill domains.

Provides:
- Domain abstraction
- Skill generalization
- Transfer between tasks
- Structural mapping
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog


@dataclass
class Domain:
    name: str
    skills: List[str] = field(default_factory=list)
    abstractions: List[str] = field(default_factory=list)
    examples: List[Dict] = field(default_factory=list)
    similarity_to: Dict[str, float] = field(default_factory=dict)


@dataclass
class Transfer:
    source_domain: str
    target_domain: str
    skill_transferred: str
    success: bool = False
    confidence: float = 0.0


class CrossDomainTransfer:
    """Transfer learning across skill domains."""

    def __init__(self, data_dir: str = "data/cross_domain"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logger = structlog.get_logger(component="cross_domain")

        self.domains: Dict[str, Domain] = {}
        self.transfers: List[Transfer] = []

        self._setup_domains()
        self._load()

    def _setup_domains(self):
        self.domains = {
            "coding": Domain(
                name="coding",
                skills=["sorting", "searching", "recursion", "data_structures"],
                abstractions=["algorithm", "efficiency", "correctness"],
            ),
            "planning": Domain(
                name="planning",
                skills=["scheduling", "resource_allocation", "constraint_satisfaction"],
                abstractions=["optimization", "trade_off", "sequencing"],
            ),
            "reasoning": Domain(
                name="reasoning",
                skills=["deduction", "induction", "abduction", "analogy"],
                abstractions=["logic", "evidence", "inference"],
            ),
            "physics": Domain(
                name="physics",
                skills=["prediction", "estimation", "simulation"],
                abstractions=["cause_effect", "conservation", "dynamics"],
            ),
        }

    def _load(self):
        domains_file = self.data_dir / "domains.json"
        if domains_file.exists():
            try:
                data = json.loads(domains_file.read_text())
                for name, d in data.get("domains", {}).items():
                    self.domains[name] = Domain(**d)
            except Exception as e:
                self.logger.warning("domains_load_failed", error=str(e))

    def _save(self):
        domains_file = self.data_dir / "domains.json"
        domains_file.write_text(json.dumps({
            "domains": {
                name: {
                    "name": d.name,
                    "skills": d.skills,
                    "abstractions": d.abstractions,
                    "similarity_to": d.similarity_to,
                }
                for name, d in self.domains.items()
            },
        }, indent=2))

    def find_transferable_skills(self, source: str, target: str) -> List[str]:
        """Find skills that can transfer between domains."""
        source_domain = self.domains.get(source)
        target_domain = self.domains.get(target)
        if not source_domain or not target_domain:
            return []

        common = set(source_domain.abstractions) & set(target_domain.abstractions)
        if common:
            return list(common)

        return [s for s in source_domain.skills if any(t in s for t in target_domain.skills)]

    def transfer_skill(self, source: str, target: str, skill: str) -> Transfer:
        """Transfer a skill from source to target domain."""
        transferable = self.find_transferable_skills(source, target)
        success = skill in transferable or len(transferable) > 0

        transfer = Transfer(
            source_domain=source,
            target_domain=target,
            skill_transferred=skill,
            success=success,
            confidence=0.7 if success else 0.3,
        )
        self.transfers.append(transfer)
        self._save()
        return transfer

    def to_context(self) -> str:
        successful = sum(1 for t in self.transfers if t.success)
        return f"Cross-Domain: {len(self.domains)} domains, {len(self.transfers)} transfers ({successful} successful)"
