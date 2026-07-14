"""PostgreSQL storage for crawled data."""

from datetime import datetime
from typing import AsyncIterator

import structlog
from sqlalchemy import (
    Column, String, Text, DateTime, JSON, Integer, Float,
    create_engine, select, and_
)
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine
)
from sqlalchemy.orm import DeclarativeBase

from ..crawlers.base import CrawlResult


class Base(DeclarativeBase):
    pass


class CrawlRecord(Base):
    """Database model for crawled content."""
    __tablename__ = "crawl_records"

    url = Column(String, primary_key=True)
    content_type = Column(String, index=True)
    title = Column(Text, default="")
    content = Column(Text, default="")
    metadata_ = Column("metadata", JSON, default=dict)
    source = Column(String, index=True)
    checksum = Column(String, index=True)
    crawled_at = Column(DateTime, default=datetime.utcnow)
    processed = Column(Integer, default=0)  # 0=pending, 1=processed, 2=failed
    embedding_id = Column(String, nullable=True)


class CrawlStats(Base):
    """Crawl statistics."""
    __tablename__ = "crawl_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String, index=True)
    date = Column(DateTime, index=True)
    total_crawled = Column(Integer, default=0)
    total_errors = Column(Integer, default=0)
    avg_response_time = Column(Float, default=0.0)


class Database:
    """Async PostgreSQL storage."""

    def __init__(self, database_url: str):
        self.engine = create_async_engine(database_url, echo=False)
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession)
        self.logger = structlog.get_logger()

    async def initialize(self) -> None:
        """Create tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.logger.info("database_initialized")

    async def close(self) -> None:
        """Close connections."""
        await self.engine.dispose()

    async def store(self, result: CrawlResult) -> None:
        """Store a crawl result."""
        async with self.session_factory() as session:
            record = CrawlRecord(
                url=result.url,
                content_type=result.content_type.value,
                title=result.title,
                content=result.content,
                metadata_=result.metadata,
                source=result.source,
                checksum=result.checksum,
                crawled_at=result.crawled_at,
            )
            await session.merge(record)
            await session.commit()

    async def store_batch(self, results: list[CrawlResult]) -> None:
        """Store multiple results."""
        async with self.session_factory() as session:
            for result in results:
                record = CrawlRecord(
                    url=result.url,
                    content_type=result.content_type.value,
                    title=result.title,
                    content=result.content,
                    metadata_=result.metadata,
                    source=result.source,
                    checksum=result.checksum,
                    crawled_at=result.crawled_at,
                )
                await session.merge(record)
            await session.commit()

    async def get(self, url: str) -> CrawlResult | None:
        """Get a record by URL."""
        async with self.session_factory() as session:
            result = await session.get(CrawlRecord, url)
            if result:
                return CrawlResult(
                    url=result.url,
                    content_type=result.content_type,
                    title=result.title,
                    content=result.content,
                    metadata=result.metadata_,
                    source=result.source,
                    checksum=result.checksum,
                    crawled_at=result.crawled_at,
                )
            return None

    async def search(
        self,
        query: str | None = None,
        source: str | None = None,
        content_type: str | None = None,
        limit: int = 100,
    ) -> AsyncIterator[CrawlResult]:
        """Search records."""
        async with self.session_factory() as session:
            stmt = select(CrawlRecord)
            conditions = []

            if query:
                conditions.append(
                    CrawlRecord.title.ilike(f"%{query}%") |
                    CrawlRecord.content.ilike(f"%{query}%")
                )
            if source:
                conditions.append(CrawlRecord.source == source)
            if content_type:
                conditions.append(CrawlRecord.content_type == content_type)

            if conditions:
                stmt = stmt.where(and_(*conditions))

            stmt = stmt.order_by(CrawlRecord.crawled_at.desc()).limit(limit)

            result = await session.execute(stmt)
            for record in result.scalars():
                yield CrawlResult(
                    url=record.url,
                    content_type=record.content_type,
                    title=record.title,
                    content=record.content,
                    metadata=record.metadata_,
                    source=record.source,
                    checksum=record.checksum,
                    crawled_at=record.crawled_at,
                )

    async def get_unprocessed(self, limit: int = 100) -> list[CrawlResult]:
        """Get records pending processing."""
        async with self.session_factory() as session:
            stmt = (
                select(CrawlRecord)
                .where(CrawlRecord.processed == 0)
                .order_by(CrawlRecord.crawled_at)
                .limit(limit)
            )
            result = await session.execute(stmt)
            records = result.scalars().all()

            return [
                CrawlResult(
                    url=r.url,
                    content_type=r.content_type,
                    title=r.title,
                    content=r.content,
                    metadata=r.metadata_,
                    source=r.source,
                    checksum=r.checksum,
                    crawled_at=r.crawled_at,
                )
                for r in records
            ]

    async def mark_processed(self, url: str, embedding_id: str | None = None) -> None:
        """Mark record as processed."""
        async with self.session_factory() as session:
            record = await session.get(CrawlRecord, url)
            if record:
                record.processed = 1
                record.embedding_id = embedding_id
                await session.commit()

    async def mark_failed(self, url: str) -> None:
        """Mark record as failed."""
        async with self.session_factory() as session:
            record = await session.get(CrawlRecord, url)
            if record:
                record.processed = 2
                await session.commit()

    async def get_stats(self) -> dict:
        """Get crawl statistics."""
        async with self.session_factory() as session:
            from sqlalchemy import func

            total = await session.scalar(select(func.count(CrawlRecord.url)))
            by_source = await session.execute(
                select(CrawlRecord.source, func.count(CrawlRecord.url))
                .group_by(CrawlRecord.source)
            )
            processed = await session.scalar(
                select(func.count(CrawlRecord.url)).where(CrawlRecord.processed == 1)
            )

            return {
                "total_records": total,
                "processed": processed,
                "by_source": dict(by_source.all()),
            }
