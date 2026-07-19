"""Pastebin crawler."""

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime

import httpx
import structlog
from bs4 import BeautifulSoup

from .base import BaseCrawler, ContentType, CrawlerConfig, CrawlResult


class PastebinCrawler(BaseCrawler):
    """Crawler for Pastebin paste dumps."""

    def __init__(
        self,
        api_key: str = "",
        config: CrawlerConfig | None = None,
        **kwargs,
    ):
        super().__init__("pastebin", config, **kwargs)
        self.api_key = api_key
        self.base_url = "https://pastebin.com"

    async def _setup(self) -> None:
        """Initialize session."""
        pass

    async def _cleanup(self) -> None:
        pass

    async def crawl(
        self,
        url: str,
        depth: int = 0,
        content_types: list[str] | None = None,
    ) -> AsyncIterator[CrawlResult]:
        """Crawl a paste."""
        # Extract paste key from URL
        paste_key = url.rstrip("/").split("/")[-1]
        if paste_key in ("archive", "search", "tools", "scraping"):
            # This is a listing page, not a paste
            async for result in self._crawl_listing(url):
                yield result
        else:
            async for result in self._fetch_paste(paste_key):
                yield result

    async def _fetch_paste(self, paste_key: str) -> AsyncIterator[CrawlResult]:
        """Fetch a single paste."""
        await self.rate_limiter.wait_and_acquire()

        async with httpx.AsyncClient() as client:
            # Raw content
            raw_url = f"{self.base_url}/raw/{paste_key}"
            response = await client.get(raw_url, follow_redirects=True)

            if response.status_code != 200:
                self.logger.warning(
                    "paste_fetch_failed", key=paste_key, status=response.status_code
                )
                return

            content = response.text

            # Try to get metadata from scrape API
            scrape_url = f"{self.base_url}/api/scrape"
            scrape_response = await client.post(
                scrape_url,
                data={"api_dev_key": self.api_key, "api_paste_key": paste_key},
            )

            metadata = {}
            if scrape_response.status_code == 200:
                data = scrape_response.json()
                metadata = {
                    "title": data.get("paste_title", ""),
                    "language": data.get("paste_format_long", ""),
                    "author": data.get("paste_user", ""),
                    "created_at": data.get("paste_create_date", ""),
                    "expires": data.get("paste_expire_date", ""),
                    "size": data.get("paste_size", 0),
                }

            yield CrawlResult(
                url=f"{self.base_url}/{paste_key}",
                content_type=ContentType.CODE,
                title=metadata.get("title", paste_key),
                content=content,
                metadata=metadata,
                source="pastebin",
            )

    async def _crawl_listing(self, url: str) -> AsyncIterator[CrawlResult]:
        """Crawl a listing page."""
        await self.rate_limiter.wait_and_acquire()

        async with httpx.AsyncClient() as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")
            paste_items = soup.select(".maintable a")

            for item in paste_items:
                href = item.get("href", "")
                if href.startswith("/") and len(href) > 1:
                    paste_key = href[1:]
                    async for result in self._fetch_paste(paste_key):
                        yield result

    async def search_pastes(
        self,
        query: str,
        language: str = "",
        limit: int = 100,
    ) -> AsyncIterator[CrawlResult]:
        """Search pastes."""
        await self.rate_limiter.wait_and_acquire()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/api_post.php",
                data={
                    "api_dev_key": self.api_key,
                    "api_option": "search",
                    "api_search_term": query,
                    "api_search_language": language,
                },
            )

            if response.status_code == 200:
                # Response is XML list of paste keys
                from xml.etree import ElementTree

                root = ElementTree.fromstring(response.text)
                paste_keys = [elem.text for elem in root.findall(".//paste_key")]

                for key in paste_keys[:limit]:
                    async for result in self._fetch_paste(key):
                        yield result

    async def get_recent_pastes(self, limit: int = 100) -> AsyncIterator[CrawlResult]:
        """Get recent public pastes."""
        await self.rate_limiter.wait_and_acquire()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/api_post.php",
                data={
                    "api_dev_key": self.api_key,
                    "api_option": "list",
                },
            )

            if response.status_code == 200:
                from xml.etree import ElementTree

                root = ElementTree.fromstring(response.text)
                for paste in root.findall(".//paste")[:limit]:
                    key = paste.find("paste_key").text
                    async for result in self._fetch_paste(key):
                        yield result

    async def discover_urls(self, seed_url: str) -> AsyncIterator[str]:
        """Discover paste URLs."""
        # Archive page contains recent pastes
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/archive")
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")
            links = soup.select("a[href]")

            for link in links:
                href = link.get("href", "")
                if href.startswith("/") and len(href) > 1 and not href.startswith("/archive"):
                    yield f"{self.base_url}{href}"
