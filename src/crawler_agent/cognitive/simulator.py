"""Internal Simulator for mental simulation and dreaming."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import structlog
from openai import AsyncOpenAI


class SimulationType(str, Enum):
    PLANNING = "planning"          # Simulate before acting
    REFLECTION = "reflection"      # Simulate past events
    COUNTERFACTUAL = "counterfactual"  # What-if scenarios
    PREDICTION = "prediction"      # Future state prediction
    DREAM = "dream"                # Unconstrained exploration


@dataclass
class SimulationState:
    """State in a simulation."""
    description: str
    variables: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Simulation:
    """A simulation run."""
    id: str
    simulation_type: SimulationType
    goal: str
    initial_state: SimulationState
    steps: list[dict[str, Any]] = field(default_factory=list)
    final_state: SimulationState | None = None
    outcomes: list[str] = field(default_factory=list)
    confidence: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Dream:
    """A dream-like simulation for creative exploration."""
    id: str
    theme: str
    associations: list[str] = field(default_factory=list)
    novel_connections: list[str] = field(default_factory=list)
    insights: list[str] = field(default_factory=list)
    creative_ideas: list[str] = field(default_factory=list)
    emotional_tone: str = "neutral"
    metadata: dict[str, Any] = field(default_factory=dict)


class InternalSimulator:
    """Mental simulation engine for planning and dreaming."""

    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview", api_base: str | None = None):
        self.client = AsyncOpenAI(api_key=api_key or "ollama", base_url=api_base)
        self.model = model
        self.simulations: list[Simulation] = []
        self.dreams: list[Dream] = []
        self.world_model: dict[str, Any] = {}  # Simplified world state
        self.logger = structlog.get_logger()

    async def simulate_action(
        self,
        action: str,
        current_state: dict[str, Any],
        simulation_type: SimulationType = SimulationType.PLANNING,
    ) -> Simulation:
        """Simulate an action before executing."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": f"""Simulate the outcome of an action. Type: {simulation_type.value}

Consider:
1. Preconditions needed
2. Direct effects
3. Side effects
4. Failure modes
5. Resource costs

Return JSON with: steps (list of {state, action, outcome, probability}),
final_state, outcomes (list), risks, confidence""",
                },
                {
                    "role": "user",
                    "content": f"""Current state: {json.dumps(current_state, default=str)[:1000]}
Action to simulate: {action}

Simulate:""",
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=1500,
        )

        try:
            data = json.loads(response.choices[0].message.content or "{}")
            sim = Simulation(
                id=f"sim_{len(self.simulations)}",
                simulation_type=simulation_type,
                goal=action,
                initial_state=SimulationState(
                    description="Current state",
                    variables=current_state,
                ),
                steps=data.get("steps", []),
                final_state=SimulationState(
                    description=str(data.get("final_state", "")),
                    variables=data.get("final_state", {}),
                ) if data.get("final_state") else None,
                outcomes=data.get("outcomes", []),
                confidence=data.get("confidence", 0.5),
                metadata={"risks": data.get("risks", [])},
            )
            self.simulations.append(sim)
            return sim
        except Exception as e:
            self.logger.error("simulation_failed", error=str(e))
            return Simulation(
                id="failed",
                simulation_type=simulation_type,
                goal=action,
                initial_state=SimulationState(description="Failed"),
            )

    async def simulate_plan(
        self,
        plan: list[str],
        initial_state: dict[str, Any],
    ) -> Simulation:
        """Simulate a complete plan."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """Simulate executing a multi-step plan.
For each step, track state changes and identify failure points.

Return JSON with: step_results (list of {step, new_state, success_probability, issues}),
final_state, overall_success_probability, bottlenecks, recommendations""",
                },
                {
                    "role": "user",
                    "content": f"""Initial state: {json.dumps(initial_state, default=str)[:1000]}
Plan steps: {plan}

Simulate plan execution:""",
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=2000,
        )

        try:
            data = json.loads(response.choices[0].message.content or "{}")
            sim = Simulation(
                id=f"plan_sim_{len(self.simulations)}",
                simulation_type=SimulationType.PLANNING,
                goal="Execute plan",
                initial_state=SimulationState(variables=initial_state),
                steps=data.get("step_results", []),
                confidence=data.get("overall_success_probability", 0.5),
                metadata={
                    "bottlenecks": data.get("bottlenecks", []),
                    "recommendations": data.get("recommendations", []),
                },
            )
            self.simulations.append(sim)
            return sim
        except Exception as e:
            self.logger.error("plan_simulation_failed", error=str(e))
            return Simulation(
                id="failed",
                simulation_type=SimulationType.PLANNING,
                goal="Failed plan simulation",
                initial_state=SimulationState(variables=initial_state),
            )

    async def reflect_on_past(
        self,
        event: str,
        outcome: str,
        alternatives: list[str] | None = None,
    ) -> dict[str, Any]:
        """Reflect on past events by simulating alternatives."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """Reflect on a past event by simulating alternative outcomes.
Consider: what if different decisions had been made?

Return JSON with: analysis, alternatives_simulated (list of {action, predicted_outcome, comparison},
lessons_learned, better_approaches""",
                },
                {
                    "role": "user",
                    "content": f"""Event: {event}
Actual outcome: {outcome}
Alternatives to consider: {alternatives or []}

Reflect:""",
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=1500,
        )

        try:
            return json.loads(response.choices[0].message.content or "{}")
        except Exception:
            return {"analysis": "Reflection failed"}

    async def predict_future(
        self,
        current_state: dict[str, Any],
        time_horizon: str = "1 hour",
    ) -> dict[str, Any]:
        """Predict future state."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """Predict the future state based on current conditions.
Consider trends, momentum, and likely events.

Return JSON with: predicted_state, probability, key_factors, wild_cards""",
                },
                {
                    "role": "user",
                    "content": f"""Current state: {json.dumps(current_state, default=str)[:1000]}
Time horizon: {time_horizon}

Predict future:""",
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=1000,
        )

        try:
            return json.loads(response.choices[0].message.content or "{}")
        except Exception:
            return {"error": "Prediction failed"}

    async def dream(
        self,
        theme: str,
        knowledge_context: str = "",
    ) -> Dream:
        """Generate a dream-like exploration for creative insights."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """Generate a dream-like exploration. Connect disparate ideas, 
find novel associations, and generate creative insights.

Dreams are not bound by practical constraints - explore freely.

Return JSON with: associations (list), novel_connections (list),
insights (list), creative_ideas (list), emotional_tone""",
                },
                {
                    "role": "user",
                    "content": f"""Theme for dream: {theme}
Context: {knowledge_context[:2000]}

Dream:""",
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=1500,
        )

        try:
            data = json.loads(response.choices[0].message.content or "{}")
            dream = Dream(
                id=f"dream_{len(self.dreams)}",
                theme=theme,
                associations=data.get("associations", []),
                novel_connections=data.get("novel_connections", []),
                insights=data.get("insights", []),
                creative_ideas=data.get("creative_ideas", []),
                emotional_tone=data.get("emotional_tone", "neutral"),
            )
            self.dreams.append(dream)
            return dream
        except Exception as e:
            self.logger.error("dream_failed", error=str(e))
            return Dream(id="failed", theme=theme)

    async def imagine_novel_scenario(
        self,
        constraints: list[str],
        goals: list[str],
    ) -> dict[str, Any]:
        """Imagine a novel scenario that satisfies constraints and goals."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """Imagine a novel scenario that:
1. Satisfies the given constraints
2. Achieves the given goals
3. Is creative and non-obvious

Return JSON with: scenario, how_it_meets_goals, novelty_score, implementation_steps""",
                },
                {
                    "role": "user",
                    "content": f"""Constraints: {constraints}
Goals: {goals}

Imagine a novel approach:""",
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=1200,
        )

        try:
            return json.loads(response.choices[0].message.content or "{}")
        except Exception:
            return {"error": "Imagination failed"}

    def update_world_model(self, key: str, value: Any) -> None:
        """Update the internal world model."""
        self.world_model[key] = value

    def get_world_model(self) -> dict[str, Any]:
        """Get current world model state."""
        return self.world_model.copy()

    def to_context(self) -> str:
        """Export simulation context."""
        lines = ["Recent Simulations:"]
        for sim in self.simulations[-5:]:
            lines.append(f"  [{sim.simulation_type.value}] {sim.goal[:60]}")
            lines.append(f"    Confidence: {sim.confidence:.0%}")
        if self.dreams:
            lines.append("\nRecent Dreams:")
            for dream in self.dreams[-3:]:
                lines.append(f"  Theme: {dream.theme}")
                if dream.insights:
                    lines.append(f"    Insight: {dream.insights[0]}")
        return "\n".join(lines)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_simulations": len(self.simulations),
            "total_dreams": len(self.dreams),
            "by_type": {
                t.value: sum(1 for s in self.simulations if s.simulation_type == t)
                for t in SimulationType
            },
            "avg_confidence": sum(s.confidence for s in self.simulations) / max(len(self.simulations), 1),
            "world_model_size": len(self.world_model),
        }
