"""Generic web scraper for arbitrary sites."""

from collections.abc import AsyncIterator
from urllib.parse import urljoin, urlparse

import httpx
import structlog
from bs4 import BeautifulSoup

from .base import BaseCrawler, ContentType, CrawlerConfig, CrawlResult


class WebScraperCrawler(BaseCrawler):
    """Generic web scraper for arbitrary websites."""

    def __init__(
        self,
        config: CrawlerConfig | None = None,
        **kwargs,
    ):
        super().__init__("webscraper", config, **kwargs)
        self.visited: set[str] = set()

    async def _setup(self) -> None:
        pass

    async def _cleanup(self) -> None:
        self.visited.clear()

    async def crawl(
        self,
        url: str,
        depth: int = 0,
        content_types: list[str] | None = None,
    ) -> AsyncIterator[CrawlResult]:
        """Crawl a URL and extract content."""
        if url in self.visited or depth > (content_types or [3])[0] if content_types else 3:
            return
        self.visited.add(url)

        await self.rate_limiter.wait_and_acquire()

        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()

                content_type = response.headers.get("content-type", "")

                # Skip non-HTML content
                if "text/html" not in content_type:
                    return

                soup = BeautifulSoup(response.text, "lxml")

                # Extract main content
                title = soup.title.string if soup.title else ""
                content = self._extract_content(soup)
                links = self._extract_links(soup, url)
                metadata = self._extract_metadata(soup)

                yield CrawlResult(
                    url=url,
                    content_type=ContentType.DOCUMENTATION,
                    title=title or url,
                    content=content,
                    metadata={
                        **metadata,
                        "links_count": len(links),
                        "content_type": content_type,
                        "status_code": response.status_code,
                    },
                    source="webscraper",
                )

        except Exception as e:
            self.logger.warning("scrape_failed", url=url, error=str(e))

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extract main text content from page."""
        # Remove script and style elements
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        # Try to find main content
        main = soup.find("main") or soup.find("article") or soup.find("body")
        if main:
            text = main.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)

        # Clean up whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)[:10000]  # Limit content size

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        """Extract all links from page."""
        links = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)

            # Only HTTP(S) links
            if parsed.scheme in ("http", "https"):
                links.append(full_url)

        return list(set(links))

    def _extract_metadata(self, soup: BeautifulSoup) -> dict:
        """Extract metadata from page."""
        metadata = {}

        # Meta tags
        for meta in soup.find_all("meta"):
            name = meta.get("name", "").lower()
            property_ = meta.get("property", "").lower()
            content = meta.get("content", "")

            if name == "description" or property_ == "og:description":
                metadata["description"] = content
            elif name == "keywords":
                metadata["keywords"] = [k.strip() for k in content.split(",")]
            elif property_ == "og:title":
                metadata["og_title"] = content
            elif property_ == "og:type":
                metadata["og_type"] = content
            elif name == "author":
                metadata["author"] = content

        # Structured data (JSON-LD)
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                import json

                data = json.loads(script.string)
                if isinstance(data, dict):
                    metadata["structured_data"] = data
            except Exception:
                pass

        return metadata

    async def crawl_site(
        self,
        start_url: str,
        max_pages: int = 100,
        same_domain: bool = True,
    ) -> AsyncIterator[CrawlResult]:
        """Crawl multiple pages from a site."""
        self.visited.clear()
        queue = [start_url]
        domain = urlparse(start_url).netloc

        while queue and len(self.visited) < max_pages:
            url = queue.pop(0)

            if same_domain and urlparse(url).netloc != domain:
                continue

            async for result in self.crawl(url):
                yield result

                # Add discovered links to queue
                links = result.metadata.get("links_count", 0)
                if links > 0:
                    async with httpx.AsyncClient(follow_redirects=True) as client:
                        try:
                            resp = await client.get(url)
                            soup = BeautifulSoup(resp.text, "lxml")
                            for a_tag in soup.find_all("a", href=True):
                                new_url = urljoin(url, a_tag["href"])
                                if new_url not in self.visited:
                                    queue.append(new_url)
                        except Exception:
                            pass

    async def discover_urls(self, seed_url: str) -> AsyncIterator[str]:
        """Discover URLs from a starting page."""
        await self.rate_limiter.wait_and_acquire()

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(seed_url)
            soup = BeautifulSoup(response.text, "lxml")

            for link in self._extract_links(soup, seed_url):
                yield link
