"""Configuration partagée du laboratoire.

Les secrets sont lus depuis l'environnement ou un fichier .env local.
Aucune clé n'est codée en dur et aucune valeur secrète n'est journalisée.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# Chroma tente sinon d'envoyer une télémétrie anonyme.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("CHROMA_TELEMETRY_IMPL", "none")

_SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"(?i)(api[_-]?key|token|secret)\s*[:=]\s*\S+"),
)


class RedactingFilter(logging.Filter):
    """Retire les motifs de secrets avant l'écriture d'un journal."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        redacted = message
        for pattern in _SECRET_PATTERNS:
            redacted = pattern.sub("[SECRET REDACTE]", redacted)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True


def get_logger(name: str) -> logging.Logger:
    """Retourne un logger qui ne laisse pas passer de clé API."""

    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        handler.addFilter(RedactingFilter())
        logger.addHandler(handler)
        logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
        logger.propagate = False
    return logger


def _flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Paramètres d'exécution. Les champs sensibles restent des chaînes vides si absents."""

    llm_provider: str
    llm_model: str
    llm_model_advanced: str
    vision_model: str
    openai_api_key: str
    google_api_key: str
    embedding_provider: str
    embedding_model: str
    tavily_api_key: str
    langsmith_api_key: str
    langsmith_tracing: bool
    mcp_demo_host: str
    mcp_demo_port: int
    mcp_demo_url: str
    mcp_rag_host: str
    mcp_rag_port: int
    mcp_rag_url: str
    checkpoint_path: Path
    allow_python_repl: bool
    root: Path

    @property
    def chat_credentials_present(self) -> bool:
        if self.llm_provider == "openai":
            return bool(self.openai_api_key)
        if self.llm_provider == "google":
            return bool(self.google_api_key)
        if self.llm_provider in {"ollama", "fake"}:
            return True
        return False

    @property
    def vision_credentials_present(self) -> bool:
        if not self.vision_model:
            return False
        if self.llm_provider == "google" or self.vision_model.startswith("gemini"):
            return bool(self.google_api_key)
        return bool(self.openai_api_key)


def get_settings() -> Settings:
    """Relit l'environnement à chaque appel afin que les tests puissent le modifier."""

    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "openai").strip().lower(),
        llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini").strip(),
        llm_model_advanced=os.getenv("LLM_MODEL_ADVANCED", "gpt-4o-mini").strip(),
        vision_model=os.getenv("VISION_MODEL", "gpt-4o-mini").strip(),
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        google_api_key=os.getenv("GOOGLE_API_KEY", "").strip(),
        embedding_provider=os.getenv("EMBEDDING_PROVIDER", "hash").strip().lower(),
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small").strip(),
        tavily_api_key=os.getenv("TAVILY_API_KEY", "").strip(),
        langsmith_api_key=os.getenv("LANGSMITH_API_KEY", "").strip(),
        langsmith_tracing=_flag("LANGSMITH_TRACING", False),
        mcp_demo_host=os.getenv("MCP_DEMO_HOST", "127.0.0.1").strip(),
        mcp_demo_port=int(os.getenv("MCP_DEMO_PORT", "8000")),
        mcp_demo_url=os.getenv("MCP_DEMO_URL", "http://127.0.0.1:8000/mcp").strip(),
        mcp_rag_host=os.getenv("MCP_RAG_HOST", "127.0.0.1").strip(),
        mcp_rag_port=int(os.getenv("MCP_RAG_PORT", "8001")),
        mcp_rag_url=os.getenv("MCP_RAG_URL", "http://127.0.0.1:8001/mcp").strip(),
        checkpoint_path=Path(os.getenv("CHECKPOINT_PATH", "data/checkpoints.sqlite")),
        allow_python_repl=_flag("AGENTIC_ALLOW_PYTHON_REPL", False),
        root=ROOT,
    )
