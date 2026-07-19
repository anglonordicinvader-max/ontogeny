"""Jira crawler using REST API v2/v3."""

from collections.abc import AsyncIterator
from datetime import datetime

import httpx
import structlog

from .base import BaseCrawler, ContentType, CrawlerConfig, CrawlResult


class JiraCrawler(BaseCrawler):
    """Crawler for Jira issues and projects."""

    def __init__(
        self,
        base_url: str,
        email: str = "",
        api_token: str = "",
        config: CrawlerConfig | None = None,
        **kwargs,
    ):
        super().__init__("jira", config, **kwargs)
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}/rest/api/3"
        self.auth = (email, api_token) if email and api_token else None

    async def _setup(self) -> None:
        if self.auth:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/myself",
                    auth=self.auth,
                )
                if response.status_code == 200:
                    user = response.json()
                    self.logger.info("jira_connected", user=user.get("displayName"))

    async def _cleanup(self) -> None:
        pass

    async def crawl(
        self,
        url: str,
        depth: int = 0,
        content_types: list[str] | None = None,
    ) -> AsyncIterator[CrawlResult]:
        # Parse Jira issue URL
        if "/browse/" in url or "/issues/" in url:
            parts = url.rstrip("/").split("/")
            issue_key = parts[-1]
            async for result in self._get_issue(issue_key):
                yield result

    async def _get_issue(self, issue_key: str) -> AsyncIterator[CrawlResult]:
        """Get a single Jira issue."""
        await self.rate_limiter.wait_and_acquire()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/issue/{issue_key}",
                auth=self.auth,
                params={"expand": "renderedFields"},
            )
            response.raise_for_status()
            issue = response.json()

            fields = issue.get("fields", {})

            # Extract description
            desc = fields.get("description", {})
            description = self._extract_adf_text(desc) if desc else ""

            # Extract comments
            comments = []
            for comment in fields.get("comment", {}).get("comments", []):
                comments.append(
                    {
                        "author": comment.get("author", {}).get("displayName", ""),
                        "body": self._extract_adf_text(comment.get("body", {})),
                        "created": comment.get("created"),
                    }
                )

            yield CrawlResult(
                url=f"{self.base_url}/browse/{issue_key}",
                content_type=ContentType.ISSUE,
                title=f"{issue_key}: {fields.get('summary', '')}",
                content=description,
                metadata={
                    "key": issue_key,
                    "status": fields.get("status", {}).get("name"),
                    "priority": fields.get("priority", {}).get("name"),
                    "issue_type": fields.get("issuetype", {}).get("name"),
                    "assignee": fields.get("assignee", {}).get("displayName")
                    if fields.get("assignee")
                    else None,
                    "reporter": fields.get("reporter", {}).get("displayName")
                    if fields.get("reporter")
                    else None,
                    "created": fields.get("created"),
                    "updated": fields.get("updated"),
                    "labels": fields.get("labels", []),
                    "components": [c["name"] for c in fields.get("components", [])],
                    "fix_versions": [v["name"] for v in fields.get("fixVersions", [])],
                    "comments": comments,
                    "subtasks": [
                        {"key": s["key"], "summary": s["fields"]["summary"]}
                        for s in fields.get("subtasks", [])
                    ],
                },
                source="jira",
            )

    def _extract_adf_text(self, adf: dict) -> str:
        """Extract plain text from Atlassian Document Format."""
        if isinstance(adf, str):
            return adf

        text_parts = []
        content = adf.get("content", [])
        for block in content:
            block_type = block.get("type", "")
            if block_type == "paragraph":
                for inline in block.get("content", []):
                    if inline.get("type") == "text":
                        text_parts.append(inline.get("text", ""))
                    elif inline.get("type") == "mention":
                        text_parts.append(f"@{inline.get('attrs', {}).get('text', '')}")
                    elif inline.get("type") == "emoji":
                        text_parts.append(f":{inline.get('attrs', {}).get('shortName', '')}:")
                text_parts.append("\n")
            elif block_type in ("heading", "heading1", "heading2", "heading3"):
                level = int(block_type[-1]) if block_type[-1].isdigit() else 1
                text_parts.append(f"{'#' * level} ")
                for inline in block.get("content", []):
                    if inline.get("type") == "text":
                        text_parts.append(inline.get("text", ""))
                text_parts.append("\n")
            elif block_type == "bulletList":
                for item in block.get("content", []):
                    text_parts.append("• ")
                    for inline in item.get("content", []):
                        if inline.get("type") == "text":
                            text_parts.append(inline.get("text", ""))
                    text_parts.append("\n")
            elif block_type == "codeBlock":
                lang = block.get("attrs", {}).get("language", "")
                text_parts.append(f"```{lang}\n")
                for inline in block.get("content", []):
                    text_parts.append(inline.get("text", ""))
                text_parts.append("\n```\n")

        return "".join(text_parts)

    async def search(
        self,
        jql: str,
        fields: list[str] | None = None,
        limit: int = 50,
    ) -> AsyncIterator[CrawlResult]:
        """Search issues using JQL."""
        await self.rate_limiter.wait_and_acquire()

        params: dict = {
            "jql": jql,
            "maxResults": min(limit, 100),
        }
        if fields:
            params["fields"] = ",".join(fields)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/search",
                auth=self.auth,
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            for issue in data.get("issues", [])[:limit]:
                issue_key = issue["key"]
                async for result in self._get_issue(issue_key):
                    yield result

    async def get_project(self, project_key: str) -> CrawlResult | None:
        """Get project info."""
        await self.rate_limiter.wait_and_acquire()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/project/{project_key}",
                auth=self.auth,
            )
            response.raise_for_status()
            project = response.json()

            return CrawlResult(
                url=f"{self.base_url}/projects/{project_key}",
                content_type=ContentType.DOCUMENTATION,
                title=project.get("name", project_key),
                content=project.get("description", ""),
                metadata={
                    "key": project_key,
                    "lead": project.get("lead", {}).get("displayName"),
                    "created": project.get("created"),
                    "issue_types": [it["name"] for it in project.get("issueTypes", [])],
                    "roles": list(project.get("roles", {}).keys()),
                },
                source="jira",
            )

    async def get_sprint_issues(
        self,
        board_id: int,
        sprint_id: int,
        limit: int = 50,
    ) -> AsyncIterator[CrawlResult]:
        """Get issues in a sprint (Agile API)."""
        await self.rate_limiter.wait_and_acquire()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/rest/agile/1.0/sprint/{sprint_id}/issue",
                auth=self.auth,
                params={"maxResults": min(limit, 100)},
            )
            response.raise_for_status()
            data = response.json()

            for issue in data.get("issues", [])[:limit]:
                async for result in self._get_issue(issue["key"]):
                    yield result

    async def discover_urls(self, seed_url: str) -> AsyncIterator[str]:
        """Discover Jira issues from recent activity."""
        async for result in self.search("ORDER BY updated DESC", limit=50):
            yield result.url
