"""Academic source crawlers (arXiv, Semantic Scholar, PubMed)."""

from typing import AsyncIterator
from datetime import datetime

import httpx
import structlog
from xml.etree import ElementTree

from .base import BaseCrawler, CrawlerConfig, CrawlResult, ContentType


class ArxivCrawler(BaseCrawler):
    """Crawler for arXiv papers."""

    def __init__(self, config: CrawlerConfig | None = None, **kwargs):
        super().__init__("arxiv", config, **kwargs)
        self.api_url = "http://export.arxiv.org/api/query"
        # arXiv requires 3 second delay between requests
        self.rate_limiter.rate = 0.33

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
        """Crawl arXiv paper."""
        # Extract paper ID from URL
        paper_id = url.split("/abs/")[-1].split("/")[0]

        await self.rate_limiter.wait_and_acquire()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.api_url,
                params={"id_list": paper_id, "max_results": 1},
            )
            response.raise_for_status()

            root = ElementTree.fromstring(response.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            entry = root.find("atom:entry", ns)
            if entry is None:
                return

            yield self._parse_entry(entry, ns)

    def _parse_entry(self, entry, ns: dict) -> CrawlResult:
        """Parse arXiv Atom entry."""
        title = entry.find("atom:title", ns).text.strip()
        summary = entry.find("atom:summary", ns).text.strip()
        authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)]
        categories = [c.get("term") for c in entry.findall("atom:category", ns)]
        published = entry.find("atom:published", ns).text
        updated = entry.find("atom:updated", ns).text

        pdf_link = ""
        for link in entry.findall("atom:link", ns):
            if link.get("title") == "pdf":
                pdf_link = link.get("href", "")

        return CrawlResult(
            url=f"https://arxiv.org/abs/{entry.find('atom:id', ns).text.split('/')[-1]}",
            content_type=ContentType.PAPER,
            title=title,
            content=summary,
            metadata={
                "authors": authors,
                "categories": categories,
                "published": published,
                "updated": updated,
                "pdf_url": pdf_link,
            },
            source="arxiv",
        )

    async def search(
        self,
        query: str,
        max_results: int = 100,
        sort_by: str = "submittedDate",
        sort_order: str = "descending",
    ) -> AsyncIterator[CrawlResult]:
        """Search arXiv."""
        await self.rate_limiter.wait_and_acquire()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.api_url,
                params={
                    "search_query": f"all:{query}",
                    "max_results": max_results,
                    "sortBy": sort_by,
                    "sortOrder": sort_order,
                },
            )
            response.raise_for_status()

            root = ElementTree.fromstring(response.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            for entry in root.findall("atom:entry", ns):
                yield self._parse_entry(entry, ns)

    async def discover_urls(self, seed_url: str) -> AsyncIterator[str]:
        """Discover arXiv URLs."""
        # Could be implemented to crawl category listings
        pass


class SemanticScholarCrawler(BaseCrawler):
    """Crawler for Semantic Scholar papers."""

    def __init__(self, api_key: str = "", config: CrawlerConfig | None = None, **kwargs):
        super().__init__("semantic_scholar", config, **kwargs)
        self.api_key = api_key
        self.api_url = "https://api.semanticscholar.org/graph/v1"
        self.headers = {}
        if api_key:
            self.headers["x-api-key"] = api_key

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
        """Crawl a paper."""
        # Extract paper ID from URL
        paper_id = url.split("/")[-1]

        await self.rate_limiter.wait_and_acquire()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/paper/{paper_id}",
                headers=self.headers,
                params={
                    "fields": "title,abstract,authors,year,citationCount,fieldsOfStudy,references,citations",
                },
            )
            response.raise_for_status()
            paper = response.json()

            yield CrawlResult(
                url=paper.get("url", url),
                content_type=ContentType.PAPER,
                title=paper.get("title", ""),
                content=paper.get("abstract", ""),
                metadata={
                    "authors": [a.get("name") for a in paper.get("authors", [])],
                    "year": paper.get("year"),
                    "citation_count": paper.get("citationCount", 0),
                    "fields_of_study": paper.get("fieldsOfStudy", []),
                    "reference_count": len(paper.get("references", [])),
                    "citation_count": len(paper.get("citations", [])),
                },
                source="semantic_scholar",
            )

    async def search(
        self,
        query: str,
        fields: str = "title,abstract,authors,year,citationCount",
        limit: int = 100,
    ) -> AsyncIterator[CrawlResult]:
        """Search papers."""
        await self.rate_limiter.wait_and_acquire()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/paper/search",
                headers=self.headers,
                params={"query": query, "fields": fields, "limit": min(limit, 100)},
            )
            response.raise_for_status()
            data = response.json()

            for paper in data.get("data", []):
                yield CrawlResult(
                    url=f"https://www.semanticscholar.org/paper/{paper['paperId']}",
                    content_type=ContentType.PAPER,
                    title=paper.get("title", ""),
                    content=paper.get("abstract", ""),
                    metadata={
                        "authors": [a.get("name") for a in paper.get("authors", [])],
                        "year": paper.get("year"),
                        "citation_count": paper.get("citationCount", 0),
                    },
                    source="semantic_scholar",
                )

    async def get_paper_citations(
        self, paper_id: str, limit: int = 100
    ) -> AsyncIterator[CrawlResult]:
        """Get papers that cite this paper."""
        await self.rate_limiter.wait_and_acquire()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/paper/{paper_id}/citations",
                headers=self.headers,
                params={"fields": "title,abstract,year,citationCount", "limit": min(limit, 100)},
            )
            response.raise_for_status()
            data = response.json()

            for item in data.get("data", []):
                paper = item.get("citingPaper", {})
                if paper.get("paperId"):
                    yield CrawlResult(
                        url=f"https://www.semanticscholar.org/paper/{paper['paperId']}",
                        content_type=ContentType.PAPER,
                        title=paper.get("title", ""),
                        content=paper.get("abstract", ""),
                        metadata={
                            "year": paper.get("year"),
                            "citation_count": paper.get("citationCount", 0),
                        },
                        source="semantic_scholar",
                    )

    async def discover_urls(self, seed_url: str) -> AsyncIterator[str]:
        """Discover paper URLs."""
        pass
