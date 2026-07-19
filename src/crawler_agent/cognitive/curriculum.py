"""Self-generated curriculum and autonomous experimentation.

Provides:
- Generate learning tasks from knowledge gaps
- Design experiments to test hypotheses
- Progressive difficulty scaling
- Skill prerequisites tracking
- Learning path optimization
"""

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog


@dataclass
class LearningTask:
    id: str
    name: str
    category: str
    difficulty: float  # 0.0 to 1.0
    prerequisites: list[str] = field(default_factory=list)
    knowledge_required: list[str] = field(default_factory=list)
    skills_to_practice: list[str] = field(default_factory=list)
    description: str = ""
    estimated_time: float = 30.0
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "difficulty": self.difficulty,
            "prerequisites": self.prerequisites,
            "knowledge_required": self.knowledge_required,
            "skills_to_practice": self.skills_to_practice,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ExperimentDesign:
    id: str
    hypothesis: str
    variables: list[dict] = field(default_factory=list)
    procedure: list[str] = field(default_factory=list)
    expected_outcome: str = ""
    difficulty: float = 0.5
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "hypothesis": self.hypothesis,
            "variables": self.variables,
            "procedure": self.procedure,
            "expected_outcome": self.expected_outcome,
            "difficulty": self.difficulty,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class SkillProgress:
    skill: str
    mastery: float = 0.0  # 0.0 to 1.0
    times_practiced: int = 0
    last_practiced: datetime | None = None
    successes: int = 0
    failures: int = 0

    @property
    def success_rate(self) -> float:
        total = self.successes + self.failures
        return self.successes / total if total > 0 else 0.0


class SelfGeneratedCurriculum:
    """Self-generated curriculum for autonomous learning."""

    def __init__(self, data_dir: str = "data/curriculum"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logger = structlog.get_logger(component="curriculum")

        self.tasks: dict[str, LearningTask] = {}
        self.experiments: list[ExperimentDesign] = []
        self.skill_progress: dict[str, SkillProgress] = {}
        self.completed_tasks: list[str] = []
        self.current_task: str | None = None

        self._setup_task_templates()
        self._load()

    def _setup_task_templates(self):
        """Setup template task types."""
        self.task_templates = {
            "coding": [
                ("Implement a sorting algorithm", 0.3),
                ("Write a recursive function", 0.4),
                ("Design a data structure", 0.6),
                ("Optimize slow code", 0.7),
                ("Implement a graph algorithm", 0.8),
            ],
            "planning": [
                ("Plan a sequence of actions", 0.3),
                ("Schedule tasks with constraints", 0.5),
                ("Plan with resource limits", 0.6),
                ("Multi-step problem solving", 0.7),
                ("Contingency planning", 0.8),
            ],
            "reasoning": [
                ("Deductive reasoning", 0.3),
                ("Inductive reasoning", 0.5),
                ("Abductive reasoning", 0.6),
                ("Counterfactual reasoning", 0.7),
                ("Causal reasoning", 0.8),
            ],
            "physics": [
                ("Predict object motion", 0.3),
                ("Estimate collision outcome", 0.5),
                ("Predict spring behavior", 0.6),
                ("Complex physics prediction", 0.8),
            ],
            "memory": [
                ("Recall recent events", 0.3),
                ("Associate related memories", 0.5),
                ("Apply past experience", 0.7),
            ],
        }

    def _load(self):
        tasks_file = self.data_dir / "tasks.json"
        if tasks_file.exists():
            try:
                data = json.loads(tasks_file.read_text())
                for task_data in data.get("tasks", []):
                    task = LearningTask(
                        id=task_data["id"],
                        name=task_data["name"],
                        category=task_data["category"],
                        difficulty=task_data["difficulty"],
                        prerequisites=task_data.get("prerequisites", []),
                        knowledge_required=task_data.get("knowledge_required", []),
                        skills_to_practice=task_data.get("skills_to_practice", []),
                        description=task_data.get("description", ""),
                    )
                    self.tasks[task.id] = task
                self.completed_tasks = data.get("completed_tasks", [])
            except Exception as e:
                self.logger.warning("tasks_load_failed", error=str(e))

        progress_file = self.data_dir / "progress.json"
        if progress_file.exists():
            try:
                data = json.loads(progress_file.read_text())
                for skill, prog in data.get("skills", {}).items():
                    self.skill_progress[skill] = SkillProgress(
                        skill=skill,
                        mastery=prog.get("mastery", 0),
                        times_practiced=prog.get("times_practiced", 0),
                        successes=prog.get("successes", 0),
                        failures=prog.get("failures", 0),
                    )
            except Exception as e:
                self.logger.warning("progress_load_failed", error=str(e))

    def _save(self):
        tasks_file = self.data_dir / "tasks.json"
        tasks_file.write_text(
            json.dumps(
                {
                    "tasks": [t.to_dict() for t in self.tasks.values()],
                    "completed_tasks": self.completed_tasks[-200:],
                    "saved_at": datetime.utcnow().isoformat(),
                },
                indent=2,
            )
        )

        progress_file = self.data_dir / "progress.json"
        progress_file.write_text(
            json.dumps(
                {
                    "skills": {
                        skill: {
                            "mastery": sp.mastery,
                            "times_practiced": sp.times_practiced,
                            "successes": sp.successes,
                            "failures": sp.failures,
                        }
                        for skill, sp in self.skill_progress.items()
                    },
                    "saved_at": datetime.utcnow().isoformat(),
                },
                indent=2,
            )
        )

    def generate_tasks(
        self,
        knowledge_gaps: list[str],
        weak_skills: list[str],
        count: int = 5,
    ) -> list[LearningTask]:
        """Generate learning tasks based on gaps and weaknesses."""
        generated = []
        for _ in range(count):
            category = "coding"
            if weak_skills:
                category = weak_skills[0]

            templates = self.task_templates.get(category, self.task_templates["coding"])
            for template_name, difficulty in templates:
                if any(gap.lower() in template_name.lower() for gap in knowledge_gaps):
                    task_id = str(uuid.uuid4())[:8]
                    task = LearningTask(
                        id=task_id,
                        name=template_name,
                        category=category,
                        difficulty=difficulty,
                        description=f"Practice: {template_name}",
                        skills_to_practice=weak_skills[:3],
                    )
                    self.tasks[task_id] = task
                    generated.append(task)
                    break

        if not generated and self.task_templates.get("coding"):
            template_name, difficulty = self.task_templates["coding"][0]
            task_id = str(uuid.uuid4())[:8]
            task = LearningTask(
                id=task_id,
                name=template_name,
                category="coding",
                difficulty=difficulty,
                description=f"Practice: {template_name}",
            )
            self.tasks[task_id] = task
            generated.append(task)

        self._save()
        return generated

    def design_experiment(self, hypothesis: str, context: dict = None) -> ExperimentDesign:
        """Design an experiment to test a hypothesis."""
        experiment_id = str(uuid.uuid4())[:8]

        variables = [
            {"name": "initial_state", "type": "independent", "range": "configurable"},
            {"name": "action_applied", "type": "independent", "range": "configurable"},
            {"name": "outcome_observed", "type": "dependent", "range": "measurable"},
        ]

        procedure = [
            "Set up initial state in sandbox",
            "Record initial measurements",
            "Apply action/force",
            "Observe and record outcome",
            "Compare with hypothesis prediction",
            "Analyze results and update model",
        ]

        experiment = ExperimentDesign(
            id=experiment_id,
            hypothesis=hypothesis,
            variables=variables,
            procedure=procedure,
            expected_outcome="Hypothesis confirmed or rejected with evidence",
            difficulty=0.6,
        )
        self.experiments.append(experiment)
        self._save()
        return experiment

    def record_task_completion(
        self,
        task_id: str,
        success: bool,
        score: float = 0.0,
    ):
        """Record completion of a learning task."""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            for skill in task.skills_to_practice:
                if skill not in self.skill_progress:
                    self.skill_progress[skill] = SkillProgress(skill=skill)
                sp = self.skill_progress[skill]
                sp.times_practiced += 1
                if success:
                    sp.successes += 1
                    sp.mastery = min(1.0, sp.mastery + 0.1)
                else:
                    sp.failures += 1
                    sp.mastery = max(0.0, sp.mastery - 0.05)
                sp.last_practiced = datetime.utcnow()

            if task_id not in self.completed_tasks:
                self.completed_tasks.append(task_id)

            self._save()

    def get_next_task(self) -> LearningTask | None:
        """Get the next learning task based on progress."""
        incomplete = [t for t in self.tasks.values() if t.id not in self.completed_tasks]
        if not incomplete:
            return None

        weak_skills = [skill for skill, sp in self.skill_progress.items() if sp.mastery < 0.5]

        def task_priority(task):
            skill_match = sum(1 for s in task.skills_to_practice if s in weak_skills)
            return (-skill_match, task.difficulty)

        incomplete.sort(key=task_priority)
        return incomplete[0] if incomplete else None

    def get_learning_path(self, goal: str) -> list[LearningTask]:
        """Generate a learning path toward a goal."""
        tasks = sorted(self.tasks.values(), key=lambda t: t.difficulty)
        return [t for t in tasks if t.id not in self.completed_tasks][:10]

    def to_context(self) -> str:
        incomplete = [t for t in self.tasks.values() if t.id not in self.completed_tasks]
        weak_skills = [s for s, p in self.skill_progress.items() if p.mastery < 0.5]
        return (
            f"Curriculum: {len(self.tasks)} tasks ({len(self.completed_tasks)} completed), "
            f"{len(incomplete)} remaining, {len(weak_skills)} weak skills"
        )
