"""GitLab crawler."""

from typing import AsyncIterator

import httpx
import structlog

from .base import BaseCrawler, CrawlerConfig, CrawlResult, ContentType


class GitLabCrawler(BaseCrawler):
    """Crawler for GitLab repositories, issues, and merge requests."""

    def __init__(
        self,
        token: str,
        instance_url: str = "https://gitlab.com",
        config: CrawlerConfig | None = None,
        **kwargs,
    ):
        super().__init__("gitlab", config, **kwargs)
        self.token = token
        self.api_url = f"{instance_url}/api/v4"
        self.headers = {"PRIVATE-TOKEN": token}

    async def _setup(self) -> None:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/user", headers=self.headers)
            response.raise_for_status()
            user = response.json()
            self.logger.info("gitlab_connected", user=user["username"])

    async def _cleanup(self) -> None:
        pass

    async def crawl(
        self,
        url: str,
        depth: int = 0,
        content_types: list[str] | None = None,
    ) -> AsyncIterator[CrawlResult]:
        content_types = content_types or ["projects", "issues", "merge_requests"]

        if "projects" in content_types:
            async for result in self._crawl_projects():
                yield result

        if "issues" in content_types:
            async for result in self._crawl_issues(url):
                yield result

        if "merge_requests" in content_types:
            async for result in self._crawl_merge_requests(url):
                yield result

    async def _crawl_projects(self, owned: bool = False) -> AsyncIterator[CrawlResult]:
        async with httpx.AsyncClient() as client:
            params = {"per_page": 100, "order_by": "last_activity_at"}
            if owned:
                params["owned"] = "true"

            page = 1
            while True:
                response = await client.get(
                    f"{self.api_url}/projects",
                    headers=self.headers,
                    params={**params, "page": page},
                )
                response.raise_for_status()
                projects = response.json()
                if not projects:
                    break

                for proj in projects:
                    yield CrawlResult(
                        url=proj["web_url"],
                        content_type=ContentType.REPOSITORY,
                        title=proj["path_with_namespace"],
                        content=proj.get("description", ""),
                        metadata={
                            "stars": proj.get("star_count", 0),
                            "forks": proj.get("forks_count", 0),
                            "language": proj.get("language"),
                            "default_branch": proj.get("default_branch"),
                            "visibility": proj.get("visibility"),
                            "topics": proj.get("topics", []),
                        },
                        source="gitlab",
                    )
                page += 1

    async def _crawl_issues(self, project_id: str) -> AsyncIterator[CrawlResult]:
        async with httpx.AsyncClient() as client:
            page = 1
            while True:
                response = await client.get(
                    f"{self.api_url}/projects/{project_id}/issues",
                    headers=self.headers,
                    params={"per_page": 100, "page": page},
                )
                response.raise_for_status()
                issues = response.json()
                if not issues:
                    break

                for issue in issues:
                    yield CrawlResult(
                        url=issue["web_url"],
                        content_type=ContentType.ISSUE,
                        title=issue["title"],
                        content=issue.get("description", ""),
                        metadata={
                            "iid": issue["iid"],
                            "state": issue["state"],
                            "labels": issue.get("labels", []),
                            "author": issue["author"]["username"],
                            "created_at": issue["created_at"],
                            "comments": issue.get("user_notes_count", 0),
                        },
                        source="gitlab",
                    )
                page += 1

    async def _crawl_merge_requests(self, project_id: str) -> AsyncIterator[CrawlResult]:
        async with httpx.AsyncClient() as client:
            page = 1
            while True:
                response = await client.get(
                    f"{self.api_url}/projects/{project_id}/merge_requests",
                    headers=self.headers,
                    params={"per_page": 100, "page": page},
                )
                response.raise_for_status()
                mrs = response.json()
                if not mrs:
                    break

                for mr in mrs:
                    yield CrawlResult(
                        url=mr["web_url"],
                        content_type=ContentType.ISSUE,
                        title=mr["title"],
                        content=mr.get("description", ""),
                        metadata={
                            "iid": mr["iid"],
                            "state": mr["state"],
                            "author": mr["author"]["username"],
                            "source_branch": mr["source_branch"],
                            "target_branch": mr["target_branch"],
                            "created_at": mr["created_at"],
                            "labels": mr.get("labels", []),
                        },
                        source="gitlab",
                    )
                page += 1

    async def search_projects(self, query: str, limit: int = 50) -> AsyncIterator[CrawlResult]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/projects",
                headers=self.headers,
                params={"search": query, "per_page": min(limit, 100)},
            )
            response.raise_for_status()
            for proj in response.json()[:limit]:
                yield CrawlResult(
                    url=proj["web_url"],
                    content_type=ContentType.REPOSITORY,
                    title=proj["path_with_namespace"],
                    content=proj.get("description", ""),
                    metadata={
                        "stars": proj.get("star_count", 0),
                        "forks": proj.get("forks_count", 0),
                        "language": proj.get("language"),
                    },
                    source="gitlab",
                )

    async def discover_urls(self, seed_url: str) -> AsyncIterator[str]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/projects",
                headers=self.headers,
                params={"per_page": 100, "order_by": "last_activity_at"},
            )
            for proj in response.json():
                yield proj["web_url"]
