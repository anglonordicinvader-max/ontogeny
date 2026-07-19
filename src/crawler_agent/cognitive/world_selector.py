"""World selector - picks practical world based on skill needs.

Provides:
- Skill-to-world mapping
- Weak skill detection
- Goal-based selection
- Progressive difficulty
- Variety sampling
- Survival/critical adaptation worlds
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import structlog

from crawler_agent.cognitive.practical_worlds import (
    PRACTICAL_WORLDS,
    PracticalWorld,
    WorldType,
    get_practical_world,
    get_worlds_by_difficulty,
)
from crawler_agent.cognitive.survival_worlds import (
    ALL_SURVIVAL_WORLDS,
    SurvivalChallenge,
    TaskType,
    get_survival_world,
    get_worlds_by_tier,
)


@dataclass
class SkillWorldMapping:
    skill: str
    worlds: list[str]
    weight: float = 1.0


SKILL_WORLD_MAP: list[SkillWorldMapping] = [
    SkillWorldMapping("navigation", ["small_house", "indoor_maze", "office_building"]),
    SkillWorldMapping("climbing", ["construction_site", "parkour_course", "stair_climb"]),
    SkillWorldMapping("pushing", ["warehouse", "truck_loading", "construction_site"]),
    SkillWorldMapping("balance", ["parkour_course", "stair_climb", "robot_obstacle_course"]),
    SkillWorldMapping("jumping", ["parkour_course", "robot_obstacle_course"]),
    SkillWorldMapping("door_use", ["small_house", "office_building", "indoor_maze"]),
    SkillWorldMapping("stairs", ["stair_climb", "office_building", "construction_site"]),
    SkillWorldMapping("object_manipulation", ["warehouse", "truck_loading", "small_house"]),
    SkillWorldMapping("endurance", ["stair_climb", "robot_obstacle_course", "parkour_course"]),
    SkillWorldMapping(
        "problem_solving", ["indoor_maze", "parkour_course", "robot_obstacle_course"]
    ),
    # Survival/critical mappings
    SkillWorldMapping("fire_survival", ["fire_escape", "multi_hazard", "extreme_weather_rescue"]),
    SkillWorldMapping("flood_survival", ["flood_escape", "multi_hazard"]),
    SkillWorldMapping("earthquake_survival", ["earthquake_rubble", "multi_hazard"]),
    SkillWorldMapping("rescue", ["rescue_mission", "multi_robot_rescue", "extreme_weather_rescue"]),
    SkillWorldMapping("hazard_avoidance", ["chemical_zone", "fire_escape", "multi_hazard"]),
    SkillWorldMapping("balance_extreme", ["high_wind", "ice_rink", "sloped_path"]),
    SkillWorldMapping(
        "damage_adaptation", ["damaged_robot", "total_system_failure", "catastrophic_failure"]
    ),
    SkillWorldMapping("unknown_terrain", ["hostile_terrain_mission", "unknown_environment_scan"]),
    SkillWorldMapping("tool_advanced", ["tool_sequence", "basic_tool"]),
    SkillWorldMapping("night_operations", ["night_nav", "total_system_failure"]),
]


@dataclass
class SelectionCriteria:
    weak_skills: list[str] = field(default_factory=list)
    goal_description: str = ""
    max_difficulty: float = 1.0
    preferred_type: WorldType | None = None
    exclude_worlds: list[str] = field(default_factory=list)
    prefer_variety: bool = True


@dataclass
class SelectionResult:
    world: PracticalWorld
    reason: str
    matched_skills: list[str]
    difficulty_rating: float


class WorldSelector:
    """Picks practical world based on skill needs."""

    def __init__(self):
        self.logger = structlog.get_logger(component="world_selector")
        self.history: list[str] = []
        self.skill_scores: dict[str, float] = {}

    def update_skill(self, skill: str, score: float):
        """Update skill mastery score."""
        self.skill_scores[skill] = max(0.0, min(1.0, score))

    def get_weak_skills(self, threshold: float = 0.5) -> list[str]:
        """Get skills below mastery threshold."""
        return [s for s, score in self.skill_scores.items() if score < threshold]

    def select(self, criteria: SelectionCriteria) -> SelectionResult:
        """Select best world based on criteria."""
        candidates = []

        # Search both practical and survival worlds
        all_worlds = {}
        all_worlds.update(PRACTICAL_WORLDS)
        for name, world in ALL_SURVIVAL_WORLDS.items():
            all_worlds[name] = world

        for name, world in all_worlds.items():
            if name in criteria.exclude_worlds:
                continue

            # Handle difficulty filtering for both world types
            if isinstance(world, SurvivalChallenge):
                if world.tier > criteria.max_difficulty * 4:
                    continue
            elif hasattr(world, "difficulty"):
                if world.difficulty > criteria.max_difficulty:
                    continue

            score = 0.0
            matched = []

            for mapping in SKILL_WORLD_MAP:
                if mapping.skill in criteria.weak_skills:
                    if name in mapping.worlds:
                        score += mapping.weight * 2.0
                        matched.append(mapping.skill)

            # Tag matching
            tags = world.tags if hasattr(world, "tags") else []
            for tag in tags:
                for skill in criteria.weak_skills:
                    if skill.replace("_", " ") in tag or tag in skill.replace("_", " "):
                        score += 0.5

            if criteria.goal_description:
                goal_lower = criteria.goal_description.lower()
                for tag in tags:
                    if tag in goal_lower:
                        score += 1.0

            if criteria.prefer_variety and name in self.history[-3:]:
                score -= 0.5

            candidates.append((world, score, matched))

        if not candidates:
            fallback = get_practical_world("small_house")
            return SelectionResult(
                world=fallback,
                reason="No suitable world found, using default",
                matched_skills=[],
                difficulty_rating=fallback.difficulty,
            )

        candidates.sort(key=lambda x: x[1], reverse=True)
        best_world, best_score, matched = candidates[0]

        self.history.append(best_world.name if hasattr(best_world, "name") else str(best_world))
        if len(self.history) > 20:
            self.history = self.history[-20:]

        reason_parts = []
        if matched:
            reason_parts.append(f"addresses {', '.join(matched)}")
        if best_score > 2:
            reason_parts.append("strong skill match")
        elif best_score > 0:
            reason_parts.append("partial match")
        else:
            reason_parts.append("available option")

        return SelectionResult(
            world=best_world,
            reason=f"Selected: {'; '.join(reason_parts)}",
            matched_skills=matched,
            difficulty_rating=best_world.difficulty
            if hasattr(best_world, "difficulty")
            else best_world.tier / 4.0,
        )

    def select_by_goal(self, goal: str) -> SelectionResult:
        """Select world based on natural language goal."""
        criteria = SelectionCriteria(
            goal_description=goal,
            weak_skills=self.get_weak_skills(),
        )
        return self.select(criteria)

    def select_by_difficulty(self, max_difficulty: float) -> SelectionResult:
        """Select easiest available world under difficulty cap."""
        criteria = SelectionCriteria(max_difficulty=max_difficulty)
        return self.select(criteria)

    def get_progression(self) -> list[PracticalWorld]:
        """Get worlds in difficulty order for progressive training."""
        return get_worlds_by_difficulty()

    def to_context(self) -> str:
        weak = self.get_weak_skills()
        recent = self.history[-3:] if self.history else []
        practical_count = len(PRACTICAL_WORLDS)
        survival_count = len(ALL_SURVIVAL_WORLDS)
        return (
            f"World Selector: {practical_count} practical + {survival_count} survival worlds, "
            f"{len(weak)} weak skills, recent: {', '.join(recent)}"
        )
