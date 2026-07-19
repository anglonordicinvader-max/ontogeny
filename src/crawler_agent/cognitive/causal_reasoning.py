"""Causal Reasoning Engine for intervention-based reasoning."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, StrEnum
from typing import Any

import networkx as nx
import structlog

from .backend import CognitiveBackend


class CausalRelation(StrEnum):
    DIRECT_CAUSE = "direct_cause"
    INDIRECT_CAUSE = "indirect_cause"
    CONTRIBUTING_FACTOR = "contributing_factor"
    NECESSARY_CONDITION = "necessary_condition"
    SUFFICIENT_CONDITION = "sufficient_condition"
    CORRELATION = "correlation"
    CONFOUNDING = "confounding"
    MEDIATION = "mediation"
    MODERATION = "moderation"


@dataclass
class CausalVariable:
    """A variable in the causal model."""

    id: str
    name: str
    description: str = ""
    variable_type: str = "continuous"  # continuous, discrete, binary
    observed_value: Any = None
    confidence: float = 0.5
    interventions: list[dict] = field(default_factory=list)


@dataclass
class CausalEdge:
    """A causal relationship."""

    source: str
    target: str
    relation: CausalRelation
    strength: float = 1.0
    confidence: float = 0.5
    evidence: list[str] = field(default_factory=list)
    mechanisms: list[str] = field(default_factory=list)


@dataclass
class Intervention:
    """A causal intervention."""

    variable: str
    value: Any
    do_operator: bool = True  # do(x=v) vs observe(x=v)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Counterfactual:
    """A counterfactual scenario."""

    description: str
    interventions: list[Intervention]
    predicted_outcome: str = ""
    confidence: float = 0.5
    actual_outcome: str = ""


class CausalReasoner:
    """Engine for causal and counterfactual reasoning."""

    def __init__(self, backend: CognitiveBackend):
        self.backend = backend
        self.dag = nx.DiGraph()  # Directed Acyclic Graph
        self.variables: dict[str, CausalVariable] = {}
        self.edges: list[CausalEdge] = []
        self.interventions: list[Intervention] = []
        self.counterfactuals: list[Counterfactual] = []
        self.logger = structlog.get_logger()

    async def extract_causal_structure(
        self,
        text: str,
        context: str = "",
    ) -> tuple[list[CausalVariable], list[CausalEdge]]:
        """Extract causal structure from text."""
        system_prompt = """Extract causal relationships from text. Return JSON with:
- variables: list of {name, type, description}
- edges: list of {cause, effect, relation_type, strength, mechanisms}

Relation types: direct_cause, indirect_cause, contributing_factor,
necessary_condition, sufficient_condition, correlation, confounding

Be precise about causal vs correlational claims."""

        user_prompt = f"Context: {context}\n\nExtract causal structure from:\n{text[:4000]}"

        response = await self.backend.complete(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=2000,
            temperature=0.3,
        )

        try:
            data = response.parsed_json
            variables = []
            edges = []

            for v in data.get("variables", []):
                name = v.get("name", "unknown")
                if isinstance(name, list):
                    name = str(name[0]) if name else "unknown"
                var = CausalVariable(
                    id=str(name).lower().replace(" ", "_"),
                    name=str(name),
                    description=v.get("description", ""),
                    variable_type=v.get("type", "continuous"),
                )
                variables.append(var)

            for e in data.get("edges", []):
                try:
                    rel = CausalRelation(e.get("relation_type", "correlation"))
                except ValueError:
                    rel = CausalRelation.CORRELATION
                cause = e.get("cause", "unknown")
                effect = e.get("effect", "unknown")
                if isinstance(cause, list):
                    cause = str(cause[0]) if cause else "unknown"
                if isinstance(effect, list):
                    effect = str(effect[0]) if effect else "unknown"
                edge = CausalEdge(
                    source=str(cause).lower().replace(" ", "_"),
                    target=str(effect).lower().replace(" ", "_"),
                    relation=rel,
                    strength=e.get("strength", 0.5),
                    mechanisms=e.get("mechanisms", []),
                )
                edges.append(edge)

            return variables, edges

        except Exception as e:
            self.logger.error("causal_extraction_failed", error=str(e))
            return [], []

    def add_variable(self, variable: CausalVariable) -> None:
        """Add variable to causal model."""
        self.variables[variable.id] = variable
        self.dag.add_node(variable.id, **variable.__dict__)

    def add_edge(self, edge: CausalEdge) -> None:
        """Add causal edge."""
        self.edges.append(edge)
        self.dag.add_edge(
            edge.source,
            edge.target,
            relation=edge.relation.value,
            strength=edge.strength,
            confidence=edge.confidence,
        )

    def get_causes(self, effect: str) -> list[dict[str, Any]]:
        """Get all causes of an effect."""
        causes = []
        for predecessor in self.dag.predecessors(effect):
            edge_data = self.dag[predecessor][effect]
            causes.append(
                {
                    "variable": predecessor,
                    "relation": edge_data.get("relation"),
                    "strength": edge_data.get("strength", 1.0),
                }
            )
        return causes

    def get_effects(self, cause: str) -> list[dict[str, Any]]:
        """Get all effects of a cause."""
        effects = []
        for successor in self.dag.successors(cause):
            edge_data = self.dag[cause][successor]
            effects.append(
                {
                    "variable": successor,
                    "relation": edge_data.get("relation"),
                    "strength": edge_data.get("strength", 1.0),
                }
            )
        return effects

    def find_confounders(self, x: str, y: str) -> list[str]:
        """Find confounding variables between X and Y."""
        ancestors_x = nx.ancestors(self.dag, x)
        ancestors_y = nx.ancestors(self.dag, y)
        common_ancestors = ancestors_x & ancestors_y

        confounders = []
        for ancestor in common_ancestors:
            if self.dag.has_edge(ancestor, x) and self.dag.has_edge(ancestor, y):
                confounders.append(ancestor)

        return confounders

    def find_mediators(self, x: str, y: str) -> list[list[str]]:
        """Find mediating paths from X to Y."""
        try:
            all_paths = list(nx.all_simple_paths(self.dag, x, y, cutoff=5))
            mediators = [path[1:-1] for path in all_paths if len(path) > 2]
            return mediators
        except (nx.NetworkXError, nx.NodeNotFound):
            return []

    async def do_calculus(
        self,
        query: str,
        intervention: Intervention,
        context: str = "",
    ) -> dict[str, Any]:
        """Perform do-calculus intervention reasoning."""
        system_prompt = """Perform causal intervention reasoning using do-calculus.

Given:
- A causal model (DAG)
- An intervention do(X=v)
- A query about the effect

Reason about:
1. What changes when we intervene vs observe
2. Which paths are blocked/active
3. The causal effect estimate

Return JSON with: effect_estimate, reasoning, active_paths, blocked_paths, confidence"""

        user_prompt = f"""Causal Model:
Variables: {list(self.variables.keys())}
Edges: {[(e.source, e.target, e.relation.value) for e in self.edges[:20]]}

Intervention: do({intervention.variable} = {intervention.value})
Query: {query}
Context: {context}

Reason about the causal effect:"""

        response = await self.backend.complete(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=1500,
            temperature=0.3,
        )

        try:
            return response.parsed_json
        except Exception:
            return {"error": "Do-calculus reasoning failed"}

    async def counterfactual_reasoning(
        self,
        actual_outcome: str,
        intervention: Intervention,
        context: str = "",
    ) -> Counterfactual:
        """Reason about counterfactuals: what if X had been different?"""
        system_prompt = """Perform counterfactual reasoning. Given an actual outcome and a hypothetical intervention, predict what would have happened.

Return JSON with: predicted_outcome, confidence, reasoning, differences"""

        user_prompt = f"""Actual outcome: {actual_outcome}
Hypothetical: do({intervention.variable} = {intervention.value})
Context: {context}

What would have happened?"""

        response = await self.backend.complete(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=1000,
            temperature=0.3,
        )

        try:
            data = response.parsed_json
            cf = Counterfactual(
                description=data.get("reasoning", ""),
                interventions=[intervention],
                predicted_outcome=data.get("predicted_outcome", ""),
                confidence=data.get("confidence", 0.5),
                actual_outcome=actual_outcome,
            )
            self.counterfactuals.append(cf)
            return cf
        except Exception:
            return Counterfactual(
                description="Counterfactual reasoning failed",
                interventions=[intervention],
            )

    async def estimate_causal_effect(
        self,
        cause: str,
        effect: str,
        evidence: list[str] | None = None,
    ) -> dict[str, Any]:
        """Estimate causal effect between variables."""
        causes = self.get_causes(effect)
        confounders = self.find_confounders(cause, effect)
        mediators = self.find_mediators(cause, effect)

        system_prompt = """Estimate the causal effect between variables.
Consider: direct effects, indirect effects, confounders, mediators.
Return JSON with: effect_size, direction, confidence, decomposition"""

        user_prompt = f"""Cause: {cause}
Effect: {effect}
Known causes of {effect}: {causes}
Confounders: {confounders}
Mediators: {mediators}
Evidence: {evidence or []}

Estimate causal effect:"""

        response = await self.backend.complete(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=800,
            temperature=0.3,
        )

        try:
            return response.parsed_json
        except Exception:
            return {"effect_size": 0, "confidence": 0}

    def to_context(self) -> str:
        """Export causal model as context."""
        lines = ["Causal Model:"]
        for edge in self.edges[:30]:
            lines.append(f"  {edge.source} --[{edge.relation.value}]--> {edge.target}")
        return "\n".join(lines)

    def get_stats(self) -> dict[str, Any]:
        return {
            "variables": len(self.variables),
            "edges": len(self.edges),
            "interventions": len(self.interventions),
            "counterfactuals": len(self.counterfactuals),
            "is_dag": nx.is_directed_acyclic_graph(self.dag)
            if self.dag.number_of_nodes() > 0
            else True,
        }

    # === Temporal Causal Discovery ===

    async def discover_temporal_causality(
        self,
        event_sequence: list[dict[str, Any]],
        time_window: float = 1.0,
    ) -> list[CausalEdge]:
        """Discover causal relationships from temporal event sequences.

        Uses temporal precedence, co-occurrence, and Granger-like
        reasoning to identify causal links.

        Args:
            event_sequence: [{event_type, timestamp, variables, outcome}]
            time_window: Max time gap to consider for causal candidates
        """
        if len(event_sequence) < 2:
            return []

        # Sort by timestamp
        sorted_events = sorted(event_sequence, key=lambda e: e.get("timestamp", 0))

        system_prompt = """Discover causal relationships from a temporal sequence of events.

Analyze:
1. Temporal precedence (cause before effect)
2. Consistent co-occurrence patterns
3. Strength of temporal association
4. Potential confounders
5. Time lag between cause and effect

Return JSON with:
- causal_edges: [{cause_event, effect_event, relation, strength, time_lag, confidence, evidence}]
- temporal_patterns: [{pattern_description, frequency}]
- confounders: [{variable, affects}]"""

        user_prompt = f"""Event Sequence ({len(sorted_events)} events):
{self._format_events_for_prompt(sorted_events)}

Time Window: {time_window}

Discover causal relationships:"""

        response = await self.backend.complete(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=2000,
            temperature=0.3,
        )

        discovered = []
        try:
            data = response.parsed_json
            for edge_data in data.get("causal_edges", []):
                cause = edge_data.get("cause_event", "unknown")
                effect = edge_data.get("effect_event", "unknown")

                edge = CausalEdge(
                    source=str(cause).lower().replace(" ", "_"),
                    target=str(effect).lower().replace(" ", "_"),
                    relation=CausalRelation(edge_data.get("relation", "direct_cause")),
                    strength=edge_data.get("strength", 0.5),
                    confidence=edge_data.get("confidence", 0.5),
                    evidence=[str(e.get("event_type", "")) for e in sorted_events[:5]],
                )
                discovered.append(edge)

                # Add to model
                self.add_edge(edge)
        except Exception as e:
            self.logger.error("temporal_discovery_failed", error=str(e))

        self.logger.info(
            "temporal_causality_discovered",
            edges_found=len(discovered),
            events_analyzed=len(sorted_events),
        )

        return discovered

    def _format_events_for_prompt(self, events: list[dict[str, Any]]) -> str:
        """Format events for prompt."""
        lines = []
        for i, e in enumerate(events[:20]):
            ts = e.get("timestamp", "N/A")
            etype = e.get("event_type", "unknown")
            vars_str = (
                ", ".join(str(k) for k in e.get("variables", {}).keys())
                if isinstance(e.get("variables"), dict)
                else ""
            )
            lines.append(f"  {i}: [{ts}] {etype} ({vars_str})")
        return "\n".join(lines)

    async def plan_interventions(
        self,
        desired_outcome: str,
        current_state: dict[str, Any] | None = None,
        constraints: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Plan a sequence of interventions to achieve a desired outcome.

        Uses the causal model to identify:
        1. Which variables to intervene on
        2. What values to set
        3. What order to apply interventions
        4. Expected cascade effects
        5. Risk assessment for each intervention
        """
        system_prompt = """Plan causal interventions to achieve a desired outcome.

Consider:
1. Which variables are intervention points (not confounders)
2. Order of interventions (respect causal direction)
3. Expected cascading effects
4. Risk of unintended consequences
5. Confidence in each intervention

Return JSON with:
- intervention_plan: [{variable, value, rationale, expected_effects, risk_level, confidence}]
- execution_order: [variable_names in order]
- total_expected_effect: 0-1
- risk_assessment: {overall_risk, mitigations}
- alternative_plans: [{plan_name, interventions}]"""

        user_prompt = f"""Desired Outcome: {desired_outcome}
Current State: {current_state or {}}
Constraints: {constraints or []}

Causal Model:
Variables: {list(self.variables.keys())[:20]}
Edges: {[(e.source, e.target, e.relation.value) for e in self.edges[:15]]}

Plan interventions:"""

        response = await self.backend.complete(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=2000,
            temperature=0.3,
        )

        try:
            data = response.parsed_json

            # Record interventions
            for interv in data.get("intervention_plan", []):
                self.interventions.append(
                    Intervention(
                        variable=interv.get("variable", "unknown"),
                        value=interv.get("value"),
                    )
                )

            return data
        except Exception as e:
            self.logger.error("intervention_planning_failed", error=str(e))
            return {"intervention_plan": [], "total_expected_effect": 0}

    async def predict_cascade(
        self,
        initial_change: dict[str, Any],
        depth: int = 3,
    ) -> dict[str, Any]:
        """Predict the cascade of effects from an initial change.

        Traces through the causal graph to predict:
        1. Direct effects
        2. Indirect effects (through mediators)
        3. Feedback loops (if any)
        4. Converging causes
        """
        if not initial_change:
            return {"effects": [], "cascade_depth": 0}

        variable = list(initial_change.keys())[0] if initial_change else "unknown"
        value = initial_change[variable] if variable in initial_change else "unknown"

        # Trace causal paths
        effects = []
        visited = set()
        current_level = [(variable, value, 1.0)]  # (var, val, strength)

        for d in range(depth):
            next_level = []
            for var, _val, strength in current_level:
                if var in visited:
                    continue
                visited.add(var)

                # Find direct effects
                for edge in self.edges:
                    if edge.source == var and edge.target not in visited:
                        effect_strength = strength * edge.strength
                        effects.append(
                            {
                                "variable": edge.target,
                                "via_path": f"{var} -> {edge.target}",
                                "relation": edge.relation.value,
                                "strength": effect_strength,
                                "depth": d + 1,
                                "confidence": edge.confidence * strength,
                            }
                        )
                        next_level.append((edge.target, "affected", effect_strength))

            current_level = next_level
            if not current_level:
                break

        return {
            "initial_change": initial_change,
            "effects": effects,
            "cascade_depth": len(effects),
            "variables_affected": len(set(e["variable"] for e in effects)),
            "strongest_effect": max(effects, key=lambda e: e["strength"]) if effects else None,
        }
