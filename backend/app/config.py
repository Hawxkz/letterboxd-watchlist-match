import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def load_env_file() -> None:
    """
    Lightweight, dependency-free .env file reader (KISS).
    Loads key=value pairs into os.environ if they are not already set.
    Checks backend/tmdb.env, backend/.env, root tmdb.env, and root .env.
    """
    backend_dir = Path(__file__).resolve().parent.parent
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


# Initialize environment variables as early as possible
load_env_file()
