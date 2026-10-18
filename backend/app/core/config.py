import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def load_env_file() -> None:
    """
    Lightweight, dependency-free environment variable loader (KISS).
    Searches for .env and tmdb.env files in the backend and project root directories.
    """
    backend_dir = Path(__file__).resolve().parent.parent.parent
    root_dir = backend_dir.parent
    candidates = [
        backend_dir / ".env",
        backend_dir / "tmdb.env",
        root_dir / ".env",
        root_dir / "tmdb.env",
    ]
    for env_path in candidates:
        if env_path.exists() and env_path.is_file():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip("\"'")
                        if key and key not in os.environ:
                            os.environ[key] = val
            except Exception as e:
                logger.warning(f"Failed to read environment file at {env_path}: {e}")


# Initialize environment variables immediately upon module import
load_env_file()


def get_tmdb_api_key() -> str:
    """Returns the configured TMDB API key or an empty string if omitted."""
    return os.getenv("TMDB_API_KEY", "").strip()


def get_default_language() -> str:
    """Returns the preferred language code for titles and genres (e.g. 'en-US', 'de-DE')."""
    return os.getenv("TMDB_LANGUAGE", "en-US").strip() or "en-US"
