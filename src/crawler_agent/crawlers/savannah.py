"""Savannah crawler for GNU projects."""

from typing import AsyncIterator

import httpx
import structlog
from bs4 import BeautifulSoup

from .base import BaseCrawler, CrawlerConfig, CrawlResult, ContentType


class SavannahCrawler(BaseCrawler):
    """Crawler for GNU Savannah projects."""

    def __init__(
        self,
        mirror_type: str = "gnu",  # gnu or non-gnu
        config: CrawlerConfig | None = None,
        **kwargs,
    ):
        super().__init__("savannah", config, **kwargs)
        self.mirror_type = mirror_type
        self.base_url = f"https://savannah.{mirror_type}.org"

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
                f"{self.base_url}/{self.mirror_type}/{project_name}",
                follow_redirects=True,
            )
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "lxml")
                title = soup.title.text.strip() if soup.title else project_name
                desc = soup.find("meta", {"name": "description"})
                description = desc.get("content", "") if desc else ""

                yield CrawlResult(
                    url=f"{self.base_url}/{self.mirror_type}/{project_name}",
                    content_type=ContentType.REPOSITORY,
                    title=title,
                    content=description,
                    metadata={
                        "project_name": project_name,
                        "platform": f"savannah-{self.mirror_type}",
                    },
                    source="savannah",
                )

    async def list_projects(self, limit: int = 100) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/projects/index.html",
                follow_redirects=True,
            )
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "lxml")
                links = soup.select("a[href]")
                count = 0
                for link in links:
                    href = link.get("href", "")
                    if f"/{self.mirror_type}/" in href and count < limit:
                        yield CrawlResult(
                            url=f"{self.base_url}{href}" if href.startswith("/") else href,
                            content_type=ContentType.REPOSITORY,
                            title=link.text.strip(),
                            content="",
                            metadata={"platform": f"savannah-{self.mirror_type}"},
                            source="savannah",
                        )
                        count += 1

    async def discover_urls(self, seed_url: str) -> AsyncIterator[str]:
        async for project in self.list_projects(limit=50):
            yield project.url
