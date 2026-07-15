"""GitHub Code Search, Papers With Code, HF Hub, and GitHub Trending crawlers."""

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import quote

from .base import BaseCrawler, CrawlResult, ContentType, CrawlerConfig


class GitHubCodeSearchCrawler(BaseCrawler):
    """Search GitHub code using the Search API."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str = "", config: CrawlerConfig | None = None, proxy_pool: Any = None):
        super().__init__(config, proxy_pool)
        self.token = token

    async def _get_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "OntogenyCrawler/1.0",
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    async def search_code(
        self,
        query: str,
        limit: int = 30,
        language: str | None = None,
        repo: str | None = None,
    ) -> list[CrawlResult]:
        """Search GitHub code."""
        q = query
        if language:
            q += f" language:{language}"
        if repo:
            q += f" repo:{repo}"

        params = {
            "q": q,
            "per_page": min(limit, 100),
            "sort": "indexed",
            "order": "desc",
        }

        url = f"{self.BASE_URL}/search/code"
        headers = await self._get_headers()

        results = []
        async with self.session.get(url, params=params, headers=headers, proxy=self._get_proxy()) as resp:
            if resp.status == 200:
                data = await resp.json()
                for item in data.get("items", [])[:limit]:
                    result = CrawlResult(
                        url=item["html_url"],
                        title=f"{item['name']} in {item['repository']['full_name']}",
                        content=f"Path: {item['path']}\nRepo: {item['repository']['full_name']}\nURL: {item['html_url']}",
                        source="github_code_search",
                        content_type=ContentType.CODE,
                        metadata={
                            "repository": item["repository"]["full_name"],
                            "path": item["path"],
                            "sha": item["sha"],
                            "language": language,
                        },
                        timestamp=datetime.utcnow(),
                    )
                    results.append(result)
            elif resp.status == 403:
                # Rate limited
                pass

        return results

    async def search_repositories(
        self,
        query: str,
        limit: int = 30,
        sort: str = "stars",
        order: str = "desc",
    ) -> list[CrawlResult]:
        """Search GitHub repositories."""
        params = {
            "q": query,
            "per_page": min(limit, 100),
            "sort": sort,
            "order": order,
        }

        url = f"{self.BASE_URL}/search/repositories"
        headers = await self._get_headers()

        results = []
        async with self.session.get(url, params=params, headers=headers, proxy=self._get_proxy()) as resp:
            if resp.status == 200:
                data = await resp.json()
                for item in data.get("items", [])[:limit]:
                    result = CrawlResult(
                        url=item["html_url"],
                        title=item["full_name"],
                        content=item["description"] or "",
                        source="github_repo_search",
                        content_type=ContentType.REPOSITORY,
                        metadata={
                            "stars": item["stargazers_count"],
                            "forks": item["forks_count"],
                            "language": item["language"],
                            "topics": item.get("topics", []),
                        },
                        timestamp=datetime.utcnow(),
                    )
                    results.append(result)

        return results

    async def crawl(self, url: str, **kwargs) -> list[CrawlResult]:
        return []

    async def search(self, query: str, limit: int = 30, **kwargs) -> list[CrawlResult]:
        return await self.search_code(query, limit, **kwargs)


class PapersWithCodeCrawler(BaseCrawler):
    """Crawl Papers With Code for ML papers with implementations."""

    BASE_URL = "https://paperswithcode.com/api/v1"

    async def search_papers(
        self,
        query: str,
        limit: int = 30,
    ) -> list[CrawlResult]:
        """Search papers."""
        url = f"{self.BASE_URL}/papers/"
        params = {"q": query, "page": 1, "items_per_page": limit}

        results = []
        async with self.session.get(url, params=params, proxy=self._get_proxy()) as resp:
            if resp.status == 200:
                data = await resp.json()
                for item in data.get("results", []):
                    paper_url = f"https://paperswithcode.com{item['url']}"
                    repos = item.get("repositories", [])
                    repo_info = ""
                    if repos:
                        repo_info = f"\nRepo: {repos[0].get('url', '')}\nStars: {repos[0].get('stars', 0)}"

                    result = CrawlResult(
                        url=paper_url,
                        title=item["title"],
                        content=f"{item.get('abstract', '')}{repo_info}",
                        source="papers_with_code",
                        content_type=ContentType.PAPER,
                        metadata={
                            "authors": [a["name"] for a in item.get("authors", [])],
                            "published": item.get("published"),
                            "arxiv_id": item.get("arxiv_id"),
                            "tasks": [t["name"] for t in item.get("tasks", [])],
                            "datasets": [d["name"] for d in item.get("datasets", [])],
                            "repositories": repos,
                        },
                        timestamp=datetime.utcnow(),
                    )
                    results.append(result)

        return results

    async def get_paper_repositories(self, paper_id: str) -> list[CrawlResult]:
        """Get repositories for a paper."""
        url = f"{self.BASE_URL}/papers/{paper_id}/repositories/"

        results = []
        async with self.session.get(url, proxy=self._get_proxy()) as resp:
            if resp.status == 200:
                data = await resp.json()
                for repo in data.get("results", []):
                    result = CrawlResult(
                        url=repo["url"],
                        title=f"{repo['name']} - {repo.get('description', '')}",
                        content=f"Stars: {repo.get('stars', 0)}\nFramework: {repo.get('framework', '')}",
                        source="papers_with_code_repo",
                        content_type=ContentType.REPOSITORY,
                        metadata={
                            "paper_id": paper_id,
                            "stars": repo.get("stars", 0),
                            "framework": repo.get("framework"),
                            "license": repo.get("license"),
                        },
                        timestamp=datetime.utcnow(),
                    )
                    results.append(result)

        return results

    async def crawl(self, url: str, **kwargs) -> list[CrawlResult]:
        return []

    async def search(self, query: str, limit: int = 30, **kwargs) -> list[CrawlResult]:
        return await self.search_papers(query, limit)


class HuggingFaceHubCrawler(BaseCrawler):
    """Crawl Hugging Face Hub for models, datasets, and spaces."""

    BASE_URL = "https://huggingface.co/api"

    def __init__(self, token: str = "", config: CrawlerConfig | None = None, proxy_pool: Any = None):
        super().__init__(config, proxy_pool)
        self.token = token

    async def _get_headers(self) -> dict[str, str]:
        headers = {"User-Agent": "OntogenyCrawler/1.0"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def search_models(
        self,
        query: str,
        limit: int = 30,
        task: str | None = None,
        library: str | None = None,
    ) -> list[CrawlResult]:
        """Search models."""
        url = f"{self.BASE_URL}/models"
        params = {"search": query, "limit": limit, "full": "true"}
        if task:
            params["filter"] = task
        if library:
            params["library"] = library

        headers = await self._get_headers()
        results = []

        async with self.session.get(url, params=params, headers=headers, proxy=self._get_proxy()) as resp:
            if resp.status == 200:
                data = await resp.json()
                for item in data:
                    result = CrawlResult(
                        url=f"https://huggingface.co/{item['modelId']}",
                        title=item["modelId"],
                        content=item.get("description", "") or item.get("readme", "")[:500],
                        source="hf_hub_model",
                        content_type=ContentType.MODEL,
                        metadata={
                            "downloads": item.get("downloads", 0),
                            "likes": item.get("likes", 0),
                            "tags": item.get("tags", []),
                            "pipeline_tag": item.get("pipeline_tag"),
                            "library": item.get("library_name"),
                        },
                        timestamp=datetime.utcnow(),
                    )
                    results.append(result)

        return results

    async def search_datasets(
        self,
        query: str,
        limit: int = 30,
    ) -> list[CrawlResult]:
        """Search datasets."""
        url = f"{self.BASE_URL}/datasets"
        params = {"search": query, "limit": limit}

        headers = await self._get_headers()
        results = []

        async with self.session.get(url, params=params, headers=headers, proxy=self._get_proxy()) as resp:
            if resp.status == 200:
                data = await resp.json()
                for item in data:
                    result = CrawlResult(
                        url=f"https://huggingface.co/datasets/{item['id']}",
                        title=item["id"],
                        content=item.get("description", "")[:500],
                        source="hf_hub_dataset",
                        content_type=ContentType.DATASET,
                        metadata={
                            "downloads": item.get("downloads", 0),
                            "likes": item.get("likes", 0),
                            "tags": item.get("tags", []),
                        },
                        timestamp=datetime.utcnow(),
                    )
                    results.append(result)

        return results

    async def search_spaces(
        self,
        query: str,
        limit: int = 30,
    ) -> list[CrawlResult]:
        """Search Spaces (demos)."""
        url = f"{self.BASE_URL}/spaces"
        params = {"search": query, "limit": limit}

        headers = await self._get_headers()
        results = []

        async with self.session.get(url, params=params, headers=headers, proxy=self._get_proxy()) as resp:
            if resp.status == 200:
                data = await resp.json()
                for item in data:
                    result = CrawlResult(
                        url=f"https://huggingface.co/spaces/{item['id']}",
                        title=item["id"],
                        content=item.get("description", "")[:500],
                        source="hf_hub_space",
                        content_type=ContentType.APPLICATION,
                        metadata={
                            "likes": item.get("likes", 0),
                            "sdk": item.get("sdk"),
                        },
                        timestamp=datetime.utcnow(),
                    )
                    results.append(result)

        return results

    async def crawl(self, url: str, **kwargs) -> list[CrawlResult]:
        return []

    async def search(self, query: str, limit: int = 30, **kwargs) -> list[CrawlResult]:
        return await self.search_models(query, limit, **kwargs)


class GitHubTrendingCrawler(BaseCrawler):
    """Crawl GitHub Trending repositories."""

    BASE_URL = "https://github.com/trending"

    async def get_trending(
        self,
        language: str | None = None,
        since: str = "daily",  # daily, weekly, monthly
        limit: int = 30,
    ) -> list[CrawlResult]:
        """Get trending repositories."""
        params = {"since": since}
        if language:
            params["language"] = language

        url = self.BASE_URL
        results = []

        async with self.session.get(url, params=params, proxy=self._get_proxy()) as resp:
            if resp.status == 200:
                html = await resp.text()
                # Parse HTML for trending repos
                results = self._parse_trending(html, limit)

        return results

    def _parse_trending(self, html: str, limit: int) -> list[CrawlResult]:
        """Parse trending page HTML."""
        results = []
        # Simple regex parsing - in production would use BeautifulSoup
        repo_pattern = r'<article class="Box-row">.*?<h2 class="h3 lh-condensed">\s*<a href="(/[^"]+)".*?>(.*?)</a>.*?</h2>.*?<p class="col-9 color-fg-muted my-1 pr-4">(.*?)</p>.*?<span class="d-inline-block float-sm-right">(.*?)</span>'
        matches = re.findall(repo_pattern, html, re.DOTALL)

        for match in matches[:limit]:
            path, name, desc, stars = match
            name = name.strip()
            desc = re.sub(r"<[^>]+>", "", desc).strip()
            stars = re.sub(r"<[^>]+>", "", stars).strip()

            results.append(CrawlResult(
                url=f"https://github.com{path}",
                title=name,
                content=f"{desc}\nStars today: {stars}",
                source="github_trending",
                content_type=ContentType.REPOSITORY,
                metadata={
                    "language": None,  # Would extract from HTML
                    "stars_today": stars,
                },
                timestamp=datetime.utcnow(),
            ))

        return results

    async def crawl(self, url: str, **kwargs) -> list[CrawlResult]:
        return []

    async def search(self, query: str, limit: int = 30, **kwargs) -> list[CrawlResult]:
        return await self.get_trending(limit=limit)