"""Self-audit and health reporting module.

Periodically produces health reports and integrity checks:
- System health audit (all components)
- Memory integrity check
- Knowledge graph consistency
- Performance metrics
- Anomaly detection
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog


@dataclass
class AuditCheck:
    """Result of a single audit check."""

    name: str
    passed: bool
    severity: str = "info"  # info, warning, critical
    message: str = ""
    details: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class HealthReport:
    """Complete health report from a self-audit."""

    id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    overall_healthy: bool = True
    checks: list[AuditCheck] = field(default_factory=list)
    summary: str = ""
    metrics: dict = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "overall_healthy": self.overall_healthy,
            "checks": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "severity": c.severity,
                    "message": c.message,
                }
                for c in self.checks
            ],
            "summary": self.summary,
            "metrics": self.metrics,
            "recommendations": self.recommendations,
            "duration_ms": self.duration_ms,
        }


class SelfAuditor:
    """Performs periodic self-audits and generates health reports."""

    def __init__(self, data_dir: str = "data/audits"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logger = structlog.get_logger(component="self_auditor")
        self.audit_history: list[HealthReport] = []
        self._audit_interval_hours: float = 6.0
        self._last_audit_time: datetime | None = None

    async def run_full_audit(self, orchestrator) -> HealthReport:
        """Run comprehensive self-audit on all systems."""
        start = time.perf_counter()
        report = HealthReport()
        checks = []

        # 1. System health check
        checks.extend(await self._check_system_health(orchestrator))

        # 2. Memory integrity check
        checks.extend(await self._check_memory_integrity(orchestrator))

        # 3. Knowledge graph consistency
        checks.extend(await self._check_knowledge_graph(orchestrator))

        # 4. Crawler health
        checks.extend(await self._check_crawlers(orchestrator))

        # 5. LLM backend health
        checks.extend(await self._check_llm_backends(orchestrator))

        # 6. Performance metrics
        metrics = await self._collect_metrics(orchestrator)

        # 7. Anomaly detection
        anomalies = await self._detect_anomalies(orchestrator, metrics)

        # 8. Generate recommendations
        recommendations = self._generate_recommendations(checks, metrics, anomalies)

        elapsed = (time.perf_counter() - start) * 1000

        report.checks = checks
        report.metrics = metrics
        report.recommendations = recommendations
        report.duration_ms = elapsed
        report.overall_healthy = all(
            c.passed or c.severity == "info" for c in checks if c.severity != "info"
        )
        report.summary = self._generate_summary(checks, metrics)
        report.id = f"audit_{int(time.time())}"

        # Save report
        self.audit_history.append(report)
        await self._save_report(report)

        self.logger.info(
            "audit_complete",
            report_id=report.id,
            healthy=report.overall_healthy,
            checks=len(checks),
            warnings=sum(1 for c in checks if c.severity == "warning"),
            critical=sum(1 for c in checks if c.severity == "critical"),
            duration_ms=elapsed,
        )

        return report

    async def _check_system_health(self, orchestrator) -> list[AuditCheck]:
        """Check core system components."""
        checks = []

        # Check memory system
        if orchestrator.memory:
            try:
                # Try to access memory
                if hasattr(orchestrator.memory, "working"):
                    checks.append(
                        AuditCheck(
                            name="memory_system",
                            passed=True,
                            message="Memory system operational",
                        )
                    )
                else:
                    checks.append(
                        AuditCheck(
                            name="memory_system",
                            passed=False,
                            severity="critical",
                            message="Memory system not initialized",
                        )
                    )
            except Exception as e:
                checks.append(
                    AuditCheck(
                        name="memory_system",
                        passed=False,
                        severity="critical",
                        message=f"Memory system error: {str(e)[:100]}",
                    )
                )
        else:
            checks.append(
                AuditCheck(
                    name="memory_system",
                    passed=False,
                    severity="critical",
                    message="Memory system not available",
                )
            )

        # Check backend
        if orchestrator.backend:
            checks.append(
                AuditCheck(
                    name="llm_backend",
                    passed=True,
                    message="LLM backend available",
                )
            )
        else:
            checks.append(
                AuditCheck(
                    name="llm_backend",
                    passed=False,
                    severity="critical",
                    message="LLM backend not available",
                )
            )

        # Check goals
        if orchestrator.goals:
            stats = orchestrator.goals.get_stats()
            checks.append(
                AuditCheck(
                    name="goal_manager",
                    passed=True,
                    message=f"Goal manager: {stats.get('total', 0)} goals",
                    details=stats,
                )
            )

        return checks

    async def _check_memory_integrity(self, orchestrator) -> list[AuditCheck]:
        """Check memory system integrity."""
        checks = []

        if not orchestrator.memory:
            return checks

        # Check working memory bounds
        if hasattr(orchestrator.memory, "working") and hasattr(
            orchestrator.memory.working, "items"
        ):
            wm_size = len(orchestrator.memory.working.items)
            if wm_size > 100:
                checks.append(
                    AuditCheck(
                        name="working_memory_overflow",
                        passed=False,
                        severity="warning",
                        message=f"Working memory has {wm_size} items (max recommended: 50)",
                    )
                )
            else:
                checks.append(
                    AuditCheck(
                        name="working_memory_size",
                        passed=True,
                        message=f"Working memory: {wm_size} items",
                    )
                )

        # Check for memory leaks (too many episodic memories)
        if hasattr(orchestrator.memory, "episodic") and hasattr(
            orchestrator.memory.episodic, "count"
        ):
            try:
                episodic_count = await orchestrator.memory.episodic.count()
                if episodic_count > 10000:
                    checks.append(
                        AuditCheck(
                            name="episodic_memory_bloat",
                            passed=False,
                            severity="warning",
                            message=f"Episodic memory has {episodic_count} entries - consider compression",
                        )
                    )
                else:
                    checks.append(
                        AuditCheck(
                            name="episodic_memory_count",
                            passed=True,
                            message=f"Episodic memory: {episodic_count} entries",
                        )
                    )
            except Exception:
                pass

        return checks

    async def _check_knowledge_graph(self, orchestrator) -> list[AuditCheck]:
        """Check knowledge graph consistency."""
        checks = []

        if not orchestrator.knowledge_graph:
            return checks

        kg = orchestrator.knowledge_graph
        stats = kg.get_stats() if hasattr(kg, "get_stats") else {}

        node_count = stats.get("nodes", 0)
        edge_count = stats.get("edges", 0)

        if node_count > 0 and edge_count == 0:
            checks.append(
                AuditCheck(
                    name="knowledge_graph_disconnected",
                    passed=False,
                    severity="warning",
                    message=f"Knowledge graph has {node_count} nodes but no edges",
                )
            )
        elif node_count == 0:
            checks.append(
                AuditCheck(
                    name="knowledge_graph_empty",
                    passed=True,
                    severity="info",
                    message="Knowledge graph is empty (normal for new agent)",
                )
            )
        else:
            density = edge_count / max(1, node_count * (node_count - 1) / 2)
            checks.append(
                AuditCheck(
                    name="knowledge_graph_health",
                    passed=True,
                    message=f"Knowledge graph: {node_count} nodes, {edge_count} edges (density: {density:.3f})",
                    details={"nodes": node_count, "edges": edge_count, "density": density},
                )
            )

        return checks

    async def _check_crawlers(self, orchestrator) -> list[AuditCheck]:
        """Check crawler health."""
        checks = []

        total = len(orchestrator.crawlers)
        if total == 0:
            checks.append(
                AuditCheck(
                    name="crawlers_available",
                    passed=False,
                    severity="warning",
                    message="No crawlers available",
                )
            )
        else:
            checks.append(
                AuditCheck(
                    name="crawlers_available",
                    passed=True,
                    message=f"{total} crawlers available",
                )
            )

        # Check proxy pool
        if orchestrator.proxy_pool:
            proxy_stats = orchestrator.proxy_pool.get_stats()
            healthy = proxy_stats.get("healthy", 0)
            if healthy == 0:
                checks.append(
                    AuditCheck(
                        name="proxy_pool",
                        passed=False,
                        severity="warning",
                        message="No healthy proxies available",
                    )
                )
            else:
                checks.append(
                    AuditCheck(
                        name="proxy_pool",
                        passed=True,
                        message=f"{healthy} healthy proxies",
                    )
                )

        return checks

    async def _check_llm_backends(self, orchestrator) -> list[AuditCheck]:
        """Check LLM backend health."""
        checks = []

        if not orchestrator.backend:
            return checks

        stats = (
            orchestrator.backend.get_stats() if hasattr(orchestrator.backend, "get_stats") else {}
        )
        total_calls = stats.get("total_calls", 0)

        checks.append(
            AuditCheck(
                name="llm_backend_usage",
                passed=True,
                message=f"LLM backend: {total_calls} total calls",
                details=stats,
            )
        )

        return checks

    async def _collect_metrics(self, orchestrator) -> dict:
        """Collect performance metrics."""
        metrics = {}

        # Uptime
        uptime = (datetime.utcnow() - orchestrator.start_time).total_seconds()
        metrics["uptime_seconds"] = uptime

        # Iterations
        metrics["iterations"] = orchestrator.iteration

        # Execution log analysis
        if orchestrator.execution_log:
            recent = orchestrator.execution_log[-20:]
            success_count = sum(
                1 for log in recent if all(a.get("success", False) for a in log.get("actions", []))
            )
            metrics["recent_success_rate"] = success_count / max(1, len(recent))
            metrics["recent_actions"] = sum(len(log.get("actions", [])) for log in recent)

        # Memory stats
        if orchestrator.memory:
            metrics["working_memory"] = (
                len(orchestrator.memory.working.items)
                if hasattr(orchestrator.memory.working, "items")
                else 0
            )

        # Sleep consolidation stats
        if orchestrator.sleep_consolidator:
            metrics["sleep_stats"] = orchestrator.sleep_consolidator.get_stats()

        return metrics

    async def _detect_anomalies(self, orchestrator, metrics: dict) -> list[str]:
        """Detect anomalies in metrics."""
        anomalies = []

        # Check for low success rate
        if metrics.get("recent_success_rate", 1.0) < 0.3:
            anomalies.append("Low success rate detected in recent actions")

        # Check for high memory usage
        if metrics.get("working_memory", 0) > 80:
            anomalies.append("Working memory approaching capacity")

        # Check for long uptime without consolidation
        uptime_hours = metrics.get("uptime_seconds", 0) / 3600
        if uptime_hours > 12 and metrics.get("sleep_stats", {}).get("total_consolidations", 0) == 0:
            anomalies.append("Agent running >12h without memory consolidation")

        return anomalies

    def _generate_recommendations(
        self, checks: list[AuditCheck], metrics: dict, anomalies: list[str]
    ) -> list[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Based on checks
        for check in checks:
            if not check.passed:
                if check.name == "working_memory_overflow":
                    recommendations.append("Run memory compression to reduce working memory size")
                elif check.name == "episodic_memory_bloat":
                    recommendations.append(
                        "Run sleep consolidation to compress old episodic memories"
                    )
                elif check.name == "knowledge_graph_disconnected":
                    recommendations.append("Review knowledge graph edges - nodes may need linking")
                elif check.name == "proxy_pool":
                    recommendations.append(
                        "Refresh proxy pool or configure additional proxy sources"
                    )

        # Based on anomalies
        for anomaly in anomalies:
            if "success rate" in anomaly.lower():
                recommendations.append("Review recent action logs and adjust strategy")
            if "memory" in anomaly.lower() and "capacity" in anomaly.lower():
                recommendations.append("Clear working memory or increase consolidation frequency")
            if "consolidation" in anomaly.lower():
                recommendations.append("Run sleep consolidation cycle")

        # General recommendations
        if not recommendations:
            recommendations.append("System healthy - no action needed")

        return recommendations

    def _generate_summary(self, checks: list[AuditCheck], metrics: dict) -> str:
        """Generate human-readable summary."""
        total = len(checks)
        passed = sum(1 for c in checks if c.passed)
        warnings = sum(1 for c in checks if c.severity == "warning")
        critical = sum(1 for c in checks if c.severity == "critical")

        lines = [
            f"Audit: {passed}/{total} checks passed",
            f"Warnings: {warnings}, Critical: {critical}",
            f"Uptime: {metrics.get('uptime_seconds', 0) / 3600:.1f}h",
            f"Iterations: {metrics.get('iterations', 0)}",
        ]

        if metrics.get("recent_success_rate") is not None:
            lines.append(f"Recent success rate: {metrics['recent_success_rate']:.1%}")

        return "\n".join(lines)

    async def _save_report(self, report: HealthReport):
        """Save audit report to disk."""
        filename = self.data_dir / f"audit_{report.id}.json"
        try:
            with open(filename, "w") as f:
                json.dump(report.to_dict(), f, indent=2, default=str)
        except Exception as e:
            self.logger.warning("failed_to_save_audit", error=str(e))

    def should_run_audit(self) -> bool:
        """Check if enough time has passed since last audit."""
        if self._last_audit_time is None:
            return True
        elapsed = datetime.utcnow() - self._last_audit_time
        return elapsed > timedelta(hours=self._audit_interval_hours)

    def get_recent_reports(self, limit: int = 5) -> list[dict]:
        """Get recent audit reports."""
        return [r.to_dict() for r in self.audit_history[-limit:]]
