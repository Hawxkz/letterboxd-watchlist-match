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

