import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from app.models import MatchResponse, MatchedMovie, Movie
from app.services.interfaces import WatchlistScraperProtocol, MovieEnricherProtocol
from app.services.scraper import (
    LetterboxdScraperService,
    LetterboxdUserNotFoundError,
    LetterboxdScraperError,
)
from app.services.tmdb import TMDBEnricherService

logger = logging.getLogger(__name__)


class MatcherServiceError(Exception):
    """Business exception raised during watchlist matching operations."""
    pass


@dataclass
class MovieAggregate:
    """
    Aggregates movie occurrences and metadata across multiple user profiles.
    Clean helper methods provide self-documenting code.
    """
    slug: str
    title: str
    poster_url: Optional[str] = None
    poster_endpoint: Optional[str] = None
    present_in_users: Set[str] = field(default_factory=set)

    @property
    def user_count(self) -> int:
        """Returns the number of users who have this movie in their watchlist."""
        return len(self.present_in_users)

    def is_match(self, min_users_threshold: int = 2) -> bool:
        """A movie is considered a match if at least `min_users_threshold` users share it."""
        return self.user_count >= min_users_threshold

    def is_perfect_match(self, total_users_count: int) -> bool:
        """A perfect match occurs when every single user has this movie on their watchlist."""
        return self.user_count == total_users_count


class WatchlistMatcherService:
    """
    Core service for aggregating and comparing watchlists (SRP).
    Employs Dependency Injection for scraper and enricher via protocols.
    """

    def __init__(
        self,
        scraper: Optional[WatchlistScraperProtocol] = None,
        enricher: Optional[MovieEnricherProtocol] = None,
    ):
        self.scraper: WatchlistScraperProtocol = scraper or LetterboxdScraperService()
        self.enricher: MovieEnricherProtocol = enricher or TMDBEnricherService()

    async def _fetch_watchlists_concurrently(self, usernames: List[str]) -> Dict[str, List[Movie]]:
        """Fetches all user watchlists concurrently via the scraper interface."""
        scrape_tasks = [self.scraper.scrape_watchlist(username) for username in usernames]
        scrape_results = await asyncio.gather(*scrape_tasks, return_exceptions=True)

        user_watchlists: Dict[str, List[Movie]] = {}
        error_messages: List[str] = []

        for username, result in zip(usernames, scrape_results):
            if isinstance(result, LetterboxdUserNotFoundError):
                error_messages.append(f"User '{username}' was not found on Letterboxd (404).")
            elif isinstance(result, LetterboxdScraperError):
                error_messages.append(f"Error scraping watchlist for '{username}': {str(result)}")
            elif isinstance(result, Exception):
                error_messages.append(f"Error for '{username}': {str(result)}")
            else:
                user_watchlists[username] = result

        if error_messages:
            raise MatcherServiceError("; ".join(error_messages))

        return user_watchlists

    def _aggregate_movies(self, user_watchlists: Dict[str, List[Movie]]) -> Dict[str, MovieAggregate]:
        """Builds a frequency table of all movies across all profiles."""
        aggregates: Dict[str, MovieAggregate] = {}

        for username, movies_in_watchlist in user_watchlists.items():
            for movie in movies_in_watchlist:
                slug = movie.slug

                if slug not in aggregates:
                    aggregates[slug] = MovieAggregate(
                        slug=slug,
                        title=movie.title,
                        poster_url=movie.poster_url,
                        poster_endpoint=movie.poster_endpoint,
                    )

                entry = aggregates[slug]
                entry.present_in_users.add(username)

                # Update poster metadata if not yet populated
                if not entry.poster_url and movie.poster_url:
                    entry.poster_url = movie.poster_url
                if not entry.poster_endpoint and movie.poster_endpoint:
                    entry.poster_endpoint = movie.poster_endpoint

        return aggregates

    async def match_watchlists(self, usernames: List[str]) -> MatchResponse:
        """
        Executes the full watchlist comparison workflow:
        1. Fetch watchlists
        2. Aggregate movies
        3. Determine match intersections
        4. Concurrently enrich posters and TMDB metadata
        """
        total_users = len(usernames)

        # 1. Fetch watchlists
        user_watchlists = await self._fetch_watchlists_concurrently(usernames)
        user_stats: Dict[str, int] = {user: len(movies) for user, movies in user_watchlists.items()}

        # 2. Aggregate movies
        movie_aggregates = self._aggregate_movies(user_watchlists)

        # 3. Find movies shared by at least 2 users
        matched_movies: List[MatchedMovie] = []
        poster_endpoints_by_slug: Dict[str, str] = {}

        for aggregate in movie_aggregates.values():
            if aggregate.is_match(min_users_threshold=2):
                matched_movies.append(
                    MatchedMovie(
                        slug=aggregate.slug,
                        title=aggregate.title,
                        poster_url=aggregate.poster_url,
                        match_count=aggregate.user_count,
                        matched_users=sorted(list(aggregate.present_in_users)),
                        is_perfect_match=aggregate.is_perfect_match(total_users),
                    )
                )
                if aggregate.poster_endpoint:
                    poster_endpoints_by_slug[aggregate.slug] = aggregate.poster_endpoint

        # Sort order: match count descending, then alphabetically by title
        matched_movies.sort(key=lambda movie: (-movie.match_count, movie.title.lower()))

        # 4. Concurrently enrich posters and TMDB details for matches
        await asyncio.gather(
            self.scraper.resolve_posters(matched_movies, poster_endpoints_by_slug),
            self.enricher.enrich_movies(matched_movies),
        )

        perfect_matches = [m for m in matched_movies if m.is_perfect_match]
        partial_matches = [m for m in matched_movies if not m.is_perfect_match]

        return MatchResponse(
            total_users=total_users,
            usernames=usernames,
            user_stats=user_stats,
            perfect_matches=perfect_matches,
            partial_matches=partial_matches,
            all_matches=matched_movies,
        )


# Default global service instance
default_matcher_service = WatchlistMatcherService()


async def match_user_watchlists(usernames: List[str]) -> MatchResponse:
    """Module-level convenience function for matching watchlists."""
    return await default_matcher_service.match_watchlists(usernames)
