"""RubyGems crawler for Ruby packages."""

from collections.abc import AsyncIterator

import httpx
import structlog

from .base import BaseCrawler, ContentType, CrawlerConfig, CrawlResult


class RubyGemsCrawler(BaseCrawler):
    """Crawler for RubyGems packages."""

    def __init__(self, config: CrawlerConfig | None = None, **kwargs):
        super().__init__("rubygems", config, **kwargs)
        self.api_url = "https://rubygems.org/api/v1"

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
        gem_name = url.rstrip("/").split("/")[-1]
        async for result in self._get_gem(gem_name):
            yield result

    async def _get_gem(self, gem_name: str) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/gems/{gem_name}.json")
            if response.status_code == 200:
                data = response.json()
                yield CrawlResult(
                    url=data.get("project_uri", f"https://rubygems.org/gems/{gem_name}"),
                    content_type=ContentType.REPOSITORY,
                    title=data.get("name", gem_name),
                    content=data.get("info", ""),
                    metadata={
                        "version": data.get("version"),
                        "authors": data.get("authors"),
                        "homepage_uri": data.get("homepage_uri"),
                        "source_code_uri": data.get("source_code_uri"),
                        "documentation_uri": data.get("documentation_uri"),
                        "licenses": data.get("licenses", []),
                        "dependencies": {
                            "runtime": [
                                d["name"]
                                for d in data.get("dependencies", {}).get("runtime", [])[:10]
                            ],
                            "development": [
                                d["name"]
                                for d in data.get("dependencies", {}).get("development", [])[:5]
                            ],
                        },
                        "downloads": data.get("downloads"),
                        "version_downloads": data.get("version_downloads"),
                    },
                    source="rubygems",
                )

    async def search_gems(self, query: str, limit: int = 50) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/search.json",
                params={"query": query},
            )
            if response.status_code == 200:
                for gem in response.json()[:limit]:
                    yield CrawlResult(
                        url=gem.get("project_uri", ""),
                        content_type=ContentType.REPOSITORY,
                        title=gem.get("name", ""),
                        content=gem.get("info", ""),
                        metadata={
                            "version": gem.get("version"),
                            "downloads": gem.get("downloads"),
                        },
                        source="rubygems",
                    )

    async def get_recent(self, limit: int = 50) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/gems.json", params={"page": 1})
            if response.status_code == 200:
                for gem in response.json()[:limit]:
                    async for result in self._get_gem(gem["name"]):
                        yield result

    async def discover_urls(self, seed_url: str) -> AsyncIterator[str]:
        async for gem in self.get_recent(limit=50):
            yield gem.url
