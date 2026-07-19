"""HuggingFace Hub crawler."""

from collections.abc import AsyncIterator

import httpx
import structlog

from .base import BaseCrawler, ContentType, CrawlerConfig, CrawlResult


class HuggingFaceCrawler(BaseCrawler):
    """Crawler for HuggingFace models, datasets, and spaces."""

    def __init__(
        self,
        token: str = "",
        config: CrawlerConfig | None = None,
        **kwargs,
    ):
        super().__init__("huggingface", config, **kwargs)
        self.token = token
        self.api_url = "https://huggingface.co/api"
        self.headers = {}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    async def _setup(self) -> None:
        """Verify HuggingFace access."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/whoami", headers=self.headers)
            if response.status_code == 200:
                user = response.json().get("name", "anonymous")
                self.logger.info("huggingface_connected", user=user)
            else:
                self.logger.warning("huggingface_limited_access")

    async def _cleanup(self) -> None:
        pass

    async def crawl(
        self,
        url: str,
        depth: int = 0,
        content_types: list[str] | None = None,
    ) -> AsyncIterator[CrawlResult]:
        """Crawl HuggingFace content."""
        content_types = content_types or ["models", "datasets", "spaces"]

        if "models" in content_types:
            async for result in self._crawl_models(limit=100):
                yield result

        if "datasets" in content_types:
            async for result in self._crawl_datasets(limit=100):
                yield result

        if "spaces" in content_types:
            async for result in self._crawl_spaces(limit=100):
                yield result

    async def _crawl_models(self, limit: int = 100) -> AsyncIterator[CrawlResult]:
        """Crawl trending models."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/models",
                headers=self.headers,
                params={"sort": "trending", "direction": "-1", "limit": limit},
            )
            response.raise_for_status()
            models = response.json()

            for model in models:
                yield CrawlResult(
                    url=f"https://huggingface.co/{model['id']}",
                    content_type=ContentType.MODEL,
                    title=model["id"],
                    content=model.get("pipeline_tag", ""),
                    metadata={
                        "downloads": model.get("downloads", 0),
                        "likes": model.get("likes", 0),
                        "pipeline_tag": model.get("pipeline_tag"),
                        "tags": model.get("tags", []),
                        "author": model.get("author"),
                        "last_modified": model.get("lastModified"),
                    },
                    source="huggingface",
                )

    async def _crawl_datasets(self, limit: int = 100) -> AsyncIterator[CrawlResult]:
        """Crawl trending datasets."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/datasets",
                headers=self.headers,
                params={"sort": "trending", "direction": "-1", "limit": limit},
            )
            response.raise_for_status()
            datasets = response.json()

            for ds in datasets:
                yield CrawlResult(
                    url=f"https://huggingface.co/datasets/{ds['id']}",
                    content_type=ContentType.DATASET,
                    title=ds["id"],
                    content=ds.get("description", ""),
                    metadata={
                        "downloads": ds.get("downloads", 0),
                        "likes": ds.get("likes", 0),
                        "tags": ds.get("tags", []),
                        "author": ds.get("author"),
                        "last_modified": ds.get("lastModified"),
                    },
                    source="huggingface",
                )

    async def _crawl_spaces(self, limit: int = 100) -> AsyncIterator[CrawlResult]:
        """Crawl trending spaces."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/spaces",
                headers=self.headers,
                params={"sort": "trending", "direction": "-1", "limit": limit},
            )
            response.raise_for_status()
            spaces = response.json()

            for space in spaces:
                yield CrawlResult(
                    url=f"https://huggingface.co/spaces/{space['id']}",
                    content_type=ContentType.OTHER,
                    title=space["id"],
                    content=space.get("sdk", ""),
                    metadata={
                        "sdk": space.get("sdk"),
                        "likes": space.get("likes", 0),
                        "author": space.get("author"),
                        "last_modified": space.get("lastModified"),
                    },
                    source="huggingface",
                )

    async def search_models(
        self,
        query: str,
        task: str | None = None,
        library: str | None = None,
        limit: int = 50,
    ) -> AsyncIterator[CrawlResult]:
        """Search models with filters."""
        params: dict = {"search": query, "limit": limit}
        if task:
            params["filter"] = task
        if library:
            params["filter"] = library

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/models",
                headers=self.headers,
                params=params,
            )
            response.raise_for_status()
            models = response.json()

            for model in models:
                yield CrawlResult(
                    url=f"https://huggingface.co/{model['id']}",
                    content_type=ContentType.MODEL,
                    title=model["id"],
                    content=model.get("pipeline_tag", ""),
                    metadata={
                        "downloads": model.get("downloads", 0),
                        "likes": model.get("likes", 0),
                        "pipeline_tag": model.get("pipeline_tag"),
                        "tags": model.get("tags", []),
                    },
                    source="huggingface",
                )

    async def discover_urls(self, seed_url: str) -> AsyncIterator[str]:
        """Discover HuggingFace URLs."""
        # Fetch all model URLs
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/models",
                headers=self.headers,
                params={"limit": 1000},
            )
            response.raise_for_status()
            models = response.json()

            for model in models:
                yield f"https://huggingface.co/{model['id']}"
