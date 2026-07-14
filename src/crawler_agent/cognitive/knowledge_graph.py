"""Knowledge Graph for mapping relationships between concepts."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from collections import defaultdict

import networkx as nx
import structlog
from openai import AsyncOpenAI


class RelationType(str, Enum):
    IS_A = "is_a"
    PART_OF = "part_of"
    CAUSES = "causes"
    ENABLES = "enables"
    INHIBITS = "inhibits"
    SIMILAR_TO = "similar_to"
    CONTRADICTS = "contradicts"
    DEPENDS_ON = "depends_on"
    PRODUCES = "produces"
    TRANSFORMS = "transforms"
    LOCATED_IN = "located_in"
    TEMPORAL_BEFORE = "temporal_before"
    TEMPORAL_AFTER = "temporal_after"
    ABSTRACT = "abstract"


@dataclass
class Concept:
    """A concept in the knowledge graph."""
    id: str
    name: str
    description: str = ""
    embedding: list[float] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    strength: float = 1.0
    access_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Relation:
    """A relationship between concepts."""
    source_id: str
    target_id: str
    relation_type: RelationType
    weight: float = 1.0
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)


class KnowledgeGraph:
    """Graph-based knowledge representation."""

    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview", api_base: str | None = None):
        self.client = AsyncOpenAI(api_key=api_key or "ollama", base_url=api_base)
        self.model = model
        self.graph = nx.DiGraph()
        self.concepts: dict[str, Concept] = {}
        self.logger = structlog.get_logger()

    async def extract_knowledge(
        self,
        text: str,
        source: str = "",
    ) -> tuple[list[Concept], list[Relation]]:
        """Extract concepts and relations from text."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": """Extract knowledge from text. Return JSON with:
- concepts: list of {name, description, type}
- relations: list of {source, target, type, evidence}

Relation types: is_a, part_of, causes, enables, inhibits, similar_to, depends_on, produces, transforms, temporal_before, temporal_after

Focus on factual relationships. Be precise.""",
                },
                {
                    "role": "user",
                    "content": f"Extract knowledge from:\n\n{text[:5000]}",
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=2000,
        )

        try:
            data = json.loads(response.choices[0].message.content or "{}")
            concepts = []
            relations = []

            for c in data.get("concepts", []):
                concept = Concept(
                    id=c["name"].lower().replace(" ", "_"),
                    name=c["name"],
                    description=c.get("description", ""),
                    metadata={"source": source, "type": c.get("type", "concept")},
                )
                concepts.append(concept)

            for r in data.get("relations", []):
                source_id = r["source"].lower().replace(" ", "_")
                target_id = r["target"].lower().replace(" ", "_")
                relation = Relation(
                    source_id=source_id,
                    target_id=target_id,
                    relation_type=RelationType(r.get("type", "abstract")),
                    evidence=[r.get("evidence", "")],
                    confidence=0.7,
                )
                relations.append(relation)

            return concepts, relations

        except Exception as e:
            self.logger.error("knowledge_extraction_failed", error=str(e))
            return [], []

    def add_concept(self, concept: Concept) -> None:
        """Add concept to graph."""
        self.concepts[concept.id] = concept
        self.graph.add_node(
            concept.id,
            name=concept.name,
            description=concept.description,
            strength=concept.strength,
            metadata=concept.metadata,
        )

    def add_relation(self, relation: Relation) -> None:
        """Add relation to graph."""
        self.graph.add_edge(
            relation.source_id,
            relation.target_id,
            relation_type=relation.relation_type.value,
            weight=relation.weight,
            confidence=relation.confidence,
            evidence=relation.evidence,
        )

    def get_neighbors(
        self,
        concept_id: str,
        relation_type: RelationType | None = None,
        depth: int = 1,
    ) -> list[dict[str, Any]]:
        """Get neighboring concepts."""
        neighbors = []
        visited = set()

        def _traverse(node: str, current_depth: int):
            if current_depth > depth or node in visited:
                return
            visited.add(node)

            for successor in self.graph.successors(node):
                edge_data = self.graph[node][successor]
                if relation_type and edge_data.get("relation_type") != relation_type.value:
                    continue
                neighbors.append({
                    "concept": successor,
                    "relation": edge_data.get("relation_type"),
                    "weight": edge_data.get("weight", 1.0),
                    "depth": current_depth,
                })
                _traverse(successor, current_depth + 1)

        _traverse(concept_id, 1)
        return neighbors

    def find_paths(
        self,
        source: str,
        target: str,
        max_length: int = 5,
    ) -> list[list[str]]:
        """Find paths between concepts."""
        try:
            paths = list(nx.all_simple_paths(
                self.graph, source, target, cutoff=max_length
            ))
            return paths[:10]
        except (nx.NetworkXError, nx.NodeNotFound):
            return []

    def find_analogies(
        self,
        concept_a: str,
        concept_b: str,
        concept_c: str,
    ) -> list[str]:
        """Find D A : D B :: D C : ? analogies."""
        neighbors_a = {n["concept"] for n in self.get_neighbors(concept_a)}
        neighbors_b = {n["concept"] for n in self.get_neighbors(concept_b)}
        neighbors_c = {n["concept"] for n in self.get_neighbors(concept_c)}

        # Find similar patterns
        pattern_diff = neighbors_b - neighbors_a
        analogies = list(pattern_diff & neighbors_c)

        return analogies

    def get_strongest_concepts(self, limit: int = 20) -> list[Concept]:
        """Get most connected/important concepts."""
        centrality = nx.degree_centrality(self.graph)
        sorted_concepts = sorted(centrality.items(), key=lambda x: x[1], reverse=True)

        return [
            self.concepts[cid]
            for cid, _ in sorted_concepts[:limit]
            if cid in self.concepts
        ]

    def decay(self, decay_rate: float = 0.01) -> int:
        """Apply decay to unused concepts."""
        pruned = 0
        now = datetime.utcnow()

        for concept_id, concept in list(self.concepts.items()):
            days_since_access = (now - concept.last_accessed).days
            concept.strength *= (1 - decay_rate * days_since_access)

            if concept.strength < 0.1:
                self.graph.remove_node(concept_id)
                del self.concepts[concept_id]
                pruned += 1

        return pruned

    def query(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Query the knowledge graph."""
        query_lower = query.lower()
        results = []

        for concept_id, concept in self.concepts.items():
            score = 0
            if query_lower in concept.name.lower():
                score += 3
            if query_lower in concept.description.lower():
                score += 1
            if score > 0:
                results.append({
                    "concept": concept.name,
                    "description": concept.description,
                    "score": score,
                    "connections": self.graph.degree(concept_id),
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def to_context(self) -> str:
        """Export graph as context string."""
        lines = ["Knowledge Graph:"]
        for concept_id, concept in list(self.concepts.items())[:50]:
            neighbors = self.get_neighbors(concept_id, depth=1)
            if neighbors:
                rels = [f"{n['relation']}->{n['concept']}" for n in neighbors[:3]]
                lines.append(f"  {concept.name}: {', '.join(rels)}")
        return "\n".join(lines)

    def get_stats(self) -> dict[str, Any]:
        """Get graph statistics."""
        return {
            "concepts": len(self.concepts),
            "relations": self.graph.number_of_edges(),
            "avg_connectivity": sum(dict(self.graph.degree()).values()) / max(len(self.graph), 1),
            "components": nx.number_weakly_connected_components(self.graph),
        }
