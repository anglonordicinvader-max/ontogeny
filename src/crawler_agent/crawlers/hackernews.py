"""Hacker News crawler using official API."""

from collections.abc import AsyncIterator
from datetime import datetime

import httpx
import structlog

from .base import BaseCrawler, ContentType, CrawlerConfig, CrawlResult


class HackerNewsCrawler(BaseCrawler):
    """Crawler for Hacker News stories and comments."""

    def __init__(self, config: CrawlerConfig | None = None, **kwargs):
        super().__init__("hackernews", config, **kwargs)
        self.api_url = "https://hacker-news.firebaseio.com/v0"
        self.rate_limiter.rate = 5.0

    async def _setup(self) -> None:
        pass

    async def _cleanup(self) -> None:
        pass

    async def _fetch_item(self, item_id: int) -> dict | None:
        await self.rate_limiter.wait_and_acquire()
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/item/{item_id}.json")
            if response.status_code == 200:
                return response.json()
        return None

    async def crawl(
        self,
        url: str,
        depth: int = 0,
        content_types: list[str] | None = None,
    ) -> AsyncIterator[CrawlResult]:
        # Parse HN item URL
        if "item" in url:
            parts = url.rstrip("/").split("=")
            if len(parts) > 1:
                item_id = int(parts[-1])
                item = await self._fetch_item(item_id)
                if item:
                    yield self._parse_item(item)

    def _parse_item(self, item: dict) -> CrawlResult:
        item_type = item.get("type", "story")
        title = item.get("title", item.get("text", "")[:100])
        content = item.get("text", item.get("title", ""))

        return CrawlResult(
            url=item.get("url", f"https://news.ycombinator.com/item?id={item['id']}"),
            content_type=ContentType.DISCUSSION if item_type == "comment" else ContentType.OTHER,
            title=title,
            content=content,
            metadata={
                "hn_id": item["id"],
                "type": item_type,
                "by": item.get("by", ""),
                "score": item.get("score", 0),
                "descendants": item.get("descendants", 0),
                "kids": item.get("kids", []),
                "created_at": datetime.fromtimestamp(item.get("time", 0)).isoformat(),
                "parent": item.get("parent"),
            },
            source="hackernews",
        )

    async def get_top_stories(self, limit: int = 30) -> AsyncIterator[CrawlResult]:
        """Get top stories."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/topstories.json")
            story_ids = response.json()[:limit]

        for story_id in story_ids:
            item = await self._fetch_item(story_id)
            if item:
                yield self._parse_item(item)

    async def get_new_stories(self, limit: int = 30) -> AsyncIterator[CrawlResult]:
        """Get newest stories."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/newstories.json")
            story_ids = response.json()[:limit]

        for story_id in story_ids:
            item = await self._fetch_item(story_id)
            if item:
                yield self._parse_item(item)

    async def get_ask_hn(self, limit: int = 30) -> AsyncIterator[CrawlResult]:
        """Get Ask HN posts."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/askstories.json")
            story_ids = response.json()[:limit]

        for story_id in story_ids:
            item = await self._fetch_item(story_id)
            if item:
                yield self._parse_item(item)

    async def get_comments(self, story_id: int, limit: int = 50) -> AsyncIterator[CrawlResult]:
        """Get comments for a story."""
        item = await self._fetch_item(story_id)
        if not item:
            return

        kid_ids = item.get("kids", [])[:limit]
        for kid_id in kid_ids:
            comment = await self._fetch_item(kid_id)
            if comment and comment.get("type") == "comment":
                yield self._parse_item(comment)

    async def search(self, query: str, limit: int = 50) -> AsyncIterator[CrawlResult]:
        """Search HN via Algolia API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://hn.algolia.com/api/v1/search",
                params={"query": query, "hitsPerPage": min(limit, 100)},
            )
            response.raise_for_status()
            hits = response.json().get("hits", [])

            for hit in hits[:limit]:
                yield CrawlResult(
                    url=hit.get("url", f"https://news.ycombinator.com/item?id={hit['objectID']}"),
                    content_type=ContentType.OTHER,
                    title=hit.get("title", ""),
                    content=hit.get("story_text", hit.get("comment_text", "")),
                    metadata={
                        "hn_id": hit["objectID"],
                        "points": hit.get("points", 0),
                        "num_comments": hit.get("num_comments", 0),
                        "author": hit.get("author", ""),
                        "created_at": hit.get("created_at"),
                    },
                    source="hackernews",
                )

    async def discover_urls(self, seed_url: str) -> AsyncIterator[str]:
        async for story in self.get_top_stories(limit=50):
            yield story.url
