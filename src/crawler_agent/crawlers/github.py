"""GitHub crawler using API v3."""

import asyncio
from collections.abc import AsyncIterator

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from ..utils.rate_limiter import SlidingWindowRateLimiter
from .base import BaseCrawler, ContentType, CrawlerConfig, CrawlResult


class GitHubCrawler(BaseCrawler):
    """Crawler for GitHub repositories, issues, and code."""

    def __init__(
        self,
        token: str,
        config: CrawlerConfig | None = None,
        **kwargs,
    ):
        super().__init__("github", config, **kwargs)
        self.token = token
        self.api_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "CrawlerAgent/0.1",
        }
        # GitHub rate limit: 5000 requests/hour
        self.rate_limiter_api = SlidingWindowRateLimiter(
            max_requests=4500,
            window_seconds=3600,
        )

    async def _setup(self) -> None:
        """Verify GitHub token."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/user", headers=self.headers)
            response.raise_for_status()
            user = response.json()
            self.logger.info("github_connected", user=user["login"])

    async def _cleanup(self) -> None:
        pass

    async def crawl(
        self,
        url: str,
        depth: int = 0,
        content_types: list[str] | None = None,
    ) -> AsyncIterator[CrawlResult]:
        """Crawl GitHub content."""
        content_types = content_types or ["repos", "issues", "code"]

        if "repos" in content_types:
            async for result in self._crawl_repos(url, depth):
                yield result

        if "issues" in content_types:
            async for result in self._crawl_issues(url, depth):
                yield result

        if "code" in content_types:
            async for result in self._crawl_code(url, depth):
                yield result

    async def _crawl_repos(self, owner: str, depth: int) -> AsyncIterator[CrawlResult]:
        """Crawl repositories for an owner."""
        await self.rate_limiter_api.wait_and_acquire()

        async with httpx.AsyncClient() as client:
            page = 1
            while True:
                response = await client.get(
                    f"{self.api_url}/users/{owner}/repos",
                    headers=self.headers,
                    params={"page": page, "per_page": 100, "sort": "updated"},
                )
                response.raise_for_status()
                repos = response.json()

                if not repos:
                    break

                for repo in repos:
                    yield CrawlResult(
                        url=repo["html_url"],
                        content_type=ContentType.REPOSITORY,
                        title=repo["full_name"],
                        content=repo.get("description", ""),
                        metadata={
                            "stars": repo["stargazers_count"],
                            "language": repo["language"],
                            "topics": repo.get("topics", []),
                            "created_at": repo["created_at"],
                            "updated_at": repo["updated_at"],
                            "size": repo["size"],
                        },
                        source="github",
                    )

                page += 1

    async def _crawl_issues(
        self, repo: str, depth: int, state: str = "all"
    ) -> AsyncIterator[CrawlResult]:
        """Crawl issues for a repository."""
        await self.rate_limiter_api.wait_and_acquire()

        async with httpx.AsyncClient() as client:
            page = 1
            while True:
                response = await client.get(
                    f"{self.api_url}/repos/{repo}/issues",
                    headers=self.headers,
                    params={"page": page, "per_page": 100, "state": state},
                )
                response.raise_for_status()
                issues = response.json()

                if not issues:
                    break

                for issue in issues:
                    yield CrawlResult(
                        url=issue["html_url"],
                        content_type=ContentType.ISSUE,
                        title=issue["title"],
                        content=issue.get("body", ""),
                        metadata={
                            "number": issue["number"],
                            "state": issue["state"],
                            "labels": [l["name"] for l in issue.get("labels", [])],
                            "comments": issue["comments"],
                            "created_at": issue["created_at"],
                            "author": issue["user"]["login"],
                        },
                        source="github",
                    )

                page += 1

    async def _crawl_code(
        self, repo: str, depth: int, query: str = ""
    ) -> AsyncIterator[CrawlResult]:
        """Search code in repositories."""
        if not query:
            return

        await self.rate_limiter_api.wait_and_acquire()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/search/code",
                headers=self.headers,
                params={"q": f"{query} repo:{repo}", "per_page": 100},
            )
            response.raise_for_status()
            results = response.json().get("items", [])

            for item in results:
                yield CrawlResult(
                    url=item["html_url"],
                    content_type=ContentType.CODE,
                    title=item["name"],
                    content="",  # Would need separate fetch for content
                    metadata={
                        "path": item["path"],
                        "repository": item["repository"]["full_name"],
                        "score": item["score"],
                    },
                    source="github",
                )

    async def discover_urls(self, seed_url: str) -> AsyncIterator[str]:
        """Discover GitHub URLs."""
        # Parse seed to determine owner/org
        parts = seed_url.rstrip("/").split("/")
        owner = parts[-1] if len(parts) >= 4 else parts[-2]

        # Yield repos
        async with httpx.AsyncClient() as client:
            page = 1
            while True:
                response = await client.get(
                    f"{self.api_url}/users/{owner}/repos",
                    headers=self.headers,
                    params={"page": page, "per_page": 100},
                )
                response.raise_for_status()
                repos = response.json()

                if not repos:
                    break

                for repo in repos:
                    yield repo["html_url"]

                page += 1

    async def search_repositories(
        self,
        query: str,
        language: str | None = None,
        stars: str | None = None,
        limit: int = 100,
    ) -> AsyncIterator[CrawlResult]:
        """Search repositories with advanced query."""
        search_query = query
        if language:
            search_query += f" language:{language}"
        if stars:
            search_query += f" stars:>={stars}"

        await self.rate_limiter_api.wait_and_acquire()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/search/repositories",
                headers=self.headers,
                params={"q": search_query, "per_page": min(limit, 100)},
            )
            response.raise_for_status()
            results = response.json().get("items", [])

            for repo in results[:limit]:
                yield CrawlResult(
                    url=repo["html_url"],
                    content_type=ContentType.REPOSITORY,
                    title=repo["full_name"],
                    content=repo.get("description", ""),
                    metadata={
                        "stars": repo["stargazers_count"],
                        "language": repo["language"],
                        "forks": repo["forks_count"],
                        "topics": repo.get("topics", []),
                    },
                    source="github",
                )
