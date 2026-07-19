"""Discord crawler using bot API and webhooks."""

from collections.abc import AsyncIterator
from datetime import datetime

import httpx
import structlog

from .base import BaseCrawler, ContentType, CrawlerConfig, CrawlResult


class DiscordCrawler(BaseCrawler):
    """Crawler for Discord channels and messages."""

    def __init__(
        self,
        bot_token: str = "",
        config: CrawlerConfig | None = None,
        **kwargs,
    ):
        super().__init__("discord", config, **kwargs)
        self.bot_token = bot_token
        self.api_url = "https://discord.com/api/v10"
        self.headers = {"Authorization": f"Bot {bot_token}"} if bot_token else {}

    async def _setup(self) -> None:
        if self.bot_token:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.api_url}/users/@me", headers=self.headers)
                response.raise_for_status()
                user = response.json()
                self.logger.info("discord_connected", user=user["username"])

    async def _cleanup(self) -> None:
        pass

    async def crawl(
        self,
        url: str,
        depth: int = 0,
        content_types: list[str] | None = None,
    ) -> AsyncIterator[CrawlResult]:
        # Parse Discord channel URL
        if "channels" in url:
            parts = url.rstrip("/").split("/")
            channel_idx = parts.index("channels")
            if channel_idx + 2 < len(parts):
                channel_id = parts[channel_idx + 2]
                async for result in self._crawl_channel(channel_id):
                    yield result

    async def _crawl_channel(
        self,
        channel_id: str,
        limit: int = 100,
    ) -> AsyncIterator[CrawlResult]:
        """Crawl messages from a channel."""
        await self.rate_limiter.wait_and_acquire()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/channels/{channel_id}/messages",
                headers=self.headers,
                params={"limit": min(limit, 100)},
            )
            response.raise_for_status()
            messages = response.json()

            for msg in messages:
                yield CrawlResult(
                    url=f"https://discord.com/channels/{msg.get('guild_id', '@me')}/{channel_id}/{msg['id']}",
                    content_type=ContentType.DISCUSSION,
                    title=f"Message by {msg['author'].get('username', 'Unknown')}",
                    content=msg.get("content", ""),
                    metadata={
                        "message_id": msg["id"],
                        "channel_id": channel_id,
                        "author": msg["author"].get("username", ""),
                        "author_id": msg["author"]["id"],
                        "created_at": msg.get("timestamp"),
                        "edited_at": msg.get("edited_timestamp"),
                        "attachments": [a["url"] for a in msg.get("attachments", [])],
                        "embeds": len(msg.get("embeds", [])),
                        "reactions": [
                            {"emoji": r["emoji"].get("name"), "count": r["count"]}
                            for r in msg.get("reactions", [])
                        ],
                    },
                    source="discord",
                )

    async def get_guilds(self) -> list[dict]:
        """Get bot's guilds."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/users/@me/guilds",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def get_channels(self, guild_id: str) -> list[dict]:
        """Get channels in a guild."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/guilds/{guild_id}/channels",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def search_messages(
        self,
        channel_id: str,
        query: str,
        limit: int = 50,
    ) -> AsyncIterator[CrawlResult]:
        """Search messages in a channel (requires message content intent)."""
        await self.rate_limiter.wait_and_acquire()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/channels/{channel_id}/messages/search",
                headers=self.headers,
                params={"query": query, "limit": min(limit, 50)},
            )
            if response.status_code == 200:
                messages = response.json()
                for msg in messages:
                    yield CrawlResult(
                        url=f"https://discord.com/channels/@me/{channel_id}/{msg['id']}",
                        content_type=ContentType.DISCUSSION,
                        title=f"Search result by {msg['author'].get('username', '')}",
                        content=msg.get("content", ""),
                        metadata={
                            "message_id": msg["id"],
                            "channel_id": channel_id,
                            "author": msg["author"].get("username", ""),
                            "created_at": msg.get("timestamp"),
                        },
                        source="discord",
                    )

    async def discover_urls(self, seed_url: str) -> AsyncIterator[str]:
        """Discover Discord URLs from guild."""
        guilds = await self.get_guilds()
        for guild in guilds[:5]:
            channels = await self.get_channels(guild["id"])
            text_channels = [c for c in channels if c["type"] == 0]
            for channel in text_channels[:3]:
                yield f"https://discord.com/channels/{guild['id']}/{channel['id']}"


class SlackCrawler(BaseCrawler):
    """Crawler for Slack workspaces using API."""

    def __init__(
        self,
        bot_token: str = "",
        config: CrawlerConfig | None = None,
        **kwargs,
    ):
        super().__init__("slack", config, **kwargs)
        self.bot_token = bot_token
        self.api_url = "https://slack.com/api"
        self.headers = {"Authorization": f"Bearer {bot_token}"} if bot_token else {}

    async def _setup(self) -> None:
        if self.bot_token:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/auth.test",
                    headers=self.headers,
                )
                data = response.json()
                if data.get("ok"):
                    self.logger.info("slack_connected", team=data.get("team"))

    async def _cleanup(self) -> None:
        pass

    async def crawl(
        self,
        url: str,
        depth: int = 0,
        content_types: list[str] | None = None,
    ) -> AsyncIterator[CrawlResult]:
        # Parse Slack channel URL or ID
        channel_id = url.split("/")[-1] if "/" in url else url
        async for result in self._crawl_channel(channel_id):
            yield result

    async def _crawl_channel(
        self,
        channel_id: str,
        limit: int = 100,
    ) -> AsyncIterator[CrawlResult]:
        """Crawl messages from a Slack channel."""
        await self.rate_limiter.wait_and_acquire()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/conversations.history",
                headers=self.headers,
                params={"channel": channel_id, "limit": min(limit, 100)},
            )
            response.raise_for_status()
            data = response.json()

            if data.get("ok"):
                for msg in data.get("messages", []):
                    if msg.get("subtype"):  # Skip bot messages, joins, etc.
                        continue

                    user_id = msg.get("user", "")
                    text = msg.get("text", "")

                    yield CrawlResult(
                        url=f"https://slack.com/archives/{channel_id}/p{msg['ts'].replace('.', '')}",
                        content_type=ContentType.DISCUSSION,
                        title=f"Message in #{channel_id}",
                        content=text,
                        metadata={
                            "ts": msg["ts"],
                            "channel": channel_id,
                            "user": user_id,
                            "thread_ts": msg.get("thread_ts"),
                            "reply_count": msg.get("reply_count", 0),
                            "reactions": [
                                {"name": r["name"], "count": r["count"]}
                                for r in msg.get("reactions", [])
                            ],
                        },
                        source="slack",
                    )

    async def get_channels(self) -> list[dict]:
        """Get channels the bot can access."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/conversations.list",
                headers=self.headers,
                params={"types": "public_channel,private_channel", "limit": 200},
            )
            data = response.json()
            if data.get("ok"):
                return data.get("channels", [])
            return []

    async def search_messages(
        self,
        query: str,
        channel: str | None = None,
        limit: int = 50,
    ) -> AsyncIterator[CrawlResult]:
        """Search messages (requires search:read scope)."""
        await self.rate_limiter.wait_and_acquire()

        params: dict = {"query": query, "count": min(limit, 50)}
        if channel:
            params["channel"] = channel

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/search.messages",
                headers=self.headers,
                params=params,
            )
            data = response.json()

            if data.get("ok"):
                for match in data.get("messages", {}).get("matches", []):
                    msg = match.get("message", {})
                    yield CrawlResult(
                        url=f"https://slack.com/archives/{msg.get('channel', '')}/p{msg.get('ts', '').replace('.', '')}",
                        content_type=ContentType.DISCUSSION,
                        title=f"Search match by {msg.get('user', '')}",
                        content=msg.get("text", ""),
                        metadata={
                            "ts": msg.get("ts"),
                            "channel": msg.get("channel"),
                            "user": msg.get("user"),
                            "permalink": msg.get("permalink"),
                        },
                        source="slack",
                    )

    async def discover_urls(self, seed_url: str) -> AsyncIterator[str]:
        """Discover Slack channel URLs."""
        channels = await self.get_channels()
        for ch in channels[:20]:
            yield f"https://slack.com/archives/{ch['id']}"
