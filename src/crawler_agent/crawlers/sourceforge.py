"""SourceForge crawler."""

from typing import AsyncIterator

import httpx
import structlog
from bs4 import BeautifulSoup

from .base import BaseCrawler, CrawlerConfig, CrawlResult, ContentType


class SourceForgeCrawler(BaseCrawler):
    """Crawler for SourceForge projects."""

    def __init__(self, config: CrawlerConfig | None = None, **kwargs):
        super().__init__("sourceforge", config, **kwargs)
        self.api_url = "https://sourceforge.net/projects"

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
            response = await client.get(
                f"{self.api_url}/{project_name}/",
                follow_redirects=True,
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")

            title_tag = soup.find("h1", {"itemprop": "name"})
            title = title_tag.text.strip() if title_tag else project_name

            desc_tag = soup.find("meta", {"name": "description"})
            description = desc_tag.get("content", "") if desc_tag else ""

            yield CrawlResult(
                url=f"https://sourceforge.net/projects/{project_name}/",
                content_type=ContentType.REPOSITORY,
                title=title,
                content=description,
                metadata={
                    "project_name": project_name,
                    "platform": "sourceforge",
                },
                source="sourceforge",
            )

    async def search_projects(self, query: str, limit: int = 50) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/?source=hp_search_widget",
                params={"q": query},
                follow_redirects=True,
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")
            projects = soup.select(".project-list .project")[:limit]

            for proj in projects:
                name_tag = proj.select_one(".project-title a")
                if name_tag:
                    name = name_tag.text.strip()
                    href = name_tag.get("href", "")
                    yield CrawlResult(
                        url=f"https://sourceforge.net{href}" if href.startswith("/") else href,
                        content_type=ContentType.REPOSITORY,
                        title=name,
                        content=proj.select_one(".project-desc").text.strip() if proj.select_one(".project-desc") else "",
                        metadata={"platform": "sourceforge"},
                        source="sourceforge",
                    )

    async def discover_urls(self, seed_url: str) -> AsyncIterator[str]:
        async for project in self.search_projects("", limit=50):
            yield project.url
