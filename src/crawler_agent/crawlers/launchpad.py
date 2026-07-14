"""Launchpad crawler for Ubuntu/Debian projects."""

from typing import AsyncIterator

import httpx
import structlog

from .base import BaseCrawler, CrawlerConfig, CrawlResult, ContentType


class LaunchpadCrawler(BaseCrawler):
    """Crawler for Launchpad projects."""

    def __init__(self, config: CrawlerConfig | None = None, **kwargs):
        super().__init__("launchpad", config, **kwargs)
        self.api_url = "https://api.launchpad.net/devel"

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
        project_name = url.rstrip("/").split("/")[-1]
        async for result in self._get_project(project_name):
            yield result

    async def _get_project(self, project_name: str) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/{project_name}")
            if response.status_code == 200:
                data = response.json()
                yield CrawlResult(
                    url=data.get("web_link", f"https://launchpad.net/{project_name}"),
                    content_type=ContentType.REPOSITORY,
                    title=data.get("display_name", project_name),
                    content=data.get("description", ""),
                    metadata={
                        "name": data.get("name"),
                        "summary": data.get("summary"),
                        "homepage": data.get("homepage"),
                        "launchpad_project": project_name,
                    },
                    source="launchpad",
                )

    async def search_projects(self, query: str, limit: int = 50) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/projects",
                params={"ws.op": "search", "text": query, "ws.size": min(limit, 50)},
            )
            response.raise_for_status()
            data = response.json()
            for proj in data.get("entries", [])[:limit]:
                yield CrawlResult(
                    url=proj.get("web_link", ""),
                    content_type=ContentType.REPOSITORY,
                    title=proj.get("display_name", ""),
                    content=proj.get("summary", ""),
                    metadata={"platform": "launchpad"},
                    source="launchpad",
                )

    async def discover_urls(self, seed_url: str) -> AsyncIterator[str]:
        async for project in self.search_projects("", limit=50):
            yield project.url
