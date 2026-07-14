"""NuGet crawler for .NET packages."""

from typing import AsyncIterator

import httpx
import structlog

from .base import BaseCrawler, CrawlerConfig, CrawlResult, ContentType


class NugetCrawler(BaseCrawler):
    """Crawler for NuGet packages."""

    def __init__(self, config: CrawlerConfig | None = None, **kwargs):
        super().__init__("nuget", config, **kwargs)
        self.api_url = "https://api.nuget.org/v3"

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
        package_id = url.rstrip("/").split("/")[-1]
        async for result in self._get_package(package_id):
            yield result

    async def _get_package(self, package_id: str) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/registration5-gz-semver2/{package_id.lower()}/index.json",
            )
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [{}])
                if items:
                    catalog = items[0]
                    latest = catalog.get("catalogEntry", {})
                    yield CrawlResult(
                        url=f"https://www.nuget.org/packages/{package_id}",
                        content_type=ContentType.REPOSITORY,
                        title=latest.get("id", package_id),
                        content=latest.get("description", ""),
                        metadata={
                            "version": latest.get("version"),
                            "authors": latest.get("authors"),
                            "license_url": latest.get("licenseUrl"),
                            "project_url": latest.get("projectUrl"),
                            "tags": latest.get("tags", []),
                            "dependency_groups": len(latest.get("dependencyGroups", [])),
                        },
                        source="nuget",
                    )

    async def search_packages(self, query: str, limit: int = 50) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/packagebaseaddress/autocomplete",
                params={"q": query, "take": min(limit, 100)},
            )
            if response.status_code == 200:
                packages = response.json().get("data", [])
                for pkg_id in packages[:limit]:
                    async for result in self._get_package(pkg_id):
                        yield result

    async def discover_urls(self, seed_url: str) -> AsyncIterator[str]:
        popular = ["Newtonsoft.Json", "Serilog", "Dapper", "AutoMapper", "MediatR"]
        for pkg in popular:
            yield f"https://www.nuget.org/packages/{pkg}"
