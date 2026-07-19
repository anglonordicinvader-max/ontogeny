"""LLM processing pipeline for content analysis and summarization."""

from typing import Any

import structlog
from openai import AsyncOpenAI

from ..crawlers.base import CrawlResult


class LLMProcessor:
    """Process crawled content with LLM."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4-turbo-preview",
        api_base: str | None = None,
    ):
        self.client = AsyncOpenAI(api_key=api_key, base_url=api_base)
        self.model = model
        self.logger = structlog.get_logger()

    async def summarize(
        self,
        content: str,
        max_tokens: int = 500,
    ) -> str:
        """Summarize content."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a content summarizer. Be concise and factual.",
                },
                {
                    "role": "user",
                    "content": f"Summarize the following content in 2-3 paragraphs:\n\n{content[:8000]}",
                },
            ],
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    async def extract_metadata(
        self,
        content: str,
        content_type: str,
    ) -> dict[str, Any]:
        """Extract structured metadata from content."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "Extract structured metadata as JSON. Return only valid JSON.",
                },
                {
                    "role": "user",
                    "content": f"""Extract metadata from this {content_type}:

{content[:8000]}

Return JSON with: title, description, topics (list), key_entities (list), sentiment (positive/negative/neutral),
quality_score (1-10), relevance_score (1-10).""",
                },
            ],
            response_format={"type": "json_object"},
            max_tokens=1000,
        )

        import json

        return json.loads(response.choices[0].message.content or "{}")

    async def generate_embedding_text(
        self,
        result: CrawlResult,
    ) -> str:
        """Generate optimized text for embedding."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "Create a concise embedding text that captures the essence of the content.",
                },
                {
                    "role": "user",
                    "content": f"""Create an embedding-optimized version of this content:

Title: {result.title}
Type: {result.content_type.value}
Source: {result.source}
Content: {result.content[:4000]}

Return a 200-500 word summary that captures the key information for semantic search.""",
                },
            ],
            max_tokens=600,
        )
        return response.choices[0].message.content or f"{result.title} {result.content[:500]}"

    async def classify_content(
        self,
        content: str,
        categories: list[str],
    ) -> str:
        """Classify content into categories."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": f"Classify the content into one of these categories: {', '.join(categories)}",
                },
                {
                    "role": "user",
                    "content": f"Classify this content:\n\n{content[:8000]}",
                },
            ],
            max_tokens=50,
        )
        return response.choices[0].message.content or categories[0]

    async def answer_query(
        self,
        query: str,
        context: str,
    ) -> str:
        """Answer a query given context from crawled data."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "Answer questions based on the provided context. Be accurate and cite sources when possible.",
                },
                {
                    "role": "user",
                    "content": f"""Context from crawled data:

{context}

Question: {query}""",
                },
            ],
            max_tokens=1500,
        )
        return response.choices[0].message.content or "No answer found."

    async def process_batch(
        self,
        results: list[CrawlResult],
    ) -> list[dict[str, Any]]:
        """Process a batch of results."""
        processed = []
        for result in results:
            try:
                metadata = await self.extract_metadata(
                    result.content,
                    result.content_type.value,
                )
                summary = await self.summarize(result.content, max_tokens=300)
                embedding_text = await self.generate_embedding_text(result)

                processed.append(
                    {
                        "url": result.url,
                        "title": result.title,
                        "summary": summary,
                        "metadata": metadata,
                        "embedding_text": embedding_text,
                    }
                )
            except Exception as e:
                self.logger.error("processing_failed", url=result.url, error=str(e))
                continue

        return processed
