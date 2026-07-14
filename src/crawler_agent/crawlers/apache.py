"""Apache GitBox/ASF crawler."""

from typing import AsyncIterator

import httpx
import structlog

from .base import BaseCrawler, CrawlerConfig, CrawlResult, ContentType


class ApacheCrawler(BaseCrawler):
    """Crawler for Apache Software Foundation projects."""

    def __init__(self, config: CrawlerConfig | None = None, **kwargs):
        super().__init__("apache", config, **kwargs)
        self.gitbox_url = "https://gitbox.apache.org"
        self.api_url = "https://api.github.com/orgs/apache"

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
        parts = url.rstrip("/").split("/")
        repo_name = parts[-1] if parts else ""
        if repo_name:
            async for result in self._get_repo(repo_name):
                yield result

    async def _get_repo(self, repo_name: str) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/repos/{repo_name}")
            if response.status_code == 200:
                data = response.json()
                yield CrawlResult(
                    url=data.get("html_url", f"https://github.com/apache/{repo_name}"),
                    content_type=ContentType.REPOSITORY,
                    title=data["full_name"],
                    content=data.get("description", ""),
                    metadata={
                        "stars": data.get("stargazers_count", 0),
                        "forks": data.get("forks_count", 0),
                        "language": data.get("language"),
                        "created_at": data.get("created_at"),
                        "topics": data.get("topics", []),
                        "license": data.get("license", {}).get("name"),
                    },
                    source="apache",
                )

    async def search_repos(self, query: str, limit: int = 50) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/search/repositories",
                params={"q": f"org:apache {query}", "per_page": min(limit, 100)},
            )
            response.raise_for_status()
            for repo in response.json().get("items", [])[:limit]:
                yield CrawlResult(
                    url=repo["html_url"],
                    content_type=ContentType.REPOSITORY,
                    title=repo["full_name"],
                    content=repo.get("description", ""),
                    metadata={
                        "stars": repo.get("stargazers_count", 0),
                        "forks": repo.get("forks_count", 0),
                        "language": repo.get("language"),
                    },
                    source="apache",
                )

    async def discover_urls(self, seed_url: str) -> AsyncIterator[str]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/repos",
                params={"per_page": 100, "sort": "updated"},
            )
            for repo in response.json():
                yield repo["html_url"]
