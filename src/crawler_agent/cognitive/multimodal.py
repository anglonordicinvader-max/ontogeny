"""Multimodal processing module - vision and audio understanding.

Provides:
- Vision understanding via LLaVA or equivalent vision-language model
- Audio understanding via whisper or equivalent ASR model
- Image analysis and description
- Audio transcription and analysis
"""

import asyncio
import base64
import io
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog


@dataclass
class VisionResult:
    """Result from vision processing."""
    success: bool
    description: str = ""
    objects: List[str] = field(default_factory=list)
    scene: str = ""
    confidence: float = 0.0
    metadata: Dict = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class AudioResult:
    """Result from audio processing."""
    success: bool
    transcript: str = ""
    language: str = ""
    duration_seconds: float = 0.0
    segments: List[Dict] = field(default_factory=list)
    confidence: float = 0.0
    metadata: Dict = field(default_factory=dict)
    error: Optional[str] = None


class VisionProcessor:
    """Vision understanding via LLaVA or equivalent vision-language model.

    Uses Ollama's multimodal endpoint for image understanding.
    Supports LLaVA, bakllava, and other vision models.
    """

    def __init__(
        self,
        model: str = "llava",
        api_base: str = "http://localhost:11434",
        fallback_model: str = "llama3.2",
    ):
        self.model = model
        self.api_base = api_base.rstrip("/")
        self.fallback_model = fallback_model
        self.logger = logger.bind(component="vision")
        self._available = False
        self._check_availability()

    def _check_availability(self):
        """Check if vision model is available via Ollama."""
        try:
            import httpx
            resp = httpx.get(f"{self.api_base}/api/tags", timeout=5.0)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                if any(self.model in name for name in model_names):
                    self._available = True
                    self.logger.info("vision_model_available", model=self.model)
                else:
                    self.logger.info("vision_model_not_found", model=self.model, available=model_names[:5])
        except Exception:
            self.logger.info("vision_check_failed")

    @property
    def is_available(self) -> bool:
        return self._available

    async def analyze_image(
        self,
        image_path: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        prompt: str = "Describe this image in detail.",
    ) -> VisionResult:
        """Analyze an image using the vision model."""
        if not self._available:
            return VisionResult(
                success=False,
                error=f"Vision model '{self.model}' not available. Pull with: ollama pull {self.model}",
            )

        start = time.perf_counter()

        # Prepare image
        image_b64 = None
        if image_path:
            with open(image_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode()
        elif image_bytes:
            image_b64 = base64.b64encode(image_bytes).decode()
        else:
            return VisionResult(success=False, error="No image provided")

        try:
            import httpx
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.api_base}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "images": [image_b64],
                        "stream": False,
                    },
                )
                response.raise_for_status()
                data = response.json()
                description = data.get("response", "")

                elapsed = (time.perf_counter() - start) * 1000

                # Parse objects from description
                objects = self._extract_objects(description)

                return VisionResult(
                    success=True,
                    description=description,
                    objects=objects,
                    scene=self._extract_scene(description),
                    confidence=0.8,
                    metadata={"model": self.model, "response_time_ms": elapsed},
                )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return VisionResult(
                success=False,
                error=str(e),
                metadata={"response_time_ms": elapsed},
            )

    async def analyze_url(
        self,
        image_url: str,
        prompt: str = "Describe this image in detail.",
    ) -> VisionResult:
        """Analyze an image from a URL."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(image_url)
                response.raise_for_status()
                return await self.analyze_image(image_bytes=response.content, prompt=prompt)
        except Exception as e:
            return VisionResult(success=False, error=str(e))

    def _extract_objects(self, description: str) -> List[str]:
        """Extract mentioned objects from description."""
        common_objects = [
            "person", "people", "man", "woman", "child",
            "car", "vehicle", "truck", "bus", "bicycle",
            "building", "house", "tree", "plant", "flower",
            "animal", "dog", "cat", "bird",
            "computer", "phone", "screen", "table", "chair",
            "book", "paper", "text", "sign",
        ]
        found = []
        desc_lower = description.lower()
        for obj in common_objects:
            if obj in desc_lower:
                found.append(obj)
        return found

    def _extract_scene(self, description: str) -> str:
        """Extract scene type from description."""
        scenes = {
            "indoor": ["room", "office", "kitchen", "bedroom", "hall", "lobby"],
            "outdoor": ["street", "road", "park", "garden", "field", "forest", "beach"],
            "urban": ["city", "downtown", "building", "skyline", "traffic"],
            "nature": ["mountain", "river", "lake", "ocean", "forest", "desert"],
        }
        desc_lower = description.lower()
        for scene_type, keywords in scenes.items():
            if any(kw in desc_lower for kw in keywords):
                return scene_type
        return "unknown"


class AudioProcessor:
    """Audio understanding via whisper or equivalent ASR model.

    Uses Ollama's audio capabilities or external whisper endpoint.
    """

    def __init__(
        self,
        model: str = "whisper",
        api_base: str = "http://localhost:11434",
        whisper_endpoint: Optional[str] = None,
    ):
        self.model = model
        self.api_base = api_base.rstrip("/")
        self.whisper_endpoint = whisper_endpoint
        self.logger = logger.bind(component="audio")
        self._available = False
        self._check_availability()

    def _check_availability(self):
        """Check if audio model is available."""
        # Check for whisper endpoint
        if self.whisper_endpoint:
            try:
                import httpx
                resp = httpx.get(f"{self.whisper_endpoint}/health", timeout=5.0)
                if resp.status_code == 200:
                    self._available = True
                    self.logger.info("whisper_endpoint_available", endpoint=self.whisper_endpoint)
                    return
            except Exception:
                pass

        # Check Ollama for audio models
        try:
            import httpx
            resp = httpx.get(f"{self.api_base}/api/tags", timeout=5.0)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                if any("whisper" in name.lower() for name in model_names):
                    self._available = True
                    self.logger.info("whisper_model_available")
        except Exception:
            self.logger.info("audio_check_failed")

    @property
    def is_available(self) -> bool:
        return self._available

    async def transcribe(
        self,
        audio_path: Optional[str] = None,
        audio_bytes: Optional[bytes] = None,
        language: str = "en",
    ) -> AudioResult:
        """Transcribe audio to text."""
        if not self._available:
            return AudioResult(
                success=False,
                error="Audio model not available. Set whisper_endpoint or install whisper model.",
            )

        start = time.perf_counter()

        # Read audio file
        audio_data = None
        if audio_path:
            with open(audio_path, "rb") as f:
                audio_data = f.read()
        elif audio_bytes:
            audio_data = audio_bytes
        else:
            return AudioResult(success=False, error="No audio provided")

        try:
            if self.whisper_endpoint:
                return await self._transcribe_whisper_endpoint(audio_data, language, start)
            else:
                return await self._transcribe_ollama(audio_data, language, start)
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return AudioResult(success=False, error=str(e), metadata={"response_time_ms": elapsed})

    async def _transcribe_whisper_endpoint(
        self, audio_data: bytes, language: str, start: float
    ) -> AudioResult:
        """Transcribe using external whisper endpoint."""
        import httpx
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.whisper_endpoint}/transcribe",
                files={"audio": ("audio.wav", audio_data, "audio/wav")},
                data={"language": language},
            )
            response.raise_for_status()
            data = response.json()

            elapsed = (time.perf_counter() - start) * 1000
            return AudioResult(
                success=True,
                transcript=data.get("text", ""),
                language=data.get("language", language),
                duration_seconds=data.get("duration", 0.0),
                segments=data.get("segments", []),
                confidence=data.get("confidence", 0.0),
                metadata={"endpoint": self.whisper_endpoint, "response_time_ms": elapsed},
            )

    async def _transcribe_ollama(
        self, audio_data: bytes, language: str, start: float
    ) -> AudioResult:
        """Transcribe using Ollama (placeholder - Ollama doesn't natively support audio yet)."""
        # Ollama doesn't have native audio support yet
        # This is a placeholder for future integration
        elapsed = (time.perf_counter() - start) * 1000
        return AudioResult(
            success=False,
            error="Ollama audio transcription not yet supported. Use whisper_endpoint instead.",
            metadata={"response_time_ms": elapsed},
        )

    async def analyze_audio(
        self,
        audio_path: Optional[str] = None,
        audio_bytes: Optional[bytes] = None,
        prompt: str = "What is being discussed in this audio?",
    ) -> AudioResult:
        """Analyze audio content with a prompt."""
        # First transcribe
        result = await self.transcribe(audio_path=audio_path, audio_bytes=audio_bytes)
        if not result.success:
            return result

        # Then analyze the transcript using LLM
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_base}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": f"{prompt}\n\nTranscript:\n{result.transcript}",
                        "stream": False,
                    },
                )
                response.raise_for_status()
                analysis = response.json().get("response", "")
                result.metadata["analysis"] = analysis
        except Exception as e:
            result.metadata["analysis_error"] = str(e)

        return result


class MultimodalProcessor:
    """Unified interface for multimodal processing."""

    def __init__(self, settings=None):
        self.settings = settings
        self.logger = structlog.get_logger(component="multimodal")

        # Initialize vision
        vision_model = "llava"
        api_base = "http://localhost:11434"
        if settings and hasattr(settings, 'llm'):
            api_base = settings.llm.api_base.replace("/v1", "")
        self.vision = VisionProcessor(model=vision_model, api_base=api_base)

        # Initialize audio
        self.audio = AudioProcessor(api_base=api_base)

    async def initialize(self):
        """Check availability of multimodal models."""
        self.logger.info(
            "multimodal_initialized",
            vision_available=self.vision.is_available,
            audio_available=self.audio.is_available,
        )

    async def process_image(
        self,
        image_path: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        image_url: Optional[str] = None,
        prompt: str = "Describe this image in detail.",
    ) -> VisionResult:
        """Process an image from path, bytes, or URL."""
        if image_url:
            return await self.vision.analyze_url(image_url, prompt)
        return await self.vision.analyze_image(image_path=image_path, image_bytes=image_bytes, prompt=prompt)

    async def process_audio(
        self,
        audio_path: Optional[str] = None,
        audio_bytes: Optional[bytes] = None,
        language: str = "en",
        analyze: bool = False,
        prompt: str = "What is being discussed?",
    ) -> AudioResult:
        """Process audio with optional analysis."""
        if analyze:
            return await self.audio.analyze_audio(audio_path=audio_path, audio_bytes=audio_bytes, prompt=prompt)
        return await self.audio.transcribe(audio_path=audio_path, audio_bytes=audio_bytes, language=language)

    def get_status(self) -> Dict:
        return {
            "vision_available": self.vision.is_available,
            "vision_model": self.vision.model,
            "audio_available": self.audio.is_available,
            "audio_model": self.audio.model,
        }


logger = structlog.get_logger()
