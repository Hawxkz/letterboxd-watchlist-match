import pytest
from typing import Dict, List

from app.models import Movie, MatchedMovie
from app.services.interfaces import WatchlistScraperProtocol
from app.services.matcher import WatchlistMatcherService, MatcherServiceError
from app.services.scraper import LetterboxdUserNotFoundError


class FakeWatchlistScraper(WatchlistScraperProtocol):
    """
    Test double (mock) implementing WatchlistScraperProtocol.
    Enables isolated unit testing of matching logic without HTTP requests or monkey-patching.
    """

    def __init__(self, watchlists: Dict[str, List[Movie]]):
        self.watchlists = watchlists

    async def scrape_watchlist(self, username: str, force_refresh: bool = False) -> List[Movie]:
        clean_user = username.lower()
        if clean_user not in self.watchlists:
            raise LetterboxdUserNotFoundError(f"User '{username}' was not found.")
        return self.watchlists[clean_user]

    async def resolve_posters(self, movies: List[MatchedMovie], endpoints: Dict[str, str]) -> None:
        # No-op in test environment
        pass


@pytest.mark.anyio
async def test_matcher_service_with_injected_interface():
    """Tests intersection logic for perfect matches and partial matches via interface injection."""
    fake_data = {
        "alice": [
            Movie(slug="alien", title="Alien", poster_url="https://img/alien.jpg"),
            Movie(slug="blade-runner", title="Blade Runner", poster_url="https://img/br.jpg"),
            Movie(slug="matrix", title="The Matrix", poster_url="https://img/matrix.jpg"),
        ],
        "bob": [
            Movie(slug="alien", title="Alien", poster_url="https://img/alien.jpg"),
            Movie(slug="matrix", title="The Matrix", poster_url="https://img/matrix.jpg"),
            Movie(slug="inception", title="Inception", poster_url="https://img/inc.jpg"),
        ],
        "charlie": [
            Movie(slug="alien", title="Alien", poster_url="https://img/alien.jpg"),
            Movie(slug="matrix", title="The Matrix", poster_url="https://img/matrix.jpg"),
        ],
    }

    fake_scraper = FakeWatchlistScraper(watchlists=fake_data)
    matcher = WatchlistMatcherService(scraper=fake_scraper)

    response = await matcher.match_watchlists(["alice", "bob", "charlie"])

    # Verify metrics
    assert response.total_users == 3
    assert response.usernames == ["alice", "bob", "charlie"]
    assert response.user_stats == {"alice": 3, "bob": 3, "charlie": 2}

    # Perfect matches: 'alien' and 'matrix' are present on all 3 watchlists
    assert len(response.perfect_matches) == 2
    perfect_slugs = {m.slug for m in response.perfect_matches}
    assert perfect_slugs == {"alien", "matrix"}

    for match in response.perfect_matches:
        assert match.is_perfect_match is True
        assert match.match_count == 3
        assert set(match.matched_users) == {"alice", "bob", "charlie"}

    # Partial matches: no movies with count of 2 (blade-runner & inception only 1x)
    assert len(response.partial_matches) == 0


@pytest.mark.anyio
async def test_matcher_service_raises_on_missing_user():
    """Ensures missing profiles raise MatcherServiceError with descriptive details."""
    fake_scraper = FakeWatchlistScraper(watchlists={"alice": []})
    matcher = WatchlistMatcherService(scraper=fake_scraper)

    with pytest.raises(MatcherServiceError) as error_info:
        await matcher.match_watchlists(["alice", "unknown_user"])

    assert "not found" in str(error_info.value).lower()
