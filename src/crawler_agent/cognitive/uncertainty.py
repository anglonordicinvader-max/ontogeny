"""Uncertainty Tracker for confidence calibration and uncertainty quantification."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import structlog

from .backend import CognitiveBackend


class UncertaintyType(str, Enum):
    EPISTEMIC = "epistemic"      # Knowledge uncertainty (reducible)
    ALEATORIC = "aleatoric"      # Data uncertainty (irreducible)
    MODEL = "model"              # Model uncertainty
    LABEL = "label"              # Annotation uncertainty
    STRUCTURAL = "structural"    # Model structure uncertainty


class ConfidenceLevel(str, Enum):
    VERY_LOW = "very_low"    # 0-20%
    LOW = "low"              # 20-40%
    MEDIUM = "medium"        # 40-60%
    HIGH = "high"            # 60-80%
    VERY_HIGH = "very_high"  # 80-100%


@dataclass
class UncertaintyEstimate:
    """Estimate of uncertainty for a claim/prediction."""
    id: str
    claim: str
    uncertainty_type: UncertaintyType
    mean_confidence: float = 0.5
    confidence_interval: tuple[float, float] = (0.3, 0.7)
    calibration_score: float = 0.5
    evidence_count: int = 0
    contradicting_evidence: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CalibrationRecord:
    """Record for calibration tracking."""
    predicted_confidence: float
    actual_outcome: bool
    claim: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


class UncertaintyTracker:
    """Tracks and quantifies uncertainty in reasoning."""

    def __init__(self, backend: CognitiveBackend):
        self.backend = backend
        self.estimates: dict[str, UncertaintyEstimate] = {}
        self.calibration_records: list[CalibrationRecord] = []
        self.logger = structlog.get_logger()

    async def estimate_uncertainty(
        self,
        claim: str,
        evidence: list[str] | None = None,
        context: str = "",
    ) -> UncertaintyEstimate:
        """Estimate uncertainty for a claim."""
        system_prompt = """Estimate uncertainty for a claim. Consider:
1. Evidence quality and quantity
2. Contradicting information
3. Source reliability
4. Knowledge gaps

Return JSON with:
- confidence (0-1)
- uncertainty_type (epistemic/aleatoric/model/structural)
- confidence_interval [low, high]
- evidence_quality (0-1)
- contradicting_count
- reasoning"""

        user_prompt = f"""Claim: {claim}
Evidence: {evidence or []}
Context: {context}

Estimate uncertainty:"""

        response = await self.backend.complete(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=800,
            temperature=0.3,
        )

        try:
            data = response.parsed_json
            estimate = UncertaintyEstimate(
                id=f"unc_{len(self.estimates)}",
                claim=claim,
                uncertainty_type=UncertaintyType(data.get("uncertainty_type", "epistemic")),
                mean_confidence=data.get("confidence", 0.5),
                confidence_interval=tuple(data.get("confidence_interval", [0.3, 0.7])),
                evidence_count=len(evidence or []),
                contradicting_evidence=data.get("contradicting_count", 0),
                metadata={
                    "evidence_quality": data.get("evidence_quality", 0.5),
                    "reasoning": data.get("reasoning", ""),
                },
            )
            self.estimates[estimate.id] = estimate
            return estimate
        except Exception as e:
            self.logger.error("uncertainty_estimation_failed", error=str(e))
            return UncertaintyEstimate(
                id="failed",
                claim=claim,
                uncertainty_type=UncertaintyType.EPISTEMIC,
                mean_confidence=0.3,
            )

    async def calibrate(
        self,
        claim: str,
        predicted_confidence: float,
        evidence: list[str] | None = None,
    ) -> dict[str, Any]:
        """Calibrate confidence estimate with additional checks."""
        system_prompt = """Calibrate confidence for a claim. Check:
1. Is the confidence well-calibrated given the evidence?
2. Are there blind spots?
3. What would increase/decrease confidence?

Return JSON with: calibrated_confidence, adjustment_reasoning, blind_spots, confidence_bounds"""

        user_prompt = f"""Claim: {claim}
Initial confidence: {predicted_confidence}
Evidence: {evidence or []}

Calibrate:"""

        response = await self.backend.complete(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=600,
            temperature=0.3,
        )

        try:
            data = response.parsed_json
            return data
        except Exception:
            return {"calibrated_confidence": predicted_confidence}

    async def quantify_ignorance(
        self,
        topic: str,
        known: list[str] | None = None,
    ) -> dict[str, Any]:
        """Quantify what is NOT known about a topic."""
        system_prompt = """Identify knowledge gaps. Given what is known, what is NOT known?
Categorize gaps by:
1. Critical gaps (important for reasoning)
2. Useful gaps (would improve decisions)
3. Nice-to-know (low priority)

Return JSON with: knowledge_gaps (list of {gap, importance, difficulty_to_obtain}), overall_coverage"""

        user_prompt = f"""Topic: {topic}
Known: {known or []}

What is NOT known?"""

        response = await self.backend.complete(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=800,
            temperature=0.3,
        )

        try:
            return response.parsed_json
        except Exception:
            return {"knowledge_gaps": [], "overall_coverage": 0.5}

    async def epistemic_vs_aleatoric(
        self,
        prediction: str,
        evidence: list[str],
    ) -> dict[str, Any]:
        """Decompose uncertainty into epistemic vs aleatoric components."""
        system_prompt = """Decompose uncertainty into:
- Epistemic: reducible with more data/knowledge
- Aleatoric: irreducible inherent randomness

Return JSON with:
- epistemic_component (0-1)
- aleatoric_component (0-1)
- total_uncertainty (0-1)
- reducibility (how much uncertainty can be reduced)
- recommendations (what data/knowledge would help)"""

        user_prompt = f"""Prediction: {prediction}
Evidence: {evidence}

Decompose uncertainty:"""

        response = await self.backend.complete(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=600,
            temperature=0.3,
        )

        try:
            return response.parsed_json
        except Exception:
            return {"epistemic_component": 0.5, "aleatoric_component": 0.5}

    def record_calibration(
        self,
        claim: str,
        predicted_confidence: float,
        actual_outcome: bool,
    ) -> None:
        """Record a calibration outcome."""
        self.calibration_records.append(CalibrationRecord(
            predicted_confidence=predicted_confidence,
            actual_outcome=actual_outcome,
            claim=claim,
        ))

    def get_calibration_score(self) -> float:
        """Calculate overall calibration score."""
        if not self.calibration_records:
            return 0.5

        # Expected calibration error
        bins = {}
        for record in self.calibration_records:
            bin_idx = int(record.predicted_confidence * 10) / 10
            if bin_idx not in bins:
                bins[bin_idx] = {"predicted": [], "actual": []}
            bins[bin_idx]["predicted"].append(record.predicted_confidence)
            bins[bin_idx]["actual"].append(1.0 if record.actual_outcome else 0.0)

        ece = 0.0
        for bin_idx, data in bins.items():
            if data["actual"]:
                avg_predicted = sum(data["predicted"]) / len(data["predicted"])
                avg_actual = sum(data["actual"]) / len(data["actual"])
                ece += abs(avg_predicted - avg_actual) * len(data["actual"])

        return 1.0 - (ece / len(self.calibration_records))

    def get_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Convert confidence to level."""
        if confidence < 0.2:
            return ConfidenceLevel.VERY_LOW
        elif confidence < 0.4:
            return ConfidenceLevel.LOW
        elif confidence < 0.6:
            return ConfidenceLevel.MEDIUM
        elif confidence < 0.8:
            return ConfidenceLevel.HIGH
        return ConfidenceLevel.VERY_HIGH

    def should_act(self, threshold: float = 0.6) -> tuple[bool, str]:
        """Determine if we should act based on uncertainty."""
        recent = list(self.estimates.values())[-5:]
        if not recent:
            return True, "No uncertainty data"

        avg_confidence = sum(e.mean_confidence for e in recent) / len(recent)
        if avg_confidence >= threshold:
            return True, f"Confidence {avg_confidence:.0%} >= threshold"
        return False, f"Confidence {avg_confidence:.0%} < threshold, gather more evidence"

    # === Per-Action Confidence Tracking ===

    async def track_action_confidence(
        self,
        action_id: str,
        action_type: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Track confidence before an action and return guidance."""
        context = context or {}

        # Estimate confidence for this action type based on history
        relevant = [
            e for e in self.estimates.values()
            if e.metadata.get("action_type") == action_type
        ]

        if relevant:
            avg_conf = sum(e.mean_confidence for e in relevant) / len(relevant)
        else:
            avg_conf = 0.5

        # Determine confidence level
        level = self.get_confidence_level(avg_conf)

        # Check if we should act
        should_act, reason = self.should_act(threshold=0.5)

        # Identify information gaps
        info_gaps = await self._identify_information_gaps(action_type, context)

        guidance = {
            "action_id": action_id,
            "action_type": action_type,
            "confidence": avg_conf,
            "confidence_level": level.value,
            "should_act": should_act,
            "reason": reason,
            "information_gaps": info_gaps,
            "recommended_exploration": len(info_gaps) > 0 and avg_conf < 0.5,
        }

        self.logger.info(
            "action_confidence_tracked",
            action_type=action_type,
            confidence=avg_conf,
            level=level.value,
        )

        return guidance

    async def update_action_confidence(
        self,
        action_id: str,
        action_type: str,
        outcome_success: bool,
        outcome_surprise: float = 0.0,
    ):
        """Update confidence tracking after action completion."""
        # Create a new estimate for this action's outcome
        confidence = 0.8 if outcome_success else 0.3
        confidence *= (1 - outcome_surprise * 0.3)  # Surprises reduce confidence

        estimate = UncertaintyEstimate(
            id=f"action_{action_id[:8]}",
            claim=f"Action {action_type} will succeed",
            uncertainty_type=UncertaintyType.EPISTEMIC,
            mean_confidence=confidence,
            evidence_count=1,
            metadata={
                "action_type": action_type,
                "outcome_success": outcome_success,
                "outcome_surprise": outcome_surprise,
            },
        )
        self.estimates[estimate.id] = estimate

        # Record calibration
        self.record_calibration(
            claim=f"action_{action_type}",
            predicted_confidence=confidence,
            actual_outcome=outcome_success,
        )

    async def _identify_information_gaps(
        self,
        action_type: str,
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Identify information gaps that would improve confidence."""
        gaps = []

        # Check if we have enough evidence
        relevant = [
            e for e in self.estimates.values()
            if e.metadata.get("action_type") == action_type
        ]

        if len(relevant) < 3:
            gaps.append({
                "gap": "limited_history",
                "description": f"Only {len(relevant)} prior attempts for this action type",
                "priority": "high",
                "how_to_fill": "Execute more instances of this action",
            })

        # Check for high epistemic uncertainty
        epistemic = [e for e in relevant if e.uncertainty_type == UncertaintyType.EPISTEMIC]
        if epistemic:
            avg_epistemic = sum(e.mean_confidence for e in epistemic) / len(epistemic)
            if avg_epistemic < 0.4:
                gaps.append({
                    "gap": "high_epistemic_uncertainty",
                    "description": "Low knowledge about this action domain",
                    "priority": "medium",
                    "how_to_fill": "Research similar actions and outcomes",
                })

        return gaps

    def confidence_weighted_decision(
        self,
        options: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Select best option weighted by confidence."""
        if not options:
            return None

        scored = []
        for opt in options:
            action_type = opt.get("action_type", "unknown")
            relevant = [
                e for e in self.estimates.values()
                if e.metadata.get("action_type") == action_type
            ]

            if relevant:
                avg_conf = sum(e.mean_confidence for e in relevant) / len(relevant)
            else:
                avg_conf = 0.5

            score = opt.get("utility", 0.5) * avg_conf
            scored.append((opt, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0]

    def get_action_confidence_summary(self, action_type: str) -> str:
        """Get human-readable confidence summary for an action type."""
        relevant = [
            e for e in self.estimates.values()
            if e.metadata.get("action_type") == action_type
        ]

        if not relevant:
            return f"No confidence data for action type: {action_type}"

        avg_conf = sum(e.mean_confidence for e in relevant) / len(relevant)
        level = self.get_confidence_level(avg_conf)
        successes = sum(1 for e in relevant if e.metadata.get("outcome_success"))
        failures = len(relevant) - successes

        return (
            f"Action '{action_type}': {level.value} confidence ({avg_conf:.0%})\n"
            f"  History: {successes} successes, {failures} failures"
        )

    # === Epistemic Uncertainty Deep Dive ===

    async def identify_epistemic_gaps(
        self,
        domain: str,
        known_facts: list[str] | None = None,
    ) -> dict[str, Any]:
        """Deeply analyze epistemic uncertainty in a domain.

        Identifies:
        1. What is known (with confidence)
        2. What is believed but uncertain
        3. What is completely unknown (unknown unknowns)
        4. What questions would most reduce uncertainty
        """
        system_prompt = """Perform deep epistemic uncertainty analysis.

Categorize knowledge into:
1. KNOWN: Facts with high confidence (>0.8)
2. BELIEVED: Things we think are true but uncertain (0.3-0.8)
3. UNCERTAIN: Things we don't know well (0.1-0.3)
4. UNKNOWN: Complete blind spots (not even on our radar)

For each category, list specific items and their estimated confidence.
Identify the most valuable questions to ask (highest information gain).

Return JSON with:
- known: [{fact, confidence}]
- believed: [{fact, confidence, reasoning}]
- uncertain: [{topic, why_uncertain}]
- unknown_unknowns: [{potential_topic, why_might_matter}]
- high_value_questions: [{question, expected_info_gain, difficulty}]"""

        user_prompt = f"""Domain: {domain}
Known facts: {known_facts or []}

Deep epistemic analysis:"""

        response = await self.backend.complete(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=1500,
            temperature=0.3,
        )

        try:
            return response.parsed_json
        except Exception:
            return {"known": [], "believed": [], "uncertain": [], "unknown_unknowns": []}

    async def calculate_information_value(
        self,
        question: str,
        current_knowledge: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Calculate the expected information value of answering a question.

        Uses expected value of information (EVI) framework:
        EVI = P(outcome changes) × magnitude of improvement
        """
        system_prompt = """Calculate the Expected Value of Information for this question.

Consider:
1. How likely is answering this to change our current belief?
2. How much would the change improve decisions?
3. What is the cost of obtaining this information?
4. What is the expected decision quality with vs without this info?

Return JSON with:
- current_belief: {statement, confidence}
- expected_belief_shift: 0-1
- decision_improvement: 0-1
- information_cost: 0-1 (effort to obtain)
- expected_value_of_info: 0-1
- reasoning: why this value"""

        user_prompt = f"""Question: {question}
Current knowledge: {current_knowledge or {}}

Calculate information value:"""

        response = await self.backend.complete(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=600,
            temperature=0.3,
        )

        try:
            return response.parsed_json
        except Exception:
            return {"expected_value_of_info": 0.5}

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_estimates": len(self.estimates),
            "avg_confidence": sum(e.mean_confidence for e in self.estimates.values()) / max(len(self.estimates), 1),
            "calibration_records": len(self.calibration_records),
            "calibration_score": self.get_calibration_score(),
            "by_type": {
                t.value: sum(1 for e in self.estimates.values() if e.uncertainty_type == t)
                for t in UncertaintyType
            },
        }
