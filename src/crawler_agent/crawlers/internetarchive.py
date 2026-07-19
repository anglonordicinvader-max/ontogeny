"""Internet Archive crawler (archive.org, Wayback Machine)."""

from collections.abc import AsyncIterator
from datetime import datetime

import httpx
import structlog

from .base import BaseCrawler, ContentType, CrawlerConfig, CrawlResult


class InternetArchiveCrawler(BaseCrawler):
    """Crawler for Internet Archive — books, papers, historical web, media."""

    def __init__(self, config: CrawlerConfig | None = None, **kwargs):
        super().__init__("internetarchive", config, **kwargs)
        self.base_url = "https://archive.org"
        self.search_url = f"{self.base_url}/advancedsearch.php"
        self.metadata_url = f"{self.base_url}/metadata"
        self.wayback_cdx_url = "https://web.archive.org/cdx/search/cdx"
        # Archive.org requests slower rate
        self.rate_limiter.rate = 2.0

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
        """Crawl an Internet Archive item or Wayback Machine snapshot."""
        if "archive.org/details/" in url:
            identifier = url.split("/details/")[-1].split("?")[0].split("/")[0]
            async for result in self._crawl_item(identifier):
                yield result
        elif "web.archive.org" in url:
            async for result in self._crawl_wayback(url):
                yield result
        else:
            # Try as identifier
            identifier = url.strip("/").split("/")[-1]
            async for result in self._crawl_item(identifier):
                yield result

    async def _crawl_item(self, identifier: str) -> AsyncIterator[CrawlResult]:
        """Crawl an archive.org item via metadata API."""
        try:
            response = await self._fetch(
                f"{self.metadata_url}/{identifier}",
                params={"output": "json"},
            )
            response.raise_for_status()
            data = response.json()

            metadata = data.get("metadata", {})
            files = data.get("files", [])

            title = metadata.get("title", identifier)
            description = metadata.get("description", "")
            if isinstance(description, list):
                description = " ".join(description)

            creator = metadata.get("creator", "")
            if isinstance(creator, list):
                creator = ", ".join(creator)

            subject = metadata.get("subject", "")
            if isinstance(subject, list):
                subject = ", ".join(subject)

            # Find text/book files
            text_files = [
                f for f in files if f.get("name", "").endswith((".txt", ".pdf", ".epub", ".djvu"))
            ]

            # Try to get full text if available
            full_text = ""
            txt_file = next((f for f in files if f.get("name", "").endswith(".txt")), None)
            if txt_file:
                try:
                    txt_response = await self._fetch(
                        f"{self.base_url}/stream/{identifier}/{txt_file['name']}",
                    )
                    if txt_response.status_code == 200:
                        full_text = txt_response.text[:5000]
                except Exception:
                    pass

            yield CrawlResult(
                url=f"https://archive.org/details/{identifier}",
                content_type=ContentType.DOCUMENTATION,
                title=title,
                content=full_text or description,
                metadata={
                    "identifier": identifier,
                    "creator": creator,
                    "date": metadata.get("date", ""),
                    "subject": subject,
                    "mediatype": metadata.get("mediatype", ""),
                    "language": metadata.get("language", ""),
                    "files_count": len(files),
                    "text_files": [f["name"] for f in text_files[:5]],
                    "reviews": metadata.get("num_reviews", 0),
                },
                source="internetarchive",
            )
        except Exception as e:
            self.logger.warning("ia_item_failed", identifier=identifier, error=str(e))

    async def _crawl_wayback(self, url: str) -> AsyncIterator[CrawlResult]:
        """Crawl a Wayback Machine snapshot."""
        # Extract original URL from wayback URL
        # Format: https://web.archive.org/web/{timestamp}/{original_url}
        parts = url.replace("https://web.archive.org/web/", "").split("/", 1)
        parts[0] if len(parts) > 1 else "*"
        original_url = parts[1] if len(parts) > 1 else parts[0]

        try:
            # Get available snapshots
            response = await self._fetch(
                self.wayback_cdx_url,
                params={
                    "url": original_url,
                    "output": "json",
                    "limit": 5,
                    "fl": "timestamp,original,statuscode,mimetype",
                },
            )
            response.raise_for_status()
            rows = response.json()

            if len(rows) < 2:  # First row is header
                return

            for row in rows[1:]:
                ts, orig, status, mime = row[0], row[1], row[2], row[3]
                if status != "200":
                    continue

                snapshot_url = f"https://web.archive.org/web/{ts}/{orig}"

                yield CrawlResult(
                    url=snapshot_url,
                    content_type=ContentType.DOCUMENTATION,
                    title=f"Archived: {orig}",
                    content=f"Wayback Machine snapshot from {ts[:4]}/{ts[4:6]}/{ts[6:8]}",
                    metadata={
                        "original_url": orig,
                        "timestamp": ts,
                        "status_code": status,
                        "mime_type": mime,
                        "archived_date": f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}",
                    },
                    source="internetarchive",
                )
        except Exception as e:
            self.logger.warning("wayback_failed", url=url, error=str(e))

    async def search(
        self,
        query: str,
        limit: int = 10,
        media_type: str = "",
        sort: str = "downloads desc",
    ) -> AsyncIterator[CrawlResult]:
        """Search Internet Archive using advanced search API."""
        params = {
            "q": query,
            "fl[]": [
                "identifier",
                "title",
                "description",
                "mediatype",
                "creator",
                "date",
                "downloads",
            ],
            "rows": limit,
            "page": 1,
            "output": "json",
            "sort[]": sort,
        }
        if media_type:
            params["q"] += f" AND mediatype:{media_type}"

        try:
            response = await self._fetch(self.search_url, params=params)
            response.raise_for_status()
            data = response.json()

            docs = data.get("response", {}).get("docs", [])
            for doc in docs:
                desc = doc.get("description", "")
                if isinstance(desc, list):
                    desc = " ".join(desc)

                yield CrawlResult(
                    url=f"https://archive.org/details/{doc.get('identifier', '')}",
                    content_type=ContentType.DOCUMENTATION,
                    title=doc.get("title", ""),
                    content=desc,
                    metadata={
                        "identifier": doc.get("identifier", ""),
                        "mediatype": doc.get("mediatype", ""),
                        "creator": doc.get("creator", ""),
                        "date": doc.get("date", ""),
                        "downloads": doc.get("downloads", 0),
                    },
                    source="internetarchive",
                )
        except Exception as e:
            self.logger.warning("ia_search_failed", query=query, error=str(e))

    async def search_books(self, query: str, limit: int = 10) -> AsyncIterator[CrawlResult]:
        """Search for books/text items specifically."""
        async for result in self.search(query, limit=limit, media_type="texts"):
            yield result

    async def search_audio(self, query: str, limit: int = 10) -> AsyncIterator[CrawlResult]:
        """Search for audio items."""
        async for result in self.search(query, limit=limit, media_type="audio"):
            yield result

    async def search_video(self, query: str, limit: int = 10) -> AsyncIterator[CrawlResult]:
        """Search for video items."""
        async for result in self.search(query, limit=limit, media_type="movies"):
            yield result

    async def search_software(self, query: str, limit: int = 10) -> AsyncIterator[CrawlResult]:
        """Search for software items."""
        async for result in self.search(query, limit=limit, media_type="software"):
            yield result

    async def search_images(self, query: str, limit: int = 10) -> AsyncIterator[CrawlResult]:
        """Search for image items."""
        async for result in self.search(query, limit=limit, media_type="image"):
            yield result

    async def get_wayback_snapshots(self, url: str, limit: int = 10) -> AsyncIterator[CrawlResult]:
        """Get all Wayback Machine snapshots for a URL."""
        async for result in self._crawl_wayback(f"https://web.archive.org/web/*/{url}"):
            yield result

    async def discover_urls(self, seed_url: str) -> AsyncIterator[str]:
        """Discover archive.org URLs from a seed."""
        yield f"https://archive.org/details/{seed_url}"
