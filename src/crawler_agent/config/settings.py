"""Configuration settings for Ontogeny's Knowledge Acquisition System."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

# Find .env relative to project root (parent of src/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_ENV_FILE = str(_PROJECT_ROOT / ".env")


class ProxyProviderConfig(BaseSettings):
    """Paid proxy provider configuration."""

    model_config = {
        "env_prefix": "PROXY_PROVIDER_",
        "env_file": _ENV_FILE,
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    name: str = ""  # brightdata, smartproxy, oxylabs, proxyrack
    api_key: str = ""
    host: str = ""
    port: int = 0
    username: str = ""
    password: str = ""


class ProxyConfig(BaseSettings):
    """Proxy configuration."""

    model_config = {
        "env_prefix": "PROXY_",
        "env_file": _ENV_FILE,
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    enabled: bool = True
    required: bool = True  # Fail if no proxy available

    # Proxy list (format: protocol://user:pass@host:port or protocol://host:port)
    proxies: list[str] = Field(default_factory=list)

    # Proxy file (one proxy per line)
    proxy_file: str = ""

    # Authentication
    username: str = ""
    password: str = ""

    # Rotation
    rotate_every: int = 10  # Requests before rotating
    max_failures: int = 3  # Failures before marking proxy dead
    health_check_interval: int = 300  # Seconds between health checks

    # Auto-refresh
    auto_refresh: bool = True
    min_proxies: int = 10
    refresh_interval: int = 300  # Seconds between refresh attempts
    fetch_free_proxies: bool = True

    # Paid providers
    providers: list[ProxyProviderConfig] = Field(default_factory=list)

    # Supported protocols
    allowed_protocols: list[str] = Field(default=["http", "https", "socks5"])

    # Timeout
    connect_timeout: float = 10.0
    read_timeout: float = 30.0


class CrawlerSettings(BaseSettings):
    """Crawler configuration."""

    model_config = {
        "env_prefix": "CRAWLER_",
        "env_file": _ENV_FILE,
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    # Rate limiting
    requests_per_second: float = 10.0
    burst_size: int = 50
    retry_attempts: int = 3
    retry_delay: float = 1.0

    # User agent rotation
    user_agents: list[str] = Field(
        default=[
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        ]
    )

    # Request headers
    accept_language: str = "en-US,en;q=0.9"
    accept_encoding: str = "gzip, deflate, br"

    # Crawling scope
    max_depth: int = 5
    max_pages_per_domain: int = 10000
    respect_robots_txt: bool = True

    # Anti-detection
    randomize_delay: bool = True
    min_delay: float = 0.5
    max_delay: float = 2.0


class StorageSettings(BaseSettings):
    """Storage configuration."""

    model_config = {
        "env_prefix": "STORAGE_",
        "env_file": _ENV_FILE,
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    # PostgreSQL
    database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/crawler"

    # Redis (caching, queues)
    redis_url: str = "redis://localhost:6379/0"

    # ChromaDB (vectors)
    chroma_path: str = "./data/chroma"

    # File storage
    file_store_path: str = "./data/files"


class LLMSettings(BaseSettings):
    """LLM configuration (routine — llama3.2)."""

    model_config = {
        "env_prefix": "LLM_",
        "env_file": _ENV_FILE,
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    provider: str = "openai"  # openai, ollama, local
    model: str = "llama3.2"
    api_key: str = "ollama"
    api_base: str = "http://localhost:11434/v1"

    # Processing
    chunk_size: int = 4000
    chunk_overlap: int = 200
    embedding_model: str = "text-embedding-3-small"

    # Rate limits
    requests_per_minute: int = 60
    tokens_per_minute: int = 150000


class CodeLLMSettings(BaseSettings):
    """Code LLM configuration (deepseek-coder-v2:16b for code generation)."""

    model_config = {
        "env_prefix": "CODE_LLM_",
        "env_file": _ENV_FILE,
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    enabled: bool = True
    model: str = "deepseek-coder-v2:16b"
    api_key: str = "ollama"
    api_base: str = "http://localhost:11434/v1"


class HeavyLLMSettings(BaseSettings):
    """Heavy LLM configuration (qwen2.5:72b for complex reasoning)."""

    model_config = {
        "env_prefix": "HEAVY_LLM_",
        "env_file": _ENV_FILE,
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    enabled: bool = True
    model: str = "qwen2.5:72b"
    api_key: str = "ollama"
    api_base: str = "http://localhost:11434/v1"


class PlatformSettings(BaseSettings):
    """Platform-specific API keys and settings."""

    model_config = {
        "env_prefix": "PLATFORM_",
        "env_file": _ENV_FILE,
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    # GitHub
    github_token: str = ""
    github_api_url: str = "https://api.github.com"

    # HuggingFace
    huggingface_token: str = ""
    huggingface_api_url: str = "https://huggingface.co/api"

    # Pastebin
    pastebin_api_key: str = ""

    # Academic
    semantic_scholar_api_key: str = ""
    ncbi_api_key: str = ""


class Settings(BaseSettings):
    """Main settings container."""

    model_config = {"env_file": _ENV_FILE, "env_file_encoding": "utf-8"}

    crawler: CrawlerSettings = Field(default_factory=CrawlerSettings)
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    code_llm: CodeLLMSettings = Field(default_factory=CodeLLMSettings)
    heavy_llm: HeavyLLMSettings = Field(default_factory=HeavyLLMSettings)
    platform: PlatformSettings = Field(default_factory=PlatformSettings)

    # Emotion visualization mode for Blender sandbox
    emotion_visualizer: str = Field(
        default="sphere", env="EMOTION_VISUALIZER"
    )  # "sphere" | "anatomy" | "both"

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"


def load_settings() -> Settings:
    """Load settings from environment and .env file."""
    return Settings()
