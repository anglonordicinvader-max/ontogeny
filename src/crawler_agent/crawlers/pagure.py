"""Pagure crawler for Fedora/Red Hat projects."""

from typing import AsyncIterator

import httpx
import structlog

from .base import BaseCrawler, CrawlerConfig, CrawlResult, ContentType


class PagureCrawler(BaseCrawler):
    """Crawler for Pagure (Fedora) projects."""

    def __init__(
        self,
        instance_url: str = "https://pagure.io",
        config: CrawlerConfig | None = None,
        **kwargs,
    ):
        super().__init__("pagure", config, **kwargs)
        self.instance_url = instance_url.rstrip("/")
        self.api_url = f"{self.instance_url}/api/0"

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
            response = await client.get(f"{self.api_url}/project/{project_name}")
            if response.status_code == 200:
                data = response.json()
                yield CrawlResult(
                    url=data.get("url", f"{self.instance_url}/{project_name}"),
                    content_type=ContentType.REPOSITORY,
                    title=data.get("fullname", project_name),
                    content=data.get("description", ""),
                    metadata={
                        "name": data.get("name"),
                        "namespace": data.get("namespace"),
                        "parent": data.get("parent"),
                        "date_created": data.get("date_created"),
                        "date_modified": data.get("date_modified"),
                        "users": len(data.get("users", [])),
                        "groups": data.get("groups", []),
                    },
                    source="pagure",
                )

    async def search_projects(self, query: str, limit: int = 50) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/projects",
                params={"namespace": "fedora", "per_page": min(limit, 100)},
            )
            response.raise_for_status()
            for proj in response.json().get("projects", [])[:limit]:
                if query.lower() in proj.get("name", "").lower():
                    yield CrawlResult(
                        url=proj.get("url", ""),
                        content_type=ContentType.REPOSITORY,
                        title=proj.get("fullname", ""),
                        content=proj.get("description", ""),
                        metadata={"platform": "pagure"},
                        source="pagure",
                    )

    async def discover_urls(self, seed_url: str) -> AsyncIterator[str]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/projects",
                params={"per_page": 100, "sort": "date_modified"},
            )
            for proj in response.json().get("projects", []):
                yield proj.get("url", "")
