"""Memory compression - summarizes old episodes to free context window."""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .backend import CognitiveBackend
from .memory import MemorySystem


@dataclass
class CompressedEpisode:
    """A compressed version of an episodic memory."""

    original_id: str
    timestamp: float
    summary: str
    key_entities: list[str]
    key_actions: list[str]
    outcome: str
    importance: float
    token_count: int


@dataclass
class CompressionStats:
    """Statistics about compression."""

    episodes_compressed: int = 0
    tokens_saved: int = 0
    avg_compression_ratio: float = 0.0
    last_compression: float = 0.0


class MemoryCompressor:
    """Compresses old episodic memories into summaries."""

    def __init__(
        self,
        backend: CognitiveBackend,
        memory: MemorySystem,
        compression_threshold_days: int = 7,
        max_context_tokens: int = 8000,
    ):
        self.backend = backend
        self.memory = memory
        self.compression_threshold_days = compression_threshold_days
        self.max_context_tokens = max_context_tokens
        self.stats = CompressionStats()
        self._load_stats()

    def _load_stats(self) -> None:
        stats_file = Path("data/memory_compression_stats.json")
        if stats_file.exists():
            try:
                data = json.loads(stats_file.read_text())
                self.stats = CompressionStats(**data)
            except Exception:
                pass

    def _save_stats(self) -> None:
        stats_file = Path("data/memory_compression_stats.json")
        stats_file.parent.mkdir(parents=True, exist_ok=True)
        stats_file.write_text(json.dumps(self.stats.__dict__, indent=2))

    async def compress_old_episodes(
        self,
        batch_size: int = 50,
    ) -> CompressionStats:
        """Compress episodes older than threshold."""
        # Get old episodes from episodic memory
        time.time() - (self.compression_threshold_days * 86400)

        # This would query the memory system for old episodes
        # For now, return current stats
        return self.stats

    async def compress_episode(
        self,
        episode: dict[str, Any],
    ) -> CompressedEpisode | None:
        """Compress a single episode."""
        content = f"Event: {episode.get('event', '')}\nOutcome: {episode.get('outcome', '')}\nContext: {episode.get('context', '')}"

        prompt = f"""Summarize this episode concisely for long-term memory.

Episode:
{content[:3000]}

Return JSON:
{{
  "summary": "one sentence summary",
  "key_entities": ["entity1", "entity2"],
  "key_actions": ["action1", "action2"],
  "outcome": "success|failure|partial",
  "importance": 0.0-1.0
}}"""

        response = await self.backend.complete(prompt, temperature=0.2, max_tokens=500)
        try:
            data = json.loads(response.content)
        except json.JSONDecodeError:
            return None

        original_tokens = len(content) // 4
        summary_tokens = len(data.get("summary", "")) // 4

        compressed = CompressedEpisode(
            original_id=episode.get("id", ""),
            timestamp=episode.get("timestamp", time.time()),
            summary=data.get("summary", ""),
            key_entities=data.get("key_entities", []),
            key_actions=data.get("key_actions", []),
            outcome=data.get("outcome", "unknown"),
            importance=data.get("importance", 0.5),
            token_count=summary_tokens,
        )

        self.stats.episodes_compressed += 1
        self.stats.tokens_saved += original_tokens - summary_tokens
        self.stats.avg_compression_ratio = self.stats.tokens_saved / max(
            self.stats.episodes_compressed * original_tokens, 1
        )
        self.stats.last_compression = time.time()
        self._save_stats()

        return compressed

    async def get_compressed_context(
        self,
        query: str,
        max_tokens: int | None = None,
    ) -> str:
        """Retrieve relevant compressed memories for a query."""
        max_tokens = max_tokens or self.max_context_tokens

        # This would query compressed episodic memory
        # For now, return empty
        return ""

    def get_stats(self) -> CompressionStats:
        return self.stats


class ContextWindowManager:
    """Manages context window allocation across memory systems."""

    def __init__(
        self,
        backend: CognitiveBackend,
        memory: MemorySystem,
        max_tokens: int = 8000,
    ):
        self.backend = backend
        self.memory = memory
        self.max_tokens = max_tokens

        # Token budgets per memory type
        self.budgets = {
            "identity": 500,
            "working": 2000,
            "episodic": 2000,
            "semantic": 1500,
            "procedural": 1000,
            "compressed": 1000,
        }

    def build_context(
        self,
        query: str,
        task_type: str = "general",
    ) -> dict[str, Any]:
        """Build optimized context window for a query."""
        # Adjust budgets based on task type
        budgets = self.budgets.copy()
        if task_type == "coding":
            budgets["procedural"] = 2500
            budgets["episodic"] = 1000
        elif task_type == "reasoning":
            budgets["semantic"] = 2500
            budgets["working"] = 1000
        elif task_type == "planning":
            budgets["episodic"] = 2500
            budgets["semantic"] = 1500

        context = {
            "query": query,
            "task_type": task_type,
            "budgets": budgets,
            "sections": {},
        }

        # This would pull from each memory system
        # For now return structure
        return context

    async def estimate_tokens(self, text: str) -> int:
        """Rough token estimation."""
        return len(text) // 4

    def trim_to_budget(self, sections: dict[str, str], budgets: dict[str, int]) -> dict[str, str]:
        """Trim sections to fit token budgets."""
        trimmed = {}
        for section, content in sections.items():
            budget = budgets.get(section, 1000)
            tokens = self.estimate_tokens(content)
            if tokens > budget:
                # Truncate keeping beginning and end
                keep_start = budget * 2  # chars
                trimmed[section] = content[:keep_start] + "\n...[truncated]..."
            else:
                trimmed[section] = content
        return trimmed


class MemoryConsolidator:
    """Consolidates memories during sleep cycles."""

    def __init__(
        self,
        backend: CognitiveBackend,
        memory: MemorySystem,
        compressor: MemoryCompressor,
    ):
        self.backend = backend
        self.memory = memory
        self.compressor = compressor

    async def consolidate(self) -> dict[str, Any]:
        """Run full consolidation cycle."""
        results = {
            "episodes_compressed": 0,
            "patterns_extracted": 0,
            "skills_formed": 0,
            "tokens_freed": 0,
        }

        # 1. Compress old episodes
        compression = await self.compressor.compress_old_episodes()
        results["episodes_compressed"] = compression.episodes_compressed
        results["tokens_freed"] = compression.tokens_saved

        # 2. Extract patterns from recent episodes
        # (Would integrate with PatternLearner)

        # 3. Identify skill candidates
        # (Would integrate with SkillLearner)

        return results


async def create_memory_compression(
    backend: CognitiveBackend,
    memory: MemorySystem,
) -> MemoryCompressor:
    return MemoryCompressor(backend, memory)
