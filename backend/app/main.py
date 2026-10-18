import logging
from typing import Optional
from fastapi import FastAPI, HTTPException, status, Depends

from app.core.cors import setup_cors
from app.core.rate_limiter import match_rate_limiter, general_rate_limiter
from app.core.cache import clear_cache
from app.models import MatchRequest, MatchResponse
from app.services.matcher import match_user_watchlists, MatcherServiceError
from app.services.scraper import scrape_user_watchlist_async  # Exposed for test compatibility

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("letterboxd_matcher")

# Initialize FastAPI application
app = FastAPI(
    title="Letterboxd Watchlist Matcher API",
    description="Find common movie favorites across multiple Letterboxd watchlists.",
    version="1.1.0",
)

# Configure CORS middleware
setup_cors(app)


@app.get("/", dependencies=[Depends(general_rate_limiter)])
def read_root():
    """Root endpoint returning service status and documentation link."""
    return {
        "app": "Letterboxd Watchlist Matcher API",
        "status": "healthy",
        "docs": "/docs",
    }


@app.get("/api/health", dependencies=[Depends(general_rate_limiter)])
def health_check():
    """Health check endpoint for monitoring and uptime probes."""
    return {"status": "ok"}


@app.post(
    "/api/match",
    response_model=MatchResponse,
    dependencies=[Depends(match_rate_limiter)],
)
async def match_watchlists(request: MatchRequest):
    """
    Main matching endpoint: Compares watchlists of two or more Letterboxd users,
    returning perfect matches and partial overlaps sorted descending by overlap count.
    Protected by RateLimiter and SSRF validation.
    """
    try:
        return await match_user_watchlists(request.usernames)
    except MatcherServiceError as mse:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(mse),
        )
    except Exception as e:
        logger.error(f"Unexpected error in matcher service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error while retrieving watchlists: {str(e)}",
        )


@app.post("/api/cache/clear")
def clear_api_cache(username: Optional[str] = None):
    """Endpoint to manually clear the scraping cache (optionally for a specific user)."""
    clear_cache(username)
    return {"message": "Cache successfully cleared", "user": username or "all"}
