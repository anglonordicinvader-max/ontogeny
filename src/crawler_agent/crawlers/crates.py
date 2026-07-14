"""crates.io crawler for Rust packages."""

from typing import AsyncIterator

import httpx
import structlog

from .base import BaseCrawler, CrawlerConfig, CrawlResult, ContentType


class CratesCrawler(BaseCrawler):
    """Crawler for crates.io packages."""

    def __init__(self, config: CrawlerConfig | None = None, **kwargs):
        super().__init__("crates", config, **kwargs)
        self.api_url = "https://crates.io/api/v1"
        self.headers = {"User-Agent": "CrawlerAgent/0.1 (research)"}

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
        crate_name = url.rstrip("/").split("/")[-1]
        async for result in self._get_crate(crate_name):
            yield result

    async def _get_crate(self, crate_name: str) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/crates/{crate_name}", headers=self.headers)
            if response.status_code == 200:
                data = response.json().get("crate", {})
                yield CrawlResult(
                    url=data.get("html_url", f"https://crates.io/crates/{crate_name}"),
                    content_type=ContentType.REPOSITORY,
                    title=data.get("name", crate_name),
                    content=data.get("description", ""),
                    metadata={
                        "version": data.get("newest_version"),
                        "downloads": data.get("downloads", 0),
                        "recent_downloads": data.get("recent_downloads", 0),
                        "categories": data.get("categories", []),
                        "keywords": data.get("keywords", []),
                        "repository": data.get("repository"),
                        "homepage": data.get("homepage"),
                        "documentation": data.get("documentation"),
                        "license": data.get("license"),
                        "max_upload_size": data.get("max_upload_size"),
                    },
                    source="crates",
                )

    async def search_crates(self, query: str, limit: int = 50) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/crates",
                headers=self.headers,
                params={"q": query, "per_page": min(limit, 100)},
            )
            response.raise_for_status()
            for crate in response.json().get("crates", [])[:limit]:
                yield CrawlResult(
                    url=crate.get("html_url", ""),
                    content_type=ContentType.REPOSITORY,
                    title=crate.get("name", ""),
                    content=crate.get("description", ""),
                    metadata={
                        "version": crate.get("newest_version"),
                        "downloads": crate.get("downloads", 0),
                        "categories": crate.get("categories", []),
                    },
                    source="crates",
                )

    async def get_recent(self, limit: int = 50) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/crates",
                headers=self.headers,
                params={"sort": "recent-downloads", "per_page": min(limit, 100)},
            )
            response.raise_for_status()
            for crate in response.json().get("crates", [])[:limit]:
                async for result in self._get_crate(crate["name"]):
                    yield result

    async def discover_urls(self, seed_url: str) -> AsyncIterator[str]:
        async for crate in self.get_recent(limit=50):
            yield crate.url
