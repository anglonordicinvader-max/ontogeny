"""Bitbucket crawler using REST API v2."""

from collections.abc import AsyncIterator
from datetime import datetime

import httpx
import structlog

from .base import BaseCrawler, ContentType, CrawlerConfig, CrawlResult


class BitbucketCrawler(BaseCrawler):
    """Crawler for Bitbucket repositories, issues, and pipelines."""

    def __init__(
        self,
        username: str = "",
        app_password: str = "",
        config: CrawlerConfig | None = None,
        **kwargs,
    ):
        super().__init__("bitbucket", config, **kwargs)
        self.auth = (username, app_password) if username and app_password else None
        self.api_url = "https://api.bitbucket.org/2.0"

    async def _setup(self) -> None:
        if self.auth:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.api_url}/user", auth=self.auth)
                if response.status_code == 200:
                    user = response.json()
                    self.logger.info("bitbucket_connected", user=user.get("display_name"))

    async def _cleanup(self) -> None:
        pass

    async def crawl(
        self,
        url: str,
        depth: int = 0,
        content_types: list[str] | None = None,
    ) -> AsyncIterator[CrawlResult]:
        parts = url.rstrip("/").split("/")
        if "repos" in parts:
            idx = parts.index("repos")
            workspace = parts[idx + 1] if idx + 1 < len(parts) else ""
            repo_slug = parts[idx + 2] if idx + 2 < len(parts) else ""
            if workspace and repo_slug:
                async for result in self._get_repo(workspace, repo_slug):
                    yield result

    async def _get_repo(self, workspace: str, repo_slug: str) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/repositories/{workspace}/{repo_slug}",
                auth=self.auth,
            )
            response.raise_for_status()
            repo = response.json()
            yield CrawlResult(
                url=repo["links"]["html"]["href"],
                content_type=ContentType.REPOSITORY,
                title=repo["full_name"],
                content=repo.get("description", ""),
                metadata={
                    "stars": repo.get("stars_count", 0),
                    "forks": repo.get("forks_count", 0),
                    "language": repo.get("language"),
                    "created_at": repo.get("created_on"),
                    "updated_at": repo.get("updated_on"),
                    "is_private": repo.get("is_private", False),
                    "default_branch": repo.get("mainbranch", {}).get("name"),
                },
                source="bitbucket",
            )

    async def search_repositories(self, query: str, limit: int = 50) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/repositories",
                auth=self.auth,
                params={"q": f'name~"{query}"', "pagelen": min(limit, 100)},
            )
            response.raise_for_status()
            for repo in response.json().get("values", [])[:limit]:
                yield CrawlResult(
                    url=repo["links"]["html"]["href"],
                    content_type=ContentType.REPOSITORY,
                    title=repo["full_name"],
                    content=repo.get("description", ""),
                    metadata={
                        "stars": repo.get("stars_count", 0),
                        "forks": repo.get("forks_count", 0),
                        "language": repo.get("language"),
                    },
                    source="bitbucket",
                )

    async def get_issues(self, workspace: str, repo_slug: str) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/repositories/{workspace}/{repo_slug}/issues",
                auth=self.auth,
                params={"pagelen": 100},
            )
            response.raise_for_status()
            for issue in response.json().get("values", []):
                yield CrawlResult(
                    url=issue["links"]["html"]["href"],
                    content_type=ContentType.ISSUE,
                    title=f"#{issue['id']}: {issue['title']}",
                    content=issue.get("content", {}).get("raw", ""),
                    metadata={
                        "id": issue["id"],
                        "state": issue["state"],
                        "priority": issue.get("priority"),
                        "kind": issue.get("kind"),
                        "author": issue.get("author", {}).get("display_name"),
                        "created_at": issue.get("created_on"),
                    },
                    source="bitbucket",
                )

    async def discover_urls(self, seed_url: str) -> AsyncIterator[str]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/repositories",
                auth=self.auth,
                params={"sort": "-updated_on", "pagelen": 50},
            )
            for repo in response.json().get("values", []):
                yield repo["links"]["html"]["href"]
