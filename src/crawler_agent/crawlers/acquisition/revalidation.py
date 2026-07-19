"""Continuous revalidation — knowledge expires naturally.

Tracks:
- Stale knowledge
- Outdated APIs
- Version changes
- Broken links
- Changed documentation
- Software releases
- Robotics documentation updates

Automatically schedules revalidation tasks.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

import structlog


class RevalidationType(StrEnum):
    STALE_KNOWLEDGE = "stale_knowledge"
    BROKEN_LINK = "broken_link"
    VERSION_CHANGE = "version_change"
    CONTENT_CHANGE = "content_change"
    SCHEDULED = "scheduled"
    MANUAL = "manual"


@dataclass
class RevalidationTask:
    """A scheduled revalidation task."""

    id: str = ""
    claim_id: str = ""
    evidence_id: str = ""
    revalidation_type: RevalidationType = RevalidationType.SCHEDULED
    url: str = ""
    domain: str = ""
    priority: int = 5  # 0-10, higher = more urgent
    scheduled_at: float = 0.0
    executed_at: float = 0.0
    completed: bool = False
    success: bool = False
    result_summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class RevalidationScheduler:
    """Manages automatic knowledge revalidation."""

    def __init__(self):
        self.tasks: list[RevalidationTask] = []
        self.completed_tasks: list[RevalidationTask] = []
        self.logger = structlog.get_logger()

    def schedule_stale_check(
        self,
        claim_id: str,
        url: str,
        domain: str,
        hours_overdue: float = 0.0,
    ) -> RevalidationTask:
        """Schedule revalidation for a stale claim."""
        task = RevalidationTask(
            id=f"rv_{len(self.tasks)}",
            claim_id=claim_id,
            revalidation_type=RevalidationType.STALE_KNOWLEDGE,
            url=url,
            domain=domain,
            priority=min(10, int(5 + hours_overdue / 24)),
            scheduled_at=time.time(),
        )
        self.tasks.append(task)
        return task

    def schedule_link_check(
        self, evidence_id: str, url: str, domain: str
    ) -> RevalidationTask:
        """Schedule a broken link check."""
        task = RevalidationTask(
            id=f"rv_{len(self.tasks)}",
            evidence_id=evidence_id,
            revalidation_type=RevalidationType.BROKEN_LINK,
            url=url,
            domain=domain,
            priority=6,
            scheduled_at=time.time(),
        )
        self.tasks.append(task)
        return task

    def schedule_version_check(
        self, evidence_id: str, url: str, domain: str, current_version: str = ""
    ) -> RevalidationTask:
        """Schedule a version change check."""
        task = RevalidationTask(
            id=f"rv_{len(self.tasks)}",
            evidence_id=evidence_id,
            revalidation_type=RevalidationType.VERSION_CHANGE,
            url=url,
            domain=domain,
            priority=7,
            scheduled_at=time.time(),
            metadata={"current_version": current_version},
        )
        self.tasks.append(task)
        return task

    def get_pending_tasks(
        self, limit: int = 10, max_priority: int = 10
    ) -> list[RevalidationTask]:
        """Get the next batch of tasks to execute."""
        pending = [t for t in self.tasks if not t.completed]
        pending.sort(key=lambda t: (-t.priority, t.scheduled_at))
        return [
            t for t in pending[:limit]
            if t.priority <= max_priority
        ]

    def complete_task(
        self, task_id: str, success: bool, summary: str = ""
    ):
        """Mark a task as completed."""
        for task in self.tasks:
            if task.id == task_id:
                task.completed = True
                task.success = success
                task.result_summary = summary
                task.executed_at = time.time()
                self.completed_tasks.append(task)
                break

    def get_stats(self) -> dict[str, Any]:
        pending = [t for t in self.tasks if not t.completed]
        return {
            "total_tasks": len(self.tasks),
            "pending": len(pending),
            "completed": len(self.completed_tasks),
            "by_type": {},
            "avg_priority": (
                sum(t.priority for t in pending) / max(1, len(pending))
            ),
        }
