"""Evidence Store — persistent document storage with full provenance.

Every retrieved document is stored with:
- Canonical URL, retrieval timestamp, publication date
- Author, organization, source category
- Content hash, extraction method, confidence
- Citation metadata, supporting/contradictory claims
- Relevant text spans
- Full provenance chain

Never inserts unsupported knowledge directly into memory.
"""

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog


@dataclass
class EvidenceDocument:
    """A single evidence document with full metadata."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    canonical_url: str = ""
    title: str = ""
    content: str = ""
    content_hash: str = ""

    # Source metadata
    source_domain: str = ""
    source_category: str = "unknown"
    author: str = ""
    organization: str = ""
    publication_date: str = ""  # ISO format

    # Retrieval metadata
    retrieved_at: datetime = field(default_factory=datetime.utcnow)
    extraction_method: str = "auto"  # "api", "http", "browser", "feed", "manual"
    http_status: int = 200
    content_type: str = ""
    content_length: int = 0
    response_time_ms: float = 0.0

    # Quality
    confidence: float = 0.5  # 0-1
    quality_score: float = 0.5  # from SourceQualityScorer
    relevance_score: float = 0.0  # 0-1, how relevant to the query

    # Claims
    supporting_claims: list[str] = field(default_factory=list)
    contradictory_claims: list[str] = field(default_factory=list)
    key_facts: list[str] = field(default_factory=list)
    relevant_spans: list[dict[str, Any]] = field(default_factory=list)

    # Citation
    citation_count: int = 0
    cited_by: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)

    # Research context
    research_plan_id: str = ""
    objective_id: str = ""
    query: str = ""
    tags: list[str] = field(default_factory=list)

    def compute_hash(self):
        """Compute content hash for deduplication."""
        self.content_hash = hashlib.sha256(
            self.content.encode("utf-8", errors="replace")
        ).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "url": self.canonical_url,
            "title": self.title,
            "content_hash": self.content_hash,
            "source_domain": self.source_domain,
            "source_category": self.source_category,
            "author": self.author,
            "organization": self.organization,
            "publication_date": self.publication_date,
            "retrieved_at": self.retrieved_at.isoformat(),
            "extraction_method": self.extraction_method,
            "confidence": self.confidence,
            "quality_score": self.quality_score,
            "relevance_score": self.relevance_score,
            "supporting_claims": self.supporting_claims,
            "contradictory_claims": self.contradictory_claims,
            "key_facts": self.key_facts,
            "citation_count": self.citation_count,
            "research_plan_id": self.research_plan_id,
            "query": self.query,
            "tags": self.tags,
            "content_length": self.content_length,
        }


class EvidenceStore:
    """Persistent evidence storage with deduplication and search."""

    def __init__(self, state_path: str | Path | None = None):
        self.documents: dict[str, EvidenceDocument] = {}
        self._hash_index: dict[str, str] = {}  # content_hash -> doc_id
        self._url_index: dict[str, list[str]] = {}  # url -> [doc_ids]
        self._tag_index: dict[str, set[str]] = {}  # tag -> {doc_ids}
        self._domain_index: dict[str, set[str]] = {}  # domain -> {doc_ids}
        self.state_path = Path(state_path) if state_path else None
        self.logger = structlog.get_logger()

        if self.state_path and self.state_path.exists():
            self._load_state()

    def store(self, doc: EvidenceDocument) -> str:
        """Store a document, deduplicating by content hash.

        Returns the document ID.
        """
        if not doc.content_hash:
            doc.compute_hash()

        # Deduplication
        if doc.content_hash in self._hash_index:
            existing_id = self._hash_index[doc.content_hash]
            self.logger.info(
                "evidence_deduplicated",
                existing_id=existing_id,
                url=doc.canonical_url,
            )
            # Merge claims from new doc into existing
            existing = self.documents.get(existing_id)
            if existing:
                for claim in doc.supporting_claims:
                    if claim not in existing.supporting_claims:
                        existing.supporting_claims.append(claim)
                for claim in doc.contradictory_claims:
                    if claim not in existing.contradictory_claims:
                        existing.contradictory_claims.append(claim)
                # Update confidence if new source corroborates
                existing.confidence = min(1.0, existing.confidence + 0.05)
            return existing_id

        # Store new document
        self.documents[doc.id] = doc
        self._hash_index[doc.content_hash] = doc.id

        # Update indexes
        self._url_index.setdefault(doc.canonical_url, []).append(doc.id)
        self._domain_index.setdefault(doc.source_domain, set()).add(doc.id)
        for tag in doc.tags:
            self._tag_index.setdefault(tag, set()).add(doc.id)

        self.logger.info(
            "evidence_stored",
            doc_id=doc.id,
            url=doc.canonical_url,
            domain=doc.source_domain,
        )
        return doc.id

    def get(self, doc_id: str) -> EvidenceDocument | None:
        return self.documents.get(doc_id)

    def find_by_url(self, url: str) -> list[EvidenceDocument]:
        doc_ids = self._url_index.get(url, [])
        return [self.documents[did] for did in doc_ids if did in self.documents]

    def find_by_domain(self, domain: str) -> list[EvidenceDocument]:
        doc_ids = self._domain_index.get(domain, set())
        return [self.documents[did] for did in doc_ids if did in self.documents]

    def find_by_tag(self, tag: str) -> list[EvidenceDocument]:
        doc_ids = self._tag_index.get(tag, set())
        return [self.documents[did] for did in doc_ids if did in self.documents]

    def find_by_hash(self, content_hash: str) -> EvidenceDocument | None:
        doc_id = self._hash_index.get(content_hash)
        if doc_id:
            return self.documents.get(doc_id)
        return None

    def search(
        self,
        query: str = "",
        domain: str = "",
        category: str = "",
        tags: list[str] | None = None,
        min_confidence: float = 0.0,
        limit: int = 50,
    ) -> list[EvidenceDocument]:
        """Search evidence store with filters."""
        results = list(self.documents.values())

        if domain:
            results = [d for d in results if d.source_domain == domain]
        if category:
            results = [d for d in results if d.source_category == category]
        if tags:
            results = [d for d in results if any(t in d.tags for t in tags)]
        if min_confidence > 0:
            results = [d for d in results if d.confidence >= min_confidence]
        if query:
            query_lower = query.lower()
            results = [
                d
                for d in results
                if query_lower in d.title.lower()
                or query_lower in d.content.lower()
                or query_lower in d.query.lower()
            ]

        # Sort by relevance then confidence
        results.sort(key=lambda d: (d.relevance_score, d.confidence), reverse=True)
        return results[:limit]

    def get_claims_for_domain(self, domain: str) -> dict[str, list[str]]:
        """Get all supporting and contradictory claims for a domain."""
        docs = self.find_by_domain(domain)
        supporting = []
        contradictory = []
        for d in docs:
            supporting.extend(d.supporting_claims)
            contradictory.extend(d.contradictory_claims)
        return {"supporting": supporting, "contradictory": contradictory}

    def compute_aggregate_confidence(self, domain: str) -> float:
        """Compute aggregate confidence for claims from a domain."""
        docs = self.find_by_domain(domain)
        if not docs:
            return 0.0
        return sum(d.confidence for d in docs) / len(docs)

    def save_state(self):
        """Persist to disk."""
        if not self.state_path:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "documents": {k: v.to_dict() for k, v in self.documents.items()},
            "hash_index": self._hash_index,
        }
        self.state_path.write_text(json.dumps(data, indent=2))

    def _load_state(self):
        try:
            data = json.loads(self.state_path.read_text())
            for doc_id, doc_data in data.get("documents", {}).items():
                doc = EvidenceDocument(
                    id=doc_data.get("id", doc_id),
                    canonical_url=doc_data.get("url", ""),
                    title=doc_data.get("title", ""),
                    source_domain=doc_data.get("source_domain", ""),
                    source_category=doc_data.get("source_category", "unknown"),
                    author=doc_data.get("author", ""),
                    organization=doc_data.get("organization", ""),
                    publication_date=doc_data.get("publication_date", ""),
                    extraction_method=doc_data.get("extraction_method", "auto"),
                    confidence=doc_data.get("confidence", 0.5),
                    quality_score=doc_data.get("quality_score", 0.5),
                    relevance_score=doc_data.get("relevance_score", 0.0),
                    supporting_claims=doc_data.get("supporting_claims", []),
                    contradictory_claims=doc_data.get("contradictory_claims", []),
                    key_facts=doc_data.get("key_facts", []),
                    citation_count=doc_data.get("citation_count", 0),
                    research_plan_id=doc_data.get("research_plan_id", ""),
                    query=doc_data.get("query", ""),
                    tags=doc_data.get("tags", []),
                    content_length=doc_data.get("content_length", 0),
                )
                self.documents[doc.id] = doc
                if doc.content_hash:
                    self._hash_index[doc.content_hash] = doc.id
                self._url_index.setdefault(doc.canonical_url, []).append(doc.id)
                self._domain_index.setdefault(doc.source_domain, set()).add(doc.id)
                for tag in doc.tags:
                    self._tag_index.setdefault(tag, set()).add(doc.id)
        except Exception as e:
            self.logger.warning("evidence_load_failed", error=str(e))

    def get_stats(self) -> dict[str, Any]:
        if not self.documents:
            return {"total_documents": 0}
        domains = {}
        for d in self.documents.values():
            domains[d.source_domain] = domains.get(d.source_domain, 0) + 1
        return {
            "total_documents": len(self.documents),
            "unique_domains": len(domains),
            "avg_confidence": sum(d.confidence for d in self.documents.values())
            / len(self.documents),
            "total_claims": sum(
                len(d.supporting_claims) + len(d.contradictory_claims)
                for d in self.documents.values()
            ),
        }
