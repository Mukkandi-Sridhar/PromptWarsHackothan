from __future__ import annotations
import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


class Config:
    # LLM provider: openai | anthropic | google | none
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_MODEL_STRONG: str = os.getenv("OPENAI_MODEL_STRONG", "gpt-4o")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")
    GOOGLE_MODEL: str = os.getenv("GOOGLE_MODEL", "gemini-1.5-flash")

    # DB paths
    DB_PATH: str = os.getenv("DB_PATH", "data/signal.db")
    CHROMA_PATH: str = os.getenv("CHROMA_PATH", "data/chroma")

    # Embedding model
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    # Feature flags
    DETERMINISTIC_MODE: bool = os.getenv("DETERMINISTIC_MODE", "false").lower() == "true"

    # Thresholds
    SUBSTANCE_PASS_THRESHOLD: int = 60
    CONVERGENCE_THRESHOLD: float = 3.0
    RETRIEVAL_TOP_K: int = 35

    @property
    def has_llm(self) -> bool:
        if self.DETERMINISTIC_MODE:
            return False
        if self.LLM_PROVIDER == "openai":
            return bool(self.OPENAI_API_KEY)
        if self.LLM_PROVIDER == "anthropic":
            return bool(self.ANTHROPIC_API_KEY)
        if self.LLM_PROVIDER == "google":
            return bool(self.GOOGLE_API_KEY)
        return False


@lru_cache(maxsize=1)
def get_config() -> Config:
    return Config()
