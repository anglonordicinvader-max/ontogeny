"""Sleep/consolidation module - offline memory processing.

Simulates sleep-like memory consolidation with:
- Knowledge graph pruning (remove weak/unused nodes)
- Concept abstraction (generalize from specific instances)
- Memory compression (summarize long-term storage)
- Long-term consolidation (move important memories to permanent storage)
"""

import asyncio
import hashlib
import random
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog


@dataclass
class MemorySnapshot:
    """A snapshot of memory state before consolidation."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    episodic_count: int = 0
    semantic_count: int = 0
    procedural_count: int = 0
    avg_strength: float = 0.5
    emotional_valence: float = 0.0
    knowledge_nodes: int = 0
    knowledge_edges: int = 0


@dataclass
class ConsolidationReport:
    """Detailed report of a consolidation cycle."""

    timestamp: datetime = field(default_factory=datetime.utcnow)
    episodes_replayed: int = 0
    memories_strengthened: int = 0
    memories_forgotten: int = 0
    concepts_abstracted: int = 0
    nodes_pruned: int = 0
    edges_pruned: int = 0
    memories_compressed: int = 0
    tokens_saved: int = 0
    knowledge_integrated: int = 0
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "episodes_replayed": self.episodes_replayed,
            "memories_strengthened": self.memories_strengthened,
            "memories_forgotten": self.memories_forgotten,
            "concepts_abstracted": self.concepts_abstracted,
            "nodes_pruned": self.nodes_pruned,
            "edges_pruned": self.edges_pruned,
            "memories_compressed": self.memories_compressed,
            "tokens_saved": self.tokens_saved,
            "knowledge_integrated": self.knowledge_integrated,
            "duration_ms": self.duration_ms,
        }


class SleepConsolidator:
    """Advanced sleep-like memory consolidation with knowledge graph management.

    During "sleep" (background processing):
    1. Replay recent experiences (strengthen traces)
    2. Strengthen important memories
    3. Forget/decay weak memories
    4. Prune knowledge graph (remove weak/unused nodes)
    5. Abstract concepts from specific instances
    6. Compress long-term memories
    7. Integrate new knowledge with existing
    8. Consolidate working memory to long-term
    """

    def __init__(self, backend=None):
        self.backend = backend
        self.consolidation_log: list[dict] = []
        self.generalizations: list[dict] = []
        self.concepts: dict[str, dict] = {}  # abstracted concepts
        self.forget_count = 0
        self.strengthen_count = 0
        self.compression_count = 0
        self.logger = structlog.get_logger()

    async def consolidate(
        self,
        memory_system: Any,
        knowledge_graph: Any = None,
        patterns: Any = None,
        importance_threshold: float = 0.3,
        max_consolidation_age_hours: float = 24.0,
    ) -> ConsolidationReport:
        """Run full consolidation cycle with knowledge graph pruning."""
        start = datetime.utcnow()
        self.logger.info("consolidation_started")
        report = ConsolidationReport()

        # 1. Replay recent experiences
        report.episodes_replayed = await self._replay_experiences(memory_system)

        # 2. Strengthen important memories
        report.memories_strengthened = await self._strengthen_memories(
            memory_system, importance_threshold
        )

        # 3. Forget/decay weak memories
        report.memories_forgotten = await self._forget_weak(memory_system, importance_threshold)

        # 4. Prune knowledge graph
        if knowledge_graph:
            pruned = await self._prune_knowledge_graph(knowledge_graph, importance_threshold)
            report.nodes_pruned = pruned.get("nodes_pruned", 0)
            report.edges_pruned = pruned.get("edges_pruned", 0)

        # 5. Abstract concepts from specific instances
        report.concepts_abstracted = await self._abstract_concepts(memory_system, knowledge_graph)

        # 6. Compress long-term memories
        compressed = await self._compress_memories(memory_system, max_consolidation_age_hours)
        report.memories_compressed = compressed.get("compressed", 0)
        report.tokens_saved = compressed.get("tokens_saved", 0)

        # 7. Integrate new knowledge with existing
        report.knowledge_integrated = await self._integrate_knowledge(
            memory_system, knowledge_graph
        )

        # 8. Consolidate working memory to long-term
        await self._consolidate_working_to_longterm(memory_system)

        elapsed = (datetime.utcnow() - start).total_seconds() * 1000
        report.duration_ms = elapsed

        self.consolidation_log.append(report.to_dict())
        self.logger.info(
            "consolidation_complete",
            replayed=report.episodes_replayed,
            strengthened=report.memories_strengthened,
            forgotten=report.memories_forgotten,
            abstracted=report.concepts_abstracted,
            pruned_nodes=report.nodes_pruned,
            compressed=report.memories_compressed,
            duration_ms=elapsed,
        )
        return report

    async def _replay_experiences(self, memory_system: Any) -> int:
        """Replay recent experiences to strengthen memory traces."""
        recent = []
        if hasattr(memory_system, "episodic") and hasattr(memory_system.episodic, "list_memories"):
            recent = await memory_system.episodic.list_memories(limit=20)

        replayed = 0
        for memory in recent:
            if hasattr(memory, "access_count"):
                memory.access_count += 1
                replayed += 1
            # Also increase strength slightly on replay
            if hasattr(memory, "strength"):
                memory.strength = min(2.0, memory.strength * 1.02)

        return replayed

    async def _strengthen_memories(self, memory_system: Any, threshold: float) -> int:
        """Strengthen memories above importance threshold."""
        strengthened = 0

        for layer_name in ["episodic", "semantic"]:
            layer = getattr(memory_system, layer_name, None)
            if layer and hasattr(layer, "list_memories"):
                memories = await layer.list_memories(limit=50)
                for memory in memories:
                    importance = getattr(memory, "importance", 0.5)
                    if importance > threshold:
                        old_strength = getattr(memory, "strength", 1.0)
                        # Stronger boost for higher importance
                        boost = 1.0 + (importance * 0.15)
                        memory.strength = min(2.0, old_strength * boost)
                        strengthened += 1

        self.strengthen_count += strengthened
        return strengthened

    async def _forget_weak(self, memory_system: Any, threshold: float) -> int:
        """Forget/decay memories below strength threshold."""
        forgotten = 0
        weak_threshold = threshold * 0.5

        for layer_name in ["episodic", "semantic"]:
            layer = getattr(memory_system, layer_name, None)
            if layer and hasattr(layer, "list_memories"):
                memories = await layer.list_memories(limit=100)
                for memory in memories:
                    strength = getattr(memory, "strength", 1.0)
                    if strength < weak_threshold:
                        # Progressive decay
                        memory.strength = strength * 0.3
                        forgotten += 1

        self.forget_count += forgotten
        return forgotten

    async def _prune_knowledge_graph(
        self, knowledge_graph: Any, threshold: float
    ) -> dict[str, int]:
        """Prune weak/unused nodes and edges from knowledge graph."""
        nodes_pruned = 0
        edges_pruned = 0

        if not hasattr(knowledge_graph, "nodes") or not hasattr(knowledge_graph, "edges"):
            return {"nodes_pruned": 0, "edges_pruned": 0}

        # Prune weak nodes (low confidence or low access count)
        weak_nodes = []
        for node_id, node in list(knowledge_graph.nodes.items()):
            confidence = getattr(node, "confidence", 0.5)
            access_count = getattr(node, "access_count", 0)
            if confidence < threshold * 0.5 and access_count < 3:
                weak_nodes.append(node_id)

        for node_id in weak_nodes:
            # Remove connected edges first
            if hasattr(knowledge_graph, "edges"):
                edges_to_remove = [
                    e_id
                    for e_id, edge in knowledge_graph.edges.items()
                    if getattr(edge, "source", "") == node_id
                    or getattr(edge, "target", "") == node_id
                ]
                for e_id in edges_to_remove:
                    del knowledge_graph.edges[e_id]
                    edges_pruned += 1
            # Remove node
            del knowledge_graph.nodes[node_id]
            nodes_pruned += 1

        # Prune weak edges (low weight)
        if hasattr(knowledge_graph, "edges"):
            weak_edges = [
                e_id
                for e_id, edge in knowledge_graph.edges.items()
                if getattr(edge, "weight", 0.5) < threshold * 0.3
            ]
            for e_id in weak_edges:
                del knowledge_graph.edges[e_id]
                edges_pruned += 1

        self.logger.info("knowledge_graph_pruned", nodes=nodes_pruned, edges=edges_pruned)
        return {"nodes_pruned": nodes_pruned, "edges_pruned": edges_pruned}

    async def _abstract_concepts(self, memory_system: Any, knowledge_graph: Any = None) -> int:
        """Abstract general concepts from specific instances."""
        abstracted = 0

        if not hasattr(memory_system, "episodic") or not hasattr(
            memory_system.episodic, "list_memories"
        ):
            return 0

        memories = await memory_system.episodic.list_memories(limit=50)
        if len(memories) < 5:
            return 0

        # Extract word frequency patterns
        word_counts = defaultdict(int)
        word_memories = defaultdict(list)
        for memory in memories:
            content = getattr(memory, "content", "")
            words = set(content.lower().split())
            for word in words:
                if len(word) > 4:
                    word_counts[word] += 1
                    word_memories[word].append(memory)

        # Create concepts from frequently co-occurring words
        common_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        for word, count in common_words[:10]:
            if count >= 3 and word not in self.concepts:
                # Find related words (co-occur in same memories)
                related = set()
                for memory in word_memories[word]:
                    content = getattr(memory, "content", "").lower()
                    for other_word in content.split():
                        if other_word != word and len(other_word) > 4:
                            related.add(other_word)

                self.concepts[word] = {
                    "word": word,
                    "frequency": count,
                    "related_words": list(related)[:10],
                    "created_at": datetime.utcnow().isoformat(),
                    "importance": min(1.0, count / 10.0),
                }
                abstracted += 1

        self.logger.info("concepts_abstracted", count=abstracted)
        return abstracted

    async def _compress_memories(self, memory_system: Any, max_age_hours: float) -> dict[str, int]:
        """Compress old memories by summarizing groups of related memories."""
        compressed = 0
        tokens_saved = 0

        if not hasattr(memory_system, "episodic") or not hasattr(
            memory_system.episodic, "list_memories"
        ):
            return {"compressed": 0, "tokens_saved": 0}

        memories = await memory_system.episodic.list_memories(limit=100)
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)

        # Group old memories by content similarity (simple word overlap)
        old_memories = []
        for memory in memories:
            created = getattr(memory, "created_at", None)
            if created and isinstance(created, datetime) and created < cutoff:
                old_memories.append(memory)

        if len(old_memories) < 5:
            return {"compressed": 0, "tokens_saved": 0}

        # Group by importance level
        importance_groups = defaultdict(list)
        for memory in old_memories:
            importance = getattr(memory, "importance", 0.5)
            bucket = round(importance * 10) / 10  # Round to nearest 0.1
            importance_groups[bucket].append(memory)

        # Compress each group into a summary
        for _importance_level, group in importance_groups.items():
            if len(group) < 3:
                continue

            # Create summary
            contents = [getattr(m, "content", "") for m in group]
            sum(len(c) // 4 for c in contents)

            # Simple compression: keep most important, summarize rest
            group.sort(key=lambda m: getattr(m, "importance", 0.5), reverse=True)
            keep_count = max(1, len(group) // 3)

            for memory in group[keep_count:]:
                # Mark as compressed (reduce strength to indicate less detail needed)
                if hasattr(memory, "strength"):
                    memory.strength = memory.strength * 0.5
                compressed += 1
                tokens_saved += len(getattr(memory, "content", "")) // 4

        self.compression_count += compressed
        self.logger.info("memories_compressed", count=compressed, tokens_saved=tokens_saved)
        return {"compressed": compressed, "tokens_saved": tokens_saved}

    async def _integrate_knowledge(self, memory_system: Any, knowledge_graph: Any = None) -> int:
        """Integrate new knowledge with existing knowledge."""
        integrated = 0

        if not (hasattr(memory_system, "episodic") and hasattr(memory_system, "semantic")):
            return 0

        if not (
            hasattr(memory_system.episodic, "list_memories")
            and hasattr(memory_system.semantic, "list_memories")
        ):
            return 0

        episodic = await memory_system.episodic.list_memories(limit=20)
        semantic = await memory_system.semantic.list_memories(limit=20)

        # Link related memories by word overlap
        for e_memory in episodic:
            e_content = set(getattr(e_memory, "content", "").lower().split())
            for s_memory in semantic:
                s_content = set(getattr(s_memory, "content", "").lower().split())
                if not e_content or not s_content:
                    continue
                overlap = len(e_content & s_content) / max(1, len(e_content | s_content))
                if overlap > 0.3:
                    integrated += 1

        # Add concepts to knowledge graph if available
        if knowledge_graph and hasattr(knowledge_graph, "add_node"):
            for concept_name, concept_data in self.concepts.items():
                if hasattr(knowledge_graph, "nodes") and concept_name not in knowledge_graph.nodes:
                    knowledge_graph.add_node(
                        concept_name,
                        type="concept",
                        importance=concept_data.get("importance", 0.5),
                        metadata=concept_data,
                    )
                    integrated += 1

        self.logger.info("knowledge_integrated", count=integrated)
        return integrated

    async def _consolidate_working_to_longterm(self, memory_system: Any) -> None:
        """Move important working memory items to long-term storage."""
        if not hasattr(memory_system, "working"):
            return

        working = memory_system.working
        if not hasattr(working, "items") or not working.items:
            return

        # Move important items to episodic memory
        for item in list(working.items):
            content = item.get("content", "") if isinstance(item, dict) else str(item)
            metadata = item.get("metadata", {}) if isinstance(item, dict) else {}
            importance = metadata.get("importance", 0.5)

            # Only move high-importance items
            if importance > 0.6:
                if hasattr(memory_system, "episodic") and hasattr(
                    memory_system.episodic, "record_event"
                ):
                    await memory_system.episodic.record_event(
                        content=content,
                        metadata=metadata,
                        importance=importance,
                    )

        # Clear working memory
        if hasattr(working, "clear"):
            working.clear()

    def get_stats(self) -> dict:
        """Get consolidation statistics."""
        return {
            "total_consolidations": len(self.consolidation_log),
            "total_strengthened": self.strengthen_count,
            "total_forgotten": self.forget_count,
            "total_generalizations": len(self.generalizations),
            "total_concepts": len(self.concepts),
            "total_compressed": self.compression_count,
        }

    def to_context(self) -> str:
        """Convert consolidation state to context string."""
        stats = self.get_stats()
        lines = [
            "Sleep/Consolidation:",
            f"  Consolidations: {stats['total_consolidations']}",
            f"  Memories Strengthened: {stats['total_strengthened']}",
            f"  Memories Forgotten: {stats['total_forgotten']}",
            f"  Concepts Abstracted: {stats['total_concepts']}",
            f"  Memories Compressed: {stats['total_compressed']}",
        ]
        if self.concepts:
            lines.append(f"  Active Concepts: {', '.join(list(self.concepts.keys())[:5])}")
        return "\n".join(lines)
