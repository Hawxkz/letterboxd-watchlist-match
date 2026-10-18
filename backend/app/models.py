import re
from urllib.parse import urlparse
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, field_validator


def extract_letterboxd_username(input_val: str) -> str:
    """
    Extracts a clean Letterboxd username from:
    - raw username: 'alice'
    - handle: '@alice'
    - profile URL: 'https://letterboxd.com/alice/'
    - watchlist URL: 'https://letterboxd.com/alice/watchlist/'
    """
    if not input_val:
        return ""
    val = input_val.strip()

    if "letterboxd.com" in val.lower():
        normalized = (
            val
            if (val.startswith("http://") or val.startswith("https://"))
            else f"https://{val}"
        )
        try:
            parsed = urlparse(normalized)
            parts = [p for p in parsed.path.split("/") if p]
            if parts:
                return parts[0].lstrip("@").strip()
        except Exception:
            match = re.search(r"letterboxd\.com/([a-zA-Z0-9_-]+)", val, re.IGNORECASE)
            if match:
                return match.group(1).lstrip("@").strip()

    return val.lstrip("@").rstrip("/").strip()


from app.security import validate_username_safety


class Movie(BaseModel):
    slug: str = Field(..., description="Letterboxd movie slug")
    title: str = Field(..., description="Movie display title")
    poster_url: Optional[str] = Field(None, description="Direct URL to movie poster image")
    poster_endpoint: Optional[str] = Field(None, description="Letterboxd endpoint to resolve poster")


class MatchRequest(BaseModel):
    usernames: List[str] = Field(..., min_length=2, description="List of Letterboxd usernames or profile URLs (min 2)")

    @field_validator("usernames")
    @classmethod
    def validate_usernames(cls, v: List[str]) -> List[str]:
        cleaned = []
        for raw in v:
            extracted = extract_letterboxd_username(raw)
            if extracted:
                # Validates against path traversal, special characters, and reserved names (SSRF mitigation)
                validated = validate_username_safety(extracted)
                cleaned.append(validated)

        if len(cleaned) < 2:
            raise ValueError("Mindestens 2 gültige Letterboxd-Usernamen sind erforderlich.")
        # Check for duplicates ignoring case
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
    slug: str
    title: str
    poster_url: Optional[str] = None
    match_count: int
    matched_users: List[str]
    is_perfect_match: bool
    rating: Optional[float] = Field(None, description="TMDB average rating (e.g. 8.4)")
    genres: List[str] = Field(default_factory=list, description="Movie genres (e.g. ['Action', 'Sci-Fi'])")
    runtime: Optional[int] = Field(None, description="Runtime in minutes (e.g. 148)")


class MatchResponse(BaseModel):
    total_users: int
    usernames: List[str]
    user_stats: Dict[str, int]
    perfect_matches: List[MatchedMovie]
    partial_matches: List[MatchedMovie]
    all_matches: List[MatchedMovie]
