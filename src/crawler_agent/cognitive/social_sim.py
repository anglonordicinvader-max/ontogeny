"""Social simulation - human models, crowd behavior, gesture, verbal commands.

Provides:
- Human models (pedestrians, helpers, obstacles)
- Crowd simulation (social forces, collision avoidance)
- Gesture recognition
- Verbal command zones
"""

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import structlog


class HumanState:
    STANDING = "standing"
    WALKING = "walking"
    RUNNING = "running"
    SITTING = "sitting"
    WAVING = "waving"
    POINTING = "pointing"
    STOPPED = "stopped"


@dataclass
class HumanModel:
    id: str
    position: List[float]
    velocity: List[float] = field(default_factory=lambda: [0, 0, 0])
    state: str = HumanState.WALKING
    personal_space: float = 0.8
    speed: float = 1.4  # m/s average walking
    target: Optional[List[float]] = None
    panic_level: float = 0.0
    awareness_radius: float = 10.0
    height: float = 1.7
    mass: float = 70.0

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "position": self.position,
            "velocity": self.velocity,
            "state": self.state,
            "panic_level": self.panic_level,
        }


@dataclass
class CrowdConfig:
    max_agents: int = 50
    social_force_repulsion: float = 2.1
    social_force_attractive: float = 0.5
    agent_speed_mean: float = 1.4
    agent_speed_std: float = 0.3
    panic_spread_rate: float = 0.1
    collision_avoidance: float = 1.5


class HumanModelSim:
    """Individual human model simulation."""

    def __init__(self):
        self.logger = structlog.get_logger(component="human_model")

    def update(self, human: HumanModel, dt: float, obstacles: Dict[str, List[float]] = None,
               other_humans: List[HumanModel] = None, robot_pos: List[float] = None) -> HumanModel:
        """Update human state."""
        if human.state == HumanState.STANDING or human.state == HumanState.SITTING:
            return human

        if human.target:
            dx = human.target[0] - human.position[0]
            dy = human.target[1] - human.position[1]
            dist = math.sqrt(dx**2 + dy**2)

            if dist < 0.5:
                human.state = HumanState.STANDING
                human.velocity = [0, 0, 0]
                return human

            speed = human.speed * (1 + human.panic_level * 0.5)
            human.velocity[0] = (dx / dist) * speed
            human.velocity[1] = (dy / dist) * speed
        else:
            human.velocity = [v * 0.9 for v in human.velocity]

        if obstacles:
            for obs_id, obs_pos in obstacles.items():
                dx = human.position[0] - obs_pos[0]
                dy = human.position[1] - obs_pos[1]
                dist = math.sqrt(dx**2 + dy**2)
                if dist < human.personal_space * 2 and dist > 0:
                    avoid_force = 2.0 / dist
                    human.velocity[0] += (dx / dist) * avoid_force * dt
                    human.velocity[1] += (dy / dist) * avoid_force * dt

        if other_humans:
            for other in other_humans:
                if other.id == human.id:
                    continue
                dx = human.position[0] - other.position[0]
                dy = human.position[1] - other.position[1]
                dist = math.sqrt(dx**2 + dy**2)
                if dist < human.personal_space and dist > 0:
                    repulsion = 1.5 / dist
                    human.velocity[0] += (dx / dist) * repulsion * dt
                    human.velocity[1] += (dy / dist) * repulsion * dt

        if robot_pos:
            dx = human.position[0] - robot_pos[0]
            dy = human.position[1] - robot_pos[1]
            dist = math.sqrt(dx**2 + dy**2)
            if dist < human.personal_space * 1.5 and dist > 0:
                human.velocity[0] += (dx / dist) * 1.0 * dt
                human.velocity[1] += (dy / dist) * 1.0 * dt

        speed = math.sqrt(human.velocity[0]**2 + human.velocity[1]**2)
        max_speed = human.speed * (1 + human.panic_level)
        if speed > max_speed:
            human.velocity[0] = (human.velocity[0] / speed) * max_speed
            human.velocity[1] = (human.velocity[1] / speed) * max_speed

        human.position[0] += human.velocity[0] * dt
        human.position[1] += human.velocity[1] * dt

        if speed > 0.1:
            human.state = HumanState.WALKING
        elif speed < 0.05:
            human.state = HumanState.STANDING

        return human


class CrowdSimulation:
    """Crowd simulation with social forces."""

    def __init__(self, config: CrowdConfig = None):
        self.config = config or CrowdConfig()
        self.humans: Dict[str, HumanModel] = {}
        self.human_sim = HumanModelSim()
        self.logger = structlog.get_logger(component="crowd")
        self.human_counter = 0

    def add_human(self, position: List[float], target: List[float] = None,
                  speed: float = None, panic: float = 0.0) -> HumanModel:
        """Add a human to the crowd."""
        self.human_counter += 1
        human = HumanModel(
            id=f"human_{self.human_counter}",
            position=list(position),
            target=target,
            speed=speed or random.gauss(self.config.agent_speed_mean, self.config.agent_speed_std),
            panic_level=panic,
        )
        self.humans[human.id] = human
        return human

    def add_group(self, center: List[float], count: int, radius: float = 2.0) -> List[HumanModel]:
        """Add a group of humans."""
        humans = []
        for _ in range(count):
            offset = [random.uniform(-radius, radius), random.uniform(-radius, radius)]
            pos = [center[0] + offset[0], center[1] + offset[1], 0]
            humans.append(self.add_human(pos))
        return humans

    def update(self, dt: float, robot_pos: List[float] = None,
               obstacles: Dict[str, List[float]] = None) -> Dict:
        """Update all humans."""
        for human in self.humans.values():
            self.human_sim.update(human, dt, obstacles, list(self.humans.values()), robot_pos)

        panicking = sum(1 for h in self.humans.values() if h.panic_level > 0.5)
        moving = sum(1 for h in self.humans.values()
                     if h.state in [HumanState.WALKING, HumanState.RUNNING])

        return {
            "total_humans": len(self.humans),
            "moving": moving,
            "panicking": panicking,
            "positions": {h.id: h.position for h in self.humans.values()},
        }

    def trigger_panic(self, epicenter: List[float], radius: float = 10.0):
        """Trigger panic response in nearby humans."""
        for human in self.humans.values():
            dx = human.position[0] - epicenter[0]
            dy = human.position[1] - epicenter[1]
            dist = math.sqrt(dx**2 + dy**2)
            if dist < radius:
                human.panic_level = min(1.0, 1.0 - dist / radius)
                human.state = HumanState.RUNNING
                if dist > 0:
                    human.velocity[0] = (dx / dist) * human.speed * 2
                    human.velocity[1] = (dy / dist) * human.speed * 2

    def get_nearest_human(self, position: List[float]) -> Optional[HumanModel]:
        """Get nearest human to position."""
        nearest = None
        min_dist = float('inf')
        for human in self.humans.values():
            dx = human.position[0] - position[0]
            dy = human.position[1] - position[1]
            dist = math.sqrt(dx**2 + dy**2)
            if dist < min_dist:
                min_dist = dist
                nearest = human
        return nearest

    def get_pedestrians_ahead(self, position: List[float], direction: List[float],
                               distance: float = 5.0) -> List[HumanModel]:
        """Get pedestrians ahead in path."""
        ahead = []
        norm = math.sqrt(sum(d**2 for d in direction))
        if norm > 0:
            direction = [d / norm for d in direction]

        for human in self.humans.values():
            dx = human.position[0] - position[0]
            dy = human.position[1] - position[1]
            dist = math.sqrt(dx**2 + dy**2)
            if dist < distance:
                to_human = [dx / dist, dy / dist] if dist > 0 else [0, 0]
                dot = direction[0] * to_human[0] + direction[1] * to_human[1]
                if dot > 0.5:
                    ahead.append(human)
        return ahead

    def to_context(self) -> str:
        panicking = sum(1 for h in self.humans.values() if h.panic_level > 0.5)
        return f"Crowd: {len(self.humans)} humans ({panicking} panicking)"


@dataclass
class Gesture:
    type: str  # wave, point, stop, follow, help, danger
    direction: List[float] = field(default_factory=lambda: [0, 0, 0])
    confidence: float = 0.0
    source: str = ""


class GestureRecognition:
    """Gesture recognition and interpretation."""

    GESTURE_TYPES = ["wave", "point", "stop", "follow", "help", "danger", "none"]

    def __init__(self):
        self.logger = structlog.get_logger(component="gesture")
        self.detected_gestures: List[Gesture] = []

    def detect(self, human: HumanModel, robot_pos: List[float] = None) -> Gesture:
        """Detect gesture from human state."""
        gesture = Gesture(type="none", source=human.id)

        if human.state == HumanState.WAVING:
            gesture = Gesture(type="wave", confidence=0.8, source=human.id)
        elif human.state == HumanState.POINTING:
            gesture = Gesture(type="point", direction=human.velocity, confidence=0.7, source=human.id)

        if human.panic_level > 0.7:
            gesture = Gesture(type="danger", confidence=human.panic_level, source=human.id)
        elif human.panic_level > 0.3:
            gesture = Gesture(type="help", confidence=human.panic_level, source=human.id)

        if robot_pos:
            dx = robot_pos[0] - human.position[0]
            dy = robot_pos[1] - human.position[1]
            dist = math.sqrt(dx**2 + dy**2)
            if dist < 3.0 and human.state == HumanState.STOPPED:
                gesture = Gesture(type="stop", confidence=0.6, source=human.id)

        self.detected_gestures.append(gesture)
        return gesture

    def get_meaning(self, gesture: Gesture) -> str:
        """Interpret gesture meaning."""
        meanings = {
            "wave": "Human is acknowledging or calling attention",
            "point": "Human is indicating a direction or object",
            "stop": "Human wants robot to stop",
            "follow": "Human wants robot to follow",
            "help": "Human needs assistance",
            "danger": "Human is warning of danger",
            "none": "No gesture detected",
        }
        return meanings.get(gesture.type, "Unknown gesture")

    def to_context(self) -> str:
        recent = self.detected_gestures[-5:] if self.detected_gestures else []
        types = [g.type for g in recent if g.type != "none"]
        return f"Gesture: {len(self.detected_gestures)} detected, recent: {types}"


@dataclass
class VerbalCommand:
    text: str
    confidence: float = 0.0
    source: str = ""
    intent: str = ""
    parameters: Dict = field(default_factory=dict)


class VerbalCommandZone:
    """Verbal command recognition zones."""

    COMMAND_PATTERNS = {
        "stop": {"intents": ["stop", "halt", "wait"], "keywords": ["stop", "halt", "wait", "freeze"]},
        "go": {"intents": ["move", "proceed", "continue"], "keywords": ["go", "move", "proceed", "forward"]},
        "follow": {"intents": ["follow", "come"], "keywords": ["follow", "come", "with me"]},
        "help": {"intents": ["assist", "help"], "keywords": ["help", "assist", "need"]},
        "danger": {"intents": ["warn", "alert"], "keywords": ["danger", "watch out", "careful"]},
        "fetch": {"intents": ["retrieve", "get"], "keywords": ["fetch", "get", "bring"]},
    }

    def __init__(self):
        self.logger = structlog.get_logger(component="verbal")
        self.detected_commands: List[VerbalCommand] = []

    def detect(self, audio_text: str, speaker_id: str = "unknown",
               confidence: float = 0.5) -> VerbalCommand:
        """Detect command from audio text."""
        command = VerbalCommand(text=audio_text, source=speaker_id, confidence=confidence)

        text_lower = audio_text.lower()
        for cmd_type, patterns in self.COMMAND_PATTERNS.items():
            for keyword in patterns["keywords"]:
                if keyword in text_lower:
                    command.intent = cmd_type
                    command.confidence = min(1.0, confidence + 0.2)
                    self.detected_commands.append(command)
                    return command

        command.intent = "unknown"
        self.detected_commands.append(command)
        return command

    def create_zone(self, center: List[float], radius: float = 5.0,
                    command_type: str = "stop") -> Dict:
        """Create a verbal command zone."""
        return {
            "center": center,
            "radius": radius,
            "command_type": command_type,
            "active": True,
        }

    def check_zone(self, position: List[float], zones: List[Dict]) -> Optional[Dict]:
        """Check if position is within any command zone."""
        for zone in zones:
            if not zone.get("active", True):
                continue
            dx = position[0] - zone["center"][0]
            dy = position[1] - zone["center"][1]
            dist = math.sqrt(dx**2 + dy**2)
            if dist < zone["radius"]:
                return zone
        return None

    def to_context(self) -> str:
        recent = self.detected_commands[-3:] if self.detected_commands else []
        intents = [c.intent for c in recent]
        return f"Verbal: {len(self.detected_commands)} commands, recent: {intents}"


class SocialSimulator:
    """Unified social simulation."""

    def __init__(self):
        self.crowd = CrowdSimulation()
        self.gesture = GestureRecognition()
        self.verbal = VerbalCommandZone()
        self.human_sim = HumanModelSim()
        self.command_zones: List[Dict] = []
        self.logger = structlog.get_logger(component="social")

    def update(self, dt: float, robot_pos: List[float] = None,
               obstacles: Dict[str, List[float]] = None) -> Dict:
        """Update social simulation."""
        crowd_state = self.crowd.update(dt, robot_pos, obstacles)

        nearest = self.crowd.get_nearest_human(robot_pos or [0, 0, 0])
        detected_gesture = None
        if nearest:
            detected_gesture = self.gesture.detect(nearest, robot_pos)

        return {
            "crowd": crowd_state,
            "nearest_human": nearest.to_dict() if nearest else None,
            "gesture": {"type": detected_gesture.type, "confidence": detected_gesture.confidence} if detected_gesture else None,
            "zones": len(self.command_zones),
        }

    def add_command_zone(self, center: List[float], radius: float = 5.0, command: str = "stop"):
        self.command_zones.append(self.verbal.create_zone(center, radius, command))

    def process_verbal(self, text: str, speaker_id: str = "unknown") -> VerbalCommand:
        return self.verbal.detect(text, speaker_id)

    def to_context(self) -> str:
        return (f"Social: {self.crowd.to_context()}, "
                f"{self.gesture.to_context()}, {self.verbal.to_context()}")
