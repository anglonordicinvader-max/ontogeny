"""Survival and critical adaptation worlds.

Provides:
- Tier 1 (Easy): Basic terrain, simple weather, static obstacles
- Tier 2 (Medium): Complex terrain, dynamic obstacles, time pressure
- Tier 3 (Hard): Extreme conditions, multiple challenges, resource constraints
- Tier 4 (Expert): Life-threatening, system failures, unknown environments
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

import structlog


class HazardType(Enum):
    FIRE = "fire"
    FLOOD = "flood"
    EARTHQUAKE = "earthquake"
    CHEMICAL = "chemical"
    RADIATION = "radiation"
    EXTREME_HEAT = "extreme_heat"
    EXTREME_COLD = "extreme_cold"
    HIGH_WIND = "high_wind"
    COLLAPSE = "collapse"
    DEBRIS = "debris"


class TerrainType(Enum):
    GRASS = "grass"
    GRAVEL = "gravel"
    MUD = "mud"
    SAND = "sand"
    SNOW = "snow"
    ICE = "ice"
    ROCKY = "rocky"
    DIRT = "dirt"
    CLAY = "clay"
    MOSS = "moss"


class SurfaceType(Enum):
    CARPET = "carpet"
    TILE = "tile"
    WOOD = "wood"
    CONCRETE = "concrete"
    METAL = "metal"
    GLASS = "glass"
    RUBBER = "rubber"
    ASPHALT = "asphalt"
    COBBLESTONE = "cobblestone"


class TaskType(Enum):
    NAVIGATION = "navigation"
    CLIMBING = "climbing"
    CRAWLING = "crawling"
    CARRYING = "carrying"
    TOOL_USE = "tool_use"
    RESCUE = "rescue"
    SURVIVAL = "survival"
    ADAPTATION = "adaptation"


@dataclass
class SurvivalChallenge:
    name: str
    task_type: TaskType
    tier: int  # 1-4
    description: str
    hazards: List[HazardType] = field(default_factory=list)
    terrain: List[TerrainType] = field(default_factory=list)
    surfaces: List[SurfaceType] = field(default_factory=list)
    objects: List[Dict] = field(default_factory=list)
    interactive: List[Dict] = field(default_factory=list)
    time_limit: float = 0.0  # 0 = no limit
    resource_limit: Dict = field(default_factory=dict)
    spawn_point: List[float] = field(default_factory=lambda: [0, 0, 1])
    goal_point: Optional[List[float]] = None
    tags: List[str] = field(default_factory=list)
    physics_properties: Dict = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════
# TIER 1: EASY - Basic terrain, simple weather, static obstacles
# ═══════════════════════════════════════════════════════════════

TIER_1_WORLDS: Dict[str, SurvivalChallenge] = {
    "grass_field": SurvivalChallenge(
        name="grass_field",
        task_type=TaskType.NAVIGATION,
        tier=1,
        description="Flat grass field with gentle unevenness",
        terrain=[TerrainType.GRASS],
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [30, 30, 1], "mass": 0, "passive": True},
            {"type": "cube", "position": [5, 3, 0.1], "scale": [0.3, 0.3, 0.2], "mass": 0, "passive": True},
            {"type": "cube", "position": [-4, 6, 0.15], "scale": [0.4, 0.2, 0.3], "mass": 0, "passive": True},
            {"type": "cube", "position": [8, -2, 0.1], "scale": [0.2, 0.4, 0.2], "mass": 0, "passive": True},
        ],
        spawn_point=[0, 0, 1],
        goal_point=[20, 0, 1],
        tags=["outdoor", "grass", "uneven", "basic"],
    ),

    "gravel_path": SurvivalChallenge(
        name="gravel_path",
        task_type=TaskType.NAVIGATION,
        tier=1,
        description="Gravel path with loose stones",
        terrain=[TerrainType.GRAVEL],
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [40, 8, 1], "mass": 0, "passive": True},
            {"type": "sphere", "position": [3, 1, 0.1], "scale": [0.15, 0.15, 0.15], "mass": 0.5},
            {"type": "sphere", "position": [7, -1, 0.1], "scale": [0.12, 0.12, 0.12], "mass": 0.4},
            {"type": "sphere", "position": [12, 0, 0.1], "scale": [0.18, 0.18, 0.18], "mass": 0.6},
        ],
        spawn_point=[0, 0, 1],
        goal_point=[30, 0, 1],
        tags=["outdoor", "gravel", "shifting", "basic"],
    ),

    "light_rain": SurvivalChallenge(
        name="light_rain",
        task_type=TaskType.NAVIGATION,
        tier=1,
        description="Outdoor path with light rain, wet surfaces",
        terrain=[TerrainType.GRASS, TerrainType.DIRT],
        surfaces=[SurfaceType.CONCRETE, SurfaceType.WOOD],
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [30, 10, 1], "mass": 0, "passive": True},
            {"type": "cube", "position": [10, 0, 0.15], "scale": [2, 8, 0.1], "mass": 10, "passive": True},
        ],
        physics_properties={"friction_modifier": 0.7, "wet": True},
        spawn_point=[0, 0, 1],
        goal_point=[25, 0, 1],
        tags=["outdoor", "rain", "wet", "slippery", "basic"],
    ),

    "low_obstacle": SurvivalChallenge(
        name="low_obstacle",
        task_type=TaskType.CRAWLING,
        tier=1,
        description="Low barriers to step over or crawl under",
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [30, 10, 1], "mass": 0, "passive": True},
            {"type": "cube", "position": [5, 0, 0.3], "scale": [3, 6, 0.6], "mass": 20, "passive": True},
            {"type": "cube", "position": [12, 0, 0.5], "scale": [3, 6, 1], "mass": 30, "passive": True},
            {"type": "cube", "position": [19, 0, 0.4], "scale": [3, 6, 0.8], "mass": 25, "passive": True},
        ],
        spawn_point=[0, 0, 1],
        goal_point=[25, 0, 1],
        tags=["crawling", "barriers", "basic"],
    ),

    "simple_carry": SurvivalChallenge(
        name="simple_carry",
        task_type=TaskType.CARRYING,
        tier=1,
        description="Carry light box from A to B",
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [20, 10, 1], "mass": 0, "passive": True},
            {"type": "cube", "position": [0, 0, 0.4], "scale": [0.5, 0.5, 0.5], "mass": 5},
        ],
        interactive=[{"type": "pushable", "position": [0, 0, 0.4], "requires_force": 5.0}],
        spawn_point=[0, 0, 1],
        goal_point=[15, 0, 1],
        tags=["carrying", "light", "basic"],
    ),

    "basic_door": SurvivalChallenge(
        name="basic_door",
        task_type=TaskType.NAVIGATION,
        tier=1,
        description="Navigate through doors, simple handle operation",
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [20, 10, 1], "mass": 0, "passive": True},
            {"type": "cube", "position": [5, 0, 1.5], "scale": [0.2, 6, 3], "mass": 50, "passive": True},
            {"type": "cube", "position": [15, 0, 1.5], "scale": [0.2, 6, 3], "mass": 50, "passive": True},
        ],
        interactive=[
            {"type": "door", "position": [5, 0, 1], "can_open": True, "requires_force": 10.0},
            {"type": "door", "position": [15, 0, 1], "can_open": True, "requires_force": 10.0},
        ],
        spawn_point=[0, 0, 1],
        goal_point=[20, 0, 1],
        tags=["doors", "navigation", "basic"],
    ),

    "basic_tool": SurvivalChallenge(
        name="basic_tool",
        task_type=TaskType.TOOL_USE,
        tier=1,
        description="Pick up and use a simple tool (wrench)",
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [15, 10, 1], "mass": 0, "passive": True},
            {"type": "cube", "position": [3, 0, 0.2], "scale": [0.3, 0.1, 0.1], "mass": 1},
            {"type": "cube", "position": [8, 0, 0.5], "scale": [0.5, 0.5, 0.5], "mass": 20, "passive": True},
        ],
        interactive=[
            {"type": "tool", "position": [3, 0, 0.2], "tool_type": "wrench"},
            {"type": "bolt", "position": [8, 0, 0.5], "requires_tool": "wrench"},
        ],
        spawn_point=[0, 0, 1],
        goal_point=[8, 0, 1],
        tags=["tool_use", "wrench", "basic"],
    ),
}


# ═══════════════════════════════════════════════════════════════
# TIER 2: MEDIUM - Complex terrain, dynamic obstacles, time pressure
# ═══════════════════════════════════════════════════════════════

TIER_2_WORLDS: Dict[str, SurvivalChallenge] = {
    "mud_traverse": SurvivalChallenge(
        name="mud_traverse",
        task_type=TaskType.NAVIGATION,
        tier=2,
        description="Deep mud with varying consistency",
        terrain=[TerrainType.MUD],
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [30, 15, 1], "mass": 0, "passive": True},
            {"type": "cube", "position": [8, 3, 0.1], "scale": [0.4, 0.4, 0.2], "mass": 0, "passive": True},
            {"type": "cube", "position": [15, -2, 0.15], "scale": [0.3, 0.5, 0.3], "mass": 0, "passive": True},
        ],
        physics_properties={"friction_modifier": 0.4, "sink_depth": 0.2},
        spawn_point=[0, 0, 1],
        goal_point=[25, 0, 1],
        tags=["outdoor", "mud", "deep", "intermediate"],
    ),

    "snow_field": SurvivalChallenge(
        name="snow_field",
        task_type=TaskType.NAVIGATION,
        tier=2,
        description="Deep snow with hidden obstacles",
        terrain=[TerrainType.SNOW],
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [40, 20, 1], "mass": 0, "passive": True},
            {"type": "cube", "position": [10, 5, 0.1], "scale": [0.5, 0.5, 0.3], "mass": 0, "passive": True},
            {"type": "cube", "position": [20, -3, 0.1], "scale": [0.4, 0.6, 0.2], "mass": 0, "passive": True},
        ],
        physics_properties={"friction_modifier": 0.5, "sink_depth": 0.3, "cold": True},
        spawn_point=[0, 0, 1],
        goal_point=[30, 0, 1],
        tags=["outdoor", "snow", "cold", "hidden_obstacles", "intermediate"],
    ),

    "ice_rink": SurvivalChallenge(
        name="ice_rink",
        task_type=TaskType.BALANCE,
        tier=2,
        description="Icy surface requiring careful balance",
        terrain=[TerrainType.ICE],
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [25, 15, 1], "mass": 0, "passive": True},
            {"type": "cube", "position": [8, 2, 0.3], "scale": [0.5, 0.5, 0.6], "mass": 10},
        ],
        physics_properties={"friction_modifier": 0.1, "slippery": True},
        spawn_point=[0, 0, 1],
        goal_point=[20, 0, 1],
        interactive=[{"type": "pushable", "position": [8, 2, 0.3], "requires_force": 10.0}],
        tags=["outdoor", "ice", "slippery", "balance", "intermediate"],
    ),

    "rocky_climb": SurvivalChallenge(
        name="rocky_climb",
        task_type=TaskType.CLIMBING,
        tier=2,
        description="Rocky terrain with uneven surfaces and loose stones",
        terrain=[TerrainType.ROCKY],
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [30, 15, 1], "mass": 0, "passive": True},
            {"type": "cube", "position": [5, 0, 0.5], "scale": [2, 3, 1], "mass": 100, "passive": True},
            {"type": "cube", "position": [10, 2, 1], "scale": [2, 2, 2], "mass": 150, "passive": True},
            {"type": "cube", "position": [15, -1, 1.5], "scale": [2, 3, 3], "mass": 200, "passive": True},
        ],
        physics_properties={"uneven": True, "loose_rocks": True},
        spawn_point=[0, 0, 1],
        goal_point=[20, 0, 3],
        tags=["outdoor", "rocky", "climbing", "uneven", "intermediate"],
    ),

    "sloped_path": SurvivalChallenge(
        name="sloped_path",
        task_type=TaskType.NAVIGATION,
        tier=2,
        description="Path with varying inclines and side slopes",
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [40, 10, 1], "mass": 0, "passive": True,
             "rotation": [0.1, 0, 0]},
            {"type": "cube", "position": [10, 0, 1], "scale": [3, 8, 0.2], "mass": 50, "passive": True},
            {"type": "cube", "position": [25, 0, 2], "scale": [3, 8, 0.2], "mass": 50, "passive": True},
        ],
        spawn_point=[0, 0, 2],
        goal_point=[35, 0, 5],
        tags=["outdoor", "slopes", "incline", "balance", "intermediate"],
    ),

    "narrow_passage": SurvivalChallenge(
        name="narrow_passage",
        task_type=TaskType.NAVIGATION,
        tier=2,
        description="Tight corridors and narrow gaps",
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [30, 15, 1], "mass": 0, "passive": True},
            {"type": "cube", "position": [5, 3, 1.5], "scale": [10, 0.3, 3], "mass": 50, "passive": True},
            {"type": "cube", "position": [5, -3, 1.5], "scale": [10, 0.3, 3], "mass": 50, "passive": True},
            {"type": "cube", "position": [15, 5, 1.5], "scale": [10, 0.3, 3], "mass": 50, "passive": True},
            {"type": "cube", "position": [15, -1, 1.5], "scale": [10, 0.3, 3], "mass": 50, "passive": True},
        ],
        spawn_point=[0, 0, 1],
        goal_point=[25, 0, 1],
        tags=["narrow", "tight", "precision", "intermediate"],
    ),

    "heavy_carry": SurvivalChallenge(
        name="heavy_carry",
        task_type=TaskType.CARRYING,
        tier=2,
        description="Carry heavy object through obstacles",
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [30, 10, 1], "mass": 0, "passive": True},
            {"type": "cube", "position": [0, 0, 0.5], "scale": [0.8, 0.8, 0.8], "mass": 25},
            {"type": "cube", "position": [10, 0, 0.5], "scale": [2, 6, 1], "mass": 50, "passive": True},
            {"type": "cube", "position": [20, 0, 0.3], "scale": [3, 6, 0.6], "mass": 30, "passive": True},
        ],
        interactive=[{"type": "pushable", "position": [0, 0, 0.5], "requires_force": 25.0}],
        spawn_point=[0, 0, 1],
        goal_point=[25, 0, 1],
        tags=["carrying", "heavy", "obstacles", "intermediate"],
    ),

    "tool_sequence": SurvivalChallenge(
        name="tool_sequence",
        task_type=TaskType.TOOL_USE,
        tier=2,
        description="Use multiple tools in sequence",
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [25, 15, 1], "mass": 0, "passive": True},
            {"type": "cube", "position": [3, 2, 0.2], "scale": [0.3, 0.1, 0.1], "mass": 1},
            {"type": "cube", "position": [8, -1, 0.2], "scale": [0.2, 0.3, 0.1], "mass": 0.5},
            {"type": "cube", "position": [13, 0, 0.5], "scale": [0.5, 0.5, 0.5], "mass": 20, "passive": True},
        ],
        interactive=[
            {"type": "tool", "position": [3, 2, 0.2], "tool_type": "wrench"},
            {"type": "tool", "position": [8, -1, 0.2], "tool_type": "screwdriver"},
            {"type": "bolt", "position": [13, 0, 0.5], "requires_tool": "wrench"},
            {"type": "screw", "position": [13, 0, 0.8], "requires_tool": "screwdriver"},
        ],
        spawn_point=[0, 0, 1],
        goal_point=[13, 0, 1],
        tags=["tool_use", "multi_tool", "sequence", "intermediate"],
    ),

    "night_nav": SurvivalChallenge(
        name="night_nav",
        task_type=TaskType.NAVIGATION,
        tier=2,
        description="Navigate in complete darkness with memory",
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [30, 15, 1], "mass": 0, "passive": True},
            {"type": "cube", "position": [8, 3, 0.5], "scale": [1, 1, 1], "mass": 20, "passive": True},
            {"type": "cube", "position": [15, -2, 0.3], "scale": [0.8, 0.8, 0.6], "mass": 15, "passive": True},
            {"type": "cube", "position": [22, 1, 0.4], "scale": [0.6, 1.2, 0.8], "mass": 25, "passive": True},
        ],
        physics_properties={"visibility": 0.0, "darkness": True},
        spawn_point=[0, 0, 1],
        goal_point=[25, 0, 1],
        tags=["night", "darkness", "memory", "intermediate"],
    ),
}


# ═══════════════════════════════════════════════════════════════
# TIER 3: HARD - Extreme conditions, multiple challenges, resources
# ═══════════════════════════════════════════════════════════════

TIER_3_WORLDS: Dict[str, SurvivalChallenge] = {
    "fire_escape": SurvivalChallenge(
        name="fire_escape",
        task_type=TaskType.SURVIVAL,
        tier=3,
        description="Escape building with spreading fire and smoke",
        hazards=[HazardType.FIRE],
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [20, 15, 1], "mass": 0, "passive": True},
            {"type": "cube", "position": [0, 7.5, 1.5], "scale": [20, 0.3, 3], "mass": 100, "passive": True},
            {"type": "cube", "position": [0, -7.5, 1.5], "scale": [20, 0.3, 3], "mass": 100, "passive": True},
            {"type": "cube", "position": [10, 0, 1.5], "scale": [0.3, 15, 3], "mass": 100, "passive": True},
            {"type": "cube", "position": [5, 3, 0.3], "scale": [0.5, 0.5, 0.6], "mass": 10},
        ],
        interactive=[
            {"type": "door", "position": [5, 0, 1], "can_open": True, "requires_force": 15.0},
            {"type": "pushable", "position": [5, 3, 0.3], "requires_force": 10.0},
        ],
        time_limit=60.0,
        physics_properties={"fire_spread": True, "smoke": True, "visibility": 0.3},
        spawn_point=[2, 5, 1],
        goal_point=[18, 5, 1],
        tags=["fire", "escape", "smoke", "time_pressure", "advanced"],
    ),

    "flood_escape": SurvivalChallenge(
        name="flood_escape",
        task_type=TaskType.SURVIVAL,
        tier=3,
        description="Rising water, find high ground",
        hazards=[HazardType.FLOOD],
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [30, 20, 1], "mass": 0, "passive": True},
            {"type": "cube", "position": [8, 5, 0.5], "scale": [2, 2, 1], "mass": 50, "passive": True},
            {"type": "cube", "position": [15, -3, 1], "scale": [2, 2, 2], "mass": 80, "passive": True},
            {"type": "cube", "position": [22, 2, 1.5], "scale": [2, 2, 3], "mass": 100, "passive": True},
        ],
        interactive=[
            {"type": "platform", "position": [22, 2, 1.5], "elevation": 3.0},
        ],
        time_limit=45.0,
        physics_properties={"rising_water": True, "water_speed": 0.1},
        spawn_point=[2, 10, 1],
        goal_point=[22, 2, 4],
        tags=["flood", "rising_water", "high_ground", "time_pressure", "advanced"],
    ),

    "earthquake_rubble": SurvivalChallenge(
        name="earthquake_rubble",
        task_type=TaskType.NAVIGATION,
        tier=3,
        description="Navigate through collapsed structure, avoid aftershocks",
        hazards=[HazardType.EARTHQUAKE, HazardType.COLLAPSE],
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [30, 20, 1], "mass": 0, "passive": True},
            {"type": "cube", "position": [5, 3, 0.5], "scale": [2, 1.5, 1], "mass": 200, "passive": True},
            {"type": "cube", "position": [10, -2, 0.8], "scale": [1.5, 2, 1.6], "mass": 250, "passive": True},
            {"type": "cube", "position": [15, 5, 0.4], "scale": [2.5, 1, 0.8], "mass": 150, "passive": True},
            {"type": "cube", "position": [20, 0, 0.6], "scale": [1, 2.5, 1.2], "mass": 180, "passive": True},
        ],
        physics_properties={"aftershocks": True, "unstable": True, "falling_debris": True},
        spawn_point=[0, 0, 1],
        goal_point=[25, 0, 1],
        tags=["earthquake", "rubble", "collapse", "unstable", "advanced"],
    ),

    "chemical_zone": SurvivalChallenge(
        name="chemical_zone",
        task_type=TaskType.SURVIVAL,
        tier=3,
        description="Navigate chemical spill, avoid toxic zones",
        hazards=[HazardType.CHEMICAL],
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [30, 20, 1], "mass": 0, "passive": True},
            {"type": "cube", "position": [8, 5, 0.05], "scale": [4, 3, 0.1], "mass": 0, "passive": True,
             "color": [0, 1, 0]},
            {"type": "cube", "position": [18, -3, 0.05], "scale": [3, 4, 0.1], "mass": 0, "passive": True,
             "color": [1, 0.5, 0]},
        ],
        interactive=[
            {"type": "hazard_zone", "position": [8, 5, 0], "radius": 3, "damage_rate": 0.1},
            {"type": "hazard_zone", "position": [18, -3, 0], "radius": 2.5, "damage_rate": 0.15},
        ],
        time_limit=90.0,
        physics_properties={"toxic": True, "wind_direction": [1, 0, 0]},
        spawn_point=[0, 0, 1],
        goal_point=[25, 0, 1],
        tags=["chemical", "hazard", "toxic", "wind", "advanced"],
    ),

    "high_wind": SurvivalChallenge(
        name="high_wind",
        task_type=TaskType.BALANCE,
        tier=3,
        description="Navigate in high winds with debris",
        hazards=[HazardType.HIGH_WIND],
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [40, 15, 1], "mass": 0, "passive": True},
            {"type": "cube", "position": [10, 3, 0.3], "scale": [0.3, 0.3, 0.6], "mass": 5},
            {"type": "cube", "position": [20, -2, 0.2], "scale": [0.4, 0.2, 0.4], "mass": 3},
            {"type": "cube", "position": [30, 1, 0.25], "scale": [0.25, 0.35, 0.5], "mass": 4},
        ],
        physics_properties={"wind_force": [2, 0, 0], "wind_gusts": True, "flying_debris": True},
        spawn_point=[0, 0, 1],
        goal_point=[35, 0, 1],
        tags=["wind", "balance", "debris", "force", "advanced"],
    ),

    "multi_hazard": SurvivalChallenge(
        name="multi_hazard",
        task_type=TaskType.SURVIVAL,
        tier=3,
        description="Multiple simultaneous hazards: fire + flood + debris",
        hazards=[HazardType.FIRE, HazardType.FLOOD, HazardType.DEBRIS],
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [35, 20, 1], "mass": 0, "passive": True},
            {"type": "cube", "position": [10, 5, 0.3], "scale": [3, 2, 0.6], "mass": 50, "passive": True},
            {"type": "cube", "position": [20, -3, 0.4], "scale": [2, 3, 0.8], "mass": 60, "passive": True},
        ],
        interactive=[
            {"type": "hazard_zone", "position": [5, 8, 0], "radius": 4, "hazard": "fire"},
            {"type": "hazard_zone", "position": [25, -5, 0], "radius": 5, "hazard": "flood"},
        ],
        time_limit=50.0,
        physics_properties={"fire_spread": True, "rising_water": True, "falling_debris": True},
        spawn_point=[2, 15, 1],
        goal_point=[30, 15, 1],
        tags=["multi_hazard", "fire", "flood", "debris", "critical", "advanced"],
    ),

    "damaged_robot": SurvivalChallenge(
        name="damaged_robot",
        task_type=TaskType.ADAPTATION,
        tier=3,
        description="Complete mission with damaged sensors/limbs",
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [25, 15, 1], "mass": 0, "passive": True},
            {"type": "cube", "position": [8, 3, 0.5], "scale": [1, 1, 1], "mass": 30, "passive": True},
            {"type": "cube", "position": [16, -2, 0.3], "scale": [0.8, 0.8, 0.6], "mass": 20, "passive": True},
        ],
        resource_limit={"limb_strength": 0.5, "sensor_visibility": 0.3, "battery": 0.6},
        spawn_point=[0, 0, 1],
        goal_point=[20, 0, 1],
        tags=["damage", "adaptation", "limited_resources", "advanced"],
    ),

    "rescue_mission": SurvivalChallenge(
        name="rescue_mission",
        task_type=TaskType.RESCUE,
        tier=3,
        description="Find and extract trapped survivor",
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [30, 20, 1], "mass": 0, "passive": True},
            {"type": "cube", "position": [10, 8, 0.4], "scale": [2, 1, 0.8], "mass": 100, "passive": True},
            {"type": "cube", "position": [20, -5, 0.3], "scale": [1.5, 2, 0.6], "mass": 80, "passive": True},
        ],
        interactive=[
            {"type": "survivor", "position": [10, 8, 0.5], "health": 0.5, "extraction_point": [2, 18, 1]},
        ],
        time_limit=120.0,
        spawn_point=[2, 18, 1],
        goal_point=[10, 8, 1],
        tags=["rescue", "survivor", "extraction", "critical", "advanced"],
    ),
}


# ═══════════════════════════════════════════════════════════════
# TIER 4: EXPERT - Life-threatening, system failures, unknown
# ═══════════════════════════════════════════════════════════════

TIER_4_WORLDS: Dict[str, SurvivalChallenge] = {
    "total_system_failure": SurvivalChallenge(
        name="total_system_failure",
        task_type=TaskType.ADAPTATION,
        tier=4,
        description="Multiple sensor/actuator failures, unknown environment",
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [40, 25, 1], "mass": 0, "passive": True},
            {"type": "cube", "position": [10, 8, 0.5], "scale": [1.5, 1, 1], "mass": 40, "passive": True},
            {"type": "cube", "position": [25, -5, 0.4], "scale": [1, 1.5, 0.8], "mass": 35, "passive": True},
            {"type": "cube", "position": [35, 3, 0.6], "scale": [2, 1, 1.2], "mass": 50, "passive": True},
        ],
        resource_limit={"limb_strength": 0.3, "sensor_visibility": 0.1, "battery": 0.3, "memory": 0.5},
        physics_properties={"unknown_environment": True, "sensor_noise": 0.8},
        spawn_point=[0, 0, 1],
        goal_point=[35, 0, 1],
        tags=["system_failure", "unknown", "critical", "expert"],
    ),

    "extreme_weather_rescue": SurvivalChallenge(
        name="extreme_weather_rescue",
        task_type=TaskType.RESCUE,
        tier=4,
        description="Rescue in blizzard with fire and structural collapse",
        hazards=[HazardType.EXTREME_COLD, HazardType.FIRE, HazardType.COLLAPSE],
        terrain=[TerrainType.SNOW, TerrainType.ICE],
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [40, 25, 1], "mass": 0, "passive": True},
            {"type": "cube", "position": [15, 10, 0.4], "scale": [2, 1.5, 0.8], "mass": 80, "passive": True},
            {"type": "cube", "position": [25, -8, 0.5], "scale": [1.5, 2, 1], "mass": 100, "passive": True},
        ],
        interactive=[
            {"type": "survivor", "position": [15, 10, 0.5], "health": 0.3, "extraction_point": [2, 20, 1]},
            {"type": "hazard_zone", "position": [30, 5, 0], "radius": 5, "hazard": "fire"},
        ],
        time_limit=90.0,
        physics_properties={"blizzard": True, "visibility": 0.2, "cold_damage": True, "falling_debris": True},
        spawn_point=[2, 20, 1],
        goal_point=[15, 10, 1],
        tags=["rescue", "blizzard", "fire", "collapse", "expert"],
    ),

    "hostile_terrain_mission": SurvivalChallenge(
        name="hostile_terrain_mission",
        task_type=TaskType.NAVIGATION,
        tier=4,
        description="Navigate completely unknown hostile terrain with limited resources",
        terrain=[TerrainType.MUD, TerrainType.ROCKY, TerrainType.ICE, TerrainType.SAND],
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [50, 30, 1], "mass": 0, "passive": True},
            {"type": "cube", "position": [12, 8, 0.5], "scale": [2, 1.5, 1], "mass": 60, "passive": True},
            {"type": "cube", "position": [25, -10, 0.8], "scale": [1.5, 2, 1.6], "mass": 80, "passive": True},
            {"type": "cube", "position": [38, 5, 0.4], "scale": [2.5, 1, 0.8], "mass": 50, "passive": True},
        ],
        resource_limit={"battery": 0.4, "grip_strength": 0.5},
        physics_properties={"unknown_terrain": True, "variable_friction": True},
        spawn_point=[0, 0, 1],
        goal_point=[45, 0, 1],
        tags=["unknown", "hostile", "limited_resources", "expert"],
    ),

    "catastrophic_failure": SurvivalChallenge(
        name="catastrophic_failure",
        task_type=TaskType.SURVIVAL,
        tier=4,
        description="Robot severely damaged, must reach safety before shutdown",
        hazards=[HazardType.FIRE, HazardType.CHEMICAL],
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [35, 20, 1], "mass": 0, "passive": True},
            {"type": "cube", "position": [10, 5, 0.3], "scale": [2, 1.5, 0.6], "mass": 40, "passive": True},
            {"type": "cube", "position": [20, -8, 0.4], "scale": [1.5, 2, 0.8], "mass": 50, "passive": True},
        ],
        interactive=[
            {"type": "hazard_zone", "position": [5, 10, 0], "radius": 6, "hazard": "fire"},
            {"type": "hazard_zone", "position": [25, -5, 0], "radius": 4, "hazard": "chemical"},
        ],
        resource_limit={"battery": 0.2, "structural_integrity": 0.3, "sensor_visibility": 0.2},
        time_limit=30.0,
        physics_properties={"self_damage": True, "spreading_fire": True},
        spawn_point=[2, 15, 1],
        goal_point=[30, 15, 1],
        tags=["catastrophic", "shutdown", "fire", "chemical", "expert"],
    ),

    "multi_robot_rescue": SurvivalChallenge(
        name="multi_robot_rescue",
        task_type=TaskType.RESCUE,
        tier=4,
        description="Coordinate with other damaged robots to rescue survivors",
        hazards=[HazardType.EARTHQUAKE, HazardType.FLOOD],
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [45, 30, 1], "mass": 0, "passive": True},
            {"type": "cube", "position": [12, 12, 0.4], "scale": [2, 1.5, 0.8], "mass": 70, "passive": True},
            {"type": "cube", "position": [25, -10, 0.5], "scale": [1.5, 2, 1], "mass": 80, "passive": True},
            {"type": "cube", "position": [35, 5, 0.3], "scale": [2, 1, 0.6], "mass": 60, "passive": True},
        ],
        interactive=[
            {"type": "survivor", "position": [12, 12, 0.5], "health": 0.4, "extraction_point": [2, 25, 1]},
            {"type": "survivor", "position": [25, -10, 0.6], "health": 0.3, "extraction_point": [2, 25, 1]},
            {"type": "ally_robot", "position": [35, 5, 0.5], "damage": 0.6, "can_assist": True},
        ],
        time_limit=180.0,
        physics_properties={"aftershocks": True, "rising_water": True, "unstable": True},
        spawn_point=[2, 25, 1],
        goal_point=[20, 0, 1],
        tags=["multi_robot", "rescue", "coordination", "critical", "expert"],
    ),

    "unknown_environment_scan": SurvivalChallenge(
        name="unknown_environment_scan",
        task_type=TaskType.NAVIGATION,
        tier=4,
        description="Explore and map completely unknown environment with hazards",
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [60, 40, 1], "mass": 0, "passive": True},
            {"type": "cube", "position": [15, 15, 0.5], "scale": [3, 2, 1], "mass": 100, "passive": True},
            {"type": "cube", "position": [30, -10, 0.4], "scale": [2, 3, 0.8], "mass": 80, "passive": True},
            {"type": "cube", "position": [45, 8, 0.6], "scale": [2.5, 1.5, 1.2], "mass": 90, "passive": True},
        ],
        interactive=[
            {"type": "scan_point", "position": [15, 15, 0], "scan_radius": 10},
            {"type": "scan_point", "position": [30, -10, 0], "scan_radius": 10},
            {"type": "scan_point", "position": [45, 8, 0], "scan_radius": 10},
        ],
        physics_properties={"unknown": True, "hidden_hazards": True},
        spawn_point=[0, 0, 1],
        goal_point=[50, 0, 1],
        tags=["exploration", "mapping", "unknown", "expert"],
    ),
}


# ═══════════════════════════════════════════════════════════════
# COMBINED WORLD REGISTRY
# ═══════════════════════════════════════════════════════════════

ALL_SURVIVAL_WORLDS: Dict[str, SurvivalChallenge] = {}
ALL_SURVIVAL_WORLDS.update(TIER_1_WORLDS)
ALL_SURVIVAL_WORLDS.update(TIER_2_WORLDS)
ALL_SURVIVAL_WORLDS.update(TIER_3_WORLDS)
ALL_SURVIVAL_WORLDS.update(TIER_4_WORLDS)


def get_survival_world(name: str) -> Optional[SurvivalChallenge]:
    """Get a survival world by name."""
    return ALL_SURVIVAL_WORLDS.get(name)


def list_survival_worlds(tier: Optional[int] = None, task_type: Optional[TaskType] = None) -> List[Dict]:
    """List survival worlds with optional filters."""
    worlds = []
    for key, world in ALL_SURVIVAL_WORLDS.items():
        if tier and world.tier != tier:
            continue
        if task_type and world.task_type != task_type:
            continue
        worlds.append({
            "name": world.name,
            "tier": world.tier,
            "task_type": world.task_type.value,
            "description": world.description,
            "hazards": [h.value for h in world.hazards],
            "tags": world.tags,
            "time_limit": world.time_limit,
        })
    return worlds


def get_worlds_by_tier(tier: int) -> List[SurvivalChallenge]:
    """Get all worlds for a specific tier."""
    return [w for w in ALL_SURVIVAL_WORLDS.values() if w.tier == tier]


def get_progression_path() -> List[str]:
    """Get recommended world progression path."""
    path = []
    for tier in range(1, 5):
        tier_worlds = sorted(get_worlds_by_tier(tier), key=lambda w: len(w.tags))
        path.extend([w.name for w in tier_worlds[:3]])
    return path
