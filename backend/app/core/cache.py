from pathlib import Path
from typing import Optional
import diskcache

# Central directory for SQLite-backed diskcache in backend/.diskcache
CACHE_DIR = Path(__file__).resolve().parent.parent.parent / ".diskcache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
cache = diskcache.Cache(str(CACHE_DIR))

# Standard cache expiration durations (TTLs)
WATCHLIST_TTL_SECONDS = 60 * 60            # 60 minutes for scraped watchlists
POSTER_TTL_SECONDS = 24 * 60 * 60           # 24 hours for resolved poster URLs
TMDB_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60   # 7 days for TMDB metadata (genres, ratings, runtime)


def clear_cache(username: Optional[str] = None) -> None:
    """
    Clears the cache either specifically for a single user's watchlist
    or completely purges all stored cache keys.
    """
    if username:
        clean_user = username.strip().lower()
        cache.delete(f"watchlist:{clean_user}")
    else:
        cache.clear()
