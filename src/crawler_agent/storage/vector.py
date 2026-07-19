"""Vector storage using ChromaDB for semantic search."""

from typing import Any

import chromadb
import structlog
from chromadb.config import Settings

from ..crawlers.base import CrawlResult


class VectorStore:
    """Vector storage for semantic search."""

    def __init__(self, persist_directory: str = "./data/chroma"):
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name="crawled_content",
            metadata={"hnsw:space": "cosine"},
        )
        self.logger = structlog.get_logger()

    def add(
        self,
        result: CrawlResult,
        embedding: list[float] | None = None,
    ) -> str:
        """Add content to vector store."""
        # Create document text for embedding
        doc_text = f"{result.title}\n\n{result.content[:5000]}"

        metadata = {
            "url": result.url,
            "source": result.source,
            "content_type": result.content_type.value,
            "title": result.title[:500],
            "crawled_at": result.crawled_at.isoformat(),
        }
        # Add custom metadata
        for k, v in result.metadata.items():
            if isinstance(v, (str, int, float, bool)):
                metadata[k] = v

        self.collection.add(
            documents=[doc_text],
            metadatas=[metadata],
            ids=[result.checksum or result.url],
            embeddings=[embedding] if embedding else None,
        )

        self.logger.debug("vector_added", url=result.url)
        return result.checksum or result.url

    def add_batch(
        self,
        results: list[CrawlResult],
        embeddings: list[list[float]] | None = None,
    ) -> list[str]:
        """Add multiple documents."""
        documents = []
        metadatas = []
        ids = []

        for i, result in enumerate(results):
            doc_text = f"{result.title}\n\n{result.content[:5000]}"

            metadata = {
                "url": result.url,
                "source": result.source,
                "content_type": result.content_type.value,
                "title": result.title[:500],
                "crawled_at": result.crawled_at.isoformat(),
            }
            for k, v in result.metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    metadata[k] = v

            documents.append(doc_text)
            metadatas.append(metadata)
            ids.append(result.checksum or f"{result.url}_{i}")

        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
            embeddings=embeddings,
        )

        return ids

    def search(
        self,
        query: str,
        n_results: int = 10,
        where: dict | None = None,
    ) -> list[dict[str, Any]]:
        """Semantic search."""
        query_params: dict[str, Any] = {
            "query_texts": [query],
            "n_results": n_results,
        }
        if where:
            query_params["where"] = where

        results = self.collection.query(**query_params)

        output = []
        for i in range(len(results["ids"][0])):
            output.append(
                {
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if results.get("distances") else None,
                }
            )

        return output

    def get_by_source(self, source: str, limit: int = 100) -> list[dict]:
        """Get documents by source."""
        return self.search(" ", n_results=limit, where={"source": source})

    def delete(self, doc_id: str) -> None:
        """Delete document by ID."""
        self.collection.delete(ids=[doc_id])

    def count(self) -> int:
        """Get total document count."""
        return self.collection.count()
