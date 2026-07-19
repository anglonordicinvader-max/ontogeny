"""Tests for the Unified Acquisition Manager system.

Tests cover:
- AcquisitionManager initialization and lifecycle
- ResearchPlanner goal-directed planning
- EvidenceStore storage, deduplication, search
- SourceQualityScorer scoring and classification
- DomainPolicies enforcement
- ProxyManager selection and health
- RequestManager caching, rate limiting, dedup
- ClaimValidator claim tracking
- RevalidationScheduler task management
- AcquisitionObservability metrics
"""

import asyncio
import tempfile
from pathlib import Path

import pytest


# ── Fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def tmp_state_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def acquisition_config(tmp_state_dir):
    from crawler_agent.crawlers.acquisition.manager import AcquisitionConfig
    return AcquisitionConfig(
        state_dir=tmp_state_dir,
        max_concurrent_requests=5,
        max_requests_per_minute=60,
        cache_ttl_seconds=60,
        session_budget=100,
    )


@pytest.fixture
def manager(acquisition_config):
    from crawler_agent.crawlers.acquisition.manager import AcquisitionManager
    return AcquisitionManager(config=acquisition_config)


@pytest.fixture
def evidence_store(tmp_state_dir):
    from crawler_agent.crawlers.acquisition.evidence_store import EvidenceStore
    return EvidenceStore(state_path=Path(tmp_state_dir) / "evidence.json")


@pytest.fixture
def source_scorer():
    from crawler_agent.crawlers.acquisition.source_scorer import SourceQualityScorer
    return SourceQualityScorer()


@pytest.fixture
def domain_policies(tmp_state_dir):
    from crawler_agent.crawlers.acquisition.domain_policies import DomainPolicies
    return DomainPolicies(state_path=Path(tmp_state_dir) / "policies.json")


@pytest.fixture
def claim_validator():
    from crawler_agent.crawlers.acquisition.knowledge_validator import ClaimValidator
    return ClaimValidator()


# ── AcquisitionManager Tests ───────────────────────────────────────────

class TestAcquisitionManager:
    def test_initialization(self, manager):
        assert manager is not None
        assert manager.config is not None
        assert manager.research_planner is not None
        assert manager.evidence_store is not None
        assert manager.source_scorer is not None
        assert manager.domain_policies is not None

    def test_create_research_plan(self, manager):
        plan = manager.create_research_plan(
            objective="Learn about quantum computing",
            description="Research plan for quantum computing",
            budget=100,
            sub_objectives=[
                {"description": "Find academic papers", "query": "quantum computing"},
            ],
        )
        assert plan is not None
        assert plan.objective == "Learn about quantum computing"
        assert len(plan.objectives) == 1
        assert plan.total_budget == 100

    def test_create_plan_from_goal(self, manager):
        plan = manager.create_plan_from_goal(
            goal="Understand neural network architectures",
            context={"domain": "machine_learning"},
        )
        assert plan is not None
        assert len(plan.objectives) > 0
        assert manager._active_plan == plan

    def test_dashboard(self, manager):
        dashboard = manager.get_dashboard()
        assert "research" in dashboard
        assert "evidence" in dashboard
        assert "sources" in dashboard
        assert "policies" in dashboard
        assert "proxy" in dashboard
        assert "requests" in dashboard
        assert "claims" in dashboard
        assert "revalidation" in dashboard
        assert "metrics" in dashboard

    def test_register_crawler(self, manager):
        class MockCrawler:
            name = "test_crawler"
        crawler = MockCrawler()
        manager.register_crawler("test", crawler)
        assert manager.get_crawler("test") is crawler
        assert manager.get_crawler("nonexistent") is None

    def test_save_state(self, manager):
        # Should not raise
        manager.save_state()


# ── ResearchPlanner Tests ──────────────────────────────────────────────

class TestResearchPlanner:
    def test_create_plan(self):
        from crawler_agent.crawlers.acquisition.research_planner import ResearchPlanner
        planner = ResearchPlanner()
        plan = planner.create_plan(
            objective="Test objective",
            sub_objectives=[
                {"description": "Sub 1", "query": "test query", "priority": 10},
                {"description": "Sub 2", "query": "test query 2", "priority": 5},
            ],
        )
        assert plan is not None
        assert len(plan.objectives) == 2
        # Higher priority first
        assert plan.objectives[0].priority >= plan.objectives[1].priority

    def test_create_plan_from_goal(self):
        from crawler_agent.crawlers.acquisition.research_planner import ResearchPlanner
        planner = ResearchPlanner()
        plan = planner.create_plan_from_goal(
            goal_description="Learn about Python libraries",
            memory_relevant_facts=["Python is a programming language"],
        )
        assert plan is not None
        assert len(plan.objectives) >= 3  # auto-generates sub-objectives
        assert plan.metadata.get("memory_context") is not None

    def test_get_next_objective(self):
        from crawler_agent.crawlers.acquisition.research_planner import (
            ResearchPlanner, ObjectiveStatus,
        )
        planner = ResearchPlanner()
        plan = planner.create_plan(
            objective="Test",
            sub_objectives=[
                {"description": "A", "priority": 5},
                {"description": "B", "priority": 10},
            ],
        )
        next_obj = planner.get_next_objective(plan)
        assert next_obj is not None
        assert next_obj.priority == 10  # highest priority first

    def test_should_stop_budget(self):
        from crawler_agent.crawlers.acquisition.research_planner import (
            ResearchPlanner, ResearchPlan,
        )
        planner = ResearchPlanner()
        plan = ResearchPlan(total_budget=5, budget_used=5)
        should_stop, reason = planner.should_stop(plan)
        assert should_stop is True
        assert "budget" in reason.lower()

    def test_should_stop_all_completed(self):
        from crawler_agent.crawlers.acquisition.research_planner import (
            ResearchPlanner, ResearchPlan, ResearchObjective, ObjectiveStatus,
        )
        planner = ResearchPlanner()
        plan = ResearchPlan(total_budget=100)
        obj = ResearchObjective(status=ObjectiveStatus.COMPLETED)
        plan.objectives.append(obj)
        should_stop, reason = planner.should_stop(plan)
        assert should_stop is True

    def test_plan_summary(self):
        from crawler_agent.crawlers.acquisition.research_planner import ResearchPlanner
        planner = ResearchPlanner()
        plan = planner.create_plan(
            objective="Test",
            sub_objectives=[{"description": "A"}],
        )
        summary = planner.get_plan_summary(plan)
        assert "id" in summary
        assert "objectives" in summary


# ── EvidenceStore Tests ────────────────────────────────────────────────

class TestEvidenceStore:
    def test_store_document(self, evidence_store):
        from crawler_agent.crawlers.acquisition.evidence_store import EvidenceDocument
        doc = EvidenceDocument(
            canonical_url="https://example.com/article",
            title="Test Article",
            content="This is test content about quantum computing.",
            source_domain="example.com",
            source_category="tech_docs",
        )
        doc.compute_hash()
        doc_id = evidence_store.store(doc)
        assert doc_id is not None
        assert len(doc_id) > 0

    def test_deduplication(self, evidence_store):
        from crawler_agent.crawlers.acquisition.evidence_store import EvidenceDocument
        doc1 = EvidenceDocument(
            canonical_url="https://example.com/v1",
            title="Test",
            content="Same content here",
            source_domain="example.com",
        )
        doc1.compute_hash()
        id1 = evidence_store.store(doc1)

        doc2 = EvidenceDocument(
            canonical_url="https://example.com/v2",
            title="Test Duplicate",
            content="Same content here",
            source_domain="example.com",
        )
        doc2.compute_hash()
        id2 = evidence_store.store(doc2)

        # Same content hash -> same doc ID
        assert id1 == id2

    def test_search_by_domain(self, evidence_store):
        from crawler_agent.crawlers.acquisition.evidence_store import EvidenceDocument
        for i in range(3):
            doc = EvidenceDocument(
                canonical_url=f"https://example.com/{i}",
                content=f"Content {i}",
                source_domain="example.com",
            )
            doc.compute_hash()
            evidence_store.store(doc)

        results = evidence_store.find_by_domain("example.com")
        assert len(results) == 3

    def test_search_by_tag(self, evidence_store):
        from crawler_agent.crawlers.acquisition.evidence_store import EvidenceDocument
        doc = EvidenceDocument(
            canonical_url="https://example.com/tagged",
            content="Tagged content",
            tags=["quantum", "physics"],
        )
        doc.compute_hash()
        evidence_store.store(doc)

        results = evidence_store.find_by_tag("quantum")
        assert len(results) == 1

    def test_aggregate_confidence(self, evidence_store):
        from crawler_agent.crawlers.acquisition.evidence_store import EvidenceDocument
        for i in range(3):
            doc = EvidenceDocument(
                canonical_url=f"https://example.com/{i}",
                content=f"Content {i}",
                source_domain="example.com",
                confidence=0.5 + i * 0.1,
            )
            doc.compute_hash()
            evidence_store.store(doc)

        agg = evidence_store.compute_aggregate_confidence("example.com")
        assert 0.5 <= agg <= 0.9

    def test_stats(self, evidence_store):
        stats = evidence_store.get_stats()
        assert "total_documents" in stats

    def test_save_load_state(self, tmp_state_dir):
        from crawler_agent.crawlers.acquisition.evidence_store import (
            EvidenceStore, EvidenceDocument,
        )
        path = Path(tmp_state_dir) / "test_evidence.json"
        store = EvidenceStore(state_path=path)
        doc = EvidenceDocument(
            canonical_url="https://example.com/persist",
            content="Persist me",
            source_domain="example.com",
        )
        doc.compute_hash()
        store.store(doc)
        store.save_state()

        # Load from disk
        store2 = EvidenceStore(state_path=path)
        assert len(store2.documents) == 1


# ── SourceQualityScorer Tests ──────────────────────────────────────────

class TestSourceQualityScorer:
    def test_classify_domain(self, source_scorer):
        from crawler_agent.crawlers.acquisition.source_scorer import SourceCategory
        assert source_scorer.classify_domain("arxiv.org") == SourceCategory.ACADEMIC
        assert source_scorer.classify_domain("github.com") == SourceCategory.TECH_DOCS
        assert source_scorer.classify_domain("stackoverflow.com") == SourceCategory.FORUM
        assert source_scorer.classify_domain("api.github.com") == SourceCategory.OFFICIAL_API

    def test_score(self, source_scorer):
        from crawler_agent.crawlers.acquisition.source_scorer import SourceCategory
        score = source_scorer.score("arxiv.org", SourceCategory.ACADEMIC)
        assert score.quality_score > 0.5
        assert score.category == SourceCategory.ACADEMIC
        assert score.recommendation in ("prefer", "acceptable")

    def test_update_from_fetch(self, source_scorer):
        source_scorer.update_from_fetch("example.com", success=True, latency_ms=100)
        profile = source_scorer.get_profile("example.com")
        assert profile.total_fetches == 1
        assert profile.successful_fetches == 1
        assert profile.avg_latency_ms > 0

    def test_corroboration(self, source_scorer):
        source_scorer.update_corroboration("example.com", agrees=True)
        source_scorer.update_corroboration("example.com", agrees=True)
        source_scorer.update_corroboration("example.com", agrees=False)
        profile = source_scorer.get_profile("example.com")
        assert profile.corroboration_count == 2
        assert profile.contradiction_count == 1

    def test_rank_sources(self, source_scorer):
        from crawler_agent.crawlers.acquisition.source_scorer import SourceCategory
        source_scorer.classify_domain("arxiv.org")
        source_scorer.classify_domain("blog.example.com")
        ranked = source_scorer.rank_sources(["arxiv.org", "blog.example.com"])
        assert len(ranked) == 2
        # Academic should rank higher than unknown blog
        assert ranked[0].quality_score >= ranked[1].quality_score

    def test_stats(self, source_scorer):
        source_scorer.score("test.com")
        stats = source_scorer.get_stats()
        assert stats["total_sources"] >= 1


# ── DomainPolicies Tests ──────────────────────────────────────────────

class TestDomainPolicies:
    def test_get_policy(self, domain_policies):
        policy = domain_policies.get_policy("example.com")
        assert policy is not None
        assert policy.domain == "example.com"
        assert policy.enabled is True

    def test_is_allowed_default(self, domain_policies):
        assert domain_policies.is_allowed("example.com") is True

    def test_pause_domain(self, domain_policies):
        domain_policies.pause_domain("example.com", "maintenance")
        assert domain_policies.is_allowed("example.com") is False
        domain_policies.resume_domain("example.com")
        assert domain_policies.is_allowed("example.com") is True

    def test_global_pause(self, domain_policies):
        domain_policies.pause_global("system update")
        assert domain_policies.is_allowed("any.domain.com") is False
        domain_policies.resume_global()
        assert domain_policies.is_allowed("any.domain.com") is True

    def test_emergency_stop(self, domain_policies):
        domain_policies.emergency_stop()
        assert domain_policies.is_allowed("any.domain.com") is False

    def test_denylist(self, domain_policies):
        domain_policies.add_to_denylist("blocked.com")
        assert domain_policies.is_allowed("blocked.com") is False
        assert domain_policies.is_allowed("allowed.com") is True
        domain_policies.remove_from_denylist("blocked.com")
        assert domain_policies.is_allowed("blocked.com") is True

    def test_allowlist(self, domain_policies):
        domain_policies.add_to_allowlist("allowed.com")
        assert domain_policies.is_allowed("allowed.com") is True
        assert domain_policies.is_allowed("other.com") is False
        domain_policies.remove_from_allowlist("allowed.com")

    def test_save_load(self, tmp_state_dir):
        from crawler_agent.crawlers.acquisition.domain_policies import DomainPolicies
        path = Path(tmp_state_dir) / "test_policies.json"
        dp = DomainPolicies(state_path=path)
        dp.pause_domain("test.com", "testing")
        dp.save_state()

        dp2 = DomainPolicies(state_path=path)
        assert dp2.get_policy("test.com").paused is True

    def test_stats(self, domain_policies):
        stats = domain_policies.get_stats()
        assert "total_policies" in stats


# ── ProxyManager Tests ────────────────────────────────────────────────

class TestProxyManager:
    def test_register_and_select(self):
        from crawler_agent.crawlers.acquisition.proxy_manager import (
            ProxyManager, ProxyEndpoint,
        )
        pm = ProxyManager()
        proxy = ProxyEndpoint(url="http://proxy:8080", name="test_proxy", region="us")
        pm.register(proxy)
        selected = pm.select(domain="example.com")
        assert selected is not None
        assert selected.name == "test_proxy"

    def test_health_tracking(self):
        from crawler_agent.crawlers.acquisition.proxy_manager import (
            ProxyManager, ProxyEndpoint, ProxyStatus,
        )
        pm = ProxyManager()
        proxy = ProxyEndpoint(url="http://proxy:8080", name="test")
        pm.register(proxy)
        # Simulate failures
        for _ in range(5):
            pm.record_result("test", success=False)
        assert proxy.status == ProxyStatus.UNHEALTHY

    def test_select_region(self):
        from crawler_agent.crawlers.acquisition.proxy_manager import (
            ProxyManager, ProxyEndpoint,
        )
        pm = ProxyManager()
        pm.register(ProxyEndpoint(url="http://us:8080", name="us", region="us"))
        pm.register(ProxyEndpoint(url="http://eu:8080", name="eu", region="eu"))
        selected = pm.select(region="eu")
        assert selected is not None
        assert selected.region == "eu"

    def test_stats(self):
        from crawler_agent.crawlers.acquisition.proxy_manager import ProxyManager
        pm = ProxyManager()
        stats = pm.get_stats()
        assert stats["total"] == 0


# ── RequestManager Tests ──────────────────────────────────────────────

class TestRequestManager:
    def test_cache(self):
        from crawler_agent.crawlers.acquisition.request_manager import RequestManager
        rm = RequestManager()
        rm.store_cache("https://example.com", 200, b"content", {"ct": "text/html"})
        cached = rm.get_cached("https://example.com")
        assert cached is not None
        assert cached.content == b"content"

    def test_cache_miss(self):
        from crawler_agent.crawlers.acquisition.request_manager import RequestManager
        rm = RequestManager()
        cached = rm.get_cached("https://nonexistent.com")
        assert cached is None

    def test_deduplication(self):
        from crawler_agent.crawlers.acquisition.request_manager import RequestManager
        rm = RequestManager()
        assert rm.is_duplicate("https://example.com") is False
        rm._request_history["https://example.com"] = __import__("time").time()
        assert rm.is_duplicate("https://example.com") is True

    def test_budget(self):
        from crawler_agent.crawlers.acquisition.request_manager import RequestManager
        rm = RequestManager(budget_per_session=5)
        assert rm.can_request() is True
        rm._total_budget_used = 5
        assert rm.can_request() is False

    def test_stats(self):
        from crawler_agent.crawlers.acquisition.request_manager import RequestManager
        rm = RequestManager()
        stats = rm.get_stats()
        assert "total_requests" in stats
        assert "cache_hit_rate" in stats


# ── ClaimValidator Tests ───────────────────────────────────────────────

class TestClaimValidator:
    def test_add_claim(self, claim_validator):
        from crawler_agent.crawlers.acquisition.knowledge_validator import Claim
        claim = claim_validator.add_claim(
            text="Python is a programming language",
            subject="Python",
            predicate="is",
            obj="programming language",
            source_id="src1",
            source_quality=0.8,
        )
        assert claim is not None
        assert claim.confidence > 0.5

    def test_duplicate_claim_merges(self, claim_validator):
        c1 = claim_validator.add_claim(
            text="Fact A",
            subject="Topic",
            predicate="has",
            obj="property",
            source_id="s1",
        )
        c2 = claim_validator.add_claim(
            text="Fact A confirmed",
            subject="Topic",
            predicate="has",
            obj="property",
            source_id="s2",
        )
        # Should be the same claim with merged evidence
        assert c1.id == c2.id
        assert c1.supporting_count == 2

    def test_contradiction(self, claim_validator):
        claim = claim_validator.add_claim(
            text="X is true",
            subject="X",
            predicate="is",
            obj="true",
            source_id="s1",
        )
        # Directly add contradiction via the Claim object
        claim.add_contradiction("s2", source_quality=0.8)
        claim.add_contradiction("s3", source_quality=0.7)
        disputed = claim_validator.get_disputed_claims()
        assert len(disputed) >= 1

    def test_find_claims(self, claim_validator):
        claim_validator.add_claim(text="A", subject="Topic1", predicate="p", obj="a")
        claim_validator.add_claim(text="B", subject="Topic2", predicate="p", obj="b")
        results = claim_validator.find_claims(subject="Topic1")
        assert len(results) == 1

    def test_stats(self, claim_validator):
        stats = claim_validator.get_stats()
        assert "total_claims" in stats


# ── RevalidationScheduler Tests ────────────────────────────────────────

class TestRevalidationScheduler:
    def test_schedule_stale_check(self):
        from crawler_agent.crawlers.acquisition.revalidation import RevalidationScheduler
        rs = RevalidationScheduler()
        task = rs.schedule_stale_check("claim1", "https://example.com", "example.com")
        assert task is not None
        pending = rs.get_pending_tasks()
        assert len(pending) == 1

    def test_complete_task(self):
        from crawler_agent.crawlers.acquisition.revalidation import RevalidationScheduler
        rs = RevalidationScheduler()
        task = rs.schedule_stale_check("claim1", "url", "domain")
        rs.complete_task(task.id, success=True, summary="Still valid")
        pending = rs.get_pending_tasks()
        assert len(pending) == 0

    def test_stats(self):
        from crawler_agent.crawlers.acquisition.revalidation import RevalidationScheduler
        rs = RevalidationScheduler()
        stats = rs.get_stats()
        assert "total_tasks" in stats


# ── AcquisitionObservability Tests ──────────────────────────────────────────

class TestAcquisitionObservability:
    def test_record_request(self):
        from crawler_agent.crawlers.acquisition.observability import AcquisitionObservability
        obs = AcquisitionObservability()
        obs.record_request(latency_ms=150.0, success=True)
        obs.record_request(latency_ms=200.0, success=False)
        snap = obs.snapshot()
        assert snap.total_requests == 2
        assert snap.failed_requests == 1

    def test_record_evidence(self):
        from crawler_agent.crawlers.acquisition.observability import AcquisitionObservability
        obs = AcquisitionObservability()
        obs.record_evidence(accepted=True)
        obs.record_evidence(accepted=False, duplicate=True)
        snap = obs.snapshot()
        assert snap.evidence_stored == 2
        assert snap.evidence_accepted == 1
        assert snap.evidence_duplicates == 1

    def test_dashboard_data(self):
        from crawler_agent.crawlers.acquisition.observability import AcquisitionObservability
        obs = AcquisitionObservability()
        data = obs.get_dashboard_data()
        assert "status" in data
        assert "requests_per_minute" in data
        assert "cache_hit_rate" in data

    def test_multiple_snapshots(self):
        from crawler_agent.crawlers.acquisition.observability import AcquisitionObservability
        obs = AcquisitionObservability()
        obs.record_request()
        obs.snapshot()
        obs.record_request()
        obs.snapshot()
        assert len(obs.snapshots) == 2


# ── Integration Tests ─────────────────────────────────────────────────

class TestIntegration:
    def test_full_pipeline(self, manager):
        """Test the full acquisition pipeline."""
        # Create a plan
        plan = manager.create_research_plan(
            objective="Test research",
            sub_objectives=[
                {"description": "Find info", "query": "test", "categories": ["tech_docs"]},
            ],
        )
        assert plan is not None
        assert len(plan.objectives) == 1

        # Check dashboard
        dashboard = manager.get_dashboard()
        assert dashboard["research"]["active_plan"] is not None

    def test_source_scoring_integration(self, manager):
        """Test source scoring with the manager."""
        from crawler_agent.crawlers.acquisition.source_scorer import SourceCategory
        manager.source_scorer.classify_domain("docs.python.org")
        score = manager.source_scorer.score("docs.python.org", SourceCategory.OFFICIAL_DOCS)
        assert score.quality_score > 0.5

    def test_domain_policy_integration(self, manager):
        """Test domain policies with the manager."""
        assert manager.domain_policies.is_allowed("example.com") is True
        manager.domain_policies.pause_domain("example.com")
        assert manager.domain_policies.is_allowed("example.com") is False
        manager.domain_policies.resume_domain("example.com")

    def test_claim_validator_with_evidence(self, manager):
        """Test claims linked to evidence."""
        from crawler_agent.crawlers.acquisition.evidence_store import EvidenceDocument
        doc = EvidenceDocument(
            canonical_url="https://example.com/claim",
            content="Test content with claims",
            source_domain="example.com",
        )
        doc.compute_hash()
        doc_id = manager.evidence_store.store(doc)

        claim = manager.claim_validator.add_claim(
            text="Quantum computing uses qubits",
            subject="quantum_computing",
            predicate="uses",
            obj="qubits",
            source_id=doc_id,
            source_quality=0.8,
        )
        assert claim.confidence > 0.5
