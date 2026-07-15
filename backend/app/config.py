"""Application configuration, loaded from environment variables (.env)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (where .env.example lives), falling back to
# the backend directory.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(_BACKEND_DIR.parent / ".env")
load_dotenv(_BACKEND_DIR / ".env")


def _get(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


@dataclass
class Settings:
    # Entra / SharePoint
    tenant_id: str = field(default_factory=lambda: _get("AZURE_TENANT_ID"))
    client_id: str = field(default_factory=lambda: _get("AZURE_CLIENT_ID"))
    client_secret: str = field(default_factory=lambda: _get("AZURE_CLIENT_SECRET"))
    sharepoint_hostname: str = field(default_factory=lambda: _get("SHAREPOINT_HOSTNAME"))
    sharepoint_site_path: str = field(default_factory=lambda: _get("SHAREPOINT_SITE_PATH"))
    sharepoint_library: str = field(default_factory=lambda: _get("SHAREPOINT_LIBRARY", "Documents"))

    # Ollama
    ollama_base_url: str = field(default_factory=lambda: _get("OLLAMA_BASE_URL", "http://localhost:11434"))
    embedding_model: str = field(default_factory=lambda: _get("EMBEDDING_MODEL", "nomic-embed-text"))
    chat_model: str = field(default_factory=lambda: _get("CHAT_MODEL"))

    # Storage
    data_dir: Path = field(default_factory=lambda: Path(_get("DATA_DIR", "./data")))

    # Search / chunking
    search_top_k: int = field(default_factory=lambda: _get_int("SEARCH_TOP_K", 8))
    chunk_size: int = field(default_factory=lambda: _get_int("CHUNK_SIZE", 1200))
    chunk_overlap: int = field(default_factory=lambda: _get_int("CHUNK_OVERLAP", 150))

    # CORS
    cors_origins: list[str] = field(
        default_factory=lambda: [
            o.strip() for o in _get("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()
        ]
    )

    @property
    def sharepoint_configured(self) -> bool:
        return bool(self.tenant_id and self.client_id and self.client_secret and self.sharepoint_hostname)

    @property
    def chat_enabled(self) -> bool:
        return bool(self.chat_model)


settings = Settings()
