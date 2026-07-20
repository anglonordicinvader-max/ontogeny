"""Ontogeny Knowledge Acquisition System.

Every external information request flows through this pipeline:

    Research Goal -> Source Planning -> Acquisition Engine -> API Connectors / HTTP Retrieval
    -> Browser Rendering (only when required) -> Normalization -> Evidence Validation
    -> Knowledge Graph -> Persistent Memory -> Planning -> Maldoror Reflection

This subsystem represents intelligent evidence acquisition rather than generic
web scraping. The emphasis is on acquiring, validating, organizing, and
reasoning over external knowledge.
"""

from .domain_policies import DomainPolicies, DomainPolicy
from .evidence_store import EvidenceDocument, EvidenceStore
from .knowledge_validator import Claim, ClaimValidator
from .manager import AcquisitionManager
from .observability import AcquisitionObservability, MetricsSnapshot
from .proxy_manager import ProxyEndpoint, ProxyManager
from .request_manager import RequestManager
from .research_planner import ResearchObjective, ResearchPlan, ResearchPlanner
from .revalidation import RevalidationScheduler
from .source_scorer import SourceCategory, SourceQualityScorer

# Backward compatibility alias
CrawlObservability = AcquisitionObservability

__all__ = [
    "AcquisitionManager",
    "ResearchPlanner",
    "ResearchPlan",
    "ResearchObjective",
    "EvidenceStore",
    "EvidenceDocument",
    "SourceQualityScorer",
    "SourceCategory",
    "ProxyManager",
    "ProxyEndpoint",
    "DomainPolicies",
    "DomainPolicy",
    "RequestManager",
    "ClaimValidator",
    "Claim",
    "RevalidationScheduler",
    "AcquisitionObservability",
    "MetricsSnapshot",
    # Backward compatibility
    "CrawlObservability",
]
