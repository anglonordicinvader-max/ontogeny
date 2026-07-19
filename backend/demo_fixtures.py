"""Demo Mode fixtures — realistic, deterministic data for hackathon demonstration.

All data is based on real system schemas. No live LLM calls, no network requests,
no source code modification. Labeled as controlled demonstration fixtures.
"""

import time
import uuid
from typing import Any


def _now() -> int:
    return int(time.time() * 1000)


def _id() -> str:
    return uuid.uuid4().hex[:12]


DEMO_GOAL = {
    "id": "demo-goal-001",
    "description": "Investigate recent advances in neuromorphic computing for energy-efficient AI inference",
    "status": "active",
    "progress": 0.0,
    "priority": "high",
    "subgoals": [
        {
            "id": "demo-sub-001",
            "description": "Survey current neuromorphic chip architectures (Intel Loihi, IBM TrueNorth, SynSense)",
            "status": "pending",
            "progress": 0.0,
            "priority": "high",
        },
        {
            "id": "demo-sub-002",
            "description": "Compare energy efficiency metrics across neuromorphic vs traditional GPU inference",
            "status": "pending",
            "progress": 0.0,
            "priority": "medium",
        },
        {
            "id": "demo-sub-003",
            "description": "Identify practical deployment scenarios where neuromorphic computing offers clear advantage",
            "status": "pending",
            "progress": 0.0,
            "priority": "medium",
        },
    ],
}

DEMO_PLAN = {
    "id": "demo-plan-001",
    "goal_id": "demo-goal-001",
    "description": "Research plan: Neuromorphic computing survey",
    "status": "active",
    "steps": [
        {
            "id": "step-1",
            "description": "Search ArXiv for recent neuromorphic computing papers",
            "action": "acquire",
            "parameters": {"source": "arxiv", "query": "neuromorphic computing energy efficient inference 2024 2025"},
            "status": "completed",
            "confidence": 0.92,
            "result": "Found 12 relevant papers from 2024-2025",
        },
        {
            "id": "step-2",
            "description": "Search Semantic Scholar for citation-backed survey data",
            "action": "acquire",
            "parameters": {"source": "semantic_scholar", "query": "neuromorphic hardware survey comparison"},
            "status": "completed",
            "confidence": 0.88,
            "result": "Found 8 highly-cited survey papers",
        },
        {
            "id": "step-3",
            "description": "Retrieve energy benchmark data from HuggingFace",
            "action": "acquire",
            "parameters": {"source": "huggingface", "query": "neuromorphic benchmark energy"},
            "status": "completed",
            "confidence": 0.85,
            "result": "Found 3 benchmark datasets with energy metrics",
        },
        {
            "id": "step-4",
            "description": "Synthesize findings and write evidence summary",
            "action": "reason",
            "parameters": {},
            "status": "completed",
            "confidence": 0.90,
            "result": "Evidence summary compiled with 23 source citations",
        },
        {
            "id": "step-5",
            "description": "Store key findings in semantic memory",
            "action": "memory_write",
            "parameters": {},
            "status": "completed",
            "confidence": 0.95,
            "result": "4 concepts, 7 relations added to knowledge graph",
        },
        {
            "id": "step-6",
            "description": "Reflect on research quality and identify gaps",
            "action": "reflect",
            "parameters": {},
            "status": "completed",
            "confidence": 0.87,
            "result": "Identified gap: missing real-world deployment cost data",
        },
    ],
}

DEMO_EVIDENCE = [
    {
        "id": _id(),
        "url": "https://arxiv.org/abs/2403.12456",
        "title": "Loihi 2: A 128-Core Neuromorphic Processor with On-Chip Learning",
        "source": "ArXiv",
        "source_category": "research_paper",
        "author": "Orchard, G. et al.",
        "organization": "Intel Labs",
        "retrieved_at": _now() - 120000,
        "confidence": 0.94,
        "summary": "Intel Loihi 2 achieves 10x energy efficiency over GPU inference for spiking neural network workloads. On-chip learning enables adaptive deployment without cloud connectivity.",
        "claims": [
            {"text": "Loihi 2 achieves 10x energy efficiency over GPU", "confidence": 0.94, "supporting_sources": 3},
            {"text": "On-chip learning eliminates cloud dependency", "confidence": 0.91, "supporting_sources": 2},
        ],
        "relevance_score": 0.96,
    },
    {
        "id": _id(),
        "url": "https://arxiv.org/abs/2405.09876",
        "title": "A Survey of Neuromorphic Computing: Architecture, Algorithms, and Applications",
        "source": "ArXiv",
        "source_category": "research_paper",
        "author": "Davies, M. et al.",
        "organization": "Georgia Tech",
        "retrieved_at": _now() - 90000,
        "confidence": 0.92,
        "summary": "Comprehensive survey covering 47 neuromorphic architectures. Identifies key bottleneck: software toolchain maturity, not hardware capability.",
        "claims": [
            {"text": "Software toolchain is the primary adoption bottleneck", "confidence": 0.89, "supporting_sources": 5},
            {"text": "47 architectures reviewed across 3 generations", "confidence": 0.97, "supporting_sources": 1},
        ],
        "relevance_score": 0.93,
    },
    {
        "id": _id(),
        "url": "https://api.semanticscholar.org/paper/2024.neuromorphic.benchmark",
        "title": "Benchmarking Neuromorphic Chips: Energy Latency Trade-offs in Real-World Tasks",
        "source": "Semantic Scholar",
        "source_category": "research_paper",
        "author": "Chen, Y. et al.",
        "organization": "MIT",
        "retrieved_at": _now() - 60000,
        "confidence": 0.90,
        "summary": "Quantitative comparison of Loihi 2, TrueNorth, and SpiNNaker2 on NLP, vision, and control tasks. Neuromorphic advantage is task-dependent: 5-50x efficiency on sparse workloads, marginal on dense matrices.",
        "claims": [
            {"text": "5-50x efficiency advantage on sparse workloads", "confidence": 0.90, "supporting_sources": 4},
            {"text": "Marginal advantage on dense matrix operations", "confidence": 0.88, "supporting_sources": 3},
        ],
        "relevance_score": 0.91,
    },
    {
        "id": _id(),
        "url": "https://huggingface.co/datasets/neuromorphic-bench-2024",
        "title": "Neuromorphic Benchmark Dataset 2024",
        "source": "HuggingFace",
        "source_category": "technical_documentation",
        "author": "Community",
        "organization": "Open Source",
        "retrieved_at": _now() - 30000,
        "confidence": 0.85,
        "summary": "Standardized benchmark suite with energy measurements for 12 neuromorphic chips across 8 task categories. Includes power profiling scripts.",
        "claims": [
            {"text": "12 chips benchmarked across 8 task categories", "confidence": 0.95, "supporting_sources": 1},
        ],
        "relevance_score": 0.87,
    },
]

DEMO_MEMORY_WRITES = [
    {
        "type": "semantic",
        "content": "Neuromorphic computing (Intel Loihi 2) achieves 10x energy efficiency over GPU for SNN workloads",
        "importance": 0.9,
        "source": "ArXiv 2403.12456",
    },
    {
        "type": "semantic",
        "content": "Primary adoption bottleneck is software toolchain maturity, not hardware capability",
        "importance": 0.85,
        "source": "Survey 2405.09876",
    },
    {
        "type": "episodic",
        "content": "Completed neuromorphic computing survey: 23 sources analyzed, key finding is task-dependent advantage",
        "importance": 0.8,
        "source": "Demo session",
    },
    {
        "type": "semantic",
        "content": "Neuromorphic advantage is sparse (5-50x) vs dense (marginal) — deployment scenario matters",
        "importance": 0.88,
        "source": "Benchmark 2024",
    },
]

DEMO_KNOWLEDGE_GRAPH = {
    "nodes": [
        {"id": "n1", "name": "Neuromorphic Computing", "type": "concept", "connections": 5, "strength": 0.95},
        {"id": "n2", "name": "Intel Loihi 2", "type": "hardware", "connections": 3, "strength": 0.9},
        {"id": "n3", "name": "Spiking Neural Networks", "type": "algorithm", "connections": 4, "strength": 0.88},
        {"id": "n4", "name": "Energy Efficiency", "type": "metric", "connections": 3, "strength": 0.92},
        {"id": "n5", "name": "IBM TrueNorth", "type": "hardware", "connections": 2, "strength": 0.82},
        {"id": "n6", "name": "Software Toolchain", "type": "bottleneck", "connections": 2, "strength": 0.85},
        {"id": "n7", "name": "Sparse Workloads", "type": "workload", "connections": 2, "strength": 0.87},
        {"id": "n8", "name": "On-Chip Learning", "type": "capability", "connections": 2, "strength": 0.84},
    ],
    "edges": [
        {"source": "n1", "target": "n2", "type": "implements", "weight": 0.9},
        {"source": "n1", "target": "n3", "type": "uses", "weight": 0.95},
        {"source": "n1", "target": "n4", "type": "optimizes", "weight": 0.92},
        {"source": "n2", "target": "n3", "type": "runs", "weight": 0.88},
        {"source": "n2", "target": "n8", "type": "supports", "weight": 0.85},
        {"source": "n1", "target": "n5", "type": "alternative", "weight": 0.75},
        {"source": "n1", "target": "n6", "type": "limited_by", "weight": 0.82},
        {"source": "n3", "target": "n7", "type": "optimized_for", "weight": 0.87},
    ],
}

DEMO_REFLECTION = {
    "type": "INSIGHT",
    "severity": "low",
    "what_worked": "Multi-source acquisition strategy provided convergent evidence from 4 independent sources",
    "what_failed": "No practical deployment cost data found — all sources focused on research benchmarks",
    "root_cause": "Neuromorphic deployment is still primarily in research phase; commercial cost data is proprietary",
    "lesson": "For hardware-focused topics, prioritize industry reports and patent filings alongside academic papers",
    "self_model_update": {
        "strength_added": "Effective multi-source triangulation strategy",
        "weakness_identified": "Limited access to proprietary industry data",
        "blind_spot": "Assuming academic coverage equals practical coverage",
    },
    "confidence_delta": -0.03,
    "emotional_impact": "Satisfied with research quality, curious about deployment costs",
}

DEMO_MALDOROR_PROPOSAL = {
    "id": _id(),
    "target": "scheduler.py",
    "file_path": "src/crawler_agent/cognitive/scheduler.py",
    "description": "Add source-category-aware scheduling to prioritize research papers over forums for hardware topics",
    "reasoning": "Current scheduler treats all source categories equally. For hardware research topics, research papers and technical documentation consistently provide higher-confidence evidence than forums and blogs.",
    "expected_benefit": "Improved evidence quality for hardware/technology research topics by 15-20%",
    "risks": ["Low risk — additive change to scheduling heuristic"],
    "validation": {
        "syntax_valid": True,
        "import_safe": True,
        "sandbox_passed": True,
        "applied": False,
        "rolled_back": False,
    },
    "status": "proposed",
    "dry_run_diff": """--- a/src/crawler_agent/cognitive/scheduler.py
+++ b/src/crawler_agent/cognitive/scheduler.py
@@ -45,6 +45,12 @@
 class AcquisitionScheduler:
     def __init__(self, source_scorer: SourceQualityScorer):
         self.source_scorer = source_scorer
+        self.topic_source_priority = {
+            "hardware": ["research_paper", "technical_documentation"],
+            "software": ["technical_documentation", "research_paper"],
+            "science": ["research_paper", "government"],
+        }
 
     def prioritize_sources(self, topic: str, sources: list) -> list:
-        return sorted(sources, key=lambda s: s.quality_score, reverse=True)
+        topic_category = self._classify_topic(topic)
+        priority_types = self.topic_source_priority.get(topic_category, [])
+        def sort_key(s):
+            base = s.quality_score
+            if s.source_category in priority_types:
+                base += 0.1  # Boost priority sources
+            return base
+        return sorted(sources, key=sort_key, reverse=True)""",
}

DEMO_STEPS = [
    {
        "step": 1,
        "name": "Goal Received",
        "description": "Ontogeny receives research objective: 'Investigate neuromorphic computing for energy-efficient AI inference'",
        "status": "completed",
        "timestamp": _now() - 300000,
    },
    {
        "step": 2,
        "name": "Plan Generated",
        "description": "Planning system creates 6-step research plan with dependency resolution",
        "status": "completed",
        "timestamp": _now() - 280000,
    },
    {
        "step": 3,
        "name": "Evidence Acquired",
        "description": "Knowledge Acquisition System retrieved 4 documents from ArXiv, Semantic Scholar, and HuggingFace",
        "status": "completed",
        "timestamp": _now() - 200000,
    },
    {
        "step": 4,
        "name": "Evidence Validated",
        "description": "Source quality scorer rated all sources above 0.85 confidence. No contradictions found.",
        "status": "completed",
        "timestamp": _now() - 180000,
    },
    {
        "step": 5,
        "name": "Memory Updated",
        "description": "4 semantic memories and 1 episodic memory written. Knowledge graph: 8 nodes, 8 edges.",
        "status": "completed",
        "timestamp": _now() - 150000,
    },
    {
        "step": 6,
        "name": "Reflection Complete",
        "description": "Identified insight: multi-source triangulation effective. Gap: missing deployment cost data.",
        "status": "completed",
        "timestamp": _now() - 120000,
    },
    {
        "step": 7,
        "name": "Maldoror Proposal",
        "description": "Proposed improvement: source-category-aware scheduling for hardware research topics",
        "status": "completed",
        "timestamp": _now() - 90000,
    },
    {
        "step": 8,
        "name": "Demo Complete",
        "description": "Session summary: 23 sources analyzed, 4 concepts added to KG, 1 improvement proposed",
        "status": "completed",
        "timestamp": _now() - 60000,
    },
]


class DemoSession:
    """Manages demo state across multiple WebSocket clients."""

    def __init__(self):
        self.active = False
        self.step = 0
        self.total_steps = len(DEMO_STEPS)
        self.started_at: int | None = None
        self.events: list[dict[str, Any]] = []

    def start(self) -> dict[str, Any]:
        self.active = True
        self.step = 1
        self.started_at = _now()
        self.events = []
        self._add_event("demo", "Demo Mode started — Investigating neuromorphic computing")
        return self.get_status()

    def advance(self) -> dict[str, Any]:
        if not self.active or self.step >= self.total_steps:
            return self.get_status()
        self.step += 1
        step_data = DEMO_STEPS[self.step - 1]
        self._add_event("demo", step_data["description"])
        return self.get_status()

    def reset(self) -> dict[str, Any]:
        self.active = False
        self.step = 0
        self.started_at = None
        self.events = []
        return self.get_status()

    def get_status(self) -> dict[str, Any]:
        current_step = DEMO_STEPS[self.step - 1] if self.step > 0 and self.step <= self.total_steps else None
        return {
            "active": self.active,
            "step": self.step,
            "totalSteps": self.total_steps,
            "stepName": current_step["name"] if current_step else "Idle",
            "goal": DEMO_GOAL["description"],
            "evidenceCount": len(DEMO_EVIDENCE),
            "memoryWrites": len(DEMO_MEMORY_WRITES),
            "reflectionSummary": DEMO_REFLECTION["what_worked"] if self.step >= 6 else None,
            "maldororProposal": DEMO_MALDOROR_PROPOSAL["description"] if self.step >= 7 else None,
            "startedAt": self.started_at,
        }

    def get_goal(self) -> dict[str, Any]:
        return DEMO_GOAL

    def get_plan(self) -> dict[str, Any]:
        return DEMO_PLAN

    def get_evidence(self) -> list[dict[str, Any]]:
        if self.step < 3:
            return []
        count = min(self.step - 2, len(DEMO_EVIDENCE))
        return DEMO_EVIDENCE[:count]

    def get_memory_writes(self) -> list[dict[str, Any]]:
        if self.step < 5:
            return []
        count = min(self.step - 4, len(DEMO_MEMORY_WRITES))
        return DEMO_MEMORY_WRITES[:count]

    def get_knowledge_graph(self) -> dict[str, Any]:
        if self.step < 5:
            return {"nodes": [], "edges": []}
        return DEMO_KNOWLEDGE_GRAPH

    def get_reflection(self) -> dict[str, Any] | None:
        if self.step < 6:
            return None
        return DEMO_REFLECTION

    def get_maldoror_proposal(self) -> dict[str, Any] | None:
        if self.step < 7:
            return None
        return DEMO_MALDOROR_PROPOSAL

    def get_events(self) -> list[dict[str, Any]]:
        return self.events

    def _add_event(self, event_type: str, message: str):
        self.events.append({
            "id": _id(),
            "timestamp": _now(),
            "type": event_type,
            "message": message,
        })


demo_session = DemoSession()
