"""Practical world environments for Blender.

Provides:
- Buildings with rooms, doors, windows
- Stairs, ramps, elevators
- Vehicles, ramps, obstacles
- Interactive objects (doors, levers, buttons)
- Physically demanding environments
- Multi-room navigation
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import structlog


class WorldType(Enum):
    BUILDING = "building"
    OUTDOOR = "outdoor"
    VEHICLE = "vehicle"
    OBSTACLE_COURSE = "obstacle_course"
    INDUSTRIAL = "industrial"
    RESIDENTIAL = "residential"


class InteractiveType(Enum):
    DOOR = "door"
    LEVER = "lever"
    BUTTON = "button"
    ELEVATOR = "elevator"
    RAMP = "ramp"
    LADDER = "ladder"
    PLATFORM = "platform"
    BREAKABLE = "breakable"
    PUSHABLE = "pushable"


@dataclass
class InteractiveObject:
    object_type: InteractiveType
    position: List[float]
    rotation: List[float] = field(default_factory=lambda: [0, 0, 0])
    scale: List[float] = field(default_factory=lambda: [1, 1, 1])
    requires_force: float = 0.0
    can_open: bool = False
    linked_to: Optional[str] = None
    state: str = "closed"
    metadata: Dict = field(default_factory=dict)


@dataclass
class PracticalWorld:
    name: str
    world_type: WorldType
    description: str
    objects: List[Dict] = field(default_factory=list)
    interactive: List[InteractiveObject] = field(default_factory=list)
    spawn_point: List[float] = field(default_factory=lambda: [0, 0, 1])
    goal_point: Optional[List[float]] = None
    difficulty: float = 0.5
    tags: List[str] = field(default_factory=list)
    physics_properties: Dict = field(default_factory=dict)


PRACTICAL_WORLDS: Dict[str, PracticalWorld] = {
    # ─── Buildings ───────────────────────────────────────────────
    "small_house": PracticalWorld(
        name="small_house",
        world_type=WorldType.RESIDENTIAL,
        description="Single-story house with 4 rooms, 2 doors, windows",
        difficulty=0.3,
        tags=["indoor", "navigation", "doors", "rooms"],
        spawn_point=[0, 0, 1],
        goal_point=[8, 8, 1],
        objects=[
            # Floor
            {"type": "plane", "position": [0, 0, 0], "scale": [12, 12, 1], "mass": 0, "passive": True},
            # Walls - outer
            {"type": "cube", "position": [0, 6, 1.5], "scale": [12, 0.2, 3], "mass": 50, "passive": True},  # North
            {"type": "cube", "position": [0, -6, 1.5], "scale": [12, 0.2, 3], "mass": 50, "passive": True},  # South
            {"type": "cube", "position": [6, 0, 1.5], "scale": [0.2, 12, 3], "mass": 50, "passive": True},  # East
            {"type": "cube", "position": [-6, 0, 1.5], "scale": [0.2, 12, 3], "mass": 50, "passive": True},  # West
            # Interior walls
            {"type": "cube", "position": [0, 0, 1.5], "scale": [0.15, 6, 3], "mass": 30, "passive": True},  # Divider
            {"type": "cube", "position": [3, 3, 1.5], "scale": [6, 0.15, 3], "mass": 30, "passive": True},  # Room divider
            # Furniture
            {"type": "cube", "position": [-4, 4, 0.5], "scale": [2, 1, 1], "mass": 10, "passive": True},  # Table
            {"type": "cube", "position": [-4, 4, 1.2], "scale": [0.3, 0.3, 0.5], "mass": 2},  # Chair
            {"type": "cube", "position": [4, -4, 0.3], "scale": [2, 1.5, 0.6], "mass": 15, "passive": True},  # Bed
        ],
        interactive=[
            InteractiveObject(InteractiveType.DOOR, [0, -3, 1], [0, 0, 0], [1, 0.1, 2], can_open=True, state="closed"),
            InteractiveObject(InteractiveType.DOOR, [3, 0, 1], [0, 0, 0], [1, 0.1, 2], can_open=True, state="closed"),
        ],
    ),

    "office_building": PracticalWorld(
        name="office_building",
        world_type=WorldType.BUILDING,
        description="3-story office with stairs, elevator, multiple rooms",
        difficulty=0.6,
        tags=["indoor", "multi-story", "stairs", "elevator", "navigation"],
        spawn_point=[0, 0, 1],
        goal_point=[10, 5, 8],
        objects=[
            # Ground floor
            {"type": "plane", "position": [0, 0, 0], "scale": [20, 20, 1], "mass": 0, "passive": True},
            # Floor 2
            {"type": "cube", "position": [0, 0, 3], "scale": [20, 20, 0.3], "mass": 200, "passive": True},
            # Floor 3
            {"type": "cube", "position": [0, 0, 6], "scale": [20, 20, 0.3], "mass": 200, "passive": True},
            # Outer walls
            {"type": "cube", "position": [0, 10, 1.5], "scale": [20, 0.3, 3], "mass": 100, "passive": True},
            {"type": "cube", "position": [0, -10, 1.5], "scale": [20, 0.3, 3], "mass": 100, "passive": True},
            {"type": "cube", "position": [10, 0, 1.5], "scale": [0.3, 20, 3], "mass": 100, "passive": True},
            {"type": "cube", "position": [-10, 0, 1.5], "scale": [0.3, 20, 3], "mass": 100, "passive": True},
            # Stairs (stacked boxes)
            *[{"type": "cube", "position": [8, -8, i * 0.3 + 0.15], "scale": [1.5, 0.5, 0.3], "mass": 20, "passive": True}
              for i in range(10)],
            # Desks floor 1
            {"type": "cube", "position": [-5, 5, 0.5], "scale": [2, 1, 1], "mass": 10, "passive": True},
            {"type": "cube", "position": [-5, 2, 0.5], "scale": [2, 1, 1], "mass": 10, "passive": True},
            # Chairs
            {"type": "cube", "position": [-5, 5, 1.2], "scale": [0.3, 0.3, 0.5], "mass": 2},
            # Boxes to push
            {"type": "cube", "position": [2, -5, 0.3], "scale": [0.6, 0.6, 0.6], "mass": 5},
            {"type": "cube", "position": [3, -5, 0.3], "scale": [0.6, 0.6, 0.6], "mass": 5},
        ],
        interactive=[
            InteractiveObject(InteractiveType.DOOR, [5, 0, 1], can_open=True),
            InteractiveObject(InteractiveType.DOOR, [-5, 0, 1], can_open=True),
            InteractiveObject(InteractiveType.ELEVATOR, [8, 8, 0], scale=[2, 2, 3],
                           metadata={"floors": 3, "current_floor": 1}),
            InteractiveObject(InteractiveType.PUSHABLE, [2, -5, 0.3], scale=[0.6, 0.6, 0.6], requires_force=5.0),
        ],
    ),

    "warehouse": PracticalWorld(
        name="warehouse",
        world_type=WorldType.INDUSTRIAL,
        description="Large warehouse with shelving, forklift path, loading dock",
        difficulty=0.5,
        tags=["indoor", "large", "pushable", "obstacles"],
        spawn_point=[0, 0, 1],
        goal_point=[20, 0, 1],
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [40, 30, 1], "mass": 0, "passive": True},
            # Walls
            {"type": "cube", "position": [0, 15, 3], "scale": [40, 0.3, 6], "mass": 200, "passive": True},
            {"type": "cube", "position": [0, -15, 3], "scale": [40, 0.3, 6], "mass": 200, "passive": True},
            {"type": "cube", "position": [20, 0, 3], "scale": [0.3, 30, 6], "mass": 200, "passive": True},
            {"type": "cube", "position": [-20, 0, 3], "scale": [0.3, 30, 6], "mass": 200, "passive": True},
            # Shelving units (rows of boxes)
            *[{"type": "cube", "position": [x, y, 1.5], "scale": [0.5, 3, 3], "mass": 50, "passive": True}
              for x in range(-15, 16, 5) for y in range(-10, 11, 5)],
            # Pallets with boxes
            *[{"type": "cube", "position": [x, y, 0.4], "scale": [1.2, 1.2, 0.8], "mass": 20}
              for x in range(-10, 11, 7) for y in range(-8, 9, 6)],
            # Forklift (simple box representation)
            {"type": "cube", "position": [-15, 0, 0.5], "scale": [2, 1.2, 1], "mass": 300},
        ],
        interactive=[
            InteractiveObject(InteractiveType.PUSHABLE, [x, y, 0.4], scale=[1.2, 1.2, 0.8], requires_force=15.0)
            for x in range(-10, 11, 7) for y in range(-8, 9, 6)
        ],
    ),

    # ─── Outdoor ───────────────────────────────────────────────
    "construction_site": PracticalWorld(
        name="construction_site",
        world_type=WorldType.OUTDOOR,
        description="Construction site with scaffolding, ramps, loose materials",
        difficulty=0.7,
        tags=["outdoor", "climbing", "ramps", "pushable", "unstable"],
        spawn_point=[0, 0, 1],
        goal_point=[15, 10, 5],
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [30, 30, 1], "mass": 0, "passive": True},
            # Scaffolding poles
            *[{"type": "cylinder", "position": [x, y, 2.5], "scale": [0.1, 0.1, 5], "mass": 10, "passive": True}
              for x in range(0, 16, 4) for y in range(0, 11, 4)],
            # Scaffolding platforms
            *[{"type": "cube", "position": [x, y, 2], "scale": [3.5, 3.5, 0.15], "mass": 30, "passive": True}
              for x in range(0, 16, 4) for y in range(0, 11, 4)],
            # Ramp
            {"type": "cube", "position": [2, 0, 1], "scale": [4, 2, 0.2], "mass": 20, "passive": True,
             "rotation": [0.2, 0, 0]},
            # Loose bricks
            *[{"type": "cube", "position": [x, y, 0.2], "scale": [0.3, 0.15, 0.1], "mass": 2}
              for x in range(-5, 6) for y in range(-3, 4)],
            # Steel beam
            {"type": "cube", "position": [8, 5, 0.2], "scale": [6, 0.3, 0.3], "mass": 100},
            # Concrete blocks
            {"type": "cube", "position": [-3, 8, 0.5], "scale": [1, 1, 1], "mass": 50},
            {"type": "cube", "position": [-1, 8, 0.5], "scale": [1, 1, 1], "mass": 50},
        ],
        interactive=[
            InteractiveObject(InteractiveType.PUSHABLE, [-3, 8, 0.5], scale=[1, 1, 1], requires_force=30.0),
            InteractiveObject(InteractiveType.PUSHABLE, [-1, 8, 0.5], scale=[1, 1, 1], requires_force=30.0),
            InteractiveObject(InteractiveType.RAMP, [2, 0, 1], scale=[4, 2, 0.2]),
        ],
    ),

    "parkour_course": PracticalWorld(
        name="parkour_course",
        world_type=WorldType.OBSTACLE_COURSE,
        description="Parkour course with walls, gaps, ledges, climbing",
        difficulty=0.8,
        tags=["outdoor", "climbing", "jumping", "balance", "physically_demanding"],
        spawn_point=[0, 0, 1],
        goal_point=[25, 0, 6],
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [50, 10, 1], "mass": 0, "passive": True},
            # Wall 1 (low)
            {"type": "cube", "position": [5, 0, 1], "scale": [0.3, 3, 2], "mass": 100, "passive": True},
            # Wall 2 (medium)
            {"type": "cube", "position": [10, 0, 1.5], "scale": [0.3, 3, 3], "mass": 100, "passive": True},
            # Wall 3 (high, need to climb)
            {"type": "cube", "position": [15, 0, 2], "scale": [0.3, 3, 4], "mass": 100, "passive": True},
            # Gap (floor missing)
            # Ledge to jump to
            {"type": "cube", "position": [18, 0, 2], "scale": [1, 2, 0.3], "mass": 50, "passive": True},
            {"type": "cube", "position": [20, 0, 3], "scale": [1, 2, 0.3], "mass": 50, "passive": True},
            {"type": "cube", "position": [22, 0, 4], "scale": [1, 2, 0.3], "mass": 50, "passive": True},
            # Balance beam
            {"type": "cube", "position": [23, 0, 5], "scale": [3, 0.15, 0.15], "mass": 20, "passive": True},
            # Final platform
            {"type": "cube", "position": [25, 0, 6], "scale": [2, 2, 0.3], "mass": 50, "passive": True},
            # Stepping stones
            {"type": "cube", "position": [7, 2, 0.5], "scale": [0.8, 0.8, 1], "mass": 30, "passive": True},
            {"type": "cube", "position": [8, -1, 0.8], "scale": [0.8, 0.8, 1.6], "mass": 30, "passive": True},
        ],
        interactive=[
            InteractiveObject(InteractiveType.PUSHABLE, [7, 2, 0.5], requires_force=10.0),
        ],
    ),

    # ─── Vehicle ───────────────────────────────────────────────
    "truck_loading": PracticalWorld(
        name="truck_loading",
        world_type=WorldType.VEHICLE,
        description="Loading dock with truck, ramp, boxes to load",
        difficulty=0.6,
        tags=["outdoor", "pushable", "ramp", "loading"],
        spawn_point=[0, 0, 1],
        goal_point=[8, 0, 2],
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [20, 15, 1], "mass": 0, "passive": True},
            # Truck body
            {"type": "cube", "position": [8, 0, 1.5], "scale": [4, 2.5, 3], "mass": 500, "passive": True},
            # Truck bed (open top implied)
            {"type": "cube", "position": [8, 0, 0.3], "scale": [4, 2.5, 0.3], "mass": 200, "passive": True},
            # Loading ramp
            {"type": "cube", "position": [5, 0, 0.6], "scale": [3, 2, 0.15], "mass": 30, "passive": True,
             "rotation": [0.15, 0, 0]},
            # Boxes to load
            {"type": "cube", "position": [-3, 2, 0.4], "scale": [0.8, 0.8, 0.8], "mass": 15},
            {"type": "cube", "position": [-2, 2, 0.4], "scale": [0.8, 0.8, 0.8], "mass": 15},
            {"type": "cube", "position": [-3, -2, 0.4], "scale": [0.8, 0.8, 0.8], "mass": 15},
            {"type": "cube", "position": [-2, -2, 0.4], "scale": [0.8, 0.8, 0.8], "mass": 15},
            {"type": "cube", "position": [-3, 0, 0.4], "scale": [0.8, 0.8, 0.8], "mass": 15},
            # Pallet
            {"type": "cube", "position": [-2.5, 0, 0.15], "scale": [1.5, 1.5, 0.15], "mass": 10, "passive": True},
        ],
        interactive=[
            InteractiveObject(InteractiveType.PUSHABLE, [x, y, 0.4], scale=[0.8, 0.8, 0.8], requires_force=10.0)
            for x, y in [(-3, 2), (-2, 2), (-3, -2), (-2, -2), (-3, 0)]
        ] + [
            InteractiveObject(InteractiveType.RAMP, [5, 0, 0.6], scale=[3, 2, 0.15]),
        ],
    ),

    # ─── Stair Climbing ─────────────────────────────────────────
    "stair_climb": PracticalWorld(
        name="stair_climb",
        world_type=WorldType.BUILDING,
        description="Multi-flight staircase with landings, railings, obstacles",
        difficulty=0.5,
        tags=["indoor", "stairs", "climbing", "endurance"],
        spawn_point=[0, 0, 1],
        goal_point=[0, 0, 10],
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [8, 8, 1], "mass": 0, "passive": True},
            # Flight 1 (10 steps)
            *[{"type": "cube", "position": [0, i * 0.3, i * 0.3 + 0.15], "scale": [2, 0.25, 0.3], "mass": 30, "passive": True}
              for i in range(10)],
            # Landing 1
            {"type": "cube", "position": [0, 3.5, 3], "scale": [2, 1.5, 0.2], "mass": 50, "passive": True},
            # Flight 2 (10 steps, opposite direction)
            *[{"type": "cube", "position": [0, 3 - i * 0.3, 3.3 + i * 0.3], "scale": [2, 0.25, 0.3], "mass": 30, "passive": True}
              for i in range(10)],
            # Landing 2
            {"type": "cube", "position": [0, -0.5, 6], "scale": [2, 1.5, 0.2], "mass": 50, "passive": True},
            # Flight 3 (10 steps)
            *[{"type": "cube", "position": [0, i * 0.3, 6.3 + i * 0.3], "scale": [2, 0.25, 0.3], "mass": 30, "passive": True}
              for i in range(10)],
            # Obstacle on stairs (box to push aside)
            {"type": "cube", "position": [0, 1.5, 1.5], "scale": [0.5, 0.5, 0.5], "mass": 10},
            # Railings
            {"type": "cube", "position": [-1.2, 1.5, 1], "scale": [0.05, 0.05, 1], "mass": 5, "passive": True},
            {"type": "cube", "position": [1.2, 1.5, 1], "scale": [0.05, 0.05, 1], "mass": 5, "passive": True},
        ],
        interactive=[
            InteractiveObject(InteractiveType.PUSHABLE, [0, 1.5, 1.5], scale=[0.5, 0.5, 0.5], requires_force=8.0),
        ],
    ),

    # ─── Maze ───────────────────────────────────────────────────
    "indoor_maze": PracticalWorld(
        name="indoor_maze",
        world_type=WorldType.BUILDING,
        description="Multi-room maze with doors, dead ends, hidden passages",
        difficulty=0.7,
        tags=["indoor", "navigation", "doors", "maze"],
        spawn_point=[0, 0, 1],
        goal_point=[12, 12, 1],
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [20, 20, 1], "mass": 0, "passive": True},
            # Maze walls
            {"type": "cube", "position": [2, 2, 1.5], "scale": [4, 0.2, 3], "mass": 50, "passive": True},
            {"type": "cube", "position": [4, 4, 1.5], "scale": [0.2, 4, 3], "mass": 50, "passive": True},
            {"type": "cube", "position": [6, 2, 1.5], "scale": [4, 0.2, 3], "mass": 50, "passive": True},
            {"type": "cube", "position": [8, 4, 1.5], "scale": [0.2, 6, 3], "mass": 50, "passive": True},
            {"type": "cube", "position": [10, 6, 1.5], "scale": [4, 0.2, 3], "mass": 50, "passive": True},
            {"type": "cube", "position": [6, 8, 1.5], "scale": [6, 0.2, 3], "mass": 50, "passive": True},
            {"type": "cube", "position": [12, 8, 1.5], "scale": [0.2, 6, 3], "mass": 50, "passive": True},
            {"type": "cube", "position": [10, 10, 1.5], "scale": [4, 0.2, 3], "mass": 50, "passive": True},
            {"type": "cube", "position": [14, 10, 1.5], "scale": [0.2, 4, 3], "mass": 50, "passive": True},
        ],
        interactive=[
            InteractiveObject(InteractiveType.DOOR, [2, 0, 1], can_open=True),
            InteractiveObject(InteractiveType.DOOR, [6, 4, 1], can_open=True),
            InteractiveObject(InteractiveType.DOOR, [10, 8, 1], can_open=True),
            InteractiveObject(InteractiveType.LEVER, [4, 2, 1], metadata={"opens": "secret_passage"}),
        ],
    ),

    # ─── Obstacle Course ───────────────────────────────────────
    "robot_obstacle_course": PracticalWorld(
        name="robot_obstacle_course",
        world_type=WorldType.OBSTACLE_COURSE,
        description="Full obstacle course: walls, gaps, ramps, pushable blocks, stairs",
        difficulty=0.9,
        tags=["outdoor", "climbing", "jumping", "pushing", "balance", "comprehensive"],
        spawn_point=[0, 0, 1],
        goal_point=[30, 0, 2],
        objects=[
            {"type": "plane", "position": [0, 0, 0], "scale": [60, 20, 1], "mass": 0, "passive": True},
            # Section 1: Pushable blocks
            {"type": "cube", "position": [3, 0, 0.4], "scale": [0.6, 0.6, 0.8], "mass": 10},
            {"type": "cube", "position": [4, 0, 0.4], "scale": [0.6, 0.6, 0.8], "mass": 10},
            {"type": "cube", "position": [5, 0, 0.4], "scale": [0.6, 0.6, 0.8], "mass": 10},
            # Section 2: Low wall to climb
            {"type": "cube", "position": [8, 0, 0.5], "scale": [0.3, 4, 1], "mass": 100, "passive": True},
            # Section 3: Stepping stones over gap
            {"type": "cube", "position": [11, 2, 0.5], "scale": [0.8, 0.8, 1], "mass": 30, "passive": True},
            {"type": "cube", "position": [13, -1, 0.8], "scale": [0.8, 0.8, 1.6], "mass": 30, "passive": True},
            {"type": "cube", "position": [15, 1, 1.2], "scale": [0.8, 0.8, 2.4], "mass": 30, "passive": True},
            # Section 4: Ramp up
            {"type": "cube", "position": [18, 0, 0.8], "scale": [3, 3, 0.2], "mass": 50, "passive": True,
             "rotation": [0.2, 0, 0]},
            # Section 5: Platform jump
            {"type": "cube", "position": [22, 0, 1.5], "scale": [1.5, 2, 0.3], "mass": 50, "passive": True},
            {"type": "cube", "position": [24, 0, 2], "scale": [1.5, 2, 0.3], "mass": 50, "passive": True},
            # Section 6: Balance beam
            {"type": "cube", "position": [26, 0, 2.5], "scale": [4, 0.1, 0.1], "mass": 20, "passive": True},
            # Section 7: Stairs up
            *[{"type": "cube", "position": [28 + i * 0.3, 0, 0.15 + i * 0.3], "scale": [0.3, 1.5, 0.3], "mass": 20, "passive": True}
              for i in range(5)],
            # Goal platform
            {"type": "cube", "position": [30, 0, 2], "scale": [2, 2, 0.3], "mass": 50, "passive": True},
        ],
        interactive=[
            InteractiveObject(InteractiveType.PUSHABLE, [3, 0, 0.4], requires_force=8.0),
            InteractiveObject(InteractiveType.PUSHABLE, [4, 0, 0.4], requires_force=8.0),
            InteractiveObject(InteractiveType.PUSHABLE, [5, 0, 0.4], requires_force=8.0),
            InteractiveObject(InteractiveType.RAMP, [18, 0, 0.8]),
        ],
    ),
}


def get_practical_world(name: str) -> Optional[PracticalWorld]:
    """Get a practical world by name."""
    return PRACTICAL_WORLDS.get(name)


def list_practical_worlds(world_type: Optional[WorldType] = None) -> List[Dict]:
    """List all practical worlds."""
    worlds = []
    for key, world in PRACTICAL_WORLDS.items():
        if world_type and world.world_type != world_type:
            continue
        worlds.append({
            "name": world.name,
            "type": world.world_type.value,
            "description": world.description,
            "difficulty": world.difficulty,
            "tags": world.tags,
            "num_objects": len(world.objects),
            "num_interactive": len(world.interactive),
        })
    return worlds


def get_worlds_by_difficulty(max_difficulty: float = 1.0) -> List[PracticalWorld]:
    """Get worlds sorted by difficulty."""
    return sorted(
        [w for w in PRACTICAL_WORLDS.values() if w.difficulty <= max_difficulty],
        key=lambda w: w.difficulty,
    )
