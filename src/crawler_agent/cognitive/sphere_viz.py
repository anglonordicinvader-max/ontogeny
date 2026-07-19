"""Sphere mode visualizations - abstract proto-AGI visual representations.

Provides:
- Planning tree visualization
- Knowledge graph visualization
- Reasoning chain visualization
- Concept map visualization
- Memory visualization
"""

import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog


@dataclass
class VizNode:
    id: str
    label: str
    position: list[float]
    color: list[float] = field(default_factory=lambda: [0.5, 0.5, 0.5])
    size: float = 0.1
    node_type: str = "default"
    metadata: dict = field(default_factory=dict)


@dataclass
class VizEdge:
    source: str
    target: str
    color: list[float] = field(default_factory=lambda: [0.3, 0.3, 0.3])
    width: float = 0.02
    edge_type: str = "default"


@dataclass
class Visualization:
    name: str
    nodes: list[VizNode] = field(default_factory=list)
    edges: list[VizEdge] = field(default_factory=list)
    center: list[float] = field(default_factory=lambda: [0, 0, 0])
    timestamp: float = field(default_factory=time.time)


class SphereVisualizer:
    """Abstract sphere-based visualizations for cognitive processes."""

    def __init__(self, output_dir: str = "data/visualizations"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = structlog.get_logger(component="sphere_viz")
        self.visualizations: dict[str, Visualization] = {}

    def visualize_planning_tree(
        self,
        root: str,
        children: dict[str, list[str]],
        values: dict[str, float],
        visit_counts: dict[str, int],
    ) -> Visualization:
        """Create sphere visualization of MCTS planning tree."""
        nodes = []
        edges = []

        all_nodes = set(children.keys())
        for child_list in children.values():
            all_nodes.update(child_list)

        node_list = list(all_nodes)
        n = len(node_list)
        if n == 0:
            return Visualization(name="planning_tree")

        def sphere_point(index: int, total: int) -> list[float]:
            phi = math.acos(1 - 2 * (index + 0.5) / total)
            theta = math.pi * (1 + math.sqrt(5)) * index
            r = 0.5
            return [
                r * math.sin(phi) * math.cos(theta),
                r * math.sin(phi) * math.sin(theta),
                r * math.cos(phi),
            ]

        for i, node_id in enumerate(node_list):
            pos = sphere_point(i, n)
            value = values.get(node_id, 0.5)
            visits = visit_counts.get(node_id, 1)
            size = 0.05 + 0.1 * min(visits / 10, 1.0)

            if node_id == root:
                color = [1.0, 0.2, 0.2]
                size = 0.15
            elif value > 0.7:
                color = [0.2, 1.0, 0.2]
            elif value > 0.4:
                color = [1.0, 1.0, 0.2]
            else:
                color = [0.2, 0.2, 1.0]

            nodes.append(
                VizNode(
                    id=node_id,
                    label=f"{node_id}\nV:{value:.2f}",
                    position=pos,
                    color=color,
                    size=size,
                    node_type="plan_node",
                    metadata={"value": value, "visits": visits},
                )
            )

        for parent, child_list in children.items():
            for child in child_list:
                if parent in [n.id for n in nodes] and child in [n.id for n in nodes]:
                    edges.append(VizEdge(source=parent, target=child, edge_type="plan_edge"))

        viz = Visualization(name="planning_tree", nodes=nodes, edges=edges)
        self.visualizations["planning_tree"] = viz
        self._save_viz(viz)
        return viz

    def visualize_knowledge_graph(
        self,
        nodes_data: list[dict],
        edges_data: list[dict],
    ) -> Visualization:
        """Create sphere visualization of knowledge graph."""
        nodes = []
        edges = []
        n = len(nodes_data)

        if n == 0:
            return Visualization(name="knowledge_graph")

        def sphere_point(index: int, total: int) -> list[float]:
            phi = math.acos(1 - 2 * (index + 0.5) / total)
            theta = math.pi * (1 + math.sqrt(5)) * index
            r = 0.5
            return [
                r * math.sin(phi) * math.cos(theta),
                r * math.sin(phi) * math.sin(theta),
                r * math.cos(phi),
            ]

        for i, node_data in enumerate(nodes_data):
            pos = sphere_point(i, n)
            node_type = node_data.get("type", "concept")

            color_map = {
                "concept": [0.2, 0.6, 1.0],
                "fact": [0.2, 1.0, 0.6],
                "action": [1.0, 0.6, 0.2],
                "object": [1.0, 0.2, 0.6],
            }
            color = color_map.get(node_type, [0.5, 0.5, 0.5])

            nodes.append(
                VizNode(
                    id=node_data.get("id", str(i)),
                    label=node_data.get("label", f"Node {i}"),
                    position=pos,
                    color=color,
                    size=0.08,
                    node_type=node_type,
                    metadata=node_data,
                )
            )

        for edge_data in edges_data:
            edges.append(
                VizEdge(
                    source=edge_data.get("source", ""),
                    target=edge_data.get("target", ""),
                    edge_type=edge_data.get("type", "relation"),
                )
            )

        viz = Visualization(name="knowledge_graph", nodes=nodes, edges=edges)
        self.visualizations["knowledge_graph"] = viz
        self._save_viz(viz)
        return viz

    def visualize_reasoning_chain(
        self,
        steps: list[dict],
        conclusion: str,
        confidence: float,
    ) -> Visualization:
        """Create sphere visualization of reasoning chain."""
        nodes = []
        edges = []
        n = len(steps) + 1

        def sphere_point(index: int, total: int) -> list[float]:
            phi = math.acos(1 - 2 * (index + 0.5) / total)
            theta = math.pi * (1 + math.sqrt(5)) * index
            r = 0.4
            return [
                r * math.sin(phi) * math.cos(theta),
                r * math.sin(phi) * math.sin(theta),
                r * math.cos(phi),
            ]

        for i, step in enumerate(steps):
            pos = sphere_point(i, n)
            confidence = step.get("confidence", 0.5)
            color = [confidence, 0.5, 1 - confidence]

            nodes.append(
                VizNode(
                    id=f"step_{i}",
                    label=step.get("text", f"Step {i}")[:50],
                    position=pos,
                    color=color,
                    size=0.06,
                    node_type="reasoning_step",
                    metadata=step,
                )
            )

            if i > 0:
                edges.append(
                    VizEdge(
                        source=f"step_{i - 1}",
                        target=f"step_{i}",
                        edge_type="reasoning_flow",
                    )
                )

        conclusion_pos = sphere_point(n - 1, n)
        nodes.append(
            VizNode(
                id="conclusion",
                label=conclusion[:50],
                position=conclusion_pos,
                color=[1.0, 1.0, 0.2],
                size=0.12,
                node_type="conclusion",
                metadata={"confidence": confidence},
            )
        )

        if steps:
            edges.append(
                VizEdge(
                    source=f"step_{len(steps) - 1}",
                    target="conclusion",
                    edge_type="reasoning_flow",
                )
            )

        viz = Visualization(name="reasoning_chain", nodes=nodes, edges=edges)
        self.visualizations["reasoning_chain"] = viz
        self._save_viz(viz)
        return viz

    def visualize_concept_map(
        self,
        concepts: list[dict],
        relations: list[dict],
    ) -> Visualization:
        """Create sphere visualization of concept map."""
        nodes = []
        edges = []
        n = len(concepts)

        if n == 0:
            return Visualization(name="concept_map")

        def sphere_point(index: int, total: int) -> list[float]:
            phi = math.acos(1 - 2 * (index + 0.5) / total)
            theta = math.pi * (1 + math.sqrt(5)) * index
            r = 0.45
            return [
                r * math.sin(phi) * math.cos(theta),
                r * math.sin(phi) * math.sin(theta),
                r * math.cos(phi),
            ]

        for i, concept in enumerate(concepts):
            pos = sphere_point(i, n)
            importance = concept.get("importance", 0.5)
            size = 0.04 + 0.08 * importance
            color = [importance, 0.4, 1 - importance]

            nodes.append(
                VizNode(
                    id=concept.get("id", str(i)),
                    label=concept.get("name", f"Concept {i}"),
                    position=pos,
                    color=color,
                    size=size,
                    node_type="concept",
                    metadata=concept,
                )
            )

        for rel in relations:
            edges.append(
                VizEdge(
                    source=rel.get("source", ""),
                    target=rel.get("target", ""),
                    edge_type=rel.get("type", "related"),
                )
            )

        viz = Visualization(name="concept_map", nodes=nodes, edges=edges)
        self.visualizations["concept_map"] = viz
        self._save_viz(viz)
        return viz

    def visualize_memory(
        self,
        working: list[dict],
        episodic: list[dict],
        semantic: list[dict],
    ) -> Visualization:
        """Create sphere visualization of memory layers."""
        nodes = []
        edges = []
        all_items = []

        for item in working:
            all_items.append({**item, "layer": "working"})
        for item in episodic:
            all_items.append({**item, "layer": "episodic"})
        for item in semantic:
            all_items.append({**item, "layer": "semantic"})

        n = len(all_items)
        if n == 0:
            return Visualization(name="memory")

        def sphere_point(index: int, total: int, layer_offset: float) -> list[float]:
            phi = math.acos(1 - 2 * (index + 0.5) / total)
            theta = math.pi * (1 + math.sqrt(5)) * index
            r = 0.3 + layer_offset
            return [
                r * math.sin(phi) * math.cos(theta),
                r * math.sin(phi) * math.sin(theta),
                r * math.cos(phi),
            ]

        layer_colors = {
            "working": [1.0, 0.3, 0.3],
            "episodic": [0.3, 1.0, 0.3],
            "semantic": [0.3, 0.3, 1.0],
        }
        layer_offsets = {"working": 0.0, "episodic": 0.15, "semantic": 0.3}

        layer_counts = {"working": 0, "episodic": 0, "semantic": 0}

        for i, item in enumerate(all_items):
            layer = item.get("layer", "working")
            layer_counts[layer] += 1
            pos = sphere_point(layer_counts[layer] - 1, max(n, 1), layer_offsets[layer])

            nodes.append(
                VizNode(
                    id=f"{layer}_{i}",
                    label=item.get("content", "")[:30],
                    position=pos,
                    color=layer_colors.get(layer, [0.5, 0.5, 0.5]),
                    size=0.05,
                    node_type=f"memory_{layer}",
                    metadata=item,
                )
            )

        viz = Visualization(name="memory", nodes=nodes, edges=edges)
        self.visualizations["memory"] = viz
        self._save_viz(viz)
        return viz

    def _save_viz(self, viz: Visualization):
        """Save visualization to JSON."""
        filepath = self.output_dir / f"{viz.name}.json"
        data = {
            "name": viz.name,
            "timestamp": viz.timestamp,
            "nodes": [
                {
                    "id": n.id,
                    "label": n.label,
                    "position": n.position,
                    "color": n.color,
                    "size": n.size,
                    "type": n.node_type,
                    "metadata": n.metadata,
                }
                for n in viz.nodes
            ],
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "color": e.color,
                    "width": e.width,
                    "type": e.edge_type,
                }
                for e in viz.edges
            ],
        }
        filepath.write_text(json.dumps(data, indent=2))

    def to_context(self) -> str:
        viz_types = list(self.visualizations.keys())
        return f"Sphere Visualizer: {len(viz_types)} visualizations ({', '.join(viz_types)})"
