from typing import List
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.models import Movie, MatchRequest
from app.core.cache import cache, clear_cache
from app.core.security import validate_username_safety, is_safe_scrape_url, is_safe_ip
from app.core.rate_limiter import match_rate_limiter
from app.services.scraper import _extract_movies_from_soup
from app.services.tmdb import _generate_fallback_details, FALLBACK_CATALOG
from app.services.matcher import default_matcher_service

client = TestClient(app)


def test_health_endpoints():
    """Tests that root and health check endpoints respond with HTTP 200."""
    root_response = client.get("/")
    assert root_response.status_code == 200
    assert root_response.json()["status"] == "healthy"

    health_response = client.get("/api/health")
    assert health_response.status_code == 200
    assert health_response.json()["status"] == "ok"


def test_match_validation_too_few_users():
    """Pydantic validation: Fewer than 2 users must be rejected with HTTP 422."""
    response = client.post("/api/match", json={"usernames": ["dave"]})
    assert response.status_code == 422


def test_match_validation_duplicate_users():
    """Pydantic validation: Duplicate profiles must be rejected with HTTP 422."""
    response = client.post("/api/match", json={"usernames": ["dave", "dave"]})
    assert response.status_code == 422


def test_match_validation_with_profile_urls():
    """Tests automatic extraction and normalization of usernames from full Letterboxd profile URLs."""
    request_data = MatchRequest(usernames=[
        "https://letterboxd.com/alice/",
        "https://letterboxd.com/bob/watchlist/",
        "http://www.letterboxd.com/charlie/films",
        "@dave",
        "eve",
    ])
    assert request_data.usernames == ["alice", "bob", "charlie", "dave", "eve"]


def test_match_logic_with_mocked_scraper():
    """Tests end-to-end intersection computation via matcher service with a mocked scraper."""
    movies_alice: List[Movie] = [
        Movie(slug="movie-shared-all", title="Shared by All", poster_url="https://example.com/p1.jpg"),
        Movie(slug="movie-shared-ab", title="Shared by Alice & Bob", poster_url="https://example.com/p2.jpg"),
        Movie(slug="movie-alice-only", title="Alice Only", poster_url="https://example.com/p3.jpg"),
    ]
    movies_bob: List[Movie] = [
        Movie(slug="movie-shared-all", title="Shared by All", poster_url="https://example.com/p1.jpg"),
        Movie(slug="movie-shared-ab", title="Shared by Alice & Bob", poster_url="https://example.com/p2.jpg"),
        Movie(slug="movie-bob-only", title="Bob Only", poster_url="https://example.com/p4.jpg"),
    ]
    movies_charlie: List[Movie] = [
        Movie(slug="movie-shared-all", title="Shared by All", poster_url="https://example.com/p1.jpg"),
        Movie(slug="movie-charlie-only", title="Charlie Only", poster_url="https://example.com/p5.jpg"),
    ]

    async def mock_scrape_watchlist(username: str, force_refresh: bool = False) -> List[Movie]:
        user_lower = username.lower()
        if user_lower == "alice":
            return movies_alice
        elif user_lower == "bob":
            return movies_bob
        elif user_lower == "charlie":
            return movies_charlie
        raise ValueError(f"Unknown test user '{username}'")

    with patch.object(default_matcher_service.scraper, "scrape_watchlist", side_effect=mock_scrape_watchlist):
        response = client.post(
            "/api/match",
            json={"usernames": ["alice", "bob", "charlie"]},
        )
        assert response.status_code == 200
        payload = response.json()

        assert payload["total_users"] == 3
        assert payload["usernames"] == ["alice", "bob", "charlie"]
        assert payload["user_stats"] == {"alice": 3, "bob": 3, "charlie": 2}

        # Perfect matches (3 out of 3 users)
        assert len(payload["perfect_matches"]) == 1
        perfect_match = payload["perfect_matches"][0]
        assert perfect_match["slug"] == "movie-shared-all"
        assert perfect_match["match_count"] == 3
        assert perfect_match["is_perfect_match"] is True
        assert set(perfect_match["matched_users"]) == {"alice", "bob", "charlie"}

        # Partial matches (2 out of 3 users)
        assert len(payload["partial_matches"]) == 1
        partial_match = payload["partial_matches"][0]
        assert partial_match["slug"] == "movie-shared-ab"
        assert partial_match["match_count"] == 2
        assert partial_match["is_perfect_match"] is False
        assert set(partial_match["matched_users"]) == {"alice", "bob"}

        # All matches sorted descending by count
        assert len(payload["all_matches"]) == 2
        assert payload["all_matches"][0]["slug"] == "movie-shared-all"
        assert payload["all_matches"][1]["slug"] == "movie-shared-ab"


def test_diskcache_storage():
    """Tests storing and clearing items in the central diskcache."""
    clear_cache()
    test_key = "watchlist:testuser"
    assert cache.get(test_key) is None

    test_payload = [{"slug": "inception", "title": "Inception", "poster_url": "https://img.com/inc.jpg"}]
    cache.set(test_key, test_payload, expire=3600)

    cached_entry = cache.get(test_key)
    assert cached_entry is not None
    assert cached_entry[0]["slug"] == "inception"

    clear_cache("testuser")
    assert cache.get(test_key) is None


def test_extract_movies_from_soup():
    """Tests extraction of movie metadata from Letterboxd LazyPoster elements."""
    from bs4 import BeautifulSoup

    sample_html = """
    <div class="poster-list">
        <div class="react-component"
             data-component-class="LazyPoster"
             data-item-slug="past-lives"
             data-item-name="Past Lives (2023)"
             data-item-link="/film/past-lives/"
             data-resolvable-poster-path='{"posteredBaseLink":"/film/past-lives/","cacheBustingKey":"123"}'>
             <img src="https://s.ltrbxd.com/empty.png" alt="Past Lives" />
        </div>
    </div>
    """
    soup = BeautifulSoup(sample_html, "html.parser")
    movies = _extract_movies_from_soup(soup)
    assert len(movies) == 1
    assert movies[0]["slug"] == "past-lives"
    assert movies[0]["title"] == "Past Lives (2023)"
    assert "https://letterboxd.com/film/past-lives/poster/std/230/?k=123" == movies[0]["poster_endpoint"]


def test_tmdb_fallback_and_enrichment():
    """Tests TMDB fallback catalog lookup and deterministic mock generation."""
    # Movie from fallback catalog
    inception_meta = _generate_fallback_details("inception", "Inception")
    assert inception_meta["rating"] == 8.4
    assert "Science Fiction" in inception_meta["genres"]
    assert inception_meta["runtime"] == 148

    # Unknown movie: deterministic mock
    unknown_meta = _generate_fallback_details("some-rare-indie-film", "Some Rare Indie Film")
    assert isinstance(unknown_meta["rating"], float)
    assert 6.0 <= unknown_meta["rating"] <= 9.0
    assert len(unknown_meta["genres"]) >= 1
    assert isinstance(unknown_meta["runtime"], int)
    assert unknown_meta["runtime"] >= 60


def test_match_response_includes_tmdb_fields():
    """Tests that TMDB metadata (rating, genres, runtime) are present in the match response."""
    movies_user1: List[Movie] = [
        Movie(slug="inception", title="Inception", poster_url="https://img.com/inc.jpg"),
    ]
    movies_user2: List[Movie] = [
        Movie(slug="inception", title="Inception", poster_url="https://img.com/inc.jpg"),
    ]

    async def mock_scrape(username: str, force_refresh: bool = False) -> List[Movie]:
        return movies_user1 if username == "user1" else movies_user2

    with patch.object(default_matcher_service.scraper, "scrape_watchlist", side_effect=mock_scrape):
        response = client.post(
            "/api/match",
            json={"usernames": ["user1", "user2"]},
        )
        assert response.status_code == 200
        payload = response.json()
        assert len(payload["perfect_matches"]) == 1
        matched_film = payload["perfect_matches"][0]
        assert matched_film["slug"] == "inception"
        assert matched_film["rating"] == 8.4
        assert "Science Fiction" in matched_film["genres"]
        assert matched_film["runtime"] == 148


def test_ssrf_username_validation():
    """Tests SSRF protections against path traversal, private IPs, and reserved Letterboxd paths."""
    # Valid usernames
    assert validate_username_safety("alice") == "alice"
    assert validate_username_safety("bob_123") == "bob_123"
    assert validate_username_safety("film-fan") == "film-fan"

    # Path traversal attempts
    with pytest.raises(ValueError):
        validate_username_safety("../admin")

    with pytest.raises(ValueError):
        validate_username_safety("alice/bob")

    with pytest.raises(ValueError):
        validate_username_safety("alice?foo=bar")

    # IP addresses provided as usernames
    with pytest.raises(ValueError):
        validate_username_safety("127.0.0.1")

    with pytest.raises(ValueError):
        validate_username_safety("169.254.169.254")

    # Reserved Letterboxd route names
    with pytest.raises(ValueError):
        validate_username_safety("film")

    with pytest.raises(ValueError):
        validate_username_safety("search")

    # IP safety validation
    assert is_safe_ip("8.8.8.8") is True
    assert is_safe_ip("127.0.0.1") is False
    assert is_safe_ip("10.0.0.1") is False
    assert is_safe_ip("192.168.1.1") is False
    assert is_safe_ip("169.254.169.254") is False
    assert is_safe_ip("::1") is False

    # Safe scraping URLs
    assert is_safe_scrape_url("https://letterboxd.com/alice/watchlist/") is True
    assert is_safe_scrape_url("http://letterboxd.com/alice/watchlist/") is False  # HTTPS only
    assert is_safe_scrape_url("https://attacker.com/evil") is False              # Not whitelisted
    assert is_safe_scrape_url("https://169.254.169.254/secret") is False         # Private IP


def test_cors_preflight_and_headers():
    """Tests preflight OPTIONS requests and CORS header responses."""
    preflight_headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type",
    }
    response = client.options("/api/match", headers=preflight_headers)
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "POST" in response.headers["access-control-allow-methods"]


def test_rate_limiter_enforcement():
    """Tests enforcement of HTTP 429 Too Many Requests when rate limit threshold is exceeded."""
    match_rate_limiter.reset()
    original_limit = match_rate_limiter.requests_per_window
    match_rate_limiter.requests_per_window = 3  # Lower limit for testing

    try:
        # First 3 requests pass rate limiter (fail with 422 due to incomplete request body)
        for _ in range(3):
            response = client.post("/api/match", json={"usernames": ["dave"]})
            assert response.status_code == 422

        # 4th request must be blocked by rate limiter with HTTP 429
        rate_limited_response = client.post("/api/match", json={"usernames": ["dave"]})
        assert rate_limited_response.status_code == 429
        assert "Retry-After" in rate_limited_response.headers
        assert "X-RateLimit-Limit" in rate_limited_response.headers
        assert "Too many requests" in rate_limited_response.json()["detail"] or "Zu viele" in rate_limited_response.json()["detail"]
    finally:
        match_rate_limiter.reset()
        match_rate_limiter.requests_per_window = original_limit
