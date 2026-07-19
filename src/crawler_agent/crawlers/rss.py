"""RSS/Atom feed crawler."""

from collections.abc import AsyncIterator
from datetime import datetime

import httpx
import structlog
from bs4 import BeautifulSoup

from .base import BaseCrawler, ContentType, CrawlerConfig, CrawlResult


class RSSCrawler(BaseCrawler):
    """Crawler for RSS and Atom feeds."""

    def __init__(self, config: CrawlerConfig | None = None, **kwargs):
        super().__init__("rss", config, **kwargs)

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
        """Crawl an RSS/Atom feed."""
        await self.rate_limiter.wait_and_acquire()

        async with httpx.AsyncClient() as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if "xml" in content_type or url.endswith((".xml", ".rss", ".atom")):
                async for result in self._parse_feed(response.text, url):
                    yield result

    async def _parse_feed(self, xml_content: str, feed_url: str) -> AsyncIterator[CrawlResult]:
        """Parse RSS or Atom feed."""
        soup = BeautifulSoup(xml_content, "lxml-xml")

        # Detect feed type
        if soup.find("channel"):
            async for result in self._parse_rss(soup, feed_url):
                yield result
        elif soup.find("entry"):
            async for result in self._parse_atom(soup, feed_url):
                yield result

    async def _parse_rss(self, soup: BeautifulSoup, feed_url: str) -> AsyncIterator[CrawlResult]:
        """Parse RSS 2.0 feed."""
        channel = soup.find("channel")
        if not channel:
            return

        feed_title = channel.find("title").text if channel.find("title") else ""
        items = channel.find_all("item")

        for item in items:
            title = item.find("title").text if item.find("title") else ""
            link = item.find("link").text if item.find("link") else ""
            description = item.find("description").text if item.find("description") else ""
            pub_date = item.find("pubDate").text if item.find("pubDate") else ""
            author = item.find("author").text if item.find("author") else ""
            categories = [c.text for c in item.find_all("category")]

            yield CrawlResult(
                url=link or feed_url,
                content_type=ContentType.OTHER,
                title=title,
                content=description,
                metadata={
                    "feed_title": feed_title,
                    "feed_url": feed_url,
                    "pub_date": pub_date,
                    "author": author,
                    "categories": categories,
                },
                source="rss",
            )

    async def _parse_atom(self, soup: BeautifulSoup, feed_url: str) -> AsyncIterator[CrawlResult]:
        """Parse Atom feed."""
        entries = soup.find_all("entry")

        for entry in entries:
            title = entry.find("title").text if entry.find("title") else ""
            link_tag = entry.find("link")
            link = link_tag.get("href", "") if link_tag else ""
            summary = entry.find("summary").text if entry.find("summary") else ""
            content = entry.find("content").text if entry.find("content") else summary
            author_tag = entry.find("author")
            author = author_tag.find("name").text if author_tag and author_tag.find("name") else ""
            published = entry.find("published").text if entry.find("published") else ""
            updated = entry.find("updated").text if entry.find("updated") else ""
            categories = [c.get("term", "") for c in entry.find_all("category")]

            yield CrawlResult(
                url=link or feed_url,
                content_type=ContentType.OTHER,
                title=title,
                content=content[:5000],
                metadata={
                    "feed_url": feed_url,
                    "author": author,
                    "published": published,
                    "updated": updated,
                    "categories": categories,
                },
                source="rss",
            )

    async def discover_feeds(self, website_url: str) -> list[str]:
        """Discover RSS/Atom feeds from a website."""
        await self.rate_limiter.wait_and_acquire()

        async with httpx.AsyncClient() as client:
            response = await client.get(website_url, follow_redirects=True)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")
            feed_urls = []

            # Look for <link> tags
            for link in soup.find_all("link", type=["application/rss+xml", "application/atom+xml"]):
                href = link.get("href", "")
                if href:
                    if not href.startswith("http"):
                        from urllib.parse import urljoin

                        href = urljoin(website_url, href)
                    feed_urls.append(href)

            # Common feed paths
            common_paths = ["/feed", "/rss", "/atom.xml", "/rss.xml", "/feed.xml", "/index.xml"]
            for path in common_paths:
                feed_url = website_url.rstrip("/") + path
                try:
                    async with httpx.AsyncClient() as client:
                        resp = await client.head(feed_url, follow_redirects=True)
                        if resp.status_code == 200:
                            ct = resp.headers.get("content-type", "")
                            if "xml" in ct:
                                feed_urls.append(feed_url)
                except Exception:
                    pass

            return list(set(feed_urls))

    async def discover_urls(self, seed_url: str) -> AsyncIterator[str]:
        feeds = await self.discover_feeds(seed_url)
        for feed_url in feeds:
            async for result in self.crawl(feed_url):
                yield result.url
