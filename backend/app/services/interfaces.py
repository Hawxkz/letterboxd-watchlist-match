from typing import Dict, List, Protocol, runtime_checkable

from app.models import Movie, MatchedMovie


@runtime_checkable
class WatchlistScraperProtocol(Protocol):
    """
    Interface definition for services that scrape Letterboxd watchlists
    and resolve high-resolution poster images asynchronously.
    """

    async def scrape_watchlist(self, username: str, force_refresh: bool = False) -> List[Movie]:
        """Fetches the complete movie watchlist for a given Letterboxd username."""
        ...

    async def resolve_posters(self, movies: List[MatchedMovie], endpoints: Dict[str, str]) -> None:
        """Resolves high-resolution poster image URLs for matched movies."""
        ...


@runtime_checkable
class MovieEnricherProtocol(Protocol):
    """
    Interface definition for services that enrich movie match candidates
    with metadata such as TMDB ratings, runtime duration, and genres.
    """

    async def enrich_movies(self, movies: List[MatchedMovie]) -> None:
        """Enriches the provided list of matched movies in-place with metadata."""
        ...
