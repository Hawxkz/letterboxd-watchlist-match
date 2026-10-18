import asyncio
import logging
from typing import Dict, List, Set
from fastapi import FastAPI, HTTPException, status, Depends
from app.cors import setup_cors
from app.rate_limiter import match_rate_limiter, general_rate_limiter

from app.models import MatchRequest, MatchResponse, MatchedMovie, Movie
from app.scraper import (
    scrape_user_watchlist_async,
    resolve_posters_for_matches,
    LetterboxdUserNotFoundError,
    LetterboxdScraperError,
    clear_cache,
)
from app.tmdb import enrich_matched_movies

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("letterboxd_matcher")

app = FastAPI(
    title="Letterboxd Watchlist Matcher API",
    description="Find common movies between Letterboxd watchlists",
    version="1.0.0",
)

# CORS configuration (hardened & configurable via app.cors)
setup_cors(app)


@app.get("/", dependencies=[Depends(general_rate_limiter)])
def read_root():
    return {
        "app": "Letterboxd Watchlist Matcher API",
        "status": "healthy",
        "docs": "/docs",
    }


@app.get("/api/health", dependencies=[Depends(general_rate_limiter)])
def health_check():
    return {"status": "ok"}


@app.post(
    "/api/match",
    response_model=MatchResponse,
    dependencies=[Depends(match_rate_limiter)],
)
async def match_watchlists(request: MatchRequest):
    """
    Accepts a list of Letterboxd usernames (min 2), scrapes/retrieves their watchlists,
    and returns matched movies sorted descending by overlap count.
    Protected by RateLimiter and SSRF validation.
    """
    usernames = request.usernames
    total_users = len(usernames)

    # Scrape watchlists in parallel
    try:
        results = await asyncio.gather(
            *[scrape_user_watchlist_async(u) for u in usernames],
            return_exceptions=True
        )
    except Exception as e:
        logger.error(f"Error during parallel scraping: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unerwarteter Fehler beim Abrufen der Watchlists: {str(e)}",
        )

    # Check for exceptions
    user_watchlists: Dict[str, List[Movie]] = {}
    errors = []

    for user, res in zip(usernames, results):
        if isinstance(res, LetterboxdUserNotFoundError):
            errors.append(f"Nutzer '{user}' wurde auf Letterboxd nicht gefunden (404).")
        elif isinstance(res, LetterboxdScraperError):
            errors.append(f"Fehler beim Scrapen von '{user}': {str(res)}")
        elif isinstance(res, Exception):
            errors.append(f"Fehler bei '{user}': {str(res)}")
        else:
            user_watchlists[user] = res

    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(errors),
        )

    # Calculate overlaps
    user_stats: Dict[str, int] = {u: len(user_watchlists[u]) for u in usernames}

    # Aggregate movie data and track user presence
    movie_info: Dict[str, Dict] = {}  # slug -> {"title": ..., "poster_url": ...}
    movie_endpoints: Dict[str, str] = {}  # slug -> poster_endpoint
    movie_users: Dict[str, List[str]] = {}  # slug -> list of users

    for user, movies in user_watchlists.items():
        for movie in movies:
            slug = movie.slug
            if slug not in movie_info:
                movie_info[slug] = {
                    "title": movie.title,
                    "poster_url": movie.poster_url,
                }
                movie_users[slug] = []
            else:
                # If poster was missing from earlier occurrence, update if this one has it
                if not movie_info[slug]["poster_url"] and movie.poster_url:
                    movie_info[slug]["poster_url"] = movie.poster_url

            if movie.poster_endpoint and slug not in movie_endpoints:
                movie_endpoints[slug] = movie.poster_endpoint

            if user not in movie_users[slug]:
                movie_users[slug].append(user)

    # Build MatchedMovie items
    all_matched_movies: List[MatchedMovie] = []

    for slug, u_list in movie_users.items():
        count = len(u_list)
        # Only consider movies shared by at least 2 users for matches
        if count >= 2:
            is_perfect = count == total_users
            all_matched_movies.append(
                MatchedMovie(
                    slug=slug,
                    title=movie_info[slug]["title"],
                    poster_url=movie_info[slug]["poster_url"],
                    match_count=count,
                    matched_users=u_list,
                    is_perfect_match=is_perfect,
                )
            )

    # Sort descending by match_count, then alphabetically by title
    all_matched_movies.sort(key=lambda m: (-m.match_count, m.title.lower()))

    # Resolve posters and fetch TMDB metadata concurrently only for matched movies
    await asyncio.gather(
        resolve_posters_for_matches(all_matched_movies, movie_endpoints),
        enrich_matched_movies(all_matched_movies),
    )

    perfect_matches = [m for m in all_matched_movies if m.is_perfect_match]
    partial_matches = [m for m in all_matched_movies if not m.is_perfect_match]

    return MatchResponse(
        total_users=total_users,
        usernames=usernames,
        user_stats=user_stats,
        perfect_matches=perfect_matches,
        partial_matches=partial_matches,
        all_matches=all_matched_movies,
    )


@app.post("/api/cache/clear")
def clear_api_cache(username: str = None):
    """Endpoint to manually clear scraping cache."""
    clear_cache(username)
    return {"message": "Cache successfully cleared", "user": username or "all"}
