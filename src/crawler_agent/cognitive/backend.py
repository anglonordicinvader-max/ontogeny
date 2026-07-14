"""Cognitive backend abstraction layer.

This module defines the protocol for swapping LLM calls with
trained models, enabling actual learning and model replacement.
"""

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import structlog


def extract_json(text: str) -> dict:
    """Extract JSON object from text that may contain non-JSON content. Always returns a dict."""
    if not text or not text.strip():
        return {}
    text = text.strip()
    try:
        result = json.loads(text)
        return result if isinstance(result, dict) else {"items": result} if isinstance(result, list) else {}
    except (json.JSONDecodeError, ValueError):
        pass
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group(1).strip())
            return result if isinstance(result, dict) else {"items": result} if isinstance(result, list) else {}
        except (json.JSONDecodeError, ValueError):
            pass
    start = text.find("{")
    if start >= 0:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except (json.JSONDecodeError, ValueError):
                        break
    start_arr = text.find("[")
    if start_arr >= 0:
        depth = 0
        for i in range(start_arr, len(text)):
            if text[i] == "[":
                depth += 1
            elif text[i] == "]":
                depth -= 1
                if depth == 0:
                    try:
                        result = json.loads(text[start_arr:i + 1])
                        return result if isinstance(result, dict) else {"items": result} if isinstance(result, list) else {}
                    except (json.JSONDecodeError, ValueError):
                        break
    return {}


@dataclass
class CognitiveResponse:
    """Standard response from any cognitive backend."""
    content: str
    confidence: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)
    model_used: str = "unknown"
    tokens_used: int = 0
    parsed_json: dict = field(default_factory=dict, repr=False, init=False)

    def __post_init__(self):
        if self.content:
            self.parsed_json = extract_json(self.content)
        if self.parsed_json is None:
            self.parsed_json = {}


class CognitiveBackend(ABC):
    """Abstract protocol for cognitive processing backends.

    All cognitive modules should use this interface instead of
    direct AsyncOpenAI calls. This enables swapping LLM for
    trained models without changing module code.
    """

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> CognitiveResponse:
        """Generate a completion."""
        ...

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate embedding vector."""
        ...

    @abstractmethod
    async def classify(
        self,
        text: str,
        categories: list[str],
    ) -> dict[str, float]:
        """Classify text into categories with confidence scores."""
        ...

    @abstractmethod
    async def extract_patterns(
        self,
        data: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Extract patterns from structured data."""
        ...

    @abstractmethod
    def get_name(self) -> str:
        """Return backend name."""
        ...


class LLMBackend(CognitiveBackend):
    """LLM-based backend using OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str = "ollama",
        model: str = "llama3.2",
        api_base: str = "http://localhost:11434/v1",
    ):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=api_key, base_url=api_base)
        self.model = model
        self.logger = structlog.get_logger()

    async def complete(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> CognitiveResponse:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            content = response.choices[0].message.content or ""
            return CognitiveResponse(
                content=content,
                confidence=0.7,
                model_used=self.model,
                tokens_used=response.usage.total_tokens if response.usage else 0,
            )
        except Exception as e:
            self.logger.error("llm_backend_error", error=str(e))
            return CognitiveResponse(content="", confidence=0.0, model_used=self.model)

    async def embed(self, text: str) -> list[float]:
        response = await self.client.embeddings.create(
            model="nomic-embed-text",
            input=text,
        )
        return response.data[0].embedding

    async def classify(
        self,
        text: str,
        categories: list[str],
    ) -> dict[str, float]:
        prompt = f"""Classify the following text into exactly one of these categories: {', '.join(categories)}
Text: {text[:2000]}
Return ONLY a JSON object with category as key and confidence (0-1) as value."""

        response = await self.complete(prompt, temperature=0.1)
        try:
            return response.parsed_json
        except Exception:
            return {c: 1.0 / len(categories) for c in categories}

    async def extract_patterns(
        self,
        data: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        prompt = f"""Analyze this data and extract patterns:
{str(data)[:4000]}
Return a JSON array of pattern objects with 'type', 'description', 'confidence' fields."""

        response = await self.complete(prompt, temperature=0.3)
        try:
            return response.parsed_json
        except Exception:
            return []

    def get_name(self) -> str:
        return f"llm-{self.model}"


class PatternBackend(CognitiveBackend):
    """Local pattern-matching backend (no LLM required).

    Uses statistical patterns and rules for fast inference.
    Falls back to LLM for complex reasoning.
    """

    def __init__(self, fallback: CognitiveBackend | None = None):
        self.fallback = fallback
        self.patterns: dict[str, Any] = {}
        self.rules: list[dict[str, Any]] = []
        self.logger = structlog.get_logger()

    async def complete(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> CognitiveResponse:
        # Try pattern matching first
        for pattern in self.rules:
            if pattern["condition"](prompt):
                return CognitiveResponse(
                    content=pattern["response"],
                    confidence=pattern.get("confidence", 0.8),
                    model_used="pattern",
                )

        # Fall back to LLM
        if self.fallback:
            return await self.fallback.complete(prompt, system, max_tokens, temperature)

        return CognitiveResponse(content="", confidence=0.0, model_used="pattern-fail")

    async def embed(self, text: str) -> list[float]:
        if self.fallback:
            return await self.fallback.embed(text)
        return [0.0] * 384

    async def classify(
        self,
        text: str,
        categories: list[str],
    ) -> dict[str, float]:
        if self.fallback:
            return await self.fallback.classify(text, categories)
        return {c: 1.0 / len(categories) for c in categories}

    async def extract_patterns(
        self,
        data: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        # Local pattern extraction using statistics
        patterns = []
        if not data:
            return patterns

        # Frequency analysis
        from collections import Counter
        all_keys = Counter()
        for item in data:
            all_keys.update(item.keys())

        for key, count in all_keys.most_common(10):
            if count > len(data) * 0.3:
                patterns.append({
                    "type": "frequent_key",
                    "description": f"Key '{key}' appears in {count}/{len(data)} items",
                    "confidence": count / len(data),
                })

        return patterns

    def add_rule(
        self,
        condition: callable,
        response: str,
        confidence: float = 0.8,
    ):
        self.rules.append({
            "condition": condition,
            "response": response,
            "confidence": confidence,
        })

    def get_name(self) -> str:
        return "pattern"
