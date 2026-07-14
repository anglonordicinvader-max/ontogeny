"""Sleep/consolidation module - offline memory processing.

Simulates sleep-like memory consolidation: replays experiences,
strengthens important memories, weakens unimportant ones, and
extracts generalizations.
"""

import random
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

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


class SleepConsolidator:
    """Simulates sleep-like memory consolidation.

    During "sleep" (background processing):
    1. Replays recent experiences
    2. Strengthens important memories
    3. Weakens/forgets unimportant ones
    4. Extracts generalizations
    5. Integrates new knowledge with existing
    """

    def __init__(self):
        self.consolidation_log: list[dict[str, Any]] = []
        self.generalizations: list[dict[str, Any]] = []
        self.forget_count = 0
        self.strengthen_count = 0
        self.logger = structlog.get_logger()

    async def consolidate(
        self,
        memory_system: Any,
        patterns: Any = None,
        importance_threshold: float = 0.3,
    ) -> dict[str, Any]:
        """Run consolidation cycle."""
        self.logger.info("consolidation_started")

        # 1. Replay recent experiences
        replayed = await self._replay_experiences(memory_system)

        # 2. Strengthen important memories
        strengthened = await self._strengthen_memories(
            memory_system, importance_threshold
        )

        # 3. Forget weak memories
        forgotten = await self._forget_weak(memory_system, importance_threshold)

        # 4. Extract generalizations
        new_generalizations = await self._extract_generalizations(
            memory_system, patterns
        )

        # 5. Integrate new with existing
        integrated = await self._integrate_knowledge(memory_system)

        result = {
            "replayed": replayed,
            "strengthened": strengthened,
            "forgotten": forgotten,
            "generalizations": len(new_generalizations),
            "integrated": integrated,
        }

        self.consolidation_log.append(result)
        self.logger.info("consolidation_complete", result=result)
        return result

    async def _replay_experiences(self, memory_system: Any) -> int:
        """Replay recent experiences to strengthen memory traces."""
        # Get recent episodic memories
        recent = []
        if hasattr(memory_system, 'episodic'):
            if hasattr(memory_system.episodic, 'list_memories'):
                recent = await memory_system.episodic.list_memories(limit=20)

        replayed = 0
        for memory in recent:
            # Replay by accessing (increases strength)
            if hasattr(memory, 'access_count'):
                memory.access_count += 1
                replayed += 1

        return replayed

    async def _strengthen_memories(
        self,
        memory_system: Any,
        threshold: float,
    ) -> int:
        """Strengthen memories above importance threshold."""
        strengthened = 0

        # Strengthen episodic
        if hasattr(memory_system, 'episodic'):
            if hasattr(memory_system.episodic, 'list_memories'):
                memories = await memory_system.episodic.list_memories(limit=50)
                for memory in memories:
                    importance = getattr(memory, 'importance', 0.5)
                    if importance > threshold:
                        old_strength = getattr(memory, 'strength', 1.0)
                        memory.strength = min(2.0, old_strength * 1.1)
                        strengthened += 1

        # Strengthen semantic
        if hasattr(memory_system, 'semantic'):
            if hasattr(memory_system.semantic, 'list_memories'):
                memories = await memory_system.semantic.list_memories(limit=50)
                for memory in memories:
                    importance = getattr(memory, 'importance', 0.5)
                    if importance > threshold:
                        old_strength = getattr(memory, 'strength', 1.0)
                        memory.strength = min(2.0, old_strength * 1.1)
                        strengthened += 1

        self.strengthen_count += strengthened
        return strengthened

    async def _forget_weak(
        self,
        memory_system: Any,
        threshold: float,
    ) -> int:
        """Forget memories below strength threshold."""
        forgotten = 0
        weak_threshold = threshold * 0.5

        # Check episodic
        if hasattr(memory_system, 'episodic'):
            if hasattr(memory_system.episodic, 'list_memories'):
                memories = await memory_system.episodic.list_memories(limit=100)
                for memory in memories:
                    strength = getattr(memory, 'strength', 1.0)
                    if strength < weak_threshold:
                        # Mark for forgetting (don't actually delete, just decay)
                        memory.strength = strength * 0.5
                        forgotten += 1

        self.forget_count += forgotten
        return forgotten

    async def _extract_generalizations(
        self,
        memory_system: Any,
        patterns: Any = None,
    ) -> list[dict[str, Any]]:
        """Extract generalizations from specific experiences."""
        new_generalizations = []

        # Look for recurring themes in episodic memory
        if hasattr(memory_system, 'episodic'):
            if hasattr(memory_system.episodic, 'list_memories'):
                memories = await memory_system.episodic.list_memories(limit=50)

                # Simple frequency-based generalization
                word_counts = defaultdict(int)
                for memory in memories:
                    content = getattr(memory, 'content', '')
                    words = content.lower().split()
                    for word in words:
                        if len(word) > 4:  # Skip short words
                            word_counts[word] += 1

                # Find common concepts
                common = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
                for word, count in common[:5]:
                    if count > 5:
                        generalization = {
                            "concept": word,
                            "frequency": count,
                            "source_count": len(memories),
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                        new_generalizations.append(generalization)
                        self.generalizations.append(generalization)

        return new_generalizations

    async def _integrate_knowledge(self, memory_system: Any) -> int:
        """Integrate new knowledge with existing knowledge."""
        integrated = 0

        # Link related memories
        if hasattr(memory_system, 'episodic') and hasattr(memory_system, 'semantic'):
            if (hasattr(memory_system.episodic, 'list_memories') and
                hasattr(memory_system.semantic, 'list_memories')):
                episodic = await memory_system.episodic.list_memories(limit=20)
                semantic = await memory_system.semantic.list_memories(limit=20)

                # Simple similarity-based linking
                for e_memory in episodic:
                    e_content = getattr(e_memory, 'content', '').lower()
                    for s_memory in semantic:
                        s_content = getattr(s_memory, 'content', '').lower()
                        # Check word overlap
                        e_words = set(e_content.split())
                        s_words = set(s_content.split())
                        overlap = len(e_words & s_words) / max(1, len(e_words | s_words))
                        if overlap > 0.3:
                            integrated += 1

        return integrated

    def get_stats(self) -> dict[str, Any]:
        """Get consolidation statistics."""
        return {
            "total_consolidations": len(self.consolidation_log),
            "total_strengthened": self.strengthen_count,
            "total_forgotten": self.forget_count,
            "total_generalizations": len(self.generalizations),
        }

    def to_context(self) -> str:
        """Convert consolidation state to context string."""
        stats = self.get_stats()
        lines = [
            "Sleep/Consolidation:",
            f"  Consolidations: {stats['total_consolidations']}",
            f"  Memories Strengthened: {stats['total_strengthened']}",
            f"  Memories Forgotten: {stats['total_forgotten']}",
            f"  Generalizations: {stats['total_generalizations']}",
        ]
        return "\n".join(lines)
