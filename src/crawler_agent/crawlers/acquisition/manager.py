"""Ontogeny Knowledge Acquisition Manager — the central hub for all external knowledge acquisition.

Every external information request flows through this pipeline:

    Research Goal -> Source Planning -> Acquisition Engine -> API Connectors / HTTP Retrieval
    -> Browser Rendering (only when required) -> Normalization -> Evidence Validation
    -> Knowledge Graph -> Persistent Memory -> Planning -> Maldoror Reflection

This subsystem represents intelligent evidence acquisition rather than generic
web scraping. The emphasis is on acquiring, validating, organizing, and
reasoning over external knowledge.

All acquisition engines route through this manager.
"""

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator

import structlog

from ..base import BaseCrawler, ContentType, CrawlResult
from .domain_policies import DomainPolicies
from .evidence_store import EvidenceDocument, EvidenceStore
from .knowledge_validator import ClaimValidator
from .observability import AcquisitionObservability
from .proxy_manager import ProxyManager
from .request_manager import RequestManager
from .research_planner import ObjectiveStatus, ResearchPlan, ResearchPlanner
from .revalidation import RevalidationScheduler
from .source_scorer import SourceCategory, SourceQualityScorer


@dataclass
class AcquisitionConfig:
    """Configuration for the acquisition system."""

    state_dir: str = "data/acquisition"
    max_concurrent_requests: int = 10
    max_requests_per_minute: int = 120
    cache_ttl_seconds: float = 3600.0
    session_budget: int = 1000
    enable_proxy: bool = True
    enable_observability: bool = True


class AcquisitionManager:
    """Centralized manager for all external information requests.

    Provides a single pipeline from research goals to memory integration.
    Every crawler routes through this manager.
    """

    def __init__(self, config: AcquisitionConfig | None = None):
        self.config = config or AcquisitionConfig()
        self.logger = structlog.get_logger()

        # Initialize state directory
        state_dir = Path(self.config.state_dir)
        state_dir.mkdir(parents=True, exist_ok=True)

        # Core components
        self.research_planner = ResearchPlanner()
        self.evidence_store = EvidenceStore(state_dir / "evidence.json")
        self.source_scorer = SourceQualityScorer()
        self.domain_policies = DomainPolicies(state_dir / "domain_policies.json")
        self.proxy_manager = ProxyManager()
        self.request_manager = RequestManager(
            max_concurrent=self.config.max_concurrent_requests,
            max_requests_per_minute=self.config.max_requests_per_minute,
            cache_ttl_seconds=self.config.cache_ttl_seconds,
            budget_per_session=self.config.session_budget,
        )
        self.claim_validator = ClaimValidator()
        self.revalidation = RevalidationScheduler()
        self.observability = AcquisitionObservability()

        # Active plans
        self._active_plan: ResearchPlan | None = None

        # Crawler registry (name -> crawler instance)
        self._crawlers: dict[str, BaseCrawler] = {}

        self.logger.info(
            "acquisition_manager_initialized",
            state_dir=str(state_dir),
            budget=self.config.session_budget,
        )

    def register_crawler(self, name: str, crawler: BaseCrawler):
        """Register a crawler with the acquisition system."""
        self._crawlers[name] = crawler
        self.logger.debug("crawler_registered", name=name)

    def get_crawler(self, name: str) -> BaseCrawler | None:
        return self._crawlers.get(name)

    # ── Research Planning ──────────────────────────────────────────────

    def create_research_plan(
        self,
        objective: str,
        description: str = "",
        budget: int = 200,
        sub_objectives: list[dict[str, Any]] | None = None,
    ) -> ResearchPlan:
        """Create a new research plan."""
        plan = self.research_planner.create_plan(
            objective=objective,
            description=description,
            total_budget=budget,
            sub_objectives=sub_objectives,
        )
        self._active_plan = plan
        self.observability.record_plan()
        return plan

    def create_plan_from_goal(
        self,
        goal: str,
        context: dict[str, Any] | None = None,
        memory_facts: list[str] | None = None,
    ) -> ResearchPlan:
        """Create a research plan from a cognitive goal."""
        plan = self.research_planner.create_plan_from_goal(
            goal_description=goal,
            context=context,
            memory_relevant_facts=memory_facts,
        )
        self._active_plan = plan
        self.observability.record_plan()
        return plan

    # ── Information Acquisition ────────────────────────────────────────

    async def acquire(
        self,
        url: str,
        crawler_name: str = "",
        plan_id: str = "",
        objective_id: str = "",
        query: str = "",
        priority: str = "normal",
    ) -> EvidenceDocument | None:
        """Acquire information from a URL.

        This is the primary entry point for all information requests.
        Handles: policy checks, proxy selection, fetching, caching,
        deduplication, evidence storage, and observability.
        """
        # Parse domain
        from urllib.parse import urlparse

        from .request_manager import RequestPriority

        parsed = urlparse(url)
        domain = parsed.netloc

        # Policy check
        if not self.domain_policies.is_allowed(domain):
            self.logger.info("domain_blocked", domain=domain, url=url)
            self.observability.record_robots_exclusion()
            return None

        policy = self.domain_policies.get_policy(domain)
        if not policy.can_request():
            self.logger.info("domain_rate_limited", domain=domain)
            return None

        # Check cache
        cached = self.request_manager.get_cached(url)
        if cached:
            doc = EvidenceDocument(
                canonical_url=url,
                content=cached.content.decode("utf-8", errors="replace"),
                source_domain=domain,
                extraction_method="cache",
                content_length=len(cached.content),
            )
            doc.compute_hash()
            doc_id = self.evidence_store.store(doc)
            self.observability.record_evidence(accepted=True, duplicate=False)
            return self.evidence_store.get(doc_id)

        # Source scoring
        category = self.source_scorer.classify_domain(domain)
        source_score = self.source_scorer.score(domain, category)

        # Proxy selection
        proxy = self.proxy_manager.select(
            domain=domain,
            prefer_direct=(policy.proxy_preference == "direct"),
        )

        # Execute fetch
        crawler = self._crawlers.get(crawler_name)
        if not crawler:
            # Use any available crawler, or fallback to direct HTTP
            crawler = self._find_crawler_for_url(url)

        if crawler:
            doc = await self._fetch_via_crawler(
                crawler,
                url,
                domain,
                source_score.quality_score,
                plan_id,
                objective_id,
                query,
            )
        else:
            doc = await self._fetch_direct(
                url,
                domain,
                source_score.quality_score,
                plan_id,
                objective_id,
                query,
                proxy,
            )

        if doc:
            # Update domain policy
            policy.record_request(success=True)

            # Update source scorer
            self.source_scorer.update_from_fetch(
                domain,
                success=True,
                content_length=doc.content_length,
            )

            # Store evidence
            doc.compute_hash()
            doc_id = self.evidence_store.store(doc)

            # Cache the response
            self.request_manager.store_cache(
                url,
                200,
                doc.content.encode("utf-8", errors="replace"),
                {},
                content_type=doc.content_type,
            )

            self.observability.record_evidence(accepted=True)
            self.observability.record_domain_access(domain)
            self.observability.record_direct()  # TODO: track proxy vs direct

            return self.evidence_store.get(doc_id)
        else:
            policy.record_request(success=False)
            self.source_scorer.update_from_fetch(domain, success=False)
            self.observability.record_evidence(accepted=False)

        return None

    async def acquire_batch(
        self,
        urls: list[str],
        crawler_name: str = "",
        plan_id: str = "",
        max_concurrent: int = 5,
    ) -> list[EvidenceDocument]:
        """Acquire multiple URLs concurrently."""
        semaphore = asyncio.Semaphore(max_concurrent)
        results = []

        async def _acquire_one(url: str):
            async with semaphore:
                doc = await self.acquire(
                    url,
                    crawler_name=crawler_name,
                    plan_id=plan_id,
                )
                if doc:
                    results.append(doc)

        await asyncio.gather(
            *[_acquire_one(url) for url in urls],
            return_exceptions=True,
        )
        return results

    async def research(
        self,
        objective: str,
        max_budget: int = 100,
        source_filter: list[str] | None = None,
    ) -> list[EvidenceDocument]:
        """Execute a complete research cycle.

        Creates a plan, queries sources, collects evidence, and returns results.
        """
        plan = self.create_research_plan(objective, budget=max_budget)
        all_evidence = []
        budget_remaining = max_budget

        for obj in plan.objectives:
            if budget_remaining <= 0:
                break

            obj.status = ObjectiveStatus.IN_PROGRESS
            plan.budget_used += 1
            budget_remaining -= 1

            # Select sources based on preferred categories
            candidate_domains = self._select_sources_for_objective(obj, source_filter)

            # Query each source
            for domain in candidate_domains[: obj.max_budget]:
                if budget_remaining <= 0:
                    break

                urls = self._generate_urls_for_domain(domain, obj.query)
                for url in urls:
                    if budget_remaining <= 0:
                        break
                    doc = await self.acquire(
                        url,
                        plan_id=plan.id,
                        objective_id=obj.id,
                        query=obj.query,
                    )
                    if doc:
                        all_evidence.append(doc)
                        obj.documents_found += 1
                        obj.confidence_achieved = min(
                            1.0,
                            obj.confidence_achieved + 0.1 * doc.confidence,
                        )
                    plan.budget_used += 1
                    budget_remaining -= 1

            # Check if objective is satisfied
            if obj.confidence_achieved >= obj.confidence_target:
                obj.status = ObjectiveStatus.COMPLETED
            else:
                obj.status = ObjectiveStatus.COMPLETED  # budget exhausted

        plan.status = "completed"
        self._active_plan = None
        return all_evidence

    # ── Cognitive Integration ──────────────────────────────────────────

    async def integrate_with_memory(
        self,
        evidence: EvidenceDocument,
        memory_system: Any = None,
    ):
        """Integrate an evidence document into Ontogeny's memory systems.

        This connects acquisition to:
        - Episodic memory (what happened)
        - Semantic memory (what was learned)
        - Knowledge graph (relationships)
        - Planning context (for future decisions)
        """
        if memory_system is None:
            return

        # Add to episodic memory
        try:
            episodic = memory_system.episodic if hasattr(memory_system, "episodic") else None
            if episodic:
                await episodic.add(
                    content=f"Acquired information: {evidence.title} from {evidence.source_domain}",
                    importance=evidence.confidence * evidence.relevance_score,
                    metadata={
                        "source": evidence.canonical_url,
                        "domain": evidence.source_domain,
                        "category": evidence.source_category,
                        "evidence_id": evidence.id,
                    },
                )
                self.observability.record_memory("episodic")
        except Exception as e:
            self.logger.debug("episodic_integration_failed", error=str(e))

        # Add to semantic memory
        try:
            semantic = memory_system.semantic if hasattr(memory_system, "semantic") else None
            if semantic:
                for fact in evidence.key_facts:
                    await semantic.add(
                        content=fact,
                        source=evidence.canonical_url,
                        confidence=evidence.confidence,
                    )
                self.observability.record_memory("semantic")
        except Exception as e:
            self.logger.debug("semantic_integration_failed", error=str(e))

        # Add claims to validator
        for claim_text in evidence.supporting_claims:
            self.claim_validator.add_claim(
                text=claim_text,
                subject=evidence.source_domain,
                source_id=evidence.id,
                source_quality=evidence.quality_score,
            )
            self.observability.record_claim(disputed=False)

        for claim_text in evidence.contradictory_claims:
            self.claim_validator.add_claim(
                text=claim_text,
                subject=evidence.source_domain,
                source_id=evidence.id,
                source_quality=evidence.quality_score,
            )
            self.observability.record_claim(disputed=True)

    async def extract_and_store_knowledge(
        self,
        evidence: EvidenceDocument,
        knowledge_graph: Any = None,
    ):
        """Extract knowledge from evidence and store in the knowledge graph."""
        if knowledge_graph is None:
            return

        try:
            concepts, relations = await knowledge_graph.extract_knowledge(
                text=evidence.content[:5000],
                source=evidence.canonical_url,
            )
            for concept in concepts:
                knowledge_graph.add_concept(concept)
            for relation in relations:
                knowledge_graph.add_relation(relation)
            self.observability.record_kg_update()
        except Exception as e:
            self.logger.debug("kg_extraction_failed", error=str(e))

    # ── Internal Methods ───────────────────────────────────────────────

    def _find_crawler_for_url(self, url: str) -> BaseCrawler | None:
        """Find an appropriate crawler for a URL."""
        from urllib.parse import urlparse

        domain = urlparse(url).netloc.lower()

        # Map domains to crawlers
        domain_crawler_map = {
            "github.com": "github",
            "gitlab.com": "gitlab",
            "stackoverflow.com": "stackoverflow",
            "arxiv.org": "arxiv",
            "reddit.com": "reddit",
            "news.ycombinator.com": "hackernews",
            "pypi.org": "pypi",
            "npmjs.org": "npm",
            "crates.io": "crates",
        }

        for d, name in domain_crawler_map.items():
            if d in domain:
                return self._crawlers.get(name)

        # Fallback to webscraper
        return self._crawlers.get("webscraper")

    async def _fetch_via_crawler(
        self,
        crawler: BaseCrawler,
        url: str,
        domain: str,
        quality_score: float,
        plan_id: str,
        objective_id: str,
        query: str,
    ) -> EvidenceDocument | None:
        """Fetch using a registered crawler and wrap result as evidence."""
        try:
            results = []
            async for result in crawler.crawl(url, depth=0):
                results.append(result)
                if len(results) >= 1:
                    break

            if not results:
                return None

            r = results[0]
            return EvidenceDocument(
                canonical_url=r.url,
                title=r.title,
                content=r.content,
                source_domain=domain,
                source_category=self.source_scorer.classify_domain(domain).value,
                extraction_method="crawler",
                content_type=r.content_type.value
                if hasattr(r.content_type, "value")
                else str(r.content_type),
                content_length=len(r.content),
                quality_score=quality_score,
                research_plan_id=plan_id,
                objective_id=objective_id,
                query=query,
                metadata=r.metadata,
            )
        except Exception as e:
            self.logger.warning("crawler_fetch_failed", url=url, error=str(e))
            return None

    async def _fetch_direct(
        self,
        url: str,
        domain: str,
        quality_score: float,
        plan_id: str,
        objective_id: str,
        query: str,
        proxy_endpoint: Any | None = None,
    ) -> EvidenceDocument | None:
        """Direct HTTP fetch as fallback."""
        import httpx

        try:
            policy = self.domain_policies.get_policy(domain)
            timeout = policy.timeout_seconds if policy else 30.0

            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                proxy=proxy_endpoint.url if proxy_endpoint else None,
            ) as client:
                start = time.time()
                response = await client.get(url)
                latency_ms = (time.time() - start) * 1000

                if response.status_code != 200:
                    return None

                self.request_manager.record_bandwidth(len(response.content))

                return EvidenceDocument(
                    canonical_url=str(response.url),
                    title="",
                    content=response.text[:50000],  # cap content size
                    source_domain=domain,
                    source_category=self.source_scorer.classify_domain(domain).value,
                    extraction_method="http",
                    content_type=response.headers.get("content-type", ""),
                    content_length=len(response.content),
                    response_time_ms=latency_ms,
                    quality_score=quality_score,
                    research_plan_id=plan_id,
                    objective_id=objective_id,
                    query=query,
                )
        except Exception as e:
            self.logger.warning("direct_fetch_failed", url=url, error=str(e))
            return None

    def _select_sources_for_objective(
        self,
        objective: Any,
        source_filter: list[str] | None = None,
    ) -> list[str]:
        """Select candidate domains for a research objective."""
        preferred = objective.preferred_categories
        excluded = set(objective.excluded_domains)

        # Get all scored domains
        all_domains = list(self.source_scorer.profiles.keys())

        # If we have preferred categories, filter by those
        if preferred:
            scored = []
            for domain in all_domains:
                if domain in excluded:
                    continue
                category = self.source_scorer.classify_domain(domain)
                if category.value in preferred:
                    scored.append((domain, self.source_scorer.score(domain, category)))
            scored.sort(key=lambda x: x[1].quality_score, reverse=True)
            return [d for d, _ in scored]

        # Otherwise, return all non-excluded domains ranked by quality
        scored = []
        for domain in all_domains:
            if domain in excluded:
                continue
            scored.append((domain, self.source_scorer.score(domain)))
        scored.sort(key=lambda x: x[1].quality_score, reverse=True)
        return [d for d, _ in scored]

    def _generate_urls_for_domain(self, domain: str, query: str) -> list[str]:
        """Generate candidate URLs for a domain and query."""
        # Basic URL generation - can be enhanced with search APIs
        return [f"https://{domain}/{query.replace(' ', '+')}"]

    # ── Observability ──────────────────────────────────────────────────

    def get_dashboard(self) -> dict[str, Any]:
        """Get full dashboard data for the UI."""
        return {
            "research": {
                "active_plan": (
                    self.research_planner.get_plan_summary(self._active_plan)
                    if self._active_plan
                    else None
                ),
                "total_plans": len(self.research_planner.plans),
            },
            "evidence": self.evidence_store.get_stats(),
            "sources": self.source_scorer.get_stats(),
            "policies": self.domain_policies.get_stats(),
            "proxy": self.proxy_manager.get_stats(),
            "requests": self.request_manager.get_stats(),
            "claims": self.claim_validator.get_stats(),
            "revalidation": self.revalidation.get_stats(),
            "metrics": self.observability.get_dashboard_data(),
        }

    def save_state(self):
        """Persist all state to disk."""
        self.evidence_store.save_state()
        self.domain_policies.save_state()
        self.logger.info("acquisition_state_saved")
