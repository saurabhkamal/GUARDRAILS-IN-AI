"""
Central configuration - reads from .env and exposes settings.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# .env is at project root (parent of backend/)
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)


class Config:
    """Application settings loaded from environment."""

    # Subabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

    # Euron Euri API (gpt-4.1-nano, OpenAI-compatible)
    EURON_API_KEY: str = (
        os.getenv("EURON_API_KEY")
        or os.getenv("EURIAI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or ""
    )
    EURON_BASE_URL: str = os.getenv("EURON_BASE_URL", "https://api.euron.one/api/v1/euri")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4.1-nano")

    # API
    API_URL: str = os.getenv("API_URL", "http://localhost:8000")

    @classmethod
    def get_supabase_required(cls) -> tuple[str, str]:
        """Return (SUPABASE_URL, SUPABASE_KEY); raises if missing."""
        if not cls.SUPABASE_URL or not cls.SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
        return cls.SUPABASE_URL, cls.SUPABASE_KEY
