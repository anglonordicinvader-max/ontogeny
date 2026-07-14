"""Stack Overflow crawler using SE API."""

from typing import AsyncIterator
from datetime import datetime

import httpx
import structlog

from .base import BaseCrawler, CrawlerConfig, CrawlResult, ContentType


class StackOverflowCrawler(BaseCrawler):
    """Crawler for Stack Overflow questions and answers."""

    def __init__(
        self,
        api_key: str = "",
        config: CrawlerConfig | None = None,
        **kwargs,
    ):
        super().__init__("stackoverflow", config, **kwargs)
        self.api_key = api_key
        self.api_url = "https://api.stackexchange.com/2.3"
        # SE API: 300 requests/day without key, 10000 with key
        self.rate_limiter.rate = 0.5

    async def _setup(self) -> None:
        pass

    async def _cleanup(self) -> None:
        pass

    async def crawl(
        self,
        url: str,
        depth: int = 0,
        content_types: list[str] | None = None,
    ) -> AsyncIterator[CrawlResult]:
        # Extract question ID from URL
        parts = url.rstrip("/").split("/")
        if "questions" in parts:
            idx = parts.index("questions")
            if idx + 1 < len(parts):
                question_id = parts[idx + 1].split("-")[0]
                async for result in self._fetch_question(int(question_id)):
                    yield result

    async def _fetch_question(self, question_id: int) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()

        params = {
            "filter": "withbody",
            "site": "stackoverflow",
        }
        if self.api_key:
            params["key"] = self.api_key

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/questions/{question_id}",
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            questions = data.get("items", [])

            if questions:
                q = questions[0]
                yield CrawlResult(
                    url=q["link"],
                    content_type=ContentType.DISCUSSION,
                    title=q["title"],
                    content=q.get("body_markdown", q.get("body", "")),
                    metadata={
                        "score": q["score"],
                        "answer_count": q["answer_count"],
                        "tags": q.get("tags", []),
                        "view_count": q.get("view_count", 0),
                        "is_answered": q.get("is_answered", False),
                        "accepted_answer_id": q.get("accepted_answer_id"),
                        "created_at": datetime.fromtimestamp(q["creation_date"]).isoformat(),
                        "last_activity": datetime.fromtimestamp(q["last_activity_date"]).isoformat(),
                    },
                    source="stackoverflow",
                )

    async def search(
        self,
        query: str,
        tags: list[str] | None = None,
        sort: str = "relevance",
        limit: int = 50,
    ) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()

        params = {
            "intitle": query,
            "sort": sort,
            "order": "desc",
            "site": "stackoverflow",
            "filter": "withbody",
            "pagesize": min(limit, 100),
        }
        if tags:
            params["tagged"] = ";".join(tags)
        if self.api_key:
            params["key"] = self.api_key

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/search/advanced",
                params=params,
            )
            response.raise_for_status()
            items = response.json().get("items", [])

            for q in items[:limit]:
                yield CrawlResult(
                    url=q["link"],
                    content_type=ContentType.DISCUSSION,
                    title=q["title"],
                    content=q.get("body_markdown", q.get("body", "")),
                    metadata={
                        "score": q["score"],
                        "answer_count": q["answer_count"],
                        "tags": q.get("tags", []),
                        "view_count": q.get("view_count", 0),
                        "is_answered": q.get("is_answered", False),
                        "created_at": datetime.fromtimestamp(q["creation_date"]).isoformat(),
                    },
                    source="stackoverflow",
                )

    async def get_answers(self, question_id: int, limit: int = 20) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()

        params = {
            "sort": "votes",
            "order": "desc",
            "site": "stackoverflow",
            "filter": "withbody",
        }
        if self.api_key:
            params["key"] = self.api_key

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/questions/{question_id}/answers",
                params=params,
            )
            response.raise_for_status()
            answers = response.json().get("items", [])

            for a in answers[:limit]:
                yield CrawlResult(
                    url=f"https://stackoverflow.com/a/{a['answer_id']}",
                    content_type=ContentType.DISCUSSION,
                    title=f"Answer to #{question_id}",
                    content=a.get("body_markdown", a.get("body", "")),
                    metadata={
                        "score": a["score"],
                        "is_accepted": a.get("is_accepted", False),
                        "created_at": datetime.fromtimestamp(a["creation_date"]).isoformat(),
                        "question_id": question_id,
                    },
                    source="stackoverflow",
                )

    async def get_by_tags(
        self,
        tags: list[str],
        limit: int = 100,
    ) -> AsyncIterator[CrawlResult]:
        """Get questions by tags."""
        tag_str = ";".join(tags)
        await self.rate_limiter.wait_and_acquire()

        params = {
            "tagged": tag_str,
            "sort": "activity",
            "site": "stackoverflow",
            "filter": "withbody",
            "pagesize": min(limit, 100),
        }
        if self.api_key:
            params["key"] = self.api_key

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/questions",
                params=params,
            )
            response.raise_for_status()
            items = response.json().get("items", [])

            for q in items[:limit]:
                yield CrawlResult(
                    url=q["link"],
                    content_type=ContentType.DISCUSSION,
                    title=q["title"],
                    content=q.get("body_markdown", q.get("body", "")),
                    metadata={
                        "score": q["score"],
                        "answer_count": q["answer_count"],
                        "tags": q.get("tags", []),
                        "view_count": q.get("view_count", 0),
                    },
                    source="stackoverflow",
                )

    async def discover_urls(self, seed_url: str) -> AsyncIterator[str]:
        async with httpx.AsyncClient() as client:
            params = {
                "sort": "hot",
                "site": "stackoverflow",
                "pagesize": 100,
            }
            if self.api_key:
                params["key"] = self.api_key

            response = await client.get(
                f"{self.api_url}/questions",
                params=params,
            )
            for q in response.json().get("items", []):
                yield q["link"]
