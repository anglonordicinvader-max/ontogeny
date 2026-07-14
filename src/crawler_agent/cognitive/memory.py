"""Multi-layer persistent memory system."""

import json
import uuid
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog
from sqlalchemy import Column, String, Text, DateTime, JSON, Integer, Float, Boolean
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase


class MemoryType(str, Enum):
    EPISODIC = "episodic"      # What happened (events, experiences)
    SEMANTIC = "semantic"      # What is known (facts, knowledge)
    PROCEDURAL = "procedural"  # How to do things (skills, procedures)
    WORKING = "working"        # Current context (temporary)
    IDENTITY = "identity"      # Who I am (values, goals, personality)


class Base(DeclarativeBase):
    pass


class MemoryRecord(Base):
    """Database model for memories."""
    __tablename__ = "memories"

    id = Column(String, primary_key=True)
    memory_type = Column(String, index=True)
    content = Column(Text)
    metadata_ = Column("metadata", JSON, default=dict)
    embedding_id = Column(String, nullable=True)
    strength = Column(Float, default=1.0)  # Decay factor
    access_count = Column(Integer, default=0)
    last_accessed = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    importance = Column(Float, default=0.5)  # 0-1 importance score
    emotional_valence = Column(Float, default=0.0)  # -1 to 1
    context_tags = Column(JSON, default=list)
    consolidated = Column(Boolean, default=False)  # Moved to long-term


@dataclass
class Memory:
    """Memory entry."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    memory_type: MemoryType = MemoryType.WORKING
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    strength: float = 1.0
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    created_at: datetime = field(default_factory=datetime.utcnow)
    importance: float = 0.5
    emotional_valence: float = 0.0
    context_tags: list[str] = field(default_factory=list)
    consolidated: bool = False

    def to_record(self) -> MemoryRecord:
        return MemoryRecord(
            id=self.id,
            memory_type=self.memory_type.value,
            content=self.content,
            metadata_=self.metadata,
            strength=self.strength,
            access_count=self.access_count,
            last_accessed=self.last_accessed,
            created_at=self.created_at,
            importance=self.importance,
            emotional_valence=self.emotional_valence,
            context_tags=self.context_tags,
            consolidated=self.consolidated,
        )

    @classmethod
    def from_record(cls, record: MemoryRecord) -> "Memory":
        return cls(
            id=record.id,
            memory_type=MemoryType(record.memory_type),
            content=record.content,
            metadata=record.metadata_ or {},
            strength=record.strength,
            access_count=record.access_count,
            last_accessed=record.last_accessed,
            created_at=record.created_at,
            importance=record.importance,
            emotional_valence=record.emotional_valence,
            context_tags=record.context_tags or [],
            consolidated=record.consolidated,
        )


class EpisodicMemory:
    """Memory of events and experiences."""

    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.logger = structlog.get_logger()

    async def record_event(
        self,
        content: str,
        metadata: dict | None = None,
        importance: float = 0.5,
        emotional_valence: float = 0.0,
        tags: list[str] | None = None,
    ) -> Memory:
        """Record an episodic memory."""
        memory = Memory(
            memory_type=MemoryType.EPISODIC,
            content=content,
            metadata=metadata or {},
            importance=importance,
            emotional_valence=emotional_valence,
            context_tags=tags or [],
        )

        async with self.session_factory() as session:
            session.add(memory.to_record())
            await session.commit()

        self.logger.debug("episodic_recorded", id=memory.id, importance=importance)
        return memory

    async def recall(
        self,
        query: str | None = None,
        tags: list[str] | None = None,
        limit: int = 10,
        min_strength: float = 0.1,
    ) -> list[Memory]:
        """Recall episodic memories."""
        async with self.session_factory() as session:
            from sqlalchemy import select, and_

            stmt = select(MemoryRecord).where(
                and_(
                    MemoryRecord.memory_type == MemoryType.EPISODIC.value,
                    MemoryRecord.strength >= min_strength,
                )
            )

            if tags:
                stmt = stmt.where(MemoryRecord.context_tags.overlap(tags))

            stmt = stmt.order_by(
                MemoryRecord.importance.desc(),
                MemoryRecord.last_accessed.desc(),
            ).limit(limit)

            result = await session.execute(stmt)
            records = result.scalars().all()

            memories = []
            for record in records:
                memory = Memory.from_record(record)
                # Update access
                memory.access_count += 1
                memory.last_accessed = datetime.utcnow()
                record.access_count = memory.access_count
                record.last_accessed = memory.last_accessed
                memories.append(memory)

            await session.commit()
            return memories

    async def consolidate(self, memory_id: str) -> None:
        """Mark memory as consolidated (important enough to keep)."""
        async with self.session_factory() as session:
            record = await session.get(MemoryRecord, memory_id)
            if record:
                record.consolidated = True
                record.strength = min(1.0, record.strength + 0.2)
                await session.commit()

    async def decay(self, decay_rate: float = 0.01) -> int:
        """Apply memory decay to all unconsolidated memories."""
        async with self.session_factory() as session:
            from sqlalchemy import update, and_

            result = await session.execute(
                update(MemoryRecord)
                .where(
                    and_(
                        MemoryRecord.consolidated == False,
                        MemoryRecord.memory_type == MemoryType.EPISODIC.value,
                    )
                )
                .values(strength=MemoryRecord.strength * (1 - decay_rate))
            )
            await session.commit()
            return result.rowcount


class SemanticMemory:
    """Memory of facts and knowledge."""

    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.logger = structlog.get_logger()

    async def store_knowledge(
        self,
        fact: str,
        source: str = "",
        confidence: float = 1.0,
        metadata: dict | None = None,
    ) -> Memory:
        """Store a fact or piece of knowledge."""
        memory = Memory(
            memory_type=MemoryType.SEMANTIC,
            content=fact,
            metadata={
                "source": source,
                "confidence": confidence,
                **(metadata or {}),
            },
            importance=confidence,
        )

        async with self.session_factory() as session:
            session.add(memory.to_record())
            await session.commit()

        return memory

    async def query(
        self,
        topic: str | None = None,
        source: str | None = None,
        limit: int = 50,
    ) -> list[Memory]:
        """Query semantic memories."""
        async with self.session_factory() as session:
            from sqlalchemy import select, and_

            stmt = select(MemoryRecord).where(
                MemoryRecord.memory_type == MemoryType.SEMANTIC.value
            )

            if source:
                stmt = stmt.where(MemoryRecord.metadata_["source"].astext == source)

            stmt = stmt.order_by(MemoryRecord.importance.desc()).limit(limit)

            result = await session.execute(stmt)
            return [Memory.from_record(r) for r in result.scalars().all()]

    async def update_confidence(self, memory_id: str, new_confidence: float) -> None:
        """Update confidence in a fact."""
        async with self.session_factory() as session:
            record = await session.get(MemoryRecord, memory_id)
            if record:
                meta = record.metadata_ or {}
                meta["confidence"] = new_confidence
                record.metadata_ = meta
                record.importance = new_confidence
                await session.commit()


class ProceduralMemory:
    """Memory of skills and procedures."""

    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.logger = structlog.get_logger()

    async def store_skill(
        self,
        name: str,
        procedure: str,
        success_rate: float = 0.5,
        metadata: dict | None = None,
    ) -> Memory:
        """Store a skill or procedure."""
        memory = Memory(
            memory_type=MemoryType.PROCEDURAL,
            content=procedure,
            metadata={
                "skill_name": name,
                "success_rate": success_rate,
                "usage_count": 0,
                **(metadata or {}),
            },
            importance=success_rate,
        )

        async with self.session_factory() as session:
            session.add(memory.to_record())
            await session.commit()

        return memory

    async def get_skill(self, name: str) -> Memory | None:
        """Get a skill by name."""
        async with self.session_factory() as session:
            from sqlalchemy import select, and_

            stmt = select(MemoryRecord).where(
                and_(
                    MemoryRecord.memory_type == MemoryType.PROCEDURAL.value,
                    MemoryRecord.metadata_["skill_name"].astext == name,
                )
            )
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()
            return Memory.from_record(record) if record else None

    async def update_success_rate(self, memory_id: str, success: bool) -> None:
        """Update skill success rate."""
        async with self.session_factory() as session:
            record = await session.get(MemoryRecord, memory_id)
            if record:
                meta = record.metadata_ or {}
                old_rate = meta.get("success_rate", 0.5)
                count = meta.get("usage_count", 0)

                # Running average
                new_rate = (old_rate * count + (1.0 if success else 0.0)) / (count + 1)
                meta["success_rate"] = new_rate
                meta["usage_count"] = count + 1
                record.metadata_ = meta
                record.importance = new_rate
                await session.commit()

    async def list_skills(self) -> list[Memory]:
        """List all stored skills."""
        async with self.session_factory() as session:
            from sqlalchemy import select

            stmt = select(MemoryRecord).where(
                MemoryRecord.memory_type == MemoryType.PROCEDURAL.value
            )
            result = await session.execute(stmt)
            return [Memory.from_record(r) for r in result.scalars().all()]


class WorkingMemory:
    """Temporary working memory for current context."""

    def __init__(self, max_items: int = 50):
        self.items: list[Memory] = []
        self.max_items = max_items

    def add(self, content: str, metadata: dict | None = None) -> Memory:
        """Add to working memory."""
        memory = Memory(
            memory_type=MemoryType.WORKING,
            content=content,
            metadata=metadata or {},
        )
        self.items.append(memory)

        # Evict oldest if full
        if len(self.items) > self.max_items:
            self.items.pop(0)

        return memory

    def get_context(self, max_tokens: int = 4000) -> str:
        """Get working memory as context string."""
        context_parts = []
        total_tokens = 0

        for memory in reversed(self.items):
            text = f"[{memory.memory_type.value}] {memory.content}"
            estimated_tokens = len(text) // 4
            if total_tokens + estimated_tokens > max_tokens:
                break
            context_parts.append(text)
            total_tokens += estimated_tokens

        return "\n".join(reversed(context_parts))

    def clear(self) -> None:
        """Clear working memory."""
        self.items.clear()

    def search(self, query: str) -> list[Memory]:
        """Simple text search in working memory."""
        query_lower = query.lower()
        return [m for m in self.items if query_lower in m.content.lower()]


class IdentityMemory:
    """Memory of self - values, goals, personality."""

    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.logger = structlog.get_logger()

    async def set_value(self, key: str, value: Any) -> None:
        """Set an identity value."""
        async with self.session_factory() as session:
            memory = Memory(
                memory_type=MemoryType.IDENTITY,
                content=json.dumps(value),
                metadata={"key": key, "type": type(value).__name__},
                importance=1.0,
                consolidated=True,
            )
            session.add(memory.to_record())
            await session.commit()

    async def get_value(self, key: str) -> Any | None:
        """Get an identity value."""
        async with self.session_factory() as session:
            from sqlalchemy import select, and_

            stmt = select(MemoryRecord).where(
                and_(
                    MemoryRecord.memory_type == MemoryType.IDENTITY.value,
                    MemoryRecord.metadata_["key"].astext == key,
                )
            )
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()

            if record:
                return json.loads(record.content)
            return None

    async def get_all_values(self) -> dict[str, Any]:
        """Get all identity values."""
        async with self.session_factory() as session:
            from sqlalchemy import select

            stmt = select(MemoryRecord).where(
                MemoryRecord.memory_type == MemoryType.IDENTITY.value
            )
            result = await session.execute(stmt)

            values = {}
            for record in result.scalars():
                key = (record.metadata_ or {}).get("key")
                if key:
                    values[key] = json.loads(record.content)

            return values


class MemorySystem:
    """Unified multi-layer memory system."""

    def __init__(self, database_url: str):
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

        self.engine = create_async_engine(database_url)
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession)

        self.episodic = EpisodicMemory(self.session_factory)
        self.semantic = SemanticMemory(self.session_factory)
        self.procedural = ProceduralMemory(self.session_factory)
        self.working = WorkingMemory()
        self.identity = IdentityMemory(self.session_factory)

        self.logger = structlog.get_logger()

    async def initialize(self) -> None:
        """Create memory tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.logger.info("memory_system_initialized")

    async def record_experience(
        self,
        event: str,
        outcome: str,
        learning: str | None = None,
        importance: float = 0.5,
    ) -> Memory:
        """Record a complete experience (episodic + optional semantic)."""
        # Record episode
        episode = await self.episodic.record_event(
            content=f"Event: {event}\nOutcome: {outcome}",
            importance=importance,
            tags=["experience"],
        )

        # Extract learning as semantic knowledge
        if learning:
            await self.semantic.store_knowledge(
                fact=learning,
                source="experience",
                confidence=importance,
            )

        return episode

    async def recall_relevant(
        self,
        context: str,
        limit: int = 10,
    ) -> dict[str, list[Memory]]:
        """Recall memories relevant to a context."""
        episodic = await self.episodic.recall(limit=limit // 2)
        semantic = await self.semantic.query(limit=limit // 2)

        return {
            "episodic": episodic,
            "semantic": semantic,
            "working": self.working.search(context),
        }

    async def get_context_window(self, max_tokens: int = 4000) -> str:
        """Build context window from all memory layers."""
        parts = []

        # Identity
        values = await self.identity.get_all_values()
        if values:
            identity_str = json.dumps(values, indent=2)
            parts.append(f"[IDENTITY]\n{identity_str}")

        # Working memory
        working = self.working.get_context(max_tokens // 2)
        if working:
            parts.append(f"[WORKING MEMORY]\n{working}")

        # Recent episodic
        recent = await self.episodic.recall(limit=5)
        if recent:
            episodic_str = "\n".join(f"- {m.content[:200]}" for m in recent)
            parts.append(f"[RECENT EXPERIENCES]\n{episodic_str}")

        # Relevant semantic
        semantic = await self.semantic.query(limit=10)
        if semantic:
            semantic_str = "\n".join(f"- {m.content[:200]}" for m in semantic)
            parts.append(f"[KNOWLEDGE]\n{semantic_str}")

        # Skills
        skills = await self.procedural.list_skills()
        if skills:
            skills_str = "\n".join(
                f"- {m.metadata.get('skill_name', 'unknown')}: {m.content[:100]}"
                for m in skills[:5]
            )
            parts.append(f"[SKILLS]\n{skills_str}")

        context = "\n\n".join(parts)

        # Truncate if too long
        if len(context) > max_tokens * 4:
            context = context[:max_tokens * 4]

        return context

    async def close(self) -> None:
        """Close database connections."""
        await self.engine.dispose()
