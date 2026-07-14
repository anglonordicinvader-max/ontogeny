"""Causal Reasoning Engine for intervention-based reasoning."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import networkx as nx
import structlog
from openai import AsyncOpenAI


class CausalRelation(str, Enum):
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

    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview", api_base: str | None = None):
        self.client = AsyncOpenAI(api_key=api_key or "ollama", base_url=api_base)
        self.model = model
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
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """Extract causal relationships from text. Return JSON with:
- variables: list of {name, type, description}
- edges: list of {cause, effect, relation_type, strength, mechanisms}

Relation types: direct_cause, indirect_cause, contributing_factor, 
necessary_condition, sufficient_condition, correlation, confounding

Be precise about causal vs correlational claims.""",
                },
                {
                    "role": "user",
                    "content": f"Context: {context}\n\nExtract causal structure from:\n{text[:4000]}",
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=2000,
        )

        try:
            data = json.loads(response.choices[0].message.content or "{}")
            variables = []
            edges = []

            for v in data.get("variables", []):
                var = CausalVariable(
                    id=v["name"].lower().replace(" ", "_"),
                    name=v["name"],
                    description=v.get("description", ""),
                    variable_type=v.get("type", "continuous"),
                )
                variables.append(var)

            for e in data.get("edges", []):
                edge = CausalEdge(
                    source=e["cause"].lower().replace(" ", "_"),
                    target=e["effect"].lower().replace(" ", "_"),
                    relation=CausalRelation(e.get("relation_type", "correlation")),
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
            edge.source, edge.target,
            relation=edge.relation.value,
            strength=edge.strength,
            confidence=edge.confidence,
        )

    def get_causes(self, effect: str) -> list[dict[str, Any]]:
        """Get all causes of an effect."""
        causes = []
        for predecessor in self.dag.predecessors(effect):
            edge_data = self.dag[predecessor][effect]
            causes.append({
                "variable": predecessor,
                "relation": edge_data.get("relation"),
                "strength": edge_data.get("strength", 1.0),
            })
        return causes

    def get_effects(self, cause: str) -> list[dict[str, Any]]:
        """Get all effects of a cause."""
        effects = []
        for successor in self.dag.successors(cause):
            edge_data = self.dag[cause][successor]
            effects.append({
                "variable": successor,
                "relation": edge_data.get("relation"),
                "strength": edge_data.get("strength", 1.0),
            })
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
            # Mediators are intermediate nodes
            mediators = [
                path[1:-1] for path in all_paths if len(path) > 2
            ]
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
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """Perform causal intervention reasoning using do-calculus.

Given:
- A causal model (DAG)
- An intervention do(X=v)
- A query about the effect

Reason about:
1. What changes when we intervene vs observe
2. Which paths are blocked/active
3. The causal effect estimate

Return JSON with: effect_estimate, reasoning, active_paths, blocked_paths, confidence""",
                },
                {
                    "role": "user",
                    "content": f"""Causal Model:
Variables: {list(self.variables.keys())}
Edges: {[(e.source, e.target, e.relation.value) for e in self.edges[:20]]}

Intervention: do({intervention.variable} = {intervention.value})
Query: {query}
Context: {context}

Reason about the causal effect:""",
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=1500,
        )

        try:
            return json.loads(response.choices[0].message.content or "{}")
        except Exception:
            return {"error": "Do-calculus reasoning failed"}

    async def counterfactual_reasoning(
        self,
        actual_outcome: str,
        intervention: Intervention,
        context: str = "",
    ) -> Counterfactual:
        """Reason about counterfactuals: what if X had been different?"""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """Perform counterfactual reasoning. Given an actual outcome and a hypothetical intervention, predict what would have happened.

Return JSON with: predicted_outcome, confidence, reasoning, differences""",
                },
                {
                    "role": "user",
                    "content": f"""Actual outcome: {actual_outcome}
Hypothetical: do({intervention.variable} = {intervention.value})
Context: {context}

What would have happened?""",
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=1000,
        )

        try:
            data = json.loads(response.choices[0].message.content or "{}")
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

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """Estimate the causal effect between variables.
Consider: direct effects, indirect effects, confounders, mediators.
Return JSON with: effect_size, direction, confidence, decomposition""",
                },
                {
                    "role": "user",
                    "content": f"""Cause: {cause}
Effect: {effect}
Known causes of {effect}: {causes}
Confounders: {confounders}
Mediators: {mediators}
Evidence: {evidence or []}

Estimate causal effect:""",
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=800,
        )

        try:
            return json.loads(response.choices[0].message.content or "{}")
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
            "is_dag": nx.is_directed_acyclic_graph(self.dag) if self.dag.number_of_nodes() > 0 else True,
        }
