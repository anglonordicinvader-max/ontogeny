"""npm registry crawler."""

from typing import AsyncIterator

import httpx
import structlog

from .base import BaseCrawler, CrawlerConfig, CrawlResult, ContentType


class NpmCrawler(BaseCrawler):
    """Crawler for npm packages."""

    def __init__(self, config: CrawlerConfig | None = None, **kwargs):
        super().__init__("npm", config, **kwargs)
        self.api_url = "https://registry.npmjs.org"

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
        package_name = url.rstrip("/").split("/")[-1]
        async for result in self._get_package(package_name):
            yield result

    async def _get_package(self, package_name: str) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/{package_name}")
            if response.status_code == 200:
                data = response.json()
                latest_version = data.get("dist-tags", {}).get("latest", "")
                versions = data.get("versions", {})
                latest = versions.get(latest_version, {})

                yield CrawlResult(
                    url=f"https://www.npmjs.com/package/{package_name}",
                    content_type=ContentType.REPOSITORY,
                    title=data.get("name", package_name),
                    content=data.get("description", ""),
                    metadata={
                        "version": latest_version,
                        "author": data.get("author", {}).get("name") if isinstance(data.get("author"), dict) else data.get("author"),
                        "license": latest.get("license"),
                        "homepage": data.get("homepage"),
                        "repository": data.get("repository", {}).get("url") if isinstance(data.get("repository"), dict) else data.get("repository"),
                        "keywords": data.get("keywords", [])[:10],
                        "dependencies": list(latest.get("dependencies", {}).keys())[:20],
                        "maintainers": [m.get("name") for m in data.get("maintainers", [])[:5]],
                        "time": {
                            "created": data.get("time", {}).get("created"),
                            "modified": data.get("time", {}).get("modified"),
                        },
                    },
                    source="npm",
                )

    async def search_packages(self, query: str, limit: int = 50) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://registry.npmjs.org/-/v1/search",
                params={"text": query, "size": min(limit, 250)},
            )
            response.raise_for_status()
            for pkg in response.json().get("objects", [])[:limit]:
                obj = pkg.get("package", {})
                yield CrawlResult(
                    url=f"https://www.npmjs.com/package/{obj.get('name', '')}",
                    content_type=ContentType.REPOSITORY,
                    title=obj.get("name", ""),
                    content=obj.get("description", ""),
                    metadata={
                        "version": obj.get("version"),
                        "keywords": obj.get("keywords", []),
                        "date": obj.get("date"),
                        "score": pkg.get("score", {}),
                    },
                    source="npm",
                )

    async def discover_urls(self, seed_url: str) -> AsyncIterator[str]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://registry.npmjs.org/-/v1/search",
                params={"text": "keywords:javascript", "size": 50},
            )
            for pkg in response.json().get("objects", []):
                name = pkg.get("package", {}).get("name", "")
                if name:
                    yield f"https://www.npmjs.com/package/{name}"
