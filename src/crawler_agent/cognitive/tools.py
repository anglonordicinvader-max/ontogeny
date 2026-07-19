"""Real-world tool integrations for the cognitive agent.

Provides structured API integrations beyond web crawling:
- GitHub API (repos, issues, PRs, actions, code search)
- arXiv API (paper search, metadata, PDFs)
- ROS2 bridge for physical robotics (optional)
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger()


class ToolType(Enum):
    GITHUB = "github"
    ARXIV = "arxiv"
    ROS2 = "ros2"


@dataclass
class ToolResult:
    """Result from a tool invocation."""

    success: bool
    tool: str
    operation: str
    data: Any = None
    error: str | None = None
    metadata: dict = field(default_factory=dict)
    execution_time_ms: float = 0.0


class GitHubTool:
    """GitHub API integration for repos, issues, PRs, actions, and code search."""

    def __init__(
        self,
        token: str | None = None,
        api_url: str = "https://api.github.com",
        proxy_pool=None,
    ):
        self.token = token
        self.api_url = api_url.rstrip("/")
        self.proxy_pool = proxy_pool
        self.logger = logger.bind(tool="github")
        self._session = None

    async def _get_session(self):
        if self._session is None or self._session.closed:
            import aiohttp

            headers = {
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "Ontogeny-Agent/1.0",
            }
            if self.token:
                headers["Authorization"] = f"token {self.token}"
            if self.proxy_pool:
                proxy_url = await self.proxy_pool.get_proxy()
                if proxy_url:
                    pass
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            )
        return self._session

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        session = await self._get_session()
        url = f"{self.api_url}{path}"
        try:
            async with session.request(method, url, **kwargs) as resp:
                data = await resp.json()
                if resp.status >= 400:
                    return {
                        "error": f"HTTP {resp.status}: {data.get('message', '')}",
                        "status": resp.status,
                    }
                return data
        except Exception as e:
            return {"error": str(e)}

    async def get_repo(self, owner: str, repo: str) -> ToolResult:
        start = time.perf_counter()
        data = await self._request("GET", f"/repos/{owner}/{repo}")
        elapsed = (time.perf_counter() - start) * 1000
        if "error" in data:
            return ToolResult(
                success=False,
                tool="github",
                operation="get_repo",
                error=data["error"],
                execution_time_ms=elapsed,
            )
        return ToolResult(
            success=True,
            tool="github",
            operation="get_repo",
            data=data,
            metadata={"full_name": data.get("full_name"), "stars": data.get("stargazers_count")},
            execution_time_ms=elapsed,
        )

    async def list_issues(
        self, owner: str, repo: str, state: str = "open", per_page: int = 30
    ) -> ToolResult:
        start = time.perf_counter()
        data = await self._request(
            "GET", f"/repos/{owner}/{repo}/issues", params={"state": state, "per_page": per_page}
        )
        elapsed = (time.perf_counter() - start) * 1000
        if "error" in data:
            return ToolResult(
                success=False,
                tool="github",
                operation="list_issues",
                error=data["error"],
                execution_time_ms=elapsed,
            )
        return ToolResult(
            success=True,
            tool="github",
            operation="list_issues",
            data=data,
            metadata={"count": len(data), "state": state},
            execution_time_ms=elapsed,
        )

    async def get_issue(self, owner: str, repo: str, issue_number: int) -> ToolResult:
        start = time.perf_counter()
        data = await self._request("GET", f"/repos/{owner}/{repo}/issues/{issue_number}")
        elapsed = (time.perf_counter() - start) * 1000
        if "error" in data:
            return ToolResult(
                success=False,
                tool="github",
                operation="get_issue",
                error=data["error"],
                execution_time_ms=elapsed,
            )
        return ToolResult(
            success=True,
            tool="github",
            operation="get_issue",
            data=data,
            metadata={"number": data.get("number"), "title": data.get("title")},
            execution_time_ms=elapsed,
        )

    async def create_issue(
        self, owner: str, repo: str, title: str, body: str = "", labels: list[str] = None
    ) -> ToolResult:
        start = time.perf_counter()
        payload = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        data = await self._request("POST", f"/repos/{owner}/{repo}/issues", json=payload)
        elapsed = (time.perf_counter() - start) * 1000
        if "error" in data:
            return ToolResult(
                success=False,
                tool="github",
                operation="create_issue",
                error=data["error"],
                execution_time_ms=elapsed,
            )
        return ToolResult(
            success=True,
            tool="github",
            operation="create_issue",
            data=data,
            metadata={"number": data.get("number"), "url": data.get("html_url")},
            execution_time_ms=elapsed,
        )

    async def list_pulls(
        self, owner: str, repo: str, state: str = "open", per_page: int = 30
    ) -> ToolResult:
        start = time.perf_counter()
        data = await self._request(
            "GET", f"/repos/{owner}/{repo}/pulls", params={"state": state, "per_page": per_page}
        )
        elapsed = (time.perf_counter() - start) * 1000
        if "error" in data:
            return ToolResult(
                success=False,
                tool="github",
                operation="list_pulls",
                error=data["error"],
                execution_time_ms=elapsed,
            )
        return ToolResult(
            success=True,
            tool="github",
            operation="list_pulls",
            data=data,
            metadata={"count": len(data), "state": state},
            execution_time_ms=elapsed,
        )

    async def get_file_content(
        self, owner: str, repo: str, path: str, ref: str = "main"
    ) -> ToolResult:
        start = time.perf_counter()
        import base64

        data = await self._request(
            "GET", f"/repos/{owner}/{repo}/contents/{path}", params={"ref": ref}
        )
        elapsed = (time.perf_counter() - start) * 1000
        if "error" in data:
            return ToolResult(
                success=False,
                tool="github",
                operation="get_file_content",
                error=data["error"],
                execution_time_ms=elapsed,
            )
        content = ""
        if isinstance(data, dict) and data.get("content"):
            content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return ToolResult(
            success=True,
            tool="github",
            operation="get_file_content",
            data=content,
            metadata={"path": path, "size": data.get("size", 0), "sha": data.get("sha", "")},
            execution_time_ms=elapsed,
        )

    async def search_code(self, query: str, per_page: int = 30) -> ToolResult:
        start = time.perf_counter()
        data = await self._request("GET", "/search/code", params={"q": query, "per_page": per_page})
        elapsed = (time.perf_counter() - start) * 1000
        if "error" in data:
            return ToolResult(
                success=False,
                tool="github",
                operation="search_code",
                error=data["error"],
                execution_time_ms=elapsed,
            )
        return ToolResult(
            success=True,
            tool="github",
            operation="search_code",
            data=data,
            metadata={"count": data.get("total_count", 0)},
            execution_time_ms=elapsed,
        )

    async def list_workflow_runs(self, owner: str, repo: str, per_page: int = 30) -> ToolResult:
        start = time.perf_counter()
        data = await self._request(
            "GET", f"/repos/{owner}/{repo}/actions/runs", params={"per_page": per_page}
        )
        elapsed = (time.perf_counter() - start) * 1000
        if "error" in data:
            return ToolResult(
                success=False,
                tool="github",
                operation="list_workflow_runs",
                error=data["error"],
                execution_time_ms=elapsed,
            )
        return ToolResult(
            success=True,
            tool="github",
            operation="list_workflow_runs",
            data=data,
            metadata={"count": data.get("total_count", 0)},
            execution_time_ms=elapsed,
        )

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


class ArxivTool:
    """arXiv API integration for paper search and metadata."""

    def __init__(self, proxy_pool=None):
        self.proxy_pool = proxy_pool
        self.base_url = "http://export.arxiv.org/api/query"
        self.logger = logger.bind(tool="arxiv")
        self._session = None

    async def _get_session(self):
        if self._session is None or self._session.closed:
            import aiohttp

            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
            )
        return self._session

    def _parse_arxiv_xml(self, xml_text: str) -> list[dict]:
        import xml.etree.ElementTree as ET

        entries = []
        try:
            root = ET.fromstring(xml_text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall("atom:entry", ns):
                paper = {
                    "id": entry.find("atom:id", ns).text
                    if entry.find("atom:id", ns) is not None
                    else "",
                    "title": entry.find("atom:title", ns).text.strip().replace("\n", " ")
                    if entry.find("atom:title", ns) is not None
                    else "",
                    "summary": entry.find("atom:summary", ns).text.strip().replace("\n", " ")
                    if entry.find("atom:summary", ns) is not None
                    else "",
                    "authors": [
                        a.find("atom:name", ns).text
                        for a in entry.findall("atom:author", ns)
                        if a.find("atom:name", ns) is not None
                    ],
                    "published": entry.find("atom:published", ns).text
                    if entry.find("atom:published", ns) is not None
                    else "",
                    "updated": entry.find("atom:updated", ns).text
                    if entry.find("atom:updated", ns) is not None
                    else "",
                    "categories": [c.get("term", "") for c in entry.findall("atom:category", ns)],
                    "pdf_url": "",
                    "abs_url": "",
                }
                for link in entry.findall("atom:link", ns):
                    if link.get("title") == "pdf":
                        paper["pdf_url"] = link.get("href", "")
                    elif link.get("type") == "text/html":
                        paper["abs_url"] = link.get("href", "")
                entries.append(paper)
        except ET.ParseError as e:
            self.logger.warning("arxiv_xml_parse_error", error=str(e))
        return entries

    async def search(
        self,
        query: str,
        max_results: int = 20,
        sort_by: str = "relevance",
        sort_order: str = "descending",
    ) -> ToolResult:
        start = time.perf_counter()
        params = {
            "search_query": query,
            "max_results": max_results,
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }
        session = await self._get_session()
        try:
            async with session.get(self.base_url, params=params) as resp:
                text = await resp.text()
                papers = self._parse_arxiv_xml(text)
                elapsed = (time.perf_counter() - start) * 1000
                return ToolResult(
                    success=True,
                    tool="arxiv",
                    operation="search",
                    data=papers,
                    metadata={"query": query, "count": len(papers)},
                    execution_time_ms=elapsed,
                )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return ToolResult(
                success=False,
                tool="arxiv",
                operation="search",
                error=str(e),
                execution_time_ms=elapsed,
            )

    async def get_paper(self, paper_id: str) -> ToolResult:
        start = time.perf_counter()
        session = await self._get_session()
        try:
            async with session.get(
                self.base_url, params={"id_list": paper_id, "max_results": 1}
            ) as resp:
                text = await resp.text()
                papers = self._parse_arxiv_xml(text)
                elapsed = (time.perf_counter() - start) * 1000
                if papers:
                    return ToolResult(
                        success=True,
                        tool="arxiv",
                        operation="get_paper",
                        data=papers[0],
                        metadata={"paper_id": paper_id},
                        execution_time_ms=elapsed,
                    )
                return ToolResult(
                    success=False,
                    tool="arxiv",
                    operation="get_paper",
                    error="Paper not found",
                    execution_time_ms=elapsed,
                )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return ToolResult(
                success=False,
                tool="arxiv",
                operation="get_paper",
                error=str(e),
                execution_time_ms=elapsed,
            )

    async def get_recent(self, category: str = "cs.AI", max_results: int = 20) -> ToolResult:
        query = f"cat:{category}"
        return await self.search(
            query, max_results=max_results, sort_by="submittedDate", sort_order="descending"
        )

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


class ROS2Bridge:
    """Optional ROS2 bridge for physical robotics integration.

    Provides a lightweight interface to ROS2 topics, services, and actions
    without requiring the full ROS2 Python stack at import time.
    """

    def __init__(self, node_name: str = "ontogeny_agent", namespace: str = "/"):
        self.node_name = node_name
        self.namespace = namespace
        self.logger = logger.bind(tool="ros2")
        self._node = None
        self._available = False
        self._init_ros2()

    def _init_ros2(self):
        try:
            import rclpy
            from rclpy.node import Node

            rclpy.init(args=None)
            self._node = Node(self.node_name, namespace=self.namespace)
            self._available = True
            self.logger.info("ros2_initialized", node=self.node_name, namespace=self.namespace)
        except ImportError:
            self.logger.info("ros2_not_available", reason="rclpy not installed")
        except Exception as e:
            self.logger.warning("ros2_init_failed", error=str(e))

    @property
    def is_available(self) -> bool:
        return self._available

    async def publish(self, topic: str, message_type: str, data: dict) -> ToolResult:
        if not self._available:
            return ToolResult(
                success=False, tool="ros2", operation="publish", error="ROS2 not available"
            )
        start = time.perf_counter()
        try:
            from rclpy.qos import QoSProfile

            # Dynamic message type creation
            msg_module = self._import_msg_type(message_type)
            msg = msg_module()
            self._fill_message(msg, data)
            publisher = self._node.create_publisher(type(msg), topic, QoSProfile(depth=10))
            publisher.publish(msg)
            self._node.destroy_publisher(publisher)
            elapsed = (time.perf_counter() - start) * 1000
            return ToolResult(
                success=True,
                tool="ros2",
                operation="publish",
                data={"topic": topic},
                metadata={"message_type": message_type},
                execution_time_ms=elapsed,
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return ToolResult(
                success=False,
                tool="ros2",
                operation="publish",
                error=str(e),
                execution_time_ms=elapsed,
            )

    async def subscribe(
        self, topic: str, message_type: str, callback, timeout: float = 5.0
    ) -> ToolResult:
        if not self._available:
            return ToolResult(
                success=False, tool="ros2", operation="subscribe", error="ROS2 not available"
            )
        start = time.perf_counter()
        received_data = []
        try:
            from rclpy.qos import QoSProfile

            msg_module = self._import_msg_type(message_type)

            def _callback(msg):
                received_data.append(self._msg_to_dict(msg))

            sub = self._node.create_subscription(
                type(msg_module()), topic, _callback, QoSProfile(depth=10)
            )
            # Spin for timeout
            end_time = time.time() + timeout
            while time.time() < end_time and not received_data:
                rclpy.spin_once(self._node, timeout_sec=0.1)
            self._node.destroy_subscription(sub)
            elapsed = (time.perf_counter() - start) * 1000
            return ToolResult(
                success=True,
                tool="ros2",
                operation="subscribe",
                data=received_data[0] if received_data else None,
                metadata={"topic": topic, "received": len(received_data)},
                execution_time_ms=elapsed,
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return ToolResult(
                success=False,
                tool="ros2",
                operation="subscribe",
                error=str(e),
                execution_time_ms=elapsed,
            )

    async def call_service(self, service_name: str, service_type: str, request: dict) -> ToolResult:
        if not self._available:
            return ToolResult(
                success=False, tool="ros2", operation="call_service", error="ROS2 not available"
            )
        start = time.perf_counter()
        try:
            srv_module = self._import_srv_type(service_type)
            client = self._node.create_client(srv_module.Request, service_name)
            if not client.wait_for_service(timeout_sec=5.0):
                return ToolResult(
                    success=False,
                    tool="ros2",
                    operation="call_service",
                    error="Service not available",
                )
            req = srv_module.Request()
            self._fill_message(req, request)
            future = client.call_async(req)
            rclpy.spin_until_future_complete(self._node, future, timeout_sec=10.0)
            self._node.destroy_client(client)
            elapsed = (time.perf_counter() - start) * 1000
            if future.result() is not None:
                return ToolResult(
                    success=True,
                    tool="ros2",
                    operation="call_service",
                    data=self._msg_to_dict(future.result()),
                    execution_time_ms=elapsed,
                )
            return ToolResult(
                success=False,
                tool="ros2",
                operation="call_service",
                error="Service call failed",
                execution_time_ms=elapsed,
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return ToolResult(
                success=False,
                tool="ros2",
                operation="call_service",
                error=str(e),
                execution_time_ms=elapsed,
            )

    def _import_msg_type(self, msg_type: str):
        import importlib

        parts = msg_type.split("/")
        if len(parts) == 3:
            pkg, folder, name = parts
            module = importlib.import_module(f"{pkg}.{folder}")
            return getattr(module, name)
        raise ValueError(f"Invalid message type: {msg_type}")

    def _import_srv_type(self, srv_type: str):
        import importlib

        parts = srv_type.split("/")
        if len(parts) == 3:
            pkg, folder, name = parts
            module = importlib.import_module(f"{pkg}.{folder}")
            return getattr(module, name)
        raise ValueError(f"Invalid service type: {srv_type}")

    def _fill_message(self, msg, data: dict):
        for key, value in data.items():
            if hasattr(msg, key):
                setattr(msg, key, value)

    def _msg_to_dict(self, msg) -> dict:
        if hasattr(msg, "__dict__"):
            result = {}
            for key, value in msg.__dict__.items():
                if not key.startswith("_"):
                    if hasattr(value, "__dict__"):
                        result[key] = self._msg_to_dict(value)
                    elif isinstance(value, (list, tuple)):
                        result[key] = [
                            self._msg_to_dict(v) if hasattr(v, "__dict__") else v for v in value
                        ]
                    else:
                        result[key] = value
            return result
        return {"data": str(msg)}

    def shutdown(self):
        if self._node:
            self._node.destroy_node()
        try:
            import rclpy

            rclpy.shutdown()
        except Exception:
            pass


class ToolManager:
    """Unified interface for all tool integrations."""

    def __init__(self, settings=None, proxy_pool=None):
        self.logger = logger.bind(component="tool_manager")
        self.tools: dict[str, Any] = {}
        self._settings = settings
        self._proxy_pool = proxy_pool

    async def initialize(self):
        # GitHub
        github_token = None
        api_url = "https://api.github.com"
        if self._settings and hasattr(self._settings, "platform"):
            github_token = self._settings.platform.github_token
            api_url = self._settings.platform.github_api_url
        self.tools["github"] = GitHubTool(
            token=github_token, api_url=api_url, proxy_pool=self._proxy_pool
        )
        self.logger.info("tool_initialized", tool="github")

        # arXiv
        self.tools["arxiv"] = ArxivTool(proxy_pool=self._proxy_pool)
        self.logger.info("tool_initialized", tool="arxiv")

        # ROS2 (optional)
        self.tools["ros2"] = ROS2Bridge()
        self.logger.info("tool_initialized", tool="ros2", available=self.tools["ros2"].is_available)

    def get(self, tool_name: str) -> Any | None:
        return self.tools.get(tool_name)

    async def invoke(self, tool_name: str, operation: str, **kwargs) -> ToolResult:
        tool = self.tools.get(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                tool=tool_name,
                operation=operation,
                error=f"Tool '{tool_name}' not found",
            )
        method = getattr(tool, operation, None)
        if not method:
            return ToolResult(
                success=False,
                tool=tool_name,
                operation=operation,
                error=f"Operation '{operation}' not found",
            )
        try:
            result = await method(**kwargs)
            return result
        except Exception as e:
            return ToolResult(success=False, tool=tool_name, operation=operation, error=str(e))

    async def close(self):
        for _name, tool in self.tools.items():
            if hasattr(tool, "close"):
                try:
                    await tool.close()
                except Exception:
                    pass
            elif hasattr(tool, "shutdown"):
                try:
                    tool.shutdown()
                except Exception:
                    pass
