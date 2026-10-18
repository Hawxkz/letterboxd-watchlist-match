import asyncio
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
import httpx
from bs4 import BeautifulSoup
import diskcache

from app.models import Movie
from app.security import validate_username_safety, is_safe_scrape_url

logger = logging.getLogger(__name__)

# Diskcache directory in backend/.diskcache
CACHE_DIR = Path(__file__).resolve().parent.parent / ".diskcache"
cache = diskcache.Cache(str(CACHE_DIR))

# Default TTL: 60 minutes (3600 seconds)
WATCHLIST_TTL_SECONDS = 60 * 60
POSTER_TTL_SECONDS = 24 * 60 * 60  # Posters can be cached longer (24h)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
}


class LetterboxdUserNotFoundError(Exception):
    """Raised when the Letterboxd username does not exist."""
    pass


class LetterboxdScraperError(Exception):
    """Raised when scraping fails unexpectedly."""
    pass


def _extract_movies_from_soup(soup: BeautifulSoup) -> List[Dict]:
    """Extract raw movie entries from Letterboxd HTML."""
    movies_data = []
    
    # Modern Letterboxd markup uses React LazyPoster components
    poster_elements = soup.find_all(attrs={"data-component-class": "LazyPoster"})
    
    if not poster_elements:
        # Fallback to older letterboxd structures if any
        poster_elements = soup.select(".poster-container, [data-film-slug]")
        
    for elem in poster_elements:
        # Slug extraction
        slug = elem.get("data-item-slug") or elem.get("data-film-slug")
        link = elem.get("data-item-link") or elem.get("data-target-link") or ""
        if not slug and link:
            parts = [p for p in link.strip("/").split("/") if p]
            if parts and parts[0] == "film":
                slug = parts[1]
                
        if not slug:
            continue
            
        # Title extraction
        title = (
            elem.get("data-item-full-display-name")
            or elem.get("data-item-name")
            or elem.get("data-film-name")
        )
        if not title:
            img = elem.find("img")
            if img and img.get("alt"):
                title = img.get("alt")
            else:
                title = slug.replace("-", " ").title()

        # Poster endpoint information
        cache_key = ""
        resolvable = elem.get("data-resolvable-poster-path")
        if resolvable:
            try:
                res_data = json.loads(resolvable)
                if res_data.get("cacheBustingKey"):
                    cache_key = f"?k={res_data['cacheBustingKey']}"
            except Exception:
                pass
                
        base_link = elem.get("data-item-link") or f"/film/{slug}/"
        if not base_link.endswith("/"):
            base_link += "/"
            
        poster_endpoint = f"https://letterboxd.com{base_link}poster/std/230/{cache_key}"

        movies_data.append({
            "slug": slug,
            "title": title,
            "poster_endpoint": poster_endpoint,
        })
        
    return movies_data


async def _resolve_poster_url(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    slug: str,
    endpoint: str
) -> Optional[str]:
    """Resolve high-res poster URL for a movie, using cache if available."""
    cache_key = f"poster:{slug}"
    cached_url = cache.get(cache_key)
    if cached_url:
        return cached_url

    # SSRF protection: Ensure endpoint is an approved, safe HTTPS Letterboxd URL
    if not is_safe_scrape_url(endpoint):
        logger.warning(f"SSRF Protection blocked poster endpoint: {endpoint}")
        return None

    async with semaphore:
        try:
            resp = await client.get(endpoint, timeout=6.0, follow_redirects=True)
            if resp.history:
                for redirect in resp.history:
                    if not is_safe_scrape_url(str(redirect.url)):
                        logger.warning(f"SSRF Protection blocked redirect: {redirect.url}")
                        return None
            if resp.status_code == 200:
                data = resp.json()
                poster_url = data.get("url2x") or data.get("url")
                if poster_url:
                    cache.set(cache_key, poster_url, expire=POSTER_TTL_SECONDS)
                    return poster_url
        except Exception as e:
            logger.debug(f"Failed to fetch poster for {slug}: {e}")

    return None


async def scrape_user_watchlist_async(username: str, force_refresh: bool = False) -> List[Movie]:
    """
    Scrapes the entire Letterboxd watchlist for a given username across all pages.
    Results are cached in diskcache with a 60-minute TTL.
    """
    # SSRF protection: Validate username format and reject path traversal or reserved words
    try:
        clean_user = validate_username_safety(username).lower()
    except ValueError as ve:
        raise LetterboxdScraperError(str(ve))

    cache_key = f"watchlist:{clean_user}"
    if not force_refresh:
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            logger.info(f"Returning cached watchlist for '{clean_user}' ({len(cached_data)} films)")
            return [Movie(**item) for item in cached_data]

    base_url = f"https://letterboxd.com/{clean_user}/watchlist/"
    if not is_safe_scrape_url(base_url):
        raise LetterboxdScraperError(f"SSRF-Schutz verweigerte Anfrage für '{clean_user}'.")

    async with httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=15.0) as client:
        # 1. Fetch first page
        try:
            resp = await client.get(base_url, follow_redirects=True)
            if resp.history:
                for redirect in resp.history:
                    if not is_safe_scrape_url(str(redirect.url)):
                        raise LetterboxdScraperError("SSRF-Schutz: Unsichere Weiterleitung blockiert.")
        except LetterboxdScraperError:
            raise
        except Exception as e:
            raise LetterboxdScraperError(f"Verbindungsfehler zu Letterboxd für '{username}': {e}")

        if resp.status_code == 404:
            raise LetterboxdUserNotFoundError(f"Nutzer '{username}' wurde auf Letterboxd nicht gefunden.")
        elif resp.status_code != 200:
            raise LetterboxdScraperError(
                f"Fehler beim Laden des Profils für '{username}' (Statuscode: {resp.status_code})."
            )

        soup = BeautifulSoup(resp.text, "html.parser")
        
        # 2. Check if watchlist is empty
        empty_msg = soup.find(class_="empty-watchlist") or soup.find(class_="watchlist-empty")
        all_raw_movies = _extract_movies_from_soup(soup)
        
        if not all_raw_movies and empty_msg:
            # User exists, but has an empty watchlist
            cache.set(cache_key, [], expire=WATCHLIST_TTL_SECONDS)
            return []

        # 3. Detect total page count from pagination
        pagination_links = soup.select(".paginate-pages a, .pagination a, .paginate-page a")
        page_numbers = []
        for a in pagination_links:
            text = a.get_text(strip=True)
            if text.isdigit():
                page_numbers.append(int(text))
                
        total_pages = max(page_numbers) if page_numbers else 1

        # 4. Fetch subsequent pages concurrently if more than 1 page
        if total_pages > 1:
            page_sem = asyncio.Semaphore(8)

            async def fetch_page(page_num: int):
                url = f"https://letterboxd.com/{clean_user}/watchlist/page/{page_num}/"
                async with page_sem:
                    try:
                        r = await client.get(url, timeout=12.0, follow_redirects=True)
                        if r.status_code == 200:
                            s = BeautifulSoup(r.text, "html.parser")
                            return _extract_movies_from_soup(s)
                    except Exception as e:
                        logger.warning(f"Error fetching page {page_num} for {clean_user}: {e}")
                return []

            subsequent_tasks = [fetch_page(p) for p in range(2, total_pages + 1)]
            subsequent_results = await asyncio.gather(*subsequent_tasks)
            for page_movies in subsequent_results:
                all_raw_movies.extend(page_movies)

        # Remove duplicates while preserving order
        seen_slugs = set()
        unique_raw_movies = []
        for m in all_raw_movies:
            if m["slug"] not in seen_slugs:
                seen_slugs.add(m["slug"])
                unique_raw_movies.append(m)

        # 5. Build Movie objects (check cache without making blocking HTTP calls for non-matches)
        final_movies = []
        for raw in unique_raw_movies:
            slug = raw["slug"]
            cached_poster = cache.get(f"poster:{slug}")
            final_movies.append(Movie(
                slug=slug,
                title=raw["title"],
                poster_url=cached_poster,
                poster_endpoint=raw.get("poster_endpoint"),
            ))

        # 6. Store in diskcache (TTL: 60 minutes)
        cache.set(
            cache_key,
            [m.model_dump() for m in final_movies],
            expire=WATCHLIST_TTL_SECONDS
        )

        return final_movies


async def resolve_posters_for_matches(
    movies: List[Any],
    movie_endpoints: Dict[str, str]
) -> None:
    """Resolve high-res poster URLs only for matched movies concurrently."""
    missing = [m for m in movies if not m.poster_url and movie_endpoints.get(m.slug)]
    if not missing:
        return

    sem = asyncio.Semaphore(16)
    async with httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=8.0) as client:
        tasks = [
            _resolve_poster_url(client, sem, m.slug, movie_endpoints[m.slug])
            for m in missing
        ]
        urls = await asyncio.gather(*tasks)
        for m, url in zip(missing, urls):
            if url:
                m.poster_url = url


def clear_cache(username: Optional[str] = None) -> None:
    """Clear cache for a specific user or entirely."""
    if username:
        clean_user = username.strip().lower()
        cache.delete(f"watchlist:{clean_user}")
    else:
        cache.clear()
