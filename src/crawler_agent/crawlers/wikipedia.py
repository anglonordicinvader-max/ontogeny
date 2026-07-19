"""Wikipedia crawler using MediaWiki API."""

from collections.abc import AsyncIterator

import httpx
import structlog

from .base import BaseCrawler, ContentType, CrawlerConfig, CrawlResult


class WikipediaCrawler(BaseCrawler):
    """Crawler for Wikipedia articles."""

    def __init__(
        self,
        language: str = "en",
        config: CrawlerConfig | None = None,
        **kwargs,
    ):
        super().__init__("wikipedia", config, **kwargs)
        self.lang = language
        self.api_url = f"https://{language}.wikipedia.org/w/api.php"
        self.rate_limiter.rate = 5.0

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
        """Crawl a Wikipedia article."""
        # Extract title from URL
        title = url.split("/wiki/")[-1].replace("_", " ")
        async for result in self._fetch_article(title):
            yield result

    async def _fetch_article(self, title: str) -> AsyncIterator[CrawlResult]:
        """Fetch article content."""
        await self.rate_limiter.wait_and_acquire()

        async with httpx.AsyncClient() as client:
            # Get extract
            response = await client.get(
                self.api_url,
                params={
                    "action": "query",
                    "titles": title,
                    "prop": "extracts|categories|links|info",
                    "exintro": False,
                    "explaintext": True,
                    "cllimit": 50,
                    "pllimit": 100,
                    "inprop": "url",
                    "format": "json",
                },
            )
            response.raise_for_status()
            data = response.json()

            pages = data.get("query", {}).get("pages", {})
            for page_id, page in pages.items():
                if page_id == "-1":
                    continue

                categories = [
                    c["title"].replace("Category:", "") for c in page.get("categories", [])
                ]
                links = [l["title"] for l in page.get("links", [])]

                yield CrawlResult(
                    url=page.get("fullurl", f"https://{self.lang}.wikipedia.org/wiki/{title}"),
                    content_type=ContentType.DOCUMENTATION,
                    title=page.get("title", title),
                    content=page.get("extract", ""),
                    metadata={
                        "pageid": int(page_id),
                        "categories": categories[:50],
                        "links": links[:50],
                        "touched": page.get("touched"),
                        "lastrevid": page.get("lastrevid"),
                        "language": self.lang,
                    },
                    source="wikipedia",
                )

    async def search(self, query: str, limit: int = 20) -> AsyncIterator[CrawlResult]:
        """Search Wikipedia."""
        await self.rate_limiter.wait_and_acquire()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.api_url,
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "srlimit": min(limit, 50),
                    "srinfo": "totalhits",
                    "format": "json",
                },
            )
            response.raise_for_status()
            results = response.json().get("query", {}).get("search", [])

            for result in results[:limit]:
                async for article in self._fetch_article(result["title"]):
                    yield article

    async def get_random(self, count: int = 10) -> AsyncIterator[CrawlResult]:
        """Get random articles."""
        await self.rate_limiter.wait_and_acquire()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.api_url,
                params={
                    "action": "query",
                    "list": "random",
                    "rnlimit": min(count, 50),
                    "format": "json",
                },
            )
            response.raise_for_status()
            pages = response.json().get("query", {}).get("random", [])

            for page in pages:
                async for article in self._fetch_article(page["title"]):
                    yield article

    async def get_category_members(
        self, category: str, limit: int = 100
    ) -> AsyncIterator[CrawlResult]:
        """Get articles in a category."""
        await self.rate_limiter.wait_and_acquire()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.api_url,
                params={
                    "action": "query",
                    "list": "categorymembers",
                    "cmtitle": f"Category:{category}",
                    "cmlimit": min(limit, 500),
                    "cmtype": "page",
                    "format": "json",
                },
            )
            response.raise_for_status()
            members = response.json().get("query", {}).get("categorymembers", [])

            for member in members[:limit]:
                async for article in self._fetch_article(member["title"]):
                    yield article

    async def get_linked_articles(self, title: str, limit: int = 50) -> AsyncIterator[CrawlResult]:
        """Get articles linked from a page."""
        await self.rate_limiter.wait_and_acquire()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.api_url,
                params={
                    "action": "query",
                    "titles": title,
                    "prop": "links",
                    "pllimit": min(limit, 500),
                    "format": "json",
                },
            )
            response.raise_for_status()
            pages = response.json().get("query", {}).get("pages", {})

            for _page_id, page in pages.items():
                links = page.get("links", [])
                for link in links[:limit]:
                    async for article in self._fetch_article(link["title"]):
                        yield article

    async def discover_urls(self, seed_url: str) -> AsyncIterator[str]:
        """Discover Wikipedia URLs from a category."""
        async for article in self.get_category_members("Computer_programming", limit=100):
            yield article.url
