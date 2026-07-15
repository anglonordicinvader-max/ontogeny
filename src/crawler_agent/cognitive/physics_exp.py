"""Physics experimentation - autonomous curiosity experiments.

Provides:
- Automatic experiment design
- Hypothesis generation
- Intervention-based causal learning
- Physics model learning
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog


@dataclass
class Hypothesis:
    id: str
    statement: str
    confidence: float = 0.5
    evidence_for: int = 0
    evidence_against: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def total_evidence(self) -> int:
        return self.evidence_for + self.evidence_against

    def update(self, supports: bool):
        if supports:
            self.evidence_for += 1
            self.confidence = min(1.0, self.confidence + 0.1)
        else:
            self.evidence_against += 1
            self.confidence = max(0.0, self.confidence - 0.1)


@dataclass
class Intervention:
    variable: str
    old_value: Any
    new_value: Any
    rationale: str = ""


@dataclass
class ExperimentResult:
    hypothesis_id: str
    intervention: Intervention
    observed_outcome: str
    supports_hypothesis: bool
    metadata: Dict = field(default_factory=dict)


class PhysicsExperimenter:
    """Autonomous physics experimentation and causal learning."""

    def __init__(self):
        self.logger = structlog.get_logger(component="physics_exp")
        self.hypotheses: Dict[str, Hypothesis] = {}
        self.experiment_history: List[ExperimentResult] = []
        self.physics_model: Dict[str, Any] = {
            "gravity": 9.81,
            "friction": 0.3,
            "restitution": 0.5,
            "air_resistance": 0.01,
        }
        self.intervention_log: List[Dict] = []

    def generate_hypotheses(self, observation: str) -> List[Hypothesis]:
        """Generate hypotheses from observations."""
        generated = []
        templates = [
            ("If I push {obj} harder, it will move faster", 0.6),
            ("If I drop {obj} from higher, it will bounce higher", 0.5),
            ("If I add mass to {obj}, it will slow down", 0.7),
            ("If I reduce friction, {obj} will slide farther", 0.6),
            ("If I change the angle, {obj} will move differently", 0.5),
        ]

        for template, confidence in templates:
            hypothesis_id = str(uuid.uuid4())[:8]
            h = Hypothesis(
                id=hypothesis_id,
                statement=template.format(obj="object"),
                confidence=confidence,
            )
            self.hypotheses[hypothesis_id] = h
            generated.append(h)

        return generated

    def design_intervention(self, hypothesis: Hypothesis) -> Intervention:
        """Design an intervention to test a hypothesis."""
        if "push" in hypothesis.statement or "force" in hypothesis.statement:
            return Intervention("applied_force", 5.0, 15.0, "Increase force to test force-velocity relationship")
        elif "drop" in hypothesis.statement or "height" in hypothesis.statement:
            return Intervention("drop_height", 1.0, 3.0, "Increase height to test height-bounce relationship")
        elif "mass" in hypothesis.statement:
            return Intervention("object_mass", 1.0, 3.0, "Increase mass to test mass-speed relationship")
        elif "friction" in hypothesis.statement:
            return Intervention("surface_friction", 0.3, 0.1, "Reduce friction to test friction-distance relationship")
        else:
            return Intervention("angle", 45, 90, "Change angle to test angle-trajectory relationship")

    def run_experiment(
        self,
        hypothesis_id: str,
        sandbox_fn=None,
    ) -> ExperimentResult:
        """Run an experiment to test a hypothesis."""
        hypothesis = self.hypotheses.get(hypothesis_id)
        if not hypothesis:
            raise ValueError(f"Unknown hypothesis: {hypothesis_id}")

        intervention = self.design_intervention(hypothesis)

        if sandbox_fn:
            outcome = sandbox_fn(intervention)
        else:
            outcome = f"After changing {intervention.variable} from {intervention.old_value} to {intervention.new_value}, observed change in behavior"

        supports = "faster" in outcome or "higher" in outcome or "more" in outcome

        result = ExperimentResult(
            hypothesis_id=hypothesis_id,
            intervention=intervention,
            observed_outcome=outcome,
            supports_hypothesis=supports,
        )

        hypothesis.update(supports)
        self.experiment_history.append(result)
        self.intervention_log.append({
            "hypothesis": hypothesis.statement,
            "intervention": f"{intervention.variable}: {intervention.old_value} -> {intervention.new_value}",
            "outcome": outcome,
            "supports": supports,
        })

        return result

    def update_physics_model(self, experiment_result: ExperimentResult):
        """Update physics model based on experiment results."""
        var = experiment_result.intervention.variable
        if var == "surface_friction":
            if experiment_result.supports_hypothesis:
                self.physics_model["friction"] *= 0.9
            else:
                self.physics_model["friction"] *= 1.1
        elif var == "applied_force":
            if experiment_result.supports_hypothesis:
                self.physics_model["air_resistance"] *= 0.95

    def get_confident_hypotheses(self, threshold: float = 0.7) -> List[Hypothesis]:
        """Get hypotheses with high confidence."""
        return [h for h in self.hypotheses.values() if h.confidence >= threshold and h.total_evidence >= 3]

    def to_context(self) -> str:
        confident = self.get_confident_hypotheses()
        return (f"Physics Experimenter: {len(self.hypotheses)} hypotheses "
                f"({len(confident)} confirmed), {len(self.experiment_history)} experiments, "
                f"model: {self.physics_model}")
