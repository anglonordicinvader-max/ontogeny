"""Codeberg/Gitea crawler using Gitea API."""

from typing import AsyncIterator
from datetime import datetime

import httpx
import structlog

from .base import BaseCrawler, CrawlerConfig, CrawlResult, ContentType


class GiteaCrawler(BaseCrawler):
    """Generic crawler for Gitea instances (Codeberg, Gitea.com, etc.)."""

    def __init__(
        self,
        instance_url: str = "https://codeberg.org",
        token: str = "",
        config: CrawlerConfig | None = None,
        **kwargs,
    ):
        super().__init__("gitea", config, **kwargs)
        self.instance_url = instance_url.rstrip("/")
        self.api_url = f"{self.instance_url}/api/v1"
        self.headers = {"Authorization": f"token {token}"} if token else {}

    async def _setup(self) -> None:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/version", headers=self.headers)
            if response.status_code == 200:
                version = response.json().get("version", "unknown")
                self.logger.info("gitea_connected", instance=self.instance_url, version=version)

    async def _cleanup(self) -> None:
        pass

    async def crawl(
        self,
        url: str,
        depth: int = 0,
        content_types: list[str] | None = None,
    ) -> AsyncIterator[CrawlResult]:
        parts = url.rstrip("/").split("/")
        if "/repos/" in url or len(parts) >= 5:
            owner = parts[-2]
            repo = parts[-1]
            async for result in self._get_repo(owner, repo):
                yield result

    async def _get_repo(self, owner: str, repo: str) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/repos/{owner}/{repo}", headers=self.headers)
            response.raise_for_status()
            data = response.json()
            yield CrawlResult(
                url=data.get("html_url", f"{self.instance_url}/{owner}/{repo}"),
                content_type=ContentType.REPOSITORY,
                title=data["full_name"],
                content=data.get("description", ""),
                metadata={
                    "stars": data.get("stars_count", 0),
                    "forks": data.get("forks_count", 0),
                    "language": data.get("language"),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                    "open_issues": data.get("open_issues_count", 0),
                },
                source="gitea",
            )

    async def search_repositories(self, query: str, limit: int = 50) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/repos/search",
                headers=self.headers,
                params={"q": query, "limit": min(limit, 50)},
            )
            response.raise_for_status()
            for repo in response.json().get("data", [])[:limit]:
                yield CrawlResult(
                    url=repo.get("html_url", ""),
                    content_type=ContentType.REPOSITORY,
                    title=repo["full_name"],
                    content=repo.get("description", ""),
                    metadata={
                        "stars": repo.get("stars_count", 0),
                        "forks": repo.get("forks_count", 0),
                        "language": repo.get("language"),
                    },
                    source="gitea",
                )

    async def get_issues(self, owner: str, repo: str) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/repos/{owner}/{repo}/issues",
                headers=self.headers,
                params={"limit": 50, "state": "open"},
            )
            response.raise_for_status()
            for issue in response.json():
                yield CrawlResult(
                    url=issue.get("html_url", ""),
                    content_type=ContentType.ISSUE,
                    title=f"#{issue['number']}: {issue['title']}",
                    content=issue.get("body", ""),
                    metadata={
                        "number": issue["number"],
                        "state": issue["state"],
                        "labels": [l["name"] for l in issue.get("labels", [])],
                        "author": issue.get("user", {}).get("login"),
                        "created_at": issue.get("created_at"),
                    },
                    source="gitea",
                )

    async def discover_urls(self, seed_url: str) -> AsyncIterator[str]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/repos/search",
                headers=self.headers,
                params={"sort": "updated", "limit": 50},
            )
            for repo in response.json().get("data", []):
                yield repo.get("html_url", "")


class CodebergCrawler(GiteaCrawler):
    """Crawler specifically for Codeberg."""
    def __init__(self, token: str = "", config: CrawlerConfig | None = None, **kwargs):
        super().__init__(
            instance_url="https://codeberg.org",
            token=token,
            config=config,
            **kwargs,
        )
        self.name = "codeberg"


class GiteaDotComCrawler(GiteaCrawler):
    """Crawler for Gitea.com."""
    def __init__(self, token: str = "", config: CrawlerConfig | None = None, **kwargs):
        super().__init__(
            instance_url="https://gitea.com",
            token=token,
            config=config,
            **kwargs,
        )
        self.name = "gitea_dot_com"
