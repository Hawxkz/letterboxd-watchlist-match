from typing import List, Optional, Dict
from pydantic import BaseModel, Field, field_validator

from app.core.security import extract_letterboxd_username, validate_username_safety


class Movie(BaseModel):
    """Represents a movie entry found on a Letterboxd watchlist."""
    slug: str = Field(..., description="Letterboxd film slug (e.g. 'dune-part-two')")
    title: str = Field(..., description="Movie display title")
    poster_url: Optional[str] = Field(None, description="Direct URL to movie poster image")
    poster_endpoint: Optional[str] = Field(None, description="Letterboxd API endpoint to resolve high-res poster")


class MatchRequest(BaseModel):
    """Incoming request payload to compare two or more Letterboxd profiles."""
    usernames: List[str] = Field(
        ...,
        min_length=2,
        description="List of Letterboxd usernames or profile URLs (minimum 2)",
    )

    @field_validator("usernames")
    @classmethod
    def validate_usernames(cls, v: List[str]) -> List[str]:
        cleaned = []
        for raw in v:
            # Extract clean username from full URL, @handle, or plain text
            extracted = extract_letterboxd_username(raw)
            if extracted:
                # SSRF prevention: Validate format, reject path traversal and reserved paths
                validated = validate_username_safety(extracted)
                cleaned.append(validated)

        if len(cleaned) < 2:
            raise ValueError("Mindestens 2 gültige Letterboxd-Usernamen sind erforderlich.")

        # Deduplicate usernames (case-insensitive)
        seen = set()
        unique = []
        for u in cleaned:
            lower = u.lower()
            if lower not in seen:
                seen.add(lower)
                unique.append(u)

        if len(unique) < 2:
            raise ValueError("Bitte gib mindestens 2 verschiedene Nutzer an.")

        return unique


class MatchedMovie(BaseModel):
    """Represents a movie present on multiple watchlists with metadata and member presence."""
    slug: str
    title: str
    poster_url: Optional[str] = None
    match_count: int = Field(..., description="Number of compared profiles that have this movie on their watchlist")
    matched_users: List[str] = Field(..., description="List of profile usernames sharing this movie")
    is_perfect_match: bool = Field(..., description="True if present on all compared watchlists without exception")
    rating: Optional[float] = Field(None, description="TMDB average rating score (e.g. 8.4)")
    genres: List[str] = Field(default_factory=list, description="List of film genres (e.g. ['Action', 'Sci-Fi'])")
    runtime: Optional[int] = Field(None, description="Runtime duration in minutes (e.g. 148)")


class MatchResponse(BaseModel):
    """Structured response containing profile stats and categorized movie overlap lists."""
    total_users: int
    usernames: List[str]
    user_stats: Dict[str, int] = Field(..., description="Total watchlist count per profile")
    perfect_matches: List[MatchedMovie] = Field(..., description="Movies found on ALL submitted watchlists")
    partial_matches: List[MatchedMovie] = Field(..., description="Movies shared by multiple (but not all) profiles")
    all_matches: List[MatchedMovie] = Field(..., description="All matches sorted descending by overlap count")
