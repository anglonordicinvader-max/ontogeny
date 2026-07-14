"""Transfer learning module - applies knowledge across domains.

Extracts abstract patterns from one domain and applies them
to another, enabling cross-domain reasoning.
"""

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog


@dataclass
class AbstractPattern:
    """A domain-agnostic pattern that can transfer."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pattern_type: str = ""  # structural, procedural, causal, relational
    description: str = ""
    source_domain: str = ""
    abstract_form: str = ""  # Domain-agnostic representation
    confidence: float = 0.5
    transfer_count: int = 0
    success_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    tags: list[str] = field(default_factory=list)

    @property
    def transfer_success_rate(self) -> float:
        if self.transfer_count == 0:
            return 0.0
        return self.success_count / self.transfer_count


@dataclass
class DomainMapping:
    """Mapping between concepts in different domains."""
    source_domain: str = ""
    target_domain: str = ""
    source_concept: str = ""
    target_concept: str = ""
    similarity: float = 0.5
    confidence: float = 0.5


class TransferLearner:
    """Enables cross-domain knowledge transfer.

    Extracts abstract patterns from experiences in one domain
    and applies them to problems in another domain.
    """

    def __init__(self):
        self.abstract_patterns: dict[str, AbstractPattern] = {}
        self.domain_mappings: dict[str, DomainMapping] = {}
        self.transfer_history: list[dict[str, Any]] = []
        self.domain_knowledge: dict[str, list[str]] = defaultdict(list)
        self.logger = structlog.get_logger()

    async def extract_abstract_pattern(
        self,
        experience: dict[str, Any],
        domain: str,
    ) -> AbstractPattern | None:
        """Extract an abstract pattern from a domain-specific experience."""
        # Identify pattern type
        pattern_type = self._identify_pattern_type(experience)

        # Create abstract representation
        abstract = self._abstractize(experience, domain)

        if not abstract:
            return None

        pattern = AbstractPattern(
            pattern_type=pattern_type,
            description=abstract["description"],
            source_domain=domain,
            abstract_form=abstract["form"],
            confidence=0.5,
            tags=abstract.get("tags", []),
        )

        self.abstract_patterns[pattern.id] = pattern
        self.domain_knowledge[domain].append(pattern.id)

        self.logger.info(
            "abstract_pattern_extracted",
            domain=domain,
            type=pattern_type,
        )
        return pattern

    async def transfer_pattern(
        self,
        pattern_id: str,
        target_domain: str,
        target_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Transfer an abstract pattern to a new domain."""
        pattern = self.abstract_patterns.get(pattern_id)
        if not pattern:
            return {"error": "Pattern not found"}

        # Find domain mapping
        mapping = self._find_mapping(pattern.source_domain, target_domain)

        # Apply pattern to new domain
        application = self._apply_pattern(pattern, target_domain, target_context, mapping)

        # Record transfer
        pattern.transfer_count += 1
        transfer_record = {
            "pattern_id": pattern_id,
            "source_domain": pattern.source_domain,
            "target_domain": target_domain,
            "success": application.get("success", False),
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.transfer_history.append(transfer_record)

        if application.get("success"):
            pattern.success_count += 1

        self.logger.info(
            "pattern_transferred",
            pattern=pattern.description[:50],
            target=target_domain,
            success=application.get("success", False),
        )
        return application

    async def find_transferable_patterns(
        self,
        target_domain: str,
        target_problem: str,
    ) -> list[dict[str, Any]]:
        """Find patterns that could transfer to solve a target problem."""
        candidates = []

        for pattern in self.abstract_patterns.values():
            # Skip patterns from same domain
            if pattern.source_domain == target_domain:
                continue

            # Check relevance
            relevance = self._calculate_transfer_relevance(
                pattern, target_domain, target_problem
            )

            if relevance > 0.3:
                candidates.append({
                    "pattern": pattern,
                    "relevance": relevance,
                    "source_domain": pattern.source_domain,
                    "success_rate": pattern.transfer_success_rate,
                })

        # Sort by relevance * success rate
        candidates.sort(
            key=lambda x: x["relevance"] * (x["success_rate"] + 0.1),
            reverse=True,
        )

        return candidates[:5]

    async def learn_domain_mapping(
        self,
        source_domain: str,
        target_domain: str,
        source_concept: str,
        target_concept: str,
        similarity: float = 0.5,
    ):
        """Learn a mapping between domains."""
        mapping = DomainMapping(
            source_domain=source_domain,
            target_domain=target_domain,
            source_concept=source_concept,
            target_concept=target_concept,
            similarity=similarity,
        )
        self.domain_mappings[f"{source_domain}:{target_domain}:{source_concept}"] = mapping

    def _identify_pattern_type(self, experience: dict[str, Any]) -> str:
        """Identify what type of pattern this is."""
        if "sequence" in experience or "steps" in experience:
            return "procedural"
        elif "cause" in experience or "effect" in experience:
            return "causal"
        elif "relationship" in experience or "connected" in experience:
            return "relational"
        else:
            return "structural"

    def _abstractize(self, experience: dict[str, Any], domain: str) -> dict[str, Any] | None:
        """Create domain-agnostic representation."""
        # Simple abstraction: replace domain-specific terms with placeholders
        description = str(experience.get("description", experience.get("content", "")))
        if not description:
            return None

        # Replace domain terms with generic placeholders
        abstract = description
        domain_words = domain.replace("_", " ").split()
        for word in domain_words:
            abstract = abstract.replace(word, "{CONCEPT}")

        return {
            "description": f"In {domain}: {description[:100]}",
            "form": abstract[:200],
            "tags": [domain, self._identify_pattern_type(experience)],
        }

    def _apply_pattern(
        self,
        pattern: AbstractPattern,
        target_domain: str,
        target_context: dict[str, Any],
        mapping: DomainMapping | None,
    ) -> dict[str, Any]:
        """Apply abstract pattern to target domain."""
        # Simple pattern application
        result = {
            "pattern_type": pattern.pattern_type,
            "source": pattern.source_domain,
            "target": target_domain,
            "success": True,
            "suggestion": f"Apply {pattern.pattern_type} pattern from {pattern.source_domain} to {target_domain}",
        }

        # If we have a mapping, use it
        if mapping:
            result["mapping"] = {
                "source_concept": mapping.source_concept,
                "target_concept": mapping.target_concept,
                "similarity": mapping.similarity,
            }

        return result

    def _find_mapping(self, source_domain: str, target_domain: str) -> DomainMapping | None:
        """Find mapping between two domains."""
        for mapping in self.domain_mappings.values():
            if (mapping.source_domain == source_domain and
                mapping.target_domain == target_domain):
                return mapping
        return None

    def _calculate_transfer_relevance(
        self,
        pattern: AbstractPattern,
        target_domain: str,
        target_problem: str,
    ) -> float:
        """Calculate how relevant a pattern is for transfer."""
        relevance = 0.3  # Base relevance

        # Higher success rate = more likely to transfer
        relevance += pattern.transfer_success_rate * 0.3

        # Check if we have domain mappings
        mapping = self._find_mapping(pattern.source_domain, target_domain)
        if mapping:
            relevance += mapping.similarity * 0.3

        # Check tag overlap
        target_words = set(target_domain.replace("_", " ").split())
        pattern_words = set(pattern.tags)
        overlap = len(target_words & pattern_words)
        relevance += overlap * 0.1

        return min(1.0, relevance)

    def get_stats(self) -> dict[str, Any]:
        """Get transfer learning statistics."""
        return {
            "total_patterns": len(self.abstract_patterns),
            "total_mappings": len(self.domain_mappings),
            "total_transfers": len(self.transfer_history),
            "successful_transfers": sum(1 for t in self.transfer_history if t.get("success")),
            "domains": list(self.domain_knowledge.keys()),
        }

    def to_context(self) -> str:
        """Convert transfer learning state to context string."""
        stats = self.get_stats()
        lines = ["Transfer Learning:"]
        lines.append(f"  Abstract Patterns: {stats['total_patterns']}")
        lines.append(f"  Domain Mappings: {stats['total_mappings']}")
        lines.append(f"  Transfers: {stats['total_transfers']} ({stats['successful_transfers']} successful)")
        if stats['domains']:
            lines.append(f"  Domains: {', '.join(stats['domains'][:5])}")
        return "\n".join(lines)
