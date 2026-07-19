"""Cross-domain transfer - transfer knowledge between domains.

Provides:
- Domain abstraction
- Analogy mapping
- Skill transfer between domains
- Structural similarity detection
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import structlog


@dataclass
class Domain:
    name: str
    concepts: list[str] = field(default_factory=list)
    relations: list[dict] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    abstractions: list[str] = field(default_factory=list)


@dataclass
class TransferMapping:
    source_domain: str
    target_domain: str
    concept_mappings: dict[str, str] = field(default_factory=dict)
    relation_mappings: dict[str, str] = field(default_factory=dict)
    confidence: float = 0.0


class TransferLearner:
    """Cross-domain knowledge transfer."""

    def __init__(self, data_dir: str = "data/transfer"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logger = structlog.get_logger(component="transfer")

        self.domains: dict[str, Domain] = {}
        self.transfer_history: list[TransferMapping] = []

        self._setup_domains()
        self._load()

    def _setup_domains(self):
        """Setup known domains."""
        self.domains = {
            "physics": Domain(
                name="physics",
                concepts=["force", "mass", "velocity", "acceleration", "gravity", "friction"],
                relations=[
                    {"source": "force", "target": "mass", "type": "acts_on"},
                    {"source": "force", "target": "acceleration", "type": "causes"},
                ],
                skills=["predict_motion", "estimate_force", "calculate_trajectory"],
            ),
            "coding": Domain(
                name="coding",
                concepts=["function", "variable", "loop", "condition", "array", "recursion"],
                relations=[
                    {"source": "function", "target": "variable", "type": "uses"},
                    {"source": "loop", "target": "array", "type": "iterates"},
                ],
                skills=["write_sort", "implement_search", "debug_code"],
            ),
            "planning": Domain(
                name="planning",
                concepts=["goal", "action", "constraint", "resource", "deadline", "dependency"],
                relations=[
                    {"source": "action", "target": "goal", "type": "achieves"},
                    {"source": "constraint", "target": "action", "type": "limits"},
                ],
                skills=["schedule_tasks", "allocate_resources", "resolve_conflicts"],
            ),
            "social": Domain(
                name="social",
                concepts=[
                    "person",
                    "communication",
                    "agreement",
                    "conflict",
                    "trust",
                    "cooperation",
                ],
                relations=[
                    {"source": "communication", "target": "person", "type": "between"},
                    {"source": "trust", "target": "cooperation", "type": "enables"},
                ],
                skills=["negotiate", "persuade", "collaborate"],
            ),
        }

    def _load(self):
        domains_file = self.data_dir / "domains.json"
        if domains_file.exists():
            try:
                data = json.loads(domains_file.read_text())
                for domain_name, domain_data in data.get("domains", {}).items():
                    self.domains[domain_name] = Domain(**domain_data)
            except Exception as e:
                self.logger.warning("domains_load_failed", error=str(e))

    def _save(self):
        domains_file = self.data_dir / "domains.json"
        domains_file.write_text(
            json.dumps(
                {
                    "domains": {
                        name: {
                            "name": d.name,
                            "concepts": d.concepts,
                            "relations": d.relations,
                            "skills": d.skills,
                            "abstractions": d.abstractions,
                        }
                        for name, d in self.domains.items()
                    },
                },
                indent=2,
            )
        )

    def find_analogies(self, source_domain: str, target_domain: str) -> TransferMapping:
        """Find analogies between two domains."""
        source = self.domains.get(source_domain)
        target = self.domains.get(target_domain)

        if not source or not target:
            return TransferMapping(source_domain=source_domain, target_domain=target_domain)

        concept_mappings = {}
        for sc in source.concepts:
            for tc in target.concepts:
                if self._structural_similarity(sc, tc) > 0.3:
                    concept_mappings[sc] = tc
                    break

        confidence = len(concept_mappings) / max(len(source.concepts), 1)

        mapping = TransferMapping(
            source_domain=source_domain,
            target_domain=target_domain,
            concept_mappings=concept_mappings,
            confidence=confidence,
        )
        self.transfer_history.append(mapping)
        return mapping

    def _structural_similarity(self, concept_a: str, concept_b: str) -> float:
        """Compute structural similarity between concepts."""
        if concept_a == concept_b:
            return 1.0

        synonyms = {
            "force": ["action", "effort"],
            "mass": ["weight", "amount"],
            "velocity": ["speed", "rate"],
            "goal": ["objective", "target"],
            "action": ["step", "move"],
            "function": ["routine", "procedure"],
            "loop": ["cycle", "iteration"],
            "person": ["individual", "agent"],
        }

        for key, syns in synonyms.items():
            if (concept_a == key and concept_b in syns) or (concept_b == key and concept_a in syns):
                return 0.8

        return 0.0

    def transfer_skill(
        self,
        source_domain: str,
        target_domain: str,
        skill: str,
    ) -> str | None:
        """Transfer a skill from one domain to another."""
        mapping = self.find_analogies(source_domain, target_domain)

        if mapping.confidence < 0.2:
            return None

        transferred = f"Adapted '{skill}' from {source_domain} to {target_domain}"
        return transferred

    def abstract_domain(self, domain_name: str) -> list[str]:
        """Create abstract principles from a domain."""
        domain = self.domains.get(domain_name)
        if not domain:
            return []

        abstractions = []
        for relation in domain.relations:
            abstraction = f"{relation['type']}: {relation['source']} -> {relation['target']}"
            abstractions.append(abstraction)

        domain.abstractions = abstractions
        self._save()
        return abstractions

    def to_context(self) -> str:
        return (
            f"Transfer Learner: {len(self.domains)} domains, {len(self.transfer_history)} transfers"
        )
