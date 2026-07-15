"""Navigation - obstacle avoidance, path planning, SLAM simulation.

Provides:
- Obstacle avoidance (potential field, VFH)
- Path planning (A*, RRT, Dijkstra)
- SLAM simulation (occupancy grid)
- Waypoint following
"""

import heapq
import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import structlog


@dataclass
class Waypoint:
    x: float
    y: float
    z: float = 0.0
    tolerance: float = 0.5


@dataclass
class Path:
    waypoints: List[List[float]]
    cost: float = 0.0
    algorithm: str = ""
    valid: bool = True


class ObstacleAvoidance:
    """Obstacle avoidance using potential field method."""

    def __init__(self, safety_distance: float = 1.0, repulsive_gain: float = 10.0,
                 attractive_gain: float = 1.0):
        self.safety_distance = safety_distance
        self.repulsive_gain = repulsive_gain
        self.attractive_gain = attractive_gain
        self.logger = structlog.get_logger(component="obstacle_avoidance")

    def compute_force(self, robot_pos: List[float], goal_pos: List[float],
                      obstacles: Dict[str, List[float]], obstacle_radii: Dict[str, float] = None) -> List[float]:
        """Compute avoidance force vector."""
        if obstacle_radii is None:
            obstacle_radii = {}

        attractive = self._attractive_force(robot_pos, goal_pos)
        repulsive = self._repulsive_force(robot_pos, obstacles, obstacle_radii)

        total = [attractive[i] + repulsive[i] for i in range(3)]
        norm = math.sqrt(sum(t**2 for t in total))
        if norm > 0:
            total = [t / norm for t in total]

        return total

    def _attractive_force(self, robot_pos: List[float], goal_pos: List[float]) -> List[float]:
        """Compute attractive force toward goal."""
        diff = [goal_pos[i] - robot_pos[i] for i in range(3)]
        dist = math.sqrt(sum(d**2 for d in diff))
        if dist > 0:
            diff = [d / dist for d in diff]
        return [d * self.attractive_gain for d in diff]

    def _repulsive_force(self, robot_pos: List[float], obstacles: Dict[str, List[float]],
                         obstacle_radii: Dict[str, float]) -> List[float]:
        """Compute repulsive force from obstacles."""
        force = [0.0, 0.0, 0.0]
        for obj_id, obj_pos in obstacles.items():
            diff = [robot_pos[i] - obj_pos[i] for i in range(3)]
            dist = math.sqrt(sum(d**2 for d in diff))
            radius = obstacle_radii.get(obj_id, 0.5)
            effective_dist = dist - radius

            if 0 < effective_dist < self.safety_distance:
                influence = (self.safety_distance - effective_dist) / self.safety_distance
                if dist > 0:
                    direction = [d / dist for d in diff]
                else:
                    direction = [1, 0, 0]
                for i in range(3):
                    force[i] += self.repulsive_gain * influence * direction[i]

        return force

    def avoid(self, robot_pos: List[float], goal_pos: List[float],
              obstacles: Dict[str, List[float]], dt: float = 0.1) -> List[float]:
        """Compute new position with obstacle avoidance."""
        force = self.compute_force(robot_pos, goal_pos, obstacles)
        new_pos = [robot_pos[i] + force[i] * dt for i in range(3)]
        return new_pos


class PathPlanner:
    """Path planning using A*, RRT, and Dijkstra."""

    def __init__(self, grid_size: float = 0.5, world_bounds: Tuple[float, float] = (-50, 50)):
        self.grid_size = grid_size
        self.world_bounds = world_bounds
        self.logger = structlog.get_logger(component="path_planner")

    def a_star(self, start: List[float], goal: List[float],
               obstacles: Dict[str, List[float]], obstacle_radii: Dict[str, float] = None) -> Path:
        """A* path planning on grid."""
        if obstacle_radii is None:
            obstacle_radii = {}

        start_grid = self._to_grid(start)
        goal_grid = self._to_grid(goal)

        open_set = [(0, start_grid)]
        came_from = {}
        g_score = {start_grid: 0}
        f_score = {start_grid: self._heuristic(start_grid, goal_grid)}

        while open_set:
            _, current = heapq.heappop(open_set)

            if current == goal_grid:
                path = self._reconstruct_path(came_from, current)
                return Path(waypoints=[list(p) for p in path], cost=g_score[current], algorithm="A*")

            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
                neighbor = (current[0] + dx, current[1] + dy)

                if not self._is_valid_node(neighbor):
                    continue
                if self._is_collision(neighbor, obstacles, obstacle_radii):
                    continue

                move_cost = math.sqrt(dx**2 + dy**2) * self.grid_size
                tentative_g = g_score[current] + move_cost

                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + self._heuristic(neighbor, goal_grid)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))

        return Path(waypoints=[], cost=float('inf'), algorithm="A*", valid=False)

    def rrt(self, start: List[float], goal: List[float],
            obstacles: Dict[str, List[float]], obstacle_radii: Dict[str, float] = None,
            max_iterations: int = 1000, step_size: float = 1.0) -> Path:
        """Rapidly-exploring Random Tree path planning."""
        if obstacle_radii is None:
            obstacle_radii = {}

        tree = {tuple(start): None}
        tree_costs = {tuple(start): 0}

        for _ in range(max_iterations):
            if random.random() < 0.1:
                sample = tuple(goal)
            else:
                sample = (
                    random.uniform(self.world_bounds[0], self.world_bounds[1]),
                    random.uniform(self.world_bounds[0], self.world_bounds[1]),
                )

            nearest = min(tree.keys(), key=lambda n: math.sqrt(sum((n[i] - sample[i])**2 for i in range(2))))

            direction = [sample[i] - nearest[i] for i in range(2)]
            dist = math.sqrt(sum(d**2 for d in direction))
            if dist > 0:
                direction = [d / dist for d in direction]

            new_node = tuple(nearest[i] + direction[i] * min(step_size, dist) for i in range(2))

            if not self._is_collision(new_node, obstacles, obstacle_radii):
                tree[new_node] = nearest
                tree_costs[new_node] = tree_costs[nearest] + step_size

                if math.sqrt(sum((new_node[i] - goal[i])**2 for i in range(2))) < step_size:
                    path = []
                    node = new_node
                    while node is not None:
                        path.append([node[0], node[1], 0])
                        node = tree[node]
                    path.reverse()
                    return Path(waypoints=path, cost=tree_costs[new_node], algorithm="RRT")

        return Path(waypoints=[], cost=float('inf'), algorithm="RRT", valid=False)

    def dijkstra(self, start: List[float], goal: List[float],
                 obstacles: Dict[str, List[float]], obstacle_radii: Dict[str, float] = None) -> Path:
        """Dijkstra shortest path."""
        return self.a_star(start, goal, obstacles, obstacle_radii)

    def _to_grid(self, pos: List[float]) -> Tuple[int, int]:
        return (int(pos[0] / self.grid_size), int(pos[1] / self.grid_size))

    def _from_grid(self, grid: Tuple[int, int]) -> List[float]:
        return [grid[0] * self.grid_size, grid[1] * self.grid_size, 0]

    def _heuristic(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        return math.sqrt((a[0] - b[0])**2 + (a[1] - b[1])**2) * self.grid_size

    def _is_valid_node(self, node: Tuple[int, int]) -> bool:
        bounds_min = int(self.world_bounds[0] / self.grid_size)
        bounds_max = int(self.world_bounds[1] / self.grid_size)
        return bounds_min <= node[0] <= bounds_max and bounds_min <= node[1] <= bounds_max

    def _is_collision(self, grid_node: Tuple[int, int], obstacles: Dict[str, List[float]],
                      obstacle_radii: Dict[str, float]) -> bool:
        pos = self._from_grid(grid_node)
        for obj_id, obj_pos in obstacles.items():
            radius = obstacle_radii.get(obj_id, 0.5)
            dist = math.sqrt(sum((pos[i] - obj_pos[i])**2 for i in range(2)))
            if dist < radius + self.grid_size:
                return True
        return False

    def _reconstruct_path(self, came_from: Dict, current: Tuple) -> List[List[float]]:
        path = [self._from_grid(current)]
        while current in came_from:
            current = came_from[current]
            path.append(self._from_grid(current))
        path.reverse()
        return path


class SLAMSimulation:
    """SLAM simulation with occupancy grid mapping."""

    def __init__(self, grid_resolution: float = 0.5, map_size: Tuple[int, int] = (100, 100)):
        self.grid_resolution = grid_resolution
        self.map_size = map_size
        self.occupancy_grid = [[0.5 for _ in range(map_size[1])] for _ in range(map_size[0])]
        self.robot_path: List[List[float]] = []
        self.logger = structlog.get_logger(component="slam")

    def update(self, robot_pos: List[float], sensor_readings: List[List[float]],
               sensor_range: float = 10.0) -> Dict:
        """Update occupancy grid with new sensor readings."""
        self.robot_path.append(list(robot_pos))

        robot_grid = self._to_grid(robot_pos)
        cells_updated = 0

        for reading in sensor_readings:
            hit_grid = self._to_grid(reading)
            if 0 <= hit_grid[0] < self.map_size[0] and 0 <= hit_grid[1] < self.map_size[1]:
                self.occupancy_grid[hit_grid[0]][hit_grid[1]] = min(1.0,
                    self.occupancy_grid[hit_grid[0]][hit_grid[1]] + 0.3)
                cells_updated += 1

            ray_cells = self._bresenham(robot_grid, hit_grid)
            for cell in ray_cells:
                if 0 <= cell[0] < self.map_size[0] and 0 <= cell[1] < self.map_size[1]:
                    self.occupancy_grid[cell[0]][cell[1]] = max(0.0,
                        self.occupancy_grid[cell[0]][cell[1]] - 0.1)

        return {"cells_updated": cells_updated, "robot_pos": robot_pos}

    def _to_grid(self, pos: List[float]) -> Tuple[int, int]:
        return (int(pos[0] / self.grid_resolution) + self.map_size[0] // 2,
                int(pos[1] / self.grid_resolution) + self.map_size[1] // 2)

    def _bresenham(self, start: Tuple[int, int], end: Tuple[int, int]) -> List[Tuple[int, int]]:
        cells = []
        x0, y0 = start
        x1, y1 = end
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        while True:
            cells.append((x0, y0))
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy
        return cells

    def get_map(self) -> List[List[float]]:
        return self.occupancy_grid

    def get_path(self) -> List[List[float]]:
        return self.robot_path

    def to_context(self) -> str:
        return f"SLAM: {self.map_size[0]}x{self.map_size[1]} grid, {len(self.robot_path)} positions mapped"


class WaypointFollower:
    """Waypoint following controller."""

    def __init__(self, position_tolerance: float = 0.5, lookahead: float = 2.0):
        self.position_tolerance = position_tolerance
        self.lookahead = lookahead
        self.current_index = 0
        self.logger = structlog.get_logger(component="waypoint_follower")

    def update(self, robot_pos: List[float], waypoints: List[List[float]]) -> Dict:
        """Update waypoint following."""
        if not waypoints or self.current_index >= len(waypoints):
            return {"reached_goal": True, "command": [0, 0, 0]}

        target = waypoints[self.current_index]
        dx = target[0] - robot_pos[0]
        dy = target[1] - robot_pos[1]
        dist = math.sqrt(dx**2 + dy**2)

        if dist < self.position_tolerance:
            self.current_index += 1
            return {"reached_waypoint": True, "waypoint_index": self.current_index - 1,
                    "command": [0, 0, 0]}

        speed = min(1.0, dist / self.lookahead)
        cmd_x = (dx / dist) * speed if dist > 0 else 0
        cmd_y = (dy / dist) * speed if dist > 0 else 0

        return {"reached_goal": False, "command": [cmd_x, cmd_y, 0],
                "distance_to_waypoint": dist, "waypoint_index": self.current_index}

    def reset(self):
        self.current_index = 0

    def to_context(self) -> str:
        return f"WaypointFollower: index={self.current_index}"
