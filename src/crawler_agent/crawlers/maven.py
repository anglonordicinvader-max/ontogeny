"""Maven Central crawler for Java packages."""

from typing import AsyncIterator

import httpx
import structlog

from .base import BaseCrawler, CrawlerConfig, CrawlResult, ContentType


class MavenCrawler(BaseCrawler):
    """Crawler for Maven Central packages."""

    def __init__(self, config: CrawlerConfig | None = None, **kwargs):
        super().__init__("maven", config, **kwargs)
        self.search_url = "https://search.maven.org/solrsearch/select"
        self.central_url = "https://repo1.maven.org/maven2"

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
        if "artifactId" in url or len(parts) >= 6:
            group = parts[-3].replace(".", "/")
            artifact = parts[-2]
            async for result in self._get_artifact(group, artifact):
                yield result

    async def _get_artifact(self, group: str, artifact: str) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()
        group_dot = group.replace("/", ".")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.search_url,
                params={
                    "q": f"g:{group_dot} AND a:{artifact}",
                    "rows": 1,
                    "wt": "json",
                },
            )
            if response.status_code == 200:
                docs = response.json().get("response", {}).get("docs", [])
                if docs:
                    doc = docs[0]
                    yield CrawlResult(
                        url=f"https://search.maven.org/artifact/{doc['g']}/{doc['a']}/{doc['latestVersion']}/jar",
                        content_type=ContentType.REPOSITORY,
                        title=f"{doc['g']}:{doc['a']}",
                        content=doc.get("description", ""),
                        metadata={
                            "group_id": doc.get("g"),
                            "artifact_id": doc.get("a"),
                            "latest_version": doc.get("latestVersion"),
                            "timestamp": doc.get("timestamp"),
                            "ec": doc.get("ec", []),
                        },
                        source="maven",
                    )

    async def search_artifacts(self, query: str, limit: int = 50) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.search_url,
                params={
                    "q": f"name:{query}",
                    "rows": min(limit, 100),
                    "wt": "json",
                },
            )
            if response.status_code == 200:
                for doc in response.json().get("response", {}).get("docs", [])[:limit]:
                    yield CrawlResult(
                        url=f"https://search.maven.org/artifact/{doc['g']}/{doc['a']}/{doc['latestVersion']}/jar",
                        content_type=ContentType.REPOSITORY,
                        title=f"{doc['g']}:{doc['a']}",
                        content=doc.get("description", ""),
                        metadata={
                            "group_id": doc.get("g"),
                            "artifact_id": doc.get("a"),
                            "latest_version": doc.get("latestVersion"),
                        },
                        source="maven",
                    )

    async def discover_urls(self, seed_url: str) -> AsyncIterator[str]:
        popular = [
            ("org.apache.commons", "commons-lang3"),
            ("com.google.guava", "guava"),
            ("org.springframework", "spring-core"),
            ("junit", "junit"),
            ("com.fasterxml.jackson.core", "jackson-databind"),
        ]
        for group, artifact in popular:
            yield f"https://search.maven.org/artifact/{group}/{artifact}"
