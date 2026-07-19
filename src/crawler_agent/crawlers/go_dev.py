"""pkg.go.dev crawler for Go packages."""

from collections.abc import AsyncIterator

import httpx
import structlog

from .base import BaseCrawler, ContentType, CrawlerConfig, CrawlResult


class GoDevCrawler(BaseCrawler):
    """Crawler for Go packages via pkg.go.dev."""

    def __init__(self, config: CrawlerConfig | None = None, **kwargs):
        super().__init__("go_dev", config, **kwargs)
        self.api_url = "https://pkg.go.dev"

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
        package_path = url.replace("https://pkg.go.dev/", "").rstrip("/")
        async for result in self._get_package(package_path):
            yield result

    async def _get_package(self, package_path: str) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/{package_path}",
                headers={"Accept": "application/json"},
                follow_redirects=True,
            )
            if response.status_code == 200:
                try:
                    data = response.json()
                    yield CrawlResult(
                        url=f"{self.api_url}/{package_path}",
                        content_type=ContentType.REPOSITORY,
                        title=data.get("name", package_path),
                        content=data.get("synopsis", "")
                        + "\n\n"
                        + data.get("description", "")[:2000],
                        metadata={
                            "import_path": package_path,
                            "module_path": data.get("module", {}).get("path"),
                            "version": data.get("version"),
                            "license": data.get("license"),
                            "documentation": data.get("documentation"),
                            "repository": data.get("repository"),
                        },
                        source="go_dev",
                    )
                except Exception:
                    # Fallback to HTML scraping
                    async for result in self._scrape_package(package_path):
                        yield result

    async def _scrape_package(self, package_path: str) -> AsyncIterator[CrawlResult]:
        from bs4 import BeautifulSoup

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/{package_path}", follow_redirects=True)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "lxml")
                title = soup.find("h1", class_="AboveName")
                title_text = title.text.strip() if title else package_path
                synopsis = soup.find("div", class_="Documentation-synopsis")
                synopsis_text = synopsis.text.strip() if synopsis else ""

                yield CrawlResult(
                    url=f"{self.api_url}/{package_path}",
                    content_type=ContentType.REPOSITORY,
                    title=title_text,
                    content=synopsis_text,
                    metadata={"import_path": package_path, "source": "html_scrape"},
                    source="go_dev",
                )

    async def search_packages(self, query: str, limit: int = 50) -> AsyncIterator[CrawlResult]:
        await self.rate_limiter.wait_and_acquire()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/search",
                params={"q": query, "m": "package"},
                follow_redirects=True,
            )
            if response.status_code == 200:
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(response.text, "lxml")
                results = soup.select(".SearchSnippet")[:limit]
                for result in results:
                    title = result.select_one(".SearchSnippet-header-path")
                    synopsis = result.select_one(".SearchSnippet-synopsis")
                    if title:
                        yield CrawlResult(
                            url=f"{self.api_url}/{title.text.strip()}",
                            content_type=ContentType.REPOSITORY,
                            title=title.text.strip(),
                            content=synopsis.text.strip() if synopsis else "",
                            metadata={"platform": "go_dev"},
                            source="go_dev",
                        )

    async def discover_urls(self, seed_url: str) -> AsyncIterator[str]:
        popular = [
            "github.com/gin-gonic/gin",
            "github.com/gorilla/mux",
            "github.com/sirupsen/logrus",
            "github.com/stretchr/testify",
            "golang.org/x/text",
        ]
        for pkg in popular:
            yield f"https://pkg.go.dev/{pkg}"
