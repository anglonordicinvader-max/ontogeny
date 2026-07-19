"""Meta-cognition module for self-evaluation and reasoning monitoring."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, StrEnum
from typing import Any

import structlog

from .backend import CognitiveBackend, CognitiveResponse


class ConfidenceLevel(StrEnum):
    VERY_LOW = "very_low"  # 0-20%
    LOW = "low"  # 20-40%
    MEDIUM = "medium"  # 40-60%
    HIGH = "high"  # 60-80%
    VERY_HIGH = "very_high"  # 80-100%


@dataclass
class ReasoningTrace:
    """Trace of reasoning steps."""

    id: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    conclusion: str = ""
    confidence: float = 0.5
    confidence_level: ConfidenceLevel = ConfidenceLevel.MEDIUM
    reasoning_quality: float = 0.5
    potential_biases: list[str] = field(default_factory=list)
    alternatives_considered: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def add_step(self, thought: str, evidence: str = "", confidence: float = 0.5):
        self.steps.append(
            {
                "thought": thought,
                "evidence": evidence,
                "confidence": confidence,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    def to_context(self) -> str:
        steps_str = "\n".join(
            f"  {i + 1}. {s['thought']} (confidence: {s['confidence']:.0%})"
            for i, s in enumerate(self.steps)
        )
        return f"""Reasoning Trace:
{steps_str}
Conclusion: {self.conclusion}
Overall Confidence: {self.confidence:.0%} ({self.confidence_level.value})
Quality Score: {self.reasoning_quality:.2f}
Biases Detected: {", ".join(self.potential_biases) if self.potential_biases else "None"}
Alternatives: {", ".join(self.alternatives_considered) if self.alternatives_considered else "None"}"""


class MetaCognition:
    """Meta-cognitive monitoring and self-evaluation."""

    def __init__(self, backend: CognitiveBackend):
        self.backend = backend
        self.logger = structlog.get_logger()
        self.traces: list[ReasoningTrace] = []

    async def evaluate_reasoning(
        self,
        query: str,
        reasoning: str,
        context: str = "",
    ) -> ReasoningTrace:
        """Evaluate the quality of reasoning."""
        trace = ReasoningTrace(id=f"trace_{datetime.utcnow().timestamp()}")

        system_prompt = """You are a meta-cognitive evaluator. Analyze the reasoning process and provide:
1. Step-by-step breakdown of reasoning quality
2. Confidence assessment (0-1)
3. Potential biases detected
4. Alternative reasoning paths considered
5. Overall quality score (0-1)

Return JSON with: steps (list of {thought, quality, issues}), confidence, biases, alternatives, quality_score"""

        user_prompt = f"""Query: {query}

Reasoning to evaluate:
{reasoning}

Context: {context}

Evaluate this reasoning:"""

        response = await self.backend.complete(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=1500,
            temperature=0.3,
        )

        try:
            result = response.parsed_json

            trace.conclusion = reasoning[:500]
            trace.confidence = result.get("confidence", 0.5)
            trace.confidence_level = self._confidence_level(trace.confidence)
            trace.reasoning_quality = result.get("quality_score", 0.5)
            trace.potential_biases = result.get("biases", [])
            trace.alternatives_considered = result.get("alternatives", [])

            for step in result.get("steps", []):
                trace.add_step(
                    thought=step.get("thought", ""),
                    evidence=step.get("evidence", ""),
                    confidence=step.get("quality", 0.5),
                )

        except Exception as e:
            self.logger.error("evaluation_failed", error=str(e))
            trace.confidence = 0.3
            trace.confidence_level = ConfidenceLevel.LOW

        self.traces.append(trace)
        return trace

    async def calibrate_confidence(
        self,
        claim: str,
        evidence: list[str],
    ) -> tuple[float, str]:
        """Calibrate confidence in a claim based on evidence."""
        system_prompt = "Assess confidence in a claim based on provided evidence. Return JSON with confidence (0-1) and reasoning."

        user_prompt = f"""Claim: {claim}

Evidence:
{chr(10).join(f"- {e}" for e in evidence)}

Assess confidence:"""

        response = await self.backend.complete(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=500,
            temperature=0.3,
        )

        try:
            result = response.parsed_json
            confidence = result.get("confidence", 0.5)
            reasoning = result.get("reasoning", "Unable to assess")
            return confidence, reasoning
        except Exception:
            return 0.5, "Assessment failed"

    async def detect_hallucination(
        self,
        text: str,
        known_facts: list[str],
    ) -> dict[str, Any]:
        """Check if text contains potential hallucinations."""
        system_prompt = """Check if the text contains claims not supported by known facts.
Return JSON with: supported_claims, unsupported_claims, hallucination_risk (0-1)"""

        user_prompt = f"""Text: {text}

Known facts:
{chr(10).join(f"- {f}" for f in known_facts)}

Check for hallucinations:"""

        response = await self.backend.complete(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=1000,
            temperature=0.3,
        )

        try:
            return response.parsed_json
        except Exception:
            return {"hallucination_risk": 0.5, "error": "Assessment failed"}

    async def suggest_improvements(
        self,
        reasoning_trace: ReasoningTrace,
    ) -> list[str]:
        """Suggest improvements to reasoning."""
        system_prompt = "Suggest specific improvements to the reasoning process. Return JSON with suggestions (list of strings)."

        user_prompt = f"""Reasoning trace:
{reasoning_trace.to_context()}

Suggest improvements:"""

        response = await self.backend.complete(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=800,
            temperature=0.3,
        )

        try:
            result = response.parsed_json
            return result.get("suggestions", [])
        except Exception:
            return ["Unable to generate suggestions"]

    async def reflect_on_action(
        self,
        action: str,
        outcome: str,
        expected: str,
    ) -> dict[str, Any]:
        """Reflect on an action's outcome."""
        system_prompt = """Reflect on an action and its outcome.
Return JSON with: analysis, what_worked, what_failed, lessons_learned, confidence_in_future"""

        user_prompt = f"""Action: {action}
Expected: {expected}
Actual Outcome: {outcome}

Reflect:"""

        response = await self.backend.complete(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=1000,
            temperature=0.3,
        )

        try:
            return response.parsed_json
        except Exception:
            return {"analysis": "Reflection failed"}

    def _confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Convert confidence score to level."""
        if confidence < 0.2:
            return ConfidenceLevel.VERY_LOW
        elif confidence < 0.4:
            return ConfidenceLevel.LOW
        elif confidence < 0.6:
            return ConfidenceLevel.MEDIUM
        elif confidence < 0.8:
            return ConfidenceLevel.HIGH
        else:
            return ConfidenceLevel.VERY_HIGH

    async def should_retry(
        self,
        trace: ReasoningTrace,
        max_retries: int = 3,
    ) -> tuple[bool, str]:
        """Decide if action should be retried based on meta-cognition."""
        if trace.confidence >= 0.7:
            return False, "Confidence sufficient"

        if trace.reasoning_quality < 0.4:
            return True, "Reasoning quality too low - try different approach"

        if len(trace.potential_biases) > 2:
            return True, "Multiple biases detected - reconsider approach"

        if trace.confidence < 0.3:
            return True, "Very low confidence - gather more evidence"

        return False, "Acceptable confidence level"
