"""Uncertainty Tracker for confidence calibration and uncertainty quantification."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import structlog
from openai import AsyncOpenAI


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

    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview", api_base: str | None = None):
        self.client = AsyncOpenAI(api_key=api_key or "ollama", base_url=api_base)
        self.model = model
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
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """Estimate uncertainty for a claim. Consider:
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
- reasoning""",
                },
                {
                    "role": "user",
                    "content": f"""Claim: {claim}
Evidence: {evidence or []}
Context: {context}

Estimate uncertainty:""",
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=800,
        )

        try:
            data = json.loads(response.choices[0].message.content or "{}")
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
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """Calibrate confidence for a claim. Check:
1. Is the confidence well-calibrated given the evidence?
2. Are there blind spots?
3. What would increase/decrease confidence?

Return JSON with: calibrated_confidence, adjustment_reasoning, blind_spots, confidence_bounds""",
                },
                {
                    "role": "user",
                    "content": f"""Claim: {claim}
Initial confidence: {predicted_confidence}
Evidence: {evidence or []}

Calibrate:""",
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=600,
        )

        try:
            data = json.loads(response.choices[0].message.content or "{}")
            return data
        except Exception:
            return {"calibrated_confidence": predicted_confidence}

    async def quantify_ignorance(
        self,
        topic: str,
        known: list[str] | None = None,
    ) -> dict[str, Any]:
        """Quantify what is NOT known about a topic."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """Identify knowledge gaps. Given what is known, what is NOT known?
Categorize gaps by:
1. Critical gaps (important for reasoning)
2. Useful gaps (would improve decisions)
3. Nice-to-know (low priority)

Return JSON with: knowledge_gaps (list of {gap, importance, difficulty_to_obtain}), overall_coverage""",
                },
                {
                    "role": "user",
                    "content": f"""Topic: {topic}
Known: {known or []}

What is NOT known?""",
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=800,
        )

        try:
            return json.loads(response.choices[0].message.content or "{}")
        except Exception:
            return {"knowledge_gaps": [], "overall_coverage": 0.5}

    async def epistemic_vs_aleatoric(
        self,
        prediction: str,
        evidence: list[str],
    ) -> dict[str, Any]:
        """Decompose uncertainty into epistemic vs aleatoric components."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """Decompose uncertainty into:
- Epistemic: reducible with more data/knowledge
- Aleatoric: irreducible inherent randomness

Return JSON with:
- epistemic_component (0-1)
- aleatoric_component (0-1)
- total_uncertainty (0-1)
- reducibility (how much uncertainty can be reduced)
- recommendations (what data/knowledge would help)""",
                },
                {
                    "role": "user",
                    "content": f"""Prediction: {prediction}
Evidence: {evidence}

Decompose uncertainty:""",
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=600,
        )

        try:
            return json.loads(response.choices[0].message.content or "{}")
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
