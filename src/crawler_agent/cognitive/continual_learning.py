"""Continual lifelong learning - prevent catastrophic forgetting.

Provides:
- Elastic weight consolidation
- Experience replay
- Knowledge distillation
- Progressive skill acquisition
"""

import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog


@dataclass
class Experience:
    task: str
    action: str
    outcome: str
    reward: float
    importance: float = 0.5
    timestamp: float = 0.0


@dataclass
class Skill:
    name: str
    mastery: float = 0.0
    importance: float = 0.5
    consolidated: bool = False
    times_practiced: int = 0


class ContinualLearner:
    """Continual learning with catastrophic forgetting prevention."""

    def __init__(self, data_dir: str = "data/continual_learning", buffer_size: int = 1000):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logger = structlog.get_logger(component="continual_learning")

        self.buffer_size = buffer_size
        self.experience_buffer: list[Experience] = []
        self.skills: dict[str, Skill] = {}
        self.fisher_information: dict[str, float] = {}
        self.old_params: dict[str, float] = {}

        self._load()

    def _load(self):
        buffer_file = self.data_dir / "buffer.json"
        if buffer_file.exists():
            try:
                data = json.loads(buffer_file.read_text())
                for exp_data in data.get("buffer", []):
                    self.experience_buffer.append(Experience(**exp_data))
            except Exception as e:
                self.logger.warning("buffer_load_failed", error=str(e))

        skills_file = self.data_dir / "skills.json"
        if skills_file.exists():
            try:
                data = json.loads(skills_file.read_text())
                for skill_name, skill_data in data.get("skills", {}).items():
                    self.skills[skill_name] = Skill(
                        name=skill_name,
                        mastery=skill_data.get("mastery", 0),
                        importance=skill_data.get("importance", 0.5),
                        consolidated=skill_data.get("consolidated", False),
                        times_practiced=skill_data.get("times_practiced", 0),
                    )
            except Exception as e:
                self.logger.warning("skills_load_failed", error=str(e))

    def _save(self):
        buffer_file = self.data_dir / "buffer.json"
        buffer_file.write_text(
            json.dumps(
                {
                    "buffer": [
                        {
                            "task": e.task,
                            "action": e.action,
                            "outcome": e.outcome,
                            "reward": e.reward,
                            "importance": e.importance,
                            "timestamp": e.timestamp,
                        }
                        for e in self.experience_buffer[-self.buffer_size :]
                    ],
                },
                indent=2,
            )
        )

        skills_file = self.data_dir / "skills.json"
        skills_file.write_text(
            json.dumps(
                {
                    "skills": {
                        name: {
                            "mastery": s.mastery,
                            "importance": s.importance,
                            "consolidated": s.consolidated,
                            "times_practiced": s.times_practiced,
                        }
                        for name, s in self.skills.items()
                    },
                },
                indent=2,
            )
        )

    def store_experience(self, task: str, action: str, outcome: str, reward: float):
        """Store experience with priority based on reward."""
        importance = abs(reward) + 0.1
        exp = Experience(
            task=task,
            action=action,
            outcome=outcome,
            reward=reward,
            importance=importance,
        )
        self.experience_buffer.append(exp)

        if len(self.experience_buffer) > self.buffer_size:
            self.experience_buffer.sort(key=lambda e: e.importance, reverse=True)
            self.experience_buffer = self.experience_buffer[: self.buffer_size]

        self._save()

    def sample_replay(self, batch_size: int = 10) -> list[Experience]:
        """Sample experiences for replay, prioritized by importance."""
        if not self.experience_buffer:
            return []

        weights = [e.importance for e in self.experience_buffer]
        total = sum(weights)
        if total == 0:
            return random.sample(
                self.experience_buffer, min(batch_size, len(self.experience_buffer))
            )

        probs = [w / total for w in weights]
        indices = random.choices(range(len(self.experience_buffer)), weights=probs, k=batch_size)
        return [self.experience_buffer[i] for i in set(indices)]

    def compute_regularization_loss(self) -> float:
        """Compute elastic weight consolidation regularization loss."""
        loss = 0.0
        for skill_name, skill in self.skills.items():
            if skill.consolidated:
                fisher = self.fisher_information.get(skill_name, 1.0)
                old_param = self.old_params.get(skill_name, skill.mastery)
                loss += 0.5 * fisher * (skill.mastery - old_param) ** 2
        return loss

    def consolidate_skill(self, skill_name: str):
        """Consolidate a skill to prevent forgetting."""
        if skill_name not in self.skills:
            self.skills[skill_name] = Skill(name=skill_name)

        skill = self.skills[skill_name]
        skill.consolidated = True
        self.old_params[skill_name] = skill.mastery
        self.fisher_information[skill_name] = 1.0 / (skill.times_practiced + 1)
        self._save()

    def learn_new_skill(self, skill_name: str, initial_mastery: float = 0.1):
        """Learn a new skill while protecting old ones."""
        if skill_name not in self.skills:
            self.skills[skill_name] = Skill(
                name=skill_name,
                mastery=initial_mastery,
                importance=0.5,
            )
            self._save()

    def practice_skill(self, skill_name: str, success: bool):
        """Practice a skill, updating mastery."""
        if skill_name not in self.skills:
            self.learn_new_skill(skill_name)

        skill = self.skills[skill_name]
        skill.times_practiced += 1

        if success:
            delta = 0.1 * (1 - skill.mastery)
        else:
            delta = -0.05 * skill.mastery

        if skill.consolidated:
            fisher = self.fisher_information.get(skill_name, 1.0)
            delta *= 1.0 / (1.0 + fisher)

        skill.mastery = max(0.0, min(1.0, skill.mastery + delta))
        self._save()

    def get_weak_skills(self, threshold: float = 0.5) -> list[str]:
        """Get skills below mastery threshold."""
        return [name for name, skill in self.skills.items() if skill.mastery < threshold]

    def get_consolidated_skills(self) -> list[str]:
        """Get all consolidated skills."""
        return [name for name, skill in self.skills.items() if skill.consolidated]

    def to_context(self) -> str:
        weak = self.get_weak_skills()
        consolidated = self.get_consolidated_skills()
        return (
            f"Continual Learning: {len(self.skills)} skills "
            f"({len(consolidated)} consolidated, {len(weak)} weak), "
            f"buffer: {len(self.experience_buffer)} experiences"
        )
