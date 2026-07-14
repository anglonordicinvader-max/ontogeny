"""Autonomous goal management system."""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

import structlog


class GoalPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GoalStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"
    BLOCKED = "blocked"


class GoalSource(str, Enum):
    INTRINSIC = "intrinsic"    # Self-generated (curiosity, mastery)
    EXTRINSIC = "extrinsic"    # User-provided
    META = "meta"              # Self-improvement goals


@dataclass
class Goal:
    """A goal to pursue."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    source: GoalSource = GoalSource.EXTRINSIC
    priority: GoalPriority = GoalPriority.MEDIUM
    status: GoalStatus = GoalStatus.PENDING

    # Hierarchy
    parent_id: str | None = None
    subgoals: list[str] = field(default_factory=list)

    # Metrics
    progress: float = 0.0  # 0-1
    confidence: float = 0.5  # Confidence in achieving
    importance: float = 0.5  # How important is this goal

    # Learning
    prerequisites: list[str] = field(default_factory=list)
    learned_from: list[str] = field(default_factory=list)

    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    deadline: datetime | None = None

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "source": self.source.value,
            "priority": self.priority.value,
            "status": self.status.value,
            "parent_id": self.parent_id,
            "subgoals": self.subgoals,
            "progress": self.progress,
            "confidence": self.confidence,
            "importance": self.importance,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
@dataclass
class IntrinsicDrive:
    """Intrinsic motivation drive."""
    name: str
    description: str
    satisfaction: float = 0.0  # 0-1, current satisfaction level
    decay_rate: float = 0.01  # How fast satisfaction decays
    boost_on_fulfill: float = 0.3  # How much to boost when fulfilled

    def decay(self) -> None:
        """Apply natural decay."""
        self.satisfaction = max(0, self.satisfaction - self.decay_rate)

    def fulfill(self, amount: float = 0.3) -> float:
        """Fulfill drive, returns reward."""
        old = self.satisfaction
        self.satisfaction = min(1.0, self.satisfaction + amount)
        return (self.satisfaction - old) * self.boost_on_fulfill


class GoalManager:
    """Manages autonomous goals and intrinsic motivations."""

    def __init__(self):
        self.goals: dict[str, Goal] = {}
        self.drives: dict[str, IntrinsicDrive] = {}
        self.completed_goals: list[Goal] = []
        self.goal_history: list[dict[str, Any]] = []
        self.logger = structlog.get_logger()

        # Initialize intrinsic drives
        self._init_drives()

    def _init_drives(self) -> None:
        """Initialize intrinsic motivation drives."""
        self.drives = {
            "curiosity": IntrinsicDrive(
                name="curiosity",
                description="Desire to learn new things and explore",
                satisfaction=0.3,
                decay_rate=0.02,
            ),
            "mastery": IntrinsicDrive(
                name="mastery",
                description="Desire to improve skills and capabilities",
                satisfaction=0.3,
                decay_rate=0.01,
            ),
            "competence": IntrinsicDrive(
                name="competence",
                description="Desire to feel capable and effective",
                satisfaction=0.5,
                decay_rate=0.015,
            ),
            "autonomy": IntrinsicDrive(
                name="autonomy",
                description="Desire for self-direction and control",
                satisfaction=0.5,
                decay_rate=0.01,
            ),
            "novelty": IntrinsicDrive(
                name="novelty",
                description="Desire for new experiences and stimuli",
                satisfaction=0.2,
                decay_rate=0.03,
            ),
        }

    async def create_goal(
        self,
        description: str,
        source: GoalSource = GoalSource.EXTRINSIC,
        priority: GoalPriority = GoalPriority.MEDIUM,
        parent_id: str | None = None,
        metadata: dict | None = None,
    ) -> Goal:
        """Create a new goal."""
        goal = Goal(
            description=description,
            source=source,
            priority=priority,
            parent_id=parent_id,
            metadata=metadata or {},
        )

        self.goals[goal.id] = goal

        if parent_id and parent_id in self.goals:
            self.goals[parent_id].subgoals.append(goal.id)

        self.logger.info("goal_created", goal_id=goal.id, description=description)
        return goal

    async def generate_intrinsic_goals(self) -> list[Goal]:
        """Generate goals based on unsatisfied drives."""
        new_goals = []

        # Curiosity drive - learn something new
        if self.drives["curiosity"].satisfaction < 0.5:
            goal = await self.create_goal(
                description="Explore and learn about a new topic or domain",
                source=GoalSource.INTRINSIC,
                priority=GoalPriority.MEDIUM,
                metadata={"drive": "curiosity", "target_satisfaction": 0.7},
            )
            new_goals.append(goal)

        # Mastery drive - improve a skill
        if self.drives["mastery"].satisfaction < 0.5:
            goal = await self.create_goal(
                description="Practice and improve an existing skill",
                source=GoalSource.INTRINSIC,
                priority=GoalPriority.MEDIUM,
                metadata={"drive": "mastery", "target_satisfaction": 0.7},
            )
            new_goals.append(goal)

        # Novelty drive - try something new
        if self.drives["novelty"].satisfaction < 0.4:
            goal = await self.create_goal(
                description="尝试一个新的方法或工具",
                source=GoalSource.INTRINSIC,
                priority=GoalPriority.LOW,
                metadata={"drive": "novelty", "target_satisfaction": 0.6},
            )
            new_goals.append(goal)

        return new_goals

    async def get_active_goals(self) -> list[Goal]:
        """Get all active goals sorted by priority."""
        active = [
            g for g in self.goals.values()
            if g.status in (GoalStatus.PENDING, GoalStatus.ACTIVE)
        ]

        priority_order = {
            GoalPriority.CRITICAL: 0,
            GoalPriority.HIGH: 1,
            GoalPriority.MEDIUM: 2,
            GoalPriority.LOW: 3,
        }

        return sorted(active, key=lambda g: (priority_order[g.priority], -g.importance))

    async def select_next_goal(self) -> Goal | None:
        """Select the next goal to pursue."""
        # Generate intrinsic goals if drives are low
        await self.generate_intrinsic_goals()

        active = await self.get_active_goals()
        if not active:
            return None

        # Score goals
        scored = []
        for goal in active:
            score = self._score_goal(goal)
            scored.append((score, goal))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1] if scored else None

    def _score_goal(self, goal: Goal) -> float:
        """Score a goal for selection priority."""
        priority_weights = {
            GoalPriority.CRITICAL: 1.0,
            GoalPriority.HIGH: 0.8,
            GoalPriority.MEDIUM: 0.5,
            GoalPriority.LOW: 0.3,
        }

        source_weights = {
            GoalSource.EXTRINSIC: 1.0,  # User goals first
            GoalSource.META: 0.7,
            GoalSource.INTRINSIC: 0.5,
        }

        score = (
            priority_weights[goal.priority] * 0.4 +
            goal.importance * 0.3 +
            goal.confidence * 0.2 +
            source_weights[goal.source] * 0.1
        )

        # Boost if goal has been waiting
        wait_time = (datetime.utcnow() - goal.created_at).total_seconds() / 3600
        score += min(0.2, wait_time * 0.01)

        return score

    async def update_progress(
        self,
        goal_id: str,
        progress: float,
        notes: str = "",
    ) -> None:
        """Update goal progress."""
        if goal_id not in self.goals:
            return

        goal = self.goals[goal_id]
        goal.progress = min(1.0, progress)

        if goal.status == GoalStatus.PENDING:
            goal.status = GoalStatus.ACTIVE
            goal.started_at = datetime.utcnow()

        self.goal_history.append({
            "goal_id": goal_id,
            "event": "progress_update",
            "progress": progress,
            "notes": notes,
            "timestamp": datetime.utcnow().isoformat(),
        })

        if progress >= 1.0:
            await self.complete_goal(goal_id)

    async def complete_goal(self, goal_id: str) -> None:
        """Mark goal as completed."""
        if goal_id not in self.goals:
            return

        goal = self.goals[goal_id]
        goal.status = GoalStatus.COMPLETED
        goal.progress = 1.0
        goal.completed_at = datetime.utcnow()

        # Fulfill related drive
        drive_name = goal.metadata.get("drive")
        if drive_name and drive_name in self.drives:
            reward = self.drives[drive_name].fulfill()
            self.logger.info("drive_fulfilled", drive=drive_name, reward=reward)

        # Move to completed
        self.completed_goals.append(goal)
        del self.goals[goal_id]

        self.logger.info("goal_completed", goal_id=goal_id)

    async def fail_goal(self, goal_id: str, reason: str = "") -> None:
        """Mark goal as failed."""
        if goal_id not in self.goals:
            return

        goal = self.goals[goal_id]
        goal.status = GoalStatus.FAILED
        goal.metadata["failure_reason"] = reason

        self.goal_history.append({
            "goal_id": goal_id,
            "event": "failed",
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
        })

        self.logger.info("goal_failed", goal_id=goal_id, reason=reason)

    async def decompose_goal(
        self,
        goal_id: str,
        subgoal_descriptions: list[str],
    ) -> list[Goal]:
        """Decompose a goal into subgoals."""
        if goal_id not in self.goals:
            return []

        parent = self.goals[goal_id]
        subgoals = []

        for desc in subgoal_descriptions:
            subgoal = await self.create_goal(
                description=desc,
                source=parent.source,
                priority=parent.priority,
                parent_id=goal_id,
                metadata={"parent_description": parent.description},
            )
            subgoals.append(subgoal)

        return subgoals

    async def get_drive_status(self) -> dict[str, float]:
        """Get current drive satisfaction levels."""
        # Apply decay
        for drive in self.drives.values():
            drive.decay()

        return {name: drive.satisfaction for name, drive in self.drives.items()}

    def get_stats(self) -> dict[str, Any]:
        """Get goal system statistics."""
        return {
            "active_goals": len(self.goals),
            "completed_goals": len(self.completed_goals),
            "drives": {name: d.satisfaction for name, d in self.drives.items()},
            "history_size": len(self.goal_history),
        }
