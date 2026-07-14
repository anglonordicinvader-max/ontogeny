"""Embedding generation using sentence-transformers or OpenAI."""

from typing import List

import structlog
from sentence_transformers import SentenceTransformer


class EmbeddingGenerator:
    """Generate embeddings for semantic search."""

    def __init__(
        self,
        provider: str = "local",
        model_name: str = "all-MiniLM-L6-v2",
        api_key: str = "",
        api_base: str | None = None,
    ):
        self.provider = provider
        self.logger = structlog.get_logger()

        if provider == "local":
            self.model = SentenceTransformer(model_name)
        elif provider == "openai":
            import openai
            self.client = openai.AsyncOpenAI(api_key=api_key or "ollama", base_url=api_base)
            self.model_name = model_name
        else:
            raise ValueError(f"Unknown provider: {provider}")

    async def generate(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts."""
        if self.provider == "local":
            embeddings = self.model.encode(texts, show_progress_bar=False)
            return embeddings.tolist()
        else:
            response = await self.client.embeddings.create(
                model=self.model_name,
                input=texts,
            )
            return [item.embedding for item in response.data]

    async def generate_single(self, text: str) -> List[float]:
        """Generate embedding for single text."""
        results = await self.generate([text])
        return results[0]
