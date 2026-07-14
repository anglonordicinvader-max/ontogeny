"""Bayesian World Model - internal simulation that updates from experience.

Maintains a probabilistic model of how the world works.
Updates beliefs based on new evidence.
"""

import math
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog


@dataclass
class Belief:
    """A belief about the world."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    statement: str = ""
    probability: float = 0.5  # Prior probability 0-1
    evidence_count: int = 0
    supporting_evidence: int = 0
    contradicting_evidence: int = 0
    confidence: float = 0.5
    last_updated: datetime = field(default_factory=datetime.utcnow)
    dependencies: list[str] = field(default_factory=list)  # Other belief IDs

    def update_with_evidence(self, supports: bool, strength: float = 1.0):
        """Update belief with new evidence (Bayesian update)."""
        self.evidence_count += 1
        self.last_updated = datetime.utcnow()

        if supports:
            self.supporting_evidence += 1
            # P(H|E) = P(E|H) * P(H) / P(E)
            likelihood_ratio = strength
            self.probability = (
                likelihood_ratio * self.probability /
                (likelihood_ratio * self.probability + (1 - self.probability))
            )
        else:
            self.contradicting_evidence += 1
            # Update against belief
            self.probability = (
                (1 - strength) * self.probability /
                ((1 - strength) * self.probability + self.probability)
            )

        # Confidence based on evidence count
        self.confidence = min(1.0, self.evidence_count / 10)

    @property
    def is_reliable(self) -> bool:
        return self.confidence > 0.5 and self.evidence_count >= 3


@dataclass
class CausalLink:
    """A causal relationship between variables."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    cause: str = ""
    effect: str = ""
    strength: float = 0.5  # How strong the causal link is
    confidence: float = 0.5
    observations: int = 0
    last_observed: datetime = field(default_factory=datetime.utcnow)

    def update(self, observed: bool):
        """Update causal link based on observation."""
        self.observations += 1
        self.last_observed = datetime.utcnow()
        if observed:
            self.strength = min(1.0, self.strength + 0.05)
        else:
            self.strength = max(0.0, self.strength - 0.02)
        self.confidence = min(1.0, self.observations / 20)


class BayesianWorldModel:
    """Internal world model using Bayesian reasoning.

    Maintains beliefs about the world and updates them
    based on new evidence from crawling and learning.
    """

    def __init__(self):
        self.beliefs: dict[str, Belief] = {}
        self.causal_links: dict[str, CausalLink] = {}
        self.variables: dict[str, Any] = {}
        self.prediction_history: list[dict[str, Any]] = []
        self.logger = structlog.get_logger()

    async def observe(self, observation: dict[str, Any]):
        """Process a new observation and update the world model."""
        # Update beliefs based on observation
        for belief in self.beliefs.values():
            if self._observation_supports(belief, observation):
                belief.update_with_evidence(True)
            elif self._observation_contradicts(belief, observation):
                belief.update_with_evidence(False)

        # Update causal links
        for link in self.causal_links.values():
            if self._observation_involves(link, observation):
                link.update(True)

        # Update variables
        for key, value in observation.items():
            if key in self.variables:
                # Update with exponential moving average
                old = self.variables[key]
                if isinstance(old, (int, float)) and isinstance(value, (int, float)):
                    self.variables[key] = old * 0.7 + value * 0.3
            else:
                self.variables[key] = value

    async def add_belief(
        self,
        statement: str,
        prior: float = 0.5,
        dependencies: list[str] | None = None,
    ) -> Belief:
        """Add a new belief to the model."""
        belief = Belief(
            statement=statement,
            probability=prior,
            dependencies=dependencies or [],
        )
        self.beliefs[belief.id] = belief
        self.logger.info("belief_added", statement=statement, prior=prior)
        return belief

    async def add_causal_link(
        self,
        cause: str,
        effect: str,
        strength: float = 0.5,
    ) -> CausalLink:
        """Add a causal relationship."""
        link = CausalLink(
            cause=cause,
            effect=effect,
            strength=strength,
        )
        self.causal_links[link.id] = link
        self.logger.info("causal_link_added", cause=cause, effect=effect)
        return link

    async def predict(
        self,
        query: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a prediction based on the world model."""
        # Find relevant beliefs
        relevant_beliefs = [
            b for b in self.beliefs.values()
            if query.lower() in b.statement.lower()
        ]

        # Find relevant causal links
        relevant_causes = [
            c for c in self.causal_links.values()
            if query.lower() in c.cause.lower() or query.lower() in c.effect.lower()
        ]

        # Combine predictions
        if relevant_beliefs:
            avg_prob = sum(b.probability for b in relevant_beliefs) / len(relevant_beliefs)
        else:
            avg_prob = 0.5

        if relevant_causes:
            avg_strength = sum(c.strength for c in relevant_causes) / len(relevant_causes)
        else:
            avg_strength = 0.5

        prediction = {
            "query": query,
            "predicted_probability": avg_prob,
            "causal_strength": avg_strength,
            "confidence": sum(b.confidence for b in relevant_beliefs) / max(1, len(relevant_beliefs)),
            "evidence_count": sum(b.evidence_count for b in relevant_beliefs),
        }

        self.prediction_history.append(prediction)
        return prediction

    async def intervene(
        self,
        variable: str,
        value: Any,
    ) -> dict[str, Any]:
        """Simulate an intervention (do-calculus)."""
        # Find effects of this variable
        effects = []
        for link in self.causal_links.values():
            if link.cause == variable:
                effects.append({
                    "effect": link.effect,
                    "strength": link.strength,
                    "confidence": link.confidence,
                })

        # Simulate cascading effects
        predicted_state = dict(self.variables)
        predicted_state[variable] = value

        for effect in effects:
            effect_var = effect["effect"]
            if effect_var in predicted_state:
                # Apply causal strength
                predicted_state[effect_var] = predicted_state[effect_var] * effect["strength"]

        return {
            "intervention": {variable: value},
            "predicted_effects": effects,
            "predicted_state": predicted_state,
        }

    async def counterfactual(
        self,
        actual_outcome: str,
        variable: str,
        hypothetical_value: Any,
    ) -> dict[str, Any]:
        """Reason about what would have happened if something was different."""
        # Get current belief about outcome
        outcome_belief = None
        for belief in self.beliefs.values():
            if actual_outcome.lower() in belief.statement.lower():
                outcome_belief = belief
                break

        if not outcome_belief:
            return {
                "actual": actual_outcome,
                "hypothetical": f"Cannot evaluate: no belief about {actual_outcome}",
                "confidence": 0.0,
            }

        # Find causal path from variable to outcome
        causal_path = self._find_causal_path(variable, actual_outcome)

        # Estimate counterfactual probability
        if causal_path:
            path_strength = math.prod(link.strength for link in causal_path)
            counterfactual_prob = outcome_belief.probability * (1 - path_strength) + path_strength * 0.5
        else:
            counterfactual_prob = outcome_belief.probability * 0.9

        return {
            "actual_outcome": actual_outcome,
            "actual_probability": outcome_belief.probability,
            "counterfactual_variable": variable,
            "counterfactual_value": hypothetical_value,
            "counterfactual_probability": counterfactual_prob,
            "difference": counterfactual_prob - outcome_belief.probability,
            "causal_path_length": len(causal_path) if causal_path else 0,
        }

    def get_belief(self, statement: str) -> Belief | None:
        """Find a belief by statement."""
        for belief in self.beliefs.values():
            if statement.lower() in belief.statement.lower():
                return belief
        return None

    def get_strong_beliefs(self, min_probability: float = 0.7) -> list[Belief]:
        """Get beliefs with high probability."""
        return [
            b for b in self.beliefs.values()
            if b.probability >= min_probability and b.is_reliable
        ]

    def get_stats(self) -> dict[str, Any]:
        """Get world model statistics."""
        reliable = sum(1 for b in self.beliefs.values() if b.is_reliable)
        return {
            "total_beliefs": len(self.beliefs),
            "reliable_beliefs": reliable,
            "total_causal_links": len(self.causal_links),
            "total_variables": len(self.variables),
            "predictions_made": len(self.prediction_history),
        }

    def to_context(self) -> str:
        """Convert world model to context string."""
        strong = self.get_strong_beliefs(0.7)
        lines = ["World Model:"]
        lines.append(f"  Beliefs: {len(self.beliefs)} ({len(strong)} strong)")
        lines.append(f"  Causal Links: {len(self.causal_links)}")
        if strong:
            lines.append("  Strong Beliefs:")
            for b in strong[:5]:
                lines.append(f"    - {b.statement} (p={b.probability:.2f})")
        return "\n".join(lines)

    def _observation_supports(self, belief: Belief, observation: dict[str, Any]) -> bool:
        """Check if observation supports a belief."""
        obs_str = str(observation).lower()
        return belief.statement.lower() in obs_str

    def _observation_contradicts(self, belief: Belief, observation: dict[str, Any]) -> bool:
        """Check if observation contradicts a belief."""
        # Simple negation detection
        negations = ["not", "never", "no", "false", "incorrect"]
        obs_str = str(observation).lower()
        return any(neg in obs_str for neg in negations) and belief.statement.lower() in obs_str

    def _observation_involves(self, link: CausalLink, observation: dict[str, Any]) -> bool:
        """Check if observation involves a causal link."""
        obs_str = str(observation).lower()
        return link.cause.lower() in obs_str or link.effect.lower() in obs_str

    def _find_causal_path(self, start: str, end: str) -> list[CausalLink]:
        """Find causal path between two variables."""
        visited = set()
        path = []

        def dfs(current: str) -> bool:
            if current == end:
                return True
            visited.add(current)

            for link in self.causal_links.values():
                if link.cause == current and link.effect not in visited:
                    if dfs(link.effect):
                        path.append(link)
                        return True
            return False

        dfs(start)
        return list(reversed(path))
