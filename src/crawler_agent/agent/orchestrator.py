"""Main agent orchestrator for crawl operations."""

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any

import structlog

from ..config.settings import load_settings
from ..crawlers import (
    GitHubCrawler, HuggingFaceCrawler, PastebinCrawler,
    ArxivCrawler, SemanticScholarCrawler,
    CrawlResult, CrawlerConfig,
)
from ..storage import Database, VectorStore, DockerManager, CrawlerWorkspace
from ..processing import LLMProcessor, EmbeddingGenerator
from ..utils import ProxyPool


class TaskType(str, Enum):
    CRAWL = "crawl"
    SEARCH = "search"
    INDEX = "index"
    QUERY = "query"
    MONITOR = "monitor"
    DOCKER = "docker"


@dataclass
class Task:
    """Agent task."""
    task_type: TaskType
    source: str
    query: str = ""
    params: dict[str, Any] = None

    def __post_init__(self):
        if self.params is None:
            self.params = {}


class AgentOrchestrator:
    """Main orchestrator for crawl operations."""

    def __init__(self):
        self.settings = load_settings()
        self.logger = structlog.get_logger()

        # Storage
        self.db: Database | None = None
        self.vector_store: VectorStore | None = None

        # Processing
        self.llm: LLMProcessor | None = None
        self.embedder: EmbeddingGenerator | None = None

        # Crawlers
        self.crawlers: dict[str, Any] = {}

        # Docker workspace
        self.docker: DockerManager | None = None
        self.workspace: CrawlerWorkspace | None = None

        # Proxy pool
        self.proxy_pool = ProxyPool(self.settings.crawler.proxy_pool)

    async def initialize(self) -> None:
        """Initialize all components."""
        self.logger.info("initializing_agent")

        # Database
        self.db = Database(self.settings.storage.database_url)
        await self.db.initialize()

        # Vector store
        self.vector_store = VectorStore(self.settings.storage.chroma_path)

        # LLM
        self.llm = LLMProcessor(
            api_key=self.settings.llm.api_key,
            model=self.settings.llm.model,
            api_base=self.settings.llm.api_base,
        )

        # Embeddings
        self.embedder = EmbeddingGenerator(
            provider="openai",
            model_name=self.settings.llm.embedding_model,
            api_key=self.settings.llm.api_key,
        )

        # Initialize crawlers
        crawler_config = CrawlerConfig(
            requests_per_second=self.settings.crawler.requests_per_second,
            burst_size=self.settings.crawler.burst_size,
        )

        if self.settings.platform.github_token:
            self.crawlers["github"] = GitHubCrawler(
                token=self.settings.platform.github_token,
                config=crawler_config,
                proxy_pool=self.proxy_pool,
            )

        if self.settings.platform.huggingface_token:
            self.crawlers["huggingface"] = HuggingFaceCrawler(
                token=self.settings.platform.huggingface_token,
                config=crawler_config,
                proxy_pool=self.proxy_pool,
            )

        self.crawlers["pastebin"] = PastebinCrawler(
            api_key=self.settings.platform.pastebin_api_key,
            config=crawler_config,
            proxy_pool=self.proxy_pool,
        )

        self.crawlers["arxiv"] = ArxivCrawler(
            config=crawler_config,
            proxy_pool=self.proxy_pool,
        )

        if self.settings.platform.semantic_scholar_api_key:
            self.crawlers["semantic_scholar"] = SemanticScholarCrawler(
                api_key=self.settings.platform.semantic_scholar_api_key,
                config=crawler_config,
                proxy_pool=self.proxy_pool,
            )

        # Docker workspace
        try:
            self.docker = DockerManager()
            self.workspace = CrawlerWorkspace(self.docker)
            await self.workspace.setup()
            self.logger.info("docker_workspace_initialized")
        except Exception as e:
            self.logger.warning("docker_unavailable", error=str(e))

        # Initialize all crawlers
        for name, crawler in self.crawlers.items():
            try:
                await crawler.initialize()
                self.logger.info("crawler_initialized", name=name)
            except Exception as e:
                self.logger.error("crawler_init_failed", name=name, error=str(e))

        self.logger.info("agent_initialized", crawlers=list(self.crawlers.keys()))

    async def execute(self, task: Task) -> dict[str, Any]:
        """Execute a task."""
        self.logger.info("executing_task", task_type=task.task_type, source=task.source)

        if task.task_type == TaskType.CRAWL:
            return await self._crawl(task)
        elif task.task_type == TaskType.SEARCH:
            return await self._search(task)
        elif task.task_type == TaskType.INDEX:
            return await self._index(task)
        elif task.task_type == TaskType.QUERY:
            return await self._query(task)
        elif task.task_type == TaskType.MONITOR:
            return await self._monitor(task)
        elif task.task_type == TaskType.DOCKER:
            return await self._docker(task)
        else:
            return {"error": f"Unknown task type: {task.task_type}"}

    async def _crawl(self, task: Task) -> dict[str, Any]:
        """Crawl from a source."""
        crawler = self.crawlers.get(task.source)
        if not crawler:
            return {"error": f"No crawler for source: {task.source}"}

        results = []
        async for result in crawler.crawl(task.query, **task.params):
            results.append(result)
            await self.db.store(result)

        return {
            "source": task.source,
            "count": len(results),
            "results": [r.model_dump() for r in results[:10]],
        }

    async def _search(self, task: Task) -> dict[str, Any]:
        """Search across sources."""
        crawler = self.crawlers.get(task.source)
        if not crawler:
            return {"error": f"No crawler for source: {task.source}"}

        results = []
        async for result in crawler.search(task.query, **task.params):
            results.append(result)
            await self.db.store(result)

        return {
            "source": task.source,
            "query": task.query,
            "count": len(results),
            "results": [r.model_dump() for r in results[:10]],
        }

    async def _index(self, task: Task) -> dict[str, Any]:
        """Index unprocessed content."""
        unprocessed = await self.db.get_unprocessed(limit=100)
        if not unprocessed:
            return {"message": "No unprocessed content"}

        indexed = 0
        for result in unprocessed:
            try:
                # Generate embedding
                embedding_text = await self.llm.generate_embedding_text(result)
                embedding = await self.embedder.generate_single(embedding_text)

                # Store in vector DB
                doc_id = self.vector_store.add(result, embedding)

                # Mark as processed
                await self.db.mark_processed(result.url, doc_id)
                indexed += 1

            except Exception as e:
                self.logger.error("index_failed", url=result.url, error=str(e))
                await self.db.mark_failed(result.url)

        return {"indexed": indexed, "total": len(unprocessed)}

    async def _query(self, task: Task) -> dict[str, Any]:
        """Query the indexed data."""
        # Semantic search
        results = self.vector_store.search(task.query, n_results=10)

        # Build context
        context = "\n\n---\n\n".join(
            f"Source: {r['metadata']['source']}\nTitle: {r['metadata']['title']}\n{r['document']}"
            for r in results
        )

        # Get LLM answer
        answer = await self.llm.answer_query(task.query, context)

        return {
            "query": task.query,
            "answer": answer,
            "sources": [
                {"url": r["metadata"]["url"], "title": r["metadata"]["title"]}
                for r in results
            ],
        }

    async def _monitor(self, task: Task) -> dict[str, Any]:
        """Monitor for new content."""
        # Get stats
        stats = await self.db.get_stats()

        return {
            "stats": stats,
            "vector_count": self.vector_store.count(),
            "crawlers": list(self.crawlers.keys()),
        }

    async def _docker(self, task: Task) -> dict[str, Any]:
        """Manage Docker workspace."""
        if not self.docker or not self.workspace:
            return {"error": "Docker not available"}

        action = task.params.get("action", "list")

        if action == "list":
            services = await self.workspace.list_services()
            return {
                "services": [
                    {"name": s.name, "status": s.status, "image": s.image}
                    for s in services
                ]
            }
        elif action == "start":
            service_name = task.params.get("service_name", "crawler-service")
            image = task.params.get("image", "python:3.11-slim")
            container = await self.workspace.start_service(
                service_name=service_name,
                image=image,
                ports=task.params.get("ports"),
                env=task.params.get("env"),
            )
            return {"container": {"id": container.id, "name": container.name, "status": container.status}}
        elif action == "stop":
            service_name = task.params.get("service_name", "crawler-service")
            await self.workspace.stop_service(service_name)
            return {"stopped": service_name}
        elif action == "exec":
            container_name = task.params.get("container_name")
            command = task.params.get("command", "ls")
            containers = await self.docker.list_containers()
            target = next((c for c in containers if c.name == container_name), None)
            if target:
                output = await self.docker.exec_in_container(target.id, command)
                return {"output": output}
            return {"error": f"Container {container_name} not found"}
        elif action == "cleanup":
            await self.workspace.cleanup()
            await self.workspace.setup()
            return {"message": "Workspace reset"}
        else:
            return {"error": f"Unknown Docker action: {action}"}

    async def close(self) -> None:
        """Cleanup resources."""
        for crawler in self.crawlers.values():
            await crawler.cleanup()

        if self.db:
            await self.db.close()

        if self.workspace:
            await self.workspace.cleanup()

        self.logger.info("agent_closed")
