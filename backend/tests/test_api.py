import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.models import Movie
from app.scraper import cache, clear_cache

client = TestClient(app)


def test_health_endpoints():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

    health_resp = client.get("/api/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "ok"


def test_match_validation_too_few_users():
    # Only 1 username provided
    response = client.post("/api/match", json={"usernames": ["dave"]})
    assert response.status_code == 422  # Pydantic validation error


def test_match_validation_duplicate_users():
    # 2 identical usernames provided
    response = client.post("/api/match", json={"usernames": ["dave", "dave"]})
    assert response.status_code == 422


def test_match_validation_with_profile_urls():
    from app.models import MatchRequest
    req = MatchRequest(usernames=[
        "https://letterboxd.com/alice/",
        "https://letterboxd.com/bob/watchlist/",
        "http://www.letterboxd.com/charlie/films",
        "@dave",
        "eve",
    ])
    assert req.usernames == ["alice", "bob", "charlie", "dave", "eve"]


def test_match_logic_with_mocked_scraper():
    movies_alice = [
        Movie(slug="movie-shared-all", title="Shared by All", poster_url="https://example.com/p1.jpg"),
        Movie(slug="movie-shared-ab", title="Shared by Alice & Bob", poster_url="https://example.com/p2.jpg"),
        Movie(slug="movie-alice-only", title="Alice Only", poster_url="https://example.com/p3.jpg"),
    ]
    movies_bob = [
        Movie(slug="movie-shared-all", title="Shared by All", poster_url="https://example.com/p1.jpg"),
        Movie(slug="movie-shared-ab", title="Shared by Alice & Bob", poster_url="https://example.com/p2.jpg"),
        Movie(slug="movie-bob-only", title="Bob Only", poster_url="https://example.com/p4.jpg"),
    ]
    movies_charlie = [
        Movie(slug="movie-shared-all", title="Shared by All", poster_url="https://example.com/p1.jpg"),
        Movie(slug="movie-charlie-only", title="Charlie Only", poster_url="https://example.com/p5.jpg"),
    ]

    async def mock_scrape(username, force_refresh=False):
        if username.lower() == "alice":
            return movies_alice
        elif username.lower() == "bob":
            return movies_bob
        elif username.lower() == "charlie":
            return movies_charlie
        raise ValueError("Unknown test user")

    with patch("app.main.scrape_user_watchlist_async", side_effect=mock_scrape):
        response = client.post(
            "/api/match",
            json={"usernames": ["alice", "bob", "charlie"]},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["total_users"] == 3
        assert data["usernames"] == ["alice", "bob", "charlie"]
        assert data["user_stats"] == {"alice": 3, "bob": 3, "charlie": 2}

        # Perfect matches (3/3)
        assert len(data["perfect_matches"]) == 1
        perfect = data["perfect_matches"][0]
        assert perfect["slug"] == "movie-shared-all"
        assert perfect["match_count"] == 3
        assert perfect["is_perfect_match"] is True
        assert set(perfect["matched_users"]) == {"alice", "bob", "charlie"}

        # Partial matches (2/3)
        assert len(data["partial_matches"]) == 1
        partial = data["partial_matches"][0]
        assert partial["slug"] == "movie-shared-ab"
        assert partial["match_count"] == 2
        assert partial["is_perfect_match"] is False
        assert set(partial["matched_users"]) == {"alice", "bob"}

        # All matches: sorted descending
        assert len(data["all_matches"]) == 2
        assert data["all_matches"][0]["slug"] == "movie-shared-all"
        assert data["all_matches"][1]["slug"] == "movie-shared-ab"


def test_diskcache_storage():
    clear_cache()
    test_key = "watchlist:testuser"
    assert cache.get(test_key) is None

    test_data = [{"slug": "inception", "title": "Inception", "poster_url": "https://img.com/inc.jpg"}]
    cache.set(test_key, test_data, expire=3600)

    cached = cache.get(test_key)
    assert cached is not None
    assert cached[0]["slug"] == "inception"

    clear_cache("testuser")
    assert cache.get(test_key) is None


def test_extract_movies_from_soup():
    from bs4 import BeautifulSoup
    from app.scraper import _extract_movies_from_soup

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
    from app.tmdb import _generate_fallback_details, FALLBACK_CATALOG
    
    # Test catalog movie
    inception_data = _generate_fallback_details("inception", "Inception")
    assert inception_data["rating"] == 8.4
    assert "Science Fiction" in inception_data["genres"]
    assert inception_data["runtime"] == 148

    # Test unknown film deterministic mock
    unknown_data = _generate_fallback_details("some-rare-indie-film", "Some Rare Indie Film")
    assert isinstance(unknown_data["rating"], float)
    assert 6.0 <= unknown_data["rating"] <= 9.0
    assert len(unknown_data["genres"]) >= 1
    assert isinstance(unknown_data["runtime"], int)
    assert unknown_data["runtime"] >= 60


def test_match_response_includes_tmdb_fields():
    movies_user1 = [
        Movie(slug="inception", title="Inception", poster_url="https://img.com/inc.jpg"),
    ]
    movies_user2 = [
        Movie(slug="inception", title="Inception", poster_url="https://img.com/inc.jpg"),
    ]

    async def mock_scrape(username, force_refresh=False):
        return movies_user1 if username == "user1" else movies_user2

    with patch("app.main.scrape_user_watchlist_async", side_effect=mock_scrape):
        response = client.post(
            "/api/match",
            json={"usernames": ["user1", "user2"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["perfect_matches"]) == 1
        match = data["perfect_matches"][0]
        assert match["slug"] == "inception"
        assert match["rating"] == 8.4
        assert "Science Fiction" in match["genres"]
        assert match["runtime"] == 148


def test_ssrf_username_validation():
    from app.security import validate_username_safety, is_safe_scrape_url, is_safe_ip

    # Valid usernames
    assert validate_username_safety("alice") == "alice"
    assert validate_username_safety("bob_123") == "bob_123"
    assert validate_username_safety("film-fan") == "film-fan"

    # Directory traversal attempts
    with pytest.raises(ValueError):
        validate_username_safety("../admin")

    with pytest.raises(ValueError):
        validate_username_safety("alice/bob")

    with pytest.raises(ValueError):
        validate_username_safety("alice?foo=bar")

    # IP addresses passed as usernames
    with pytest.raises(ValueError):
        validate_username_safety("127.0.0.1")

    with pytest.raises(ValueError):
        validate_username_safety("169.254.169.254")

    # Reserved letterboxd paths
    with pytest.raises(ValueError):
        validate_username_safety("film")

    with pytest.raises(ValueError):
        validate_username_safety("search")

    # Safe IP checks
    assert is_safe_ip("8.8.8.8") is True
    assert is_safe_ip("127.0.0.1") is False
    assert is_safe_ip("10.0.0.1") is False
    assert is_safe_ip("192.168.1.1") is False
    assert is_safe_ip("169.254.169.254") is False
    assert is_safe_ip("::1") is False

    # Safe scrape URLs
    assert is_safe_scrape_url("https://letterboxd.com/alice/watchlist/") is True
    assert is_safe_scrape_url("http://letterboxd.com/alice/watchlist/") is False  # Must be HTTPS
    assert is_safe_scrape_url("https://attacker.com/evil") is False  # Untrusted host
    assert is_safe_scrape_url("https://169.254.169.254/secret") is False  # Private IP


def test_cors_preflight_and_headers():
    # Preflight OPTIONS request
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type",
    }
    response = client.options("/api/match", headers=headers)
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "POST" in response.headers["access-control-allow-methods"]


def test_rate_limiter_enforcement():
    from app.rate_limiter import match_rate_limiter

    match_rate_limiter.reset()
    original_limit = match_rate_limiter.requests_per_window
    match_rate_limiter.requests_per_window = 3  # Set low limit for fast testing

    try:
        # First 3 requests with dummy validation should pass through limiter
        for _ in range(3):
            # Send invalid request body just to reach endpoint and trigger rate limit counter
            resp = client.post("/api/match", json={"usernames": ["dave"]})
            # 422 indicates request passed rate limiter and reached validation
            assert resp.status_code == 422

        # 4th request must be rejected by RateLimiter with 429
        resp = client.post("/api/match", json={"usernames": ["dave"]})
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers
        assert "X-RateLimit-Limit" in resp.headers
        assert "Zu viele Anfragen" in resp.json()["detail"]
    finally:
        match_rate_limiter.reset()
        match_rate_limiter.requests_per_window = original_limit


