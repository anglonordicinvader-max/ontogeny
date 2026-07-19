"""Focused learning mode - quality over quantity."""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, StrEnum
from typing import Any

import structlog

from ..crawlers.base import ContentType, CrawlResult
from ..processing.embeddings import EmbeddingGenerator
from ..processing.llm import LLMProcessor
from .memory import MemorySystem


class LearningMode(StrEnum):
    FOCUSED = "focused"  # Deep processing, few sources
    BALANCED = "balanced"  # Mix of depth and breadth
    EXPLORATORY = "exploratory"  # Wide coverage, lighter processing
    INTENSIVE = "intensive"  # Deep dive on single topic


@dataclass
class SourceQuality:
    """Track quality metrics for a source."""

    url: str
    name: str
    domain: str
    avg_quality: float = 0.5
    total_crawled: int = 0
    useful_count: int = 0
    last_crawled: datetime | None = None
    crawl_frequency: timedelta = field(default_factory=lambda: timedelta(hours=6))
    priority: int = 5  # 1-10, higher = more important
    tags: list[str] = field(default_factory=list)

    @property
    def usefulness_score(self) -> float:
        if self.total_crawled == 0:
            return 0.5
        return self.useful_count / self.total_crawled

    @property
    def should_crawl(self) -> bool:
        if not self.last_crawled:
            return True
        return datetime.utcnow() - self.last_crawled > self.crawl_frequency


@dataclass
class LearningSession:
    """A focused learning session."""

    id: str
    topic: str
    mode: LearningMode
    sources: list[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: datetime | None = None
    items_processed: int = 0
    knowledge_gained: float = 0.0
    insights: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class FocusedLearner:
    """Quality-focused learning engine."""

    def __init__(
        self,
        llm: LLMProcessor,
        memory: MemorySystem,
        embedder: EmbeddingGenerator,
    ):
        self.llm = llm
        self.memory = memory
        self.embedder = embedder
        self.logger = structlog.get_logger()

        # Source registry
        self.sources: dict[str, SourceQuality] = {}
        self._init_high_value_sources()

        # Learning sessions
        self.sessions: list[LearningSession] = []
        self.current_session: LearningSession | None = None

    def _init_high_value_sources(self) -> None:
        """Initialize high-value source registry."""
        high_value = [
            # Code & AI
            SourceQuality("github.com", "GitHub", "github.com", priority=9, tags=["code", "ai"]),
            SourceQuality(
                "huggingface.co", "HuggingFace", "huggingface.co", priority=9, tags=["ai", "models"]
            ),
            SourceQuality(
                "arxiv.org", "arXiv", "arxiv.org", priority=8, tags=["research", "papers"]
            ),
            SourceQuality(
                "papers.semanticscholar.org",
                "Semantic Scholar",
                "semanticscholar.org",
                priority=8,
                tags=["research"],
            ),
            # Knowledge
            SourceQuality(
                "en.wikipedia.org",
                "Wikipedia",
                "wikipedia.org",
                priority=7,
                tags=["knowledge", "reference"],
            ),
            SourceQuality(
                "stackoverflow.com",
                "Stack Overflow",
                "stackoverflow.com",
                priority=7,
                tags=["programming", "qa"],
            ),
            # News & Community
            SourceQuality(
                "news.ycombinator.com",
                "Hacker News",
                "hackernews.com",
                priority=6,
                tags=["tech", "news"],
            ),
            SourceQuality(
                "reddit.com", "Reddit", "reddit.com", priority=5, tags=["community", "discussion"]
            ),
            # Documentation
            SourceQuality(
                "docs.python.org", "Python Docs", "python.org", priority=7, tags=["docs", "python"]
            ),
            SourceQuality(
                "developer.mozilla.org", "MDN", "mozilla.org", priority=7, tags=["docs", "web"]
            ),
        ]

        for source in high_value:
            self.sources[source.domain] = source

    def register_source(
        self,
        url: str,
        name: str,
        priority: int = 5,
        tags: list[str] | None = None,
    ) -> None:
        """Register a new source."""
        from urllib.parse import urlparse

        domain = urlparse(url).netloc

        self.sources[domain] = SourceQuality(
            url=url,
            name=name,
            domain=domain,
            priority=priority,
            tags=tags or [],
        )

    async def start_session(
        self,
        topic: str,
        mode: LearningMode = LearningMode.FOCUSED,
        max_items: int = 10,
    ) -> LearningSession:
        """Start a focused learning session."""
        session = LearningSession(
            id=f"session_{datetime.utcnow().timestamp()}",
            topic=topic,
            mode=mode,
        )
        self.current_session = session
        self.sessions.append(session)

        self.logger.info(
            "learning_session_started",
            session_id=session.id,
            topic=topic,
            mode=mode.value,
        )
        return session

    async def learn_from_source(
        self,
        result: CrawlResult,
        deep_process: bool = True,
    ) -> dict[str, Any]:
        """Learn from a single piece of content."""
        learning = {
            "source": result.source,
            "title": result.title,
            "quality": 0.0,
            "insights": [],
            "knowledge": "",
            "memory_stored": False,
        }

        # Update source quality
        domain = result.url.split("/")[2] if "/" in result.url else result.url
        if domain in self.sources:
            self.sources[domain].total_crawled += 1
            self.sources[domain].last_crawled = datetime.utcnow()

        if deep_process:
            # Deep LLM processing
            quality = await self._assess_quality(result)
            learning["quality"] = quality

            if quality > 0.6:  # Only process high-quality content
                # Extract insights
                insights = await self._extract_insights(result)
                learning["insights"] = insights

                # Generate knowledge summary
                knowledge = await self._generate_knowledge(result)
                learning["knowledge"] = knowledge

                # Store in memory
                await self._integrate_to_memory(result, insights, knowledge)
                learning["memory_stored"] = True

                # Update source usefulness
                if domain in self.sources:
                    self.sources[domain].useful_count += 1

                # Record experience
                await self.memory.record_experience(
                    event=f"Learned from {result.title}",
                    outcome=f"Generated {len(insights)} insights",
                    learning=knowledge[:500],
                    importance=quality,
                )

                if self.current_session:
                    self.current_session.items_processed += 1
                    self.current_session.knowledge_gained += quality
                    self.current_session.insights.extend(insights[:3])

        return learning

    async def _assess_quality(self, result: CrawlResult) -> float:
        """Assess content quality using LLM."""
        assessment = await self.llm.extract_metadata(
            f"{result.title}\n{result.content[:2000]}",
            result.content_type.value,
        )
        return assessment.get("quality_score", 0.5) / 10.0

    async def _extract_insights(self, result: CrawlResult) -> list[str]:
        """Extract key insights from content."""
        response = await self.llm.client.chat.completions.create(
            model=self.llm.model,
            messages=[
                {
                    "role": "system",
                    "content": """Extract key insights from this content. Be concise and specific.
Return JSON with: insights (list of strings, max 5)""",
                },
                {
                    "role": "user",
                    "content": f"Title: {result.title}\n\nContent:\n{result.content[:4000]}",
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=500,
        )

        import json

        try:
            data = json.loads(response.choices[0].message.content or "{}")
            return data.get("insights", [])[:5]
        except Exception:
            return []

    async def _generate_knowledge(self, result: CrawlResult) -> str:
        """Generate condensed knowledge from content."""
        response = await self.llm.client.chat.completions.create(
            model=self.llm.model,
            messages=[
                {
                    "role": "system",
                    "content": "Create a concise knowledge summary suitable for long-term memory storage. Focus on facts, patterns, and relationships.",
                },
                {
                    "role": "user",
                    "content": f"Summarize for knowledge storage:\n\nTitle: {result.title}\nType: {result.content_type.value}\nContent:\n{result.content[:4000]}",
                },
            ],
            max_tokens=500,
        )
        return response.choices[0].message.content or ""

    async def _integrate_to_memory(
        self,
        result: CrawlResult,
        insights: list[str],
        knowledge: str,
    ) -> None:
        """Integrate learning to memory system."""
        # Store as semantic knowledge
        await self.memory.semantic.store_knowledge(
            fact=knowledge,
            source=result.source,
            confidence=0.8,
            metadata={
                "url": result.url,
                "title": result.title,
                "content_type": result.content_type.value,
                "insights": insights,
            },
        )

        # Store insights as episodic
        for insight in insights:
            await self.memory.episodic.record_event(
                content=f"Insight from {result.title}: {insight}",
                importance=0.7,
                tags=["insight", result.source],
            )

    async def get_priority_sources(self, limit: int = 5) -> list[SourceQuality]:
        """Get sources that should be crawled next."""
        candidates = [s for s in self.sources.values() if s.should_crawl]

        # Sort by priority and usefulness
        candidates.sort(
            key=lambda s: s.priority * 0.6 + s.usefulness_score * 0.4,
            reverse=True,
        )

        return candidates[:limit]

    async def run_focused_session(
        self,
        topic: str,
        max_items: int = 10,
        min_quality: float = 0.6,
    ) -> dict[str, Any]:
        """Run a complete focused learning session."""
        session = await self.start_session(topic, LearningMode.FOCUSED, max_items)

        # Get relevant sources
        sources = await self.get_priority_sources(limit=3)

        results = []
        for source in sources:
            if session.items_processed >= max_items:
                break

            self.logger.info("crawling_source", source=source.name, topic=topic)

            # This would be called from the orchestrator's crawlers
            # For now, return the session info
            results.append(
                {
                    "source": source.name,
                    "priority": source.priority,
                    "topic": topic,
                }
            )

        session.end_time = datetime.utcnow()

        return {
            "session_id": session.id,
            "topic": topic,
            "items_processed": session.items_processed,
            "knowledge_gained": session.knowledge_gained,
            "insights": session.insights,
            "sources_used": [s.name for s in sources],
        }

    def get_stats(self) -> dict[str, Any]:
        """Get learning statistics."""
        return {
            "total_sources": len(self.sources),
            "high_priority": sum(1 for s in self.sources.values() if s.priority >= 7),
            "total_sessions": len(self.sessions),
            "active_session": self.current_session.id if self.current_session else None,
            "avg_quality": sum(s.avg_quality for s in self.sources.values())
            / max(len(self.sources), 1),
        }
