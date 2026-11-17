"""Server settings, read from environment variables or a local .env file.

The API key is only ever read here, on the server. It is never sent to the
browser and never written to logs.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    ai_provider: str        # "fake", "anthropic", or "openai"
    ai_model: str
    ai_api_key: str
    database_path: Path
    documents_dir: Path
    deadline_seconds: float = 15.0


def load_settings() -> Settings:
    provider = os.getenv("AI_PROVIDER", "fake").strip().lower()
    return Settings(
        ai_provider=provider,
        ai_model=os.getenv("AI_MODEL", "").strip(),
        ai_api_key=os.getenv("AI_API_KEY", "").strip(),
        database_path=Path(os.getenv("DATABASE_PATH", PROJECT_ROOT / "data" / "policies.db")),
        documents_dir=PROJECT_ROOT / "data" / "documents",
    )
