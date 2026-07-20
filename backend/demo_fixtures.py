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


# ─── Goal & Plan ───────────────────────────────────────────────────────

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

# ─── Evidence ──────────────────────────────────────────────────────────

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

# ─── Memory Writes ─────────────────────────────────────────────────────

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

# ─── Knowledge Graph ───────────────────────────────────────────────────

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

# ─── Reflection ────────────────────────────────────────────────────────

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

# ─── Maldoror Proposal ────────────────────────────────────────────────

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

# ─── Loading Sequence (9 init stages) ─────────────────────────────────

DEMO_LOADING_STAGES = [
    {"stage": 1, "name": "Initializing Cognitive Core", "description": "Loading orchestrator, memory, and scheduler modules", "duration_ms": 180},
    {"stage": 2, "name": "Spawning Acquisition Engines", "description": "30 knowledge acquisition engines ready (ArXiv, SemanticScholar, HuggingFace...)", "duration_ms": 120},
    {"stage": 3, "name": "Building Persistent Memory", "description": "4-layer memory system: working, episodic, semantic, procedural", "duration_ms": 90},
    {"stage": 4, "name": "Connecting Knowledge Graph", "description": "Initializing graph store with 8 nodes, 8 edges", "duration_ms": 110},
    {"stage": 5, "name": "Calibrating Maldoror", "description": "Recursive self-improvement engine online, 6-phase pipeline ready", "duration_ms": 150},
    {"stage": 6, "name": "Binding NeoCorpus", "description": "Embodiment abstraction layer: Blender + MuJoCo simulators connected", "duration_ms": 80},
    {"stage": 7, "name": "Loading Model Router", "description": "Hybrid model routing: Qwen, DeepSeek, Llama + Maldoror self-improvement engine", "duration_ms": 100},
    {"stage": 8, "name": "Initializing Reflection Engine", "description": "Self-model, metacognition, and confidence tracking online", "duration_ms": 70},
    {"stage": 9, "name": "System Ready", "description": "All subsystems operational. Cognitive architecture fully initialized.", "duration_ms": 50},
]

# ─── Subsystem Status (10 subsystems) ─────────────────────────────────

DEMO_SUBSYSTEMS = {
    "knowledge_acquisition": {
        "name": "Knowledge Acquisition",
        "engines_total": 30,
        "engines_active": 6,
        "requests_today": 847,
        "bandwidth_mb": 12.4,
        "avg_confidence": 0.89,
        "top_sources": ["ArXiv", "Semantic Scholar", "HuggingFace", "GitHub", "Wikipedia"],
    },
    "persistent_memory": {
        "name": "Persistent Memory",
        "layers": {
            "working": {"count": 12, "capacity": 50, "utilization": 0.24},
            "episodic": {"count": 234, "capacity": 10000, "utilization": 0.023},
            "semantic": {"count": 1847, "capacity": 50000, "utilization": 0.037},
            "procedural": {"count": 56, "capacity": 1000, "utilization": 0.056},
        },
        "total_records": 2149,
        "memory_ops_sec": 3.2,
    },
    "knowledge_graph": {
        "name": "Knowledge Graph",
        "nodes": 8,
        "edges": 8,
        "clusters": 3,
        "avg_degree": 2.0,
        "last_updated": "2s ago",
    },
    "goal_management": {
        "name": "Goal Management",
        "active_goals": 1,
        "completed_goals": 7,
        "failed_goals": 0,
        "current_goal": "Neuromorphic computing survey",
        "goal_progress": 0.75,
    },
    "planning": {
        "name": "Planning",
        "active_plans": 1,
        "steps_completed": 4,
        "steps_total": 6,
        "current_plan": "Neuromorphic computing survey",
        "plan_progress": 0.67,
    },
    "reflection": {
        "name": "Reflection",
        "insights_generated": 12,
        "self_model_updates": 3,
        "last_insight_type": "INSIGHT",
        "confidence_trend": "stable",
        "blind_spots_identified": 1,
    },
    "neocorpus": {
        "name": "NeoCorpus (Embodiment)",
        "connected_simulators": ["Blender", "MuJoCo"],
        "active_scene": "None (demo mode)",
        "robot_model": "G1",
        "joint_count": 29,
        "render_mode": "placeholder",
    },
    "runtime_diagnostics": {
        "name": "Runtime Diagnostics",
        "uptime_sec": 342,
        "latency_ms": 42,
        "error_rate": 0.002,
        "circuit_breaker": "closed",
        "ws_connections": 1,
        "gpu_usage_pct": 18.5,
        "memory_usage_mb": 247,
    },
    "behavior_stats": {
        "name": "Behavior Statistics",
        "total_queries": 14,
        "total_discoveries": 23,
        "total_modifications": 0,
        "total_reflections": 5,
        "total_improvements": 1,
        "curiosity_score": 0.78,
        "mastery_score": 0.65,
    },
    "model_routing": {
        "name": "Model Routing",
        "current_model": "maldoror",
        "routing_decisions": [
            {"task": "acquisition_planning", "model": "Qwen2.5:72B", "latency_ms": 120, "confidence": 0.88},
            {"task": "evidence_synthesis", "model": "DeepSeek-Coder-V2:16B", "latency_ms": 200, "confidence": 0.91},
            {"task": "reflection", "model": "maldoror", "latency_ms": 85, "confidence": 0.84},
            {"task": "code_generation", "model": "maldoror", "latency_ms": 95, "confidence": 0.92},
        ],
        "fallback_count": 0,
        "avg_latency_ms": 125,
    },
}

# ─── Maldoror Pipeline Stages ─────────────────────────────────────────

DEMO_MALDOROR_PIPELINE = {
    "stages": [
        {
            "name": "Reasoning",
            "status": "active",
            "description": "Analyzing subsystem telemetry for improvement opportunities",
            "input_sources": ["knowledge_acquisition", "persistent_memory", "reflection", "runtime_diagnostics"],
            "metrics": {"patterns_detected": 3, "anomalies": 0},
        },
        {
            "name": "Synthesis",
            "status": "active",
            "description": "Combining insights across subsystems into coherent proposal",
            "input_sources": ["reasoning"],
            "metrics": {"candidates_generated": 1, "merged": 0},
        },
        {
            "name": "Confidence",
            "status": "completed",
            "description": "Evaluating proposal reliability and expected impact",
            "input_sources": ["synthesis"],
            "metrics": {"confidence_score": 0.87, "impact_estimate": "medium"},
        },
        {
            "name": "Proposal",
            "status": "completed",
            "description": "Generating code change proposal with dry-run diff",
            "input_sources": ["confidence"],
            "metrics": {"diff_lines": 18, "files_affected": 1},
        },
        {
            "name": "Validation",
            "status": "completed",
            "description": "Running syntax check, import safety, and sandbox tests",
            "input_sources": ["proposal"],
            "metrics": {"syntax_valid": True, "import_safe": True, "sandbox_passed": True},
        },
        {
            "name": "Approval",
            "status": "pending",
            "description": "Awaiting human review or automatic approval threshold",
            "input_sources": ["validation"],
            "metrics": {"auto_approve_threshold": 0.95, "current_confidence": 0.87},
        },
    ],
    "version": "v1.2.0",
    "quality_gate": "pass",
    "improvement_pct": 4.2,
    "last_training_loss": 0.0234,
    "total_improvements": 7,
    "rollback_count": 0,
}

# ─── Runtime Metrics (live-updating during demo) ──────────────────────

DEMO_RUNTIME_METRICS = {
    "latency_ms": 42,
    "error_rate": 0.002,
    "uptime_sec": 342,
    "requests_per_sec": 1.8,
    "active_connections": 1,
    "gpu_usage_pct": 18.5,
    "memory_usage_mb": 247,
    "gc_collections": 12,
    "event_loop_utilization": 0.23,
}

# ─── Behavior Statistics ──────────────────────────────────────────────

DEMO_BEHAVIOR_STATS = {
    "queries_total": 14,
    "discoveries_total": 23,
    "modifications_total": 0,
    "reflections_total": 5,
    "improvements_total": 1,
    "curiosity_score": 0.78,
    "mastery_score": 0.65,
    "competence_score": 0.72,
    "autonomy_score": 0.81,
    "session_duration_sec": 342,
    "avg_response_time_ms": 89,
}

# ─── Model Routing Decisions ──────────────────────────────────────────

DEMO_MODEL_ROUTING = {
    "current_model": "maldoror",
    "available_models": ["maldoror", "Qwen2.5:72B", "DeepSeek-Coder-V2:16B", "Llama3.2"],
    "routing_table": [
        {"task_type": "acquisition_planning", "model": "Qwen2.5:72B", "reason": "Best at structured planning"},
        {"task_type": "evidence_synthesis", "model": "DeepSeek-Coder-V2:16B", "reason": "Strong at technical synthesis"},
        {"task_type": "reflection", "model": "maldoror", "reason": "Self-model alignment"},
        {"task_type": "code_generation", "model": "maldoror", "reason": "Self-improvement loop"},
        {"task_type": "fallback", "model": "Llama3.2", "reason": "General purpose fallback"},
    ],
    "decisions_this_session": 14,
    "avg_latency_ms": 125,
    "fallback_count": 0,
}

# ─── Demo Steps (expanded — 9 cognitive stages + 2 meta) ─────────────

DEMO_STEPS = [
    {
        "step": 1,
        "name": "System Initialization",
        "description": "All 9 initialization stages complete — 30 engines, 4-layer memory, Maldoror pipeline, NeoCorpus binding",
        "status": "completed",
        "timestamp": _now() - 350000,
    },
    {
        "step": 2,
        "name": "Goal Received",
        "description": "Ontogeny receives research objective: 'Investigate neuromorphic computing for energy-efficient AI inference'",
        "status": "completed",
        "timestamp": _now() - 300000,
    },
    {
        "step": 3,
        "name": "Plan Generated",
        "description": "Planning system creates 6-step research plan with dependency resolution",
        "status": "completed",
        "timestamp": _now() - 280000,
    },
    {
        "step": 4,
        "name": "Evidence Acquired",
        "description": "Knowledge Acquisition System retrieved 4 documents from ArXiv, Semantic Scholar, and HuggingFace",
        "status": "completed",
        "timestamp": _now() - 200000,
    },
    {
        "step": 5,
        "name": "Evidence Validated",
        "description": "Source quality scorer rated all sources above 0.85 confidence. No contradictions found.",
        "status": "completed",
        "timestamp": _now() - 180000,
    },
    {
        "step": 6,
        "name": "Memory Updated",
        "description": "4 semantic memories and 1 episodic memory written. Knowledge graph: 8 nodes, 8 edges.",
        "status": "completed",
        "timestamp": _now() - 150000,
    },
    {
        "step": 7,
        "name": "Reflection Complete",
        "description": "Identified insight: multi-source triangulation effective. Gap: missing deployment cost data.",
        "status": "completed",
        "timestamp": _now() - 120000,
    },
    {
        "step": 8,
        "name": "Maldoror Pipeline",
        "description": "Recursive improvement engine synthesizes proposal from 4 subsystem signals",
        "status": "completed",
        "timestamp": _now() - 90000,
    },
    {
        "step": 9,
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
            "reflectionSummary": DEMO_REFLECTION["what_worked"] if self.step >= 7 else None,
            "maldororProposal": DEMO_MALDOROR_PROPOSAL["description"] if self.step >= 8 else None,
            "startedAt": self.started_at,
        }

    def get_goal(self) -> dict[str, Any]:
        return DEMO_GOAL

    def get_plan(self) -> dict[str, Any]:
        return DEMO_PLAN

    def get_evidence(self) -> list[dict[str, Any]]:
        if self.step < 4:
            return []
        count = min(self.step - 3, len(DEMO_EVIDENCE))
        return DEMO_EVIDENCE[:count]

    def get_memory_writes(self) -> list[dict[str, Any]]:
        if self.step < 6:
            return []
        count = min(self.step - 5, len(DEMO_MEMORY_WRITES))
        return DEMO_MEMORY_WRITES[:count]

    def get_knowledge_graph(self) -> dict[str, Any]:
        if self.step < 6:
            return {"nodes": [], "edges": []}
        return DEMO_KNOWLEDGE_GRAPH

    def get_reflection(self) -> dict[str, Any] | None:
        if self.step < 7:
            return None
        return DEMO_REFLECTION

    def get_maldoror_proposal(self) -> dict[str, Any] | None:
        if self.step < 8:
            return None
        return DEMO_MALDOROR_PROPOSAL

    def get_subsystems(self) -> dict[str, Any]:
        if not self.active:
            return {}
        return DEMO_SUBSYSTEMS

    def get_loading_stages(self) -> list[dict[str, Any]]:
        return DEMO_LOADING_STAGES

    def get_maldoror_pipeline(self) -> dict[str, Any]:
        import time as _t, math as _m
        elapsed = _t.time() - self.started_at if self.started_at else 0
        # Dynamic improvement curve: grows with oscillation
        imp = min(15.0, elapsed * 0.4 + 2.0 * _m.sin(elapsed * 0.3) + _m.sin(elapsed * 0.7) * 0.8)
        loss = max(0.01, 0.25 - elapsed * 0.005 + 0.02 * _m.sin(elapsed * 0.5))
        total_improvements = 7 + int(elapsed / 8)
        pipeline = dict(DEMO_MALDOROR_PIPELINE)
        pipeline["improvement_pct"] = round(imp, 1)
        pipeline["last_training_loss"] = round(loss, 4)
        pipeline["total_improvements"] = total_improvements
        return pipeline

    def get_runtime_metrics(self) -> dict[str, Any]:
        import time as _t, math as _m, random as _r
        elapsed = _t.time() - self.started_at if self.started_at else 0
        return {
            "latency_ms": max(10, int(42 + 15 * _m.sin(elapsed * 0.8) + _r.gauss(0, 3))),
            "error_rate": round(max(0.001, 0.002 + 0.001 * _m.sin(elapsed * 0.4)), 4),
            "uptime_sec": int(elapsed),
            "gpu_usage_pct": round(min(95, max(20, 45 + 20 * _m.sin(elapsed * 0.3) + _r.gauss(0, 5))), 1),
            "memory_usage_mb": int(247 + 30 * _m.sin(elapsed * 0.2) + _r.gauss(0, 8)),
        }

    def get_behavior_stats(self) -> dict[str, Any]:
        import time as _t, math as _m
        elapsed = _t.time() - self.started_at if self.started_at else 0
        return {
            "curiosity_score": round(min(1.0, 0.78 + 0.1 * _m.sin(elapsed * 0.2)), 2),
            "mastery_score": round(min(1.0, 0.65 + 0.08 * _m.sin(elapsed * 0.15)), 2),
            "competence_score": round(min(1.0, 0.72 + 0.06 * _m.sin(elapsed * 0.25)), 2),
            "autonomy_score": round(min(1.0, 0.60 + 0.12 * _m.sin(elapsed * 0.18)), 2),
            "queries_total": 14 + int(elapsed / 5),
            "discoveries_total": 23 + int(elapsed / 3),
            "reflections_total": 5 + int(elapsed / 10),
            "improvements_total": 1 + int(elapsed / 12),
        }

    def get_model_routing(self) -> dict[str, Any]:
        return DEMO_MODEL_ROUTING

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
