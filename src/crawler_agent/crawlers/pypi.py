"""PyPI crawler for Python packages."""

from typing import AsyncIterator

import httpx
import structlog

from .base import BaseCrawler, CrawlerConfig, CrawlResult, ContentType


class PyPICrawler(BaseCrawler):
    """Crawler for PyPI packages."""

    def __init__(self, config: CrawlerConfig | None = None, **kwargs):
        super().__init__("pypi", config, **kwargs)
        self.api_url = "https://pypi.org/pypi"

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
        package_name = url.rstrip("/").split("/")[-2] if "/project/" in url else url.rstrip("/").split("/")[-1]
        async for result in self._get_package(package_name):
            yield result

    async def _get_package(self, package_name: str) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/{package_name}/json")
            if response.status_code == 200:
                data = response.json()
                info = data.get("info", {})
                urls = data.get("urls", [])

                yield CrawlResult(
                    url=info.get("project_url", f"https://pypi.org/project/{package_name}/"),
                    content_type=ContentType.REPOSITORY,
                    title=info.get("name", package_name),
                    content=info.get("summary", "") + "\n\n" + (info.get("description", "")[:3000]),
                    metadata={
                        "version": info.get("version"),
                        "author": info.get("author") or info.get("author_email"),
                        "license": info.get("license"),
                        "requires_python": info.get("requires_python"),
                        "home_page": info.get("home_page"),
                        "project_urls": info.get("project_urls", {}),
                        "keywords": info.get("keywords"),
                        "classifiers": info.get("classifiers", [])[:10],
                        "requires_dist": (info.get("requires_dist") or [])[:20],
                        "downloads": {
                            "last_day": urls[-1].get("downloads", 0) if urls else 0,
                        },
                    },
                    source="pypi",
                )

    async def search_packages(self, query: str, limit: int = 50) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://libraries.io/api/pypi",
                params={"q": query, "per_page": min(limit, 100)},
            )
            if response.status_code == 200:
                for pkg in response.json()[:limit]:
                    yield CrawlResult(
                        url=f"https://pypi.org/project/{pkg['name']}/",
                        content_type=ContentType.REPOSITORY,
                        title=pkg["name"],
                        content=pkg.get("description", ""),
                        metadata={
                            "latest_release": pkg.get("latest_release_number"),
                            "stars": pkg.get("stars", 0),
                            "forks": pkg.get("forks", 0),
                            "language": pkg.get("language"),
                        },
                        source="pypi",
                    )

    async def get_recent(self, limit: int = 50) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/json")
            if response.status_code == 200:
                releases = response.json().get("releases", {})
                for name in list(releases.keys())[:limit]:
                    async for result in self._get_package(name):
                        yield result

    async def discover_urls(self, seed_url: str) -> AsyncIterator[str]:
        async for pkg in self.get_recent(limit=50):
            yield pkg.url
