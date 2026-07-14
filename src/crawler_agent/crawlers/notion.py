"""Notion crawler using official API."""

from typing import AsyncIterator
from datetime import datetime

import httpx
import structlog

from .base import BaseCrawler, CrawlerConfig, CrawlResult, ContentType


class NotionCrawler(BaseCrawler):
    """Crawler for Notion pages and databases."""

    def __init__(
        self,
        api_key: str = "",
        config: CrawlerConfig | None = None,
        **kwargs,
    ):
        super().__init__("notion", config, **kwargs)
        self.api_key = api_key
        self.api_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": "2022-06-28",
        } if api_key else {}

    async def _setup(self) -> None:
        if self.api_key:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/search",
                    headers=self.headers,
                    json={"page_size": 1},
                )
                if response.status_code == 200:
                    self.logger.info("notion_connected")

    async def _cleanup(self) -> None:
        pass

    async def crawl(
        self,
        url: str,
        depth: int = 0,
        content_types: list[str] | None = None,
    ) -> AsyncIterator[CrawlResult]:
        # Extract page/database ID from Notion URL
        parts = url.rstrip("/").split("/")
        if len(parts) >= 5:
            page_id = parts[-1].split("?")[0]
            if len(page_id) == 32:
                # Format as UUID
                page_id = f"{page_id[:8]}-{page_id[8:12]}-{page_id[12:16]}-{page_id[16:20]}-{page_id[20:]}"
            async for result in self._get_page(page_id):
                yield result

    async def _get_page(self, page_id: str) -> AsyncIterator[CrawlResult]:
        """Get a Notion page."""
        await self.rate_limiter.wait_and_acquire()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/pages/{page_id}",
                headers=self.headers,
            )
            response.raise_for_status()
            page = response.json()

            # Extract title
            title_prop = page.get("properties", {}).get("title", {})
            title = ""
            if title_prop.get("type") == "title":
                title = "".join(t.get("plain_text", "") for t in title_prop.get("title", []))

            # Get content blocks
            content = await self._get_block_children(page_id)

            yield CrawlResult(
                url=page.get("url", f"https://notion.so/{page_id.replace('-', '')}"),
                content_type=ContentType.DOCUMENTATION,
                title=title or page_id,
                content=content,
                metadata={
                    "page_id": page_id,
                    "created_time": page.get("created_time"),
                    "last_edited_time": page.get("last_edited_time"),
                    "created_by": page.get("created_by", {}).get("id"),
                    "properties": {
                        k: v.get("type") for k, v in page.get("properties", {}).items()
                    },
                },
                source="notion",
            )

    async def _get_block_children(self, block_id: str, depth: int = 0) -> str:
        """Recursively get block children as text."""
        if depth > 5:  # Prevent infinite recursion
            return ""

        await self.rate_limiter.wait_and_acquire()

        blocks_text = []
        async with httpx.AsyncClient() as client:
            cursor = None
            while True:
                params: dict = {"page_size": 100}
                if cursor:
                    params["start_cursor"] = cursor

                response = await client.get(
                    f"{self.api_url}/blocks/{block_id}/children",
                    headers=self.headers,
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

                for block in data.get("results", []):
                    block_type = block.get("type", "")
                    text = self._extract_block_text(block, block_type)
                    if text:
                        blocks_text.append(text)

                    # Recurse for nested blocks
                    if block.get("has_children"):
                        nested = await self._get_block_children(block["id"], depth + 1)
                        if nested:
                            blocks_text.append(f"  {nested}")

                if not data.get("has_more"):
                    break
                cursor = data.get("next_cursor")

        return "\n".join(blocks_text)

    def _extract_block_text(self, block: dict, block_type: str) -> str:
        """Extract text content from a block."""
        content = block.get(block_type, {})

        if block_type in ("paragraph", "heading_1", "heading_2", "heading_3"):
            rich_text = content.get("rich_text", [])
            return "".join(t.get("plain_text", "") for t in rich_text)
        elif block_type == "bulleted_list_item":
            rich_text = content.get("rich_text", [])
            return "• " + "".join(t.get("plain_text", "") for t in rich_text)
        elif block_type == "numbered_list_item":
            rich_text = content.get("rich_text", [])
            return "1. " + "".join(t.get("plain_text", "") for t in rich_text)
        elif block_type == "to_do":
            rich_text = content.get("rich_text", "")
            checked = "☑" if content.get("checked") else "☐"
            return f"{checked} {rich_text}"
        elif block_type == "code":
            rich_text = content.get("rich_text", [])
            lang = content.get("language", "")
            return f"```{lang}\n{''.join(t.get('plain_text', '') for t in rich_text)}\n```"
        elif block_type == "quote":
            rich_text = content.get("rich_text", [])
            return f"> {''.join(t.get('plain_text', '') for t in rich_text)}"
        elif block_type == "callout":
            rich_text = content.get("rich_text", [])
            return f"💡 {''.join(t.get('plain_text', '') for t in rich_text)}"
        return ""

    async def search(
        self,
        query: str,
        filter_type: str = "page",
        limit: int = 50,
    ) -> AsyncIterator[CrawlResult]:
        """Search Notion."""
        await self.rate_limiter.wait_and_acquire()

        async with httpx.AsyncClient() as client:
            payload: dict = {
                "query": query,
                "page_size": min(limit, 100),
            }
            if filter_type:
                payload["filter"] = {"value": filter_type, "property": "object"}

            response = await client.post(
                f"{self.api_url}/search",
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            for result in data.get("results", [])[:limit]:
                page_id = result["id"]
                async for page_result in self._get_page(page_id):
                    yield page_result

    async def get_database(self, database_id: str, limit: int = 100) -> AsyncIterator[CrawlResult]:
        """Query a Notion database."""
        await self.rate_limiter.wait_and_acquire()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/databases/{database_id}/query",
                headers=self.headers,
                json={"page_size": min(limit, 100)},
            )
            response.raise_for_status()
            data = response.json()

            for page in data.get("results", [])[:limit]:
                page_id = page["id"]
                async for page_result in self._get_page(page_id):
                    yield page_result

    async def discover_urls(self, seed_url: str) -> AsyncIterator[str]:
        """Discover Notion pages via search."""
        async for result in self.search("", limit=50):
            yield result.url
