"""Reddit crawler using official API."""

from typing import AsyncIterator
from datetime import datetime

import httpx
import structlog

from .base import BaseCrawler, CrawlerConfig, CrawlResult, ContentType


class RedditCrawler(BaseCrawler):
    """Crawler for Reddit posts and comments."""

    def __init__(
        self,
        client_id: str = "",
        client_secret: str = "",
        user_agent: str = "CrawlerAgent/0.1",
        config: CrawlerConfig | None = None,
        **kwargs,
    ):
        super().__init__("reddit", config, **kwargs)
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self.api_url = "https://oauth.reddit.com"
        self.access_token: str = ""

    async def _setup(self) -> None:
        if self.client_id and self.client_secret:
            await self._authenticate()

    async def _authenticate(self) -> None:
        """Get OAuth token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://www.reddit.com/api/v1/access_token",
                auth=(self.client_id, self.client_secret),
                data={"grant_type": "client_credentials"},
                headers={"User-Agent": self.user_agent},
            )
            response.raise_for_status()
            self.access_token = response.json()["access_token"]
            self.logger.info("reddit_authenticated")

    async def _cleanup(self) -> None:
        pass

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": self.user_agent,
        }

    async def crawl(
        self,
        url: str,
        depth: int = 0,
        content_types: list[str] | None = None,
    ) -> AsyncIterator[CrawlResult]:
        # Parse Reddit URL
        parts = url.rstrip("/").split("/")
        if "r" in parts:
            idx = parts.index("r")
            subreddit = parts[idx + 1] if idx + 1 < len(parts) else ""
            if subreddit:
                async for result in self._crawl_subreddit(subreddit):
                    yield result

    async def _crawl_subreddit(
        self,
        subreddit: str,
        sort: str = "hot",
        limit: int = 100,
    ) -> AsyncIterator[CrawlResult]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/r/{subreddit}/{sort}",
                headers=self._headers(),
                params={"limit": limit, "raw_json": 1},
            )
            response.raise_for_status()
            posts = response.json().get("data", {}).get("children", [])

            for post in posts:
                data = post["data"]
                yield CrawlResult(
                    url=f"https://reddit.com{data['permalink']}",
                    content_type=ContentType.DISCUSSION,
                    title=data["title"],
                    content=data.get("selftext", ""),
                    metadata={
                        "subreddit": data["subreddit"],
                        "author": data["author"],
                        "score": data["score"],
                        "upvote_ratio": data.get("upvote_ratio"),
                        "num_comments": data["num_comments"],
                        "created_at": datetime.fromtimestamp(data["created_utc"]).isoformat(),
                        "url": data.get("url"),
                        "is_self": data.get("is_self", False),
                        "flair": data.get("link_flair_text"),
                    },
                    source="reddit",
                )

    async def search(
        self,
        query: str,
        subreddit: str | None = None,
        sort: str = "relevance",
        limit: int = 50,
    ) -> AsyncIterator[CrawlResult]:
        async with httpx.AsyncClient() as client:
            params = {"q": query, "sort": sort, "limit": min(limit, 100), "restrict_sr": bool(subreddit)}
            if subreddit:
                params["restrict_sr"] = "on"

            endpoint = f"/r/{subreddit}/search" if subreddit else "/search"
            response = await client.get(
                f"{self.api_url}{endpoint}",
                headers=self._headers(),
                params=params,
            )
            response.raise_for_status()
            posts = response.json().get("data", {}).get("children", [])

            for post in posts[:limit]:
                data = post["data"]
                yield CrawlResult(
                    url=f"https://reddit.com{data['permalink']}",
                    content_type=ContentType.DISCUSSION,
                    title=data["title"],
                    content=data.get("selftext", ""),
                    metadata={
                        "subreddit": data["subreddit"],
                        "author": data["author"],
                        "score": data["score"],
                        "num_comments": data["num_comments"],
                        "created_at": datetime.fromtimestamp(data["created_utc"]).isoformat(),
                    },
                    source="reddit",
                )

    async def get_comments(
        self,
        subreddit: str,
        post_id: str,
        limit: int = 100,
        sort: str = "best",
    ) -> AsyncIterator[CrawlResult]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/r/{subreddit}/comments/{post_id}",
                headers=self._headers(),
                params={"sort": sort, "limit": limit, "raw_json": 1},
            )
            response.raise_for_status()
            comments = response.json()[1].get("data", {}).get("children", [])

            for comment in comments:
                if comment["kind"] != "t1":
                    continue
                data = comment["data"]
                yield CrawlResult(
                    url=f"https://reddit.com{data.get('permalink', '')}",
                    content_type=ContentType.DISCUSSION,
                    title=f"Comment by {data['author']}",
                    content=data.get("body", ""),
                    metadata={
                        "author": data["author"],
                        "score": data["score"],
                        "created_at": datetime.fromtimestamp(data["created_utc"]).isoformat(),
                        "subreddit": data["subreddit"],
                        "post_id": data["parent_id"],
                    },
                    source="reddit",
                )

    async def discover_urls(self, seed_url: str) -> AsyncIterator[str]:
        subreddits = ["MachineLearning", "programming", "python", "artificial", "LocalLLaMA"]
        for sub in subreddits:
            async for result in self._crawl_subreddit(sub, limit=25):
                yield result.url
