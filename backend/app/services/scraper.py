import asyncio
import json
import logging
from typing import List, Optional, Dict, Any
import httpx
from bs4 import BeautifulSoup

from app.models import Movie, MatchedMovie
from app.core.cache import cache, WATCHLIST_TTL_SECONDS, POSTER_TTL_SECONDS
from app.core.security import validate_username_safety, is_safe_scrape_url
from app.services.interfaces import WatchlistScraperProtocol

logger = logging.getLogger(__name__)

DEFAULT_HEADERS: Dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
}


class LetterboxdUserNotFoundError(Exception):
    """Raised when a Letterboxd profile does not exist (HTTP 404)."""
    pass


class LetterboxdScraperError(Exception):
    """Raised when an unexpected error occurs during scraping."""
    pass


def extract_movies_from_soup(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """Extract raw movie data (slug, title, and poster endpoint) from Letterboxd HTML."""
    extracted_movies: List[Dict[str, str]] = []

    # Letterboxd renders films modernly using LazyPoster React components
    poster_elements = soup.find_all(attrs={"data-component-class": "LazyPoster"})
    if not poster_elements:
        poster_elements = soup.select(".poster-container, [data-film-slug]")

    for element in poster_elements:
        # Extract movie slug
        slug = element.get("data-item-slug") or element.get("data-film-slug")
        link = element.get("data-item-link") or element.get("data-target-link") or ""
        if not slug and link:
            path_segments = [seg for seg in link.strip("/").split("/") if seg]
            if path_segments and path_segments[0] == "film":
                slug = path_segments[1]

        if not slug:
            continue

        # Extract title
        title = (
            element.get("data-item-full-display-name")
            or element.get("data-item-name")
            or element.get("data-film-name")
        )
        if not title:
            image_tag = element.find("img")
            if image_tag and image_tag.get("alt"):
                title = image_tag.get("alt")
            else:
                title = slug.replace("-", " ").title()

        # Determine cache-busting key for the Letterboxd poster
        cache_buster = ""
        resolvable_json = element.get("data-resolvable-poster-path")
        if resolvable_json:
            try:
                parsed_data = json.loads(resolvable_json)
                if parsed_data.get("cacheBustingKey"):
                    cache_buster = f"?k={parsed_data['cacheBustingKey']}"
            except Exception:
                pass

        base_link = element.get("data-item-link") or f"/film/{slug}/"
        if not base_link.endswith("/"):
            base_link += "/"

        poster_endpoint = f"https://letterboxd.com{base_link}poster/std/230/{cache_buster}"

        extracted_movies.append({
            "slug": slug,
            "title": title,
            "poster_endpoint": poster_endpoint,
        })

    return extracted_movies


# Backward-compatible alias
_extract_movies_from_soup = extract_movies_from_soup


class LetterboxdScraperService:
    """
    Implements WatchlistScraperProtocol for Letterboxd.
    Responsible for web scraping and paginating Letterboxd watchlists.
    """

    def __init__(self, request_timeout: float = 15.0, max_concurrent_pages: int = 8):
        self.request_timeout = request_timeout
        self.max_concurrent_pages = max_concurrent_pages

    async def _resolve_single_poster_url(
        self,
        client: httpx.AsyncClient,
        concurrency_limiter: asyncio.Semaphore,
        slug: str,
        endpoint_url: str,
    ) -> Optional[str]:
        """Resolves a single movie poster URL via the Letterboxd poster endpoint."""
        cache_key = f"poster:{slug}"
        cached_url: Optional[str] = cache.get(cache_key)
        if cached_url:
            return cached_url

        # SSRF protection: Ensure target is a validated HTTPS URL
        if not await is_safe_scrape_url(endpoint_url):
            logger.warning(f"SSRF protection blocked poster endpoint: {endpoint_url}")
            return None

        async with concurrency_limiter:
            try:
                response = await client.get(endpoint_url, timeout=6.0, follow_redirects=True)
                if response.history:
                    for redirect_step in response.history:
                        if not await is_safe_scrape_url(str(redirect_step.url)):
                            logger.warning(f"SSRF protection blocked redirect: {redirect_step.url}")
                            return None

                if response.status_code == 200:
                    payload = response.json()
                    high_res_url: Optional[str] = payload.get("url2x") or payload.get("url")
                    if high_res_url:
                        cache.set(cache_key, high_res_url, expire=POSTER_TTL_SECONDS)
                        return high_res_url
            except Exception as error:
                logger.debug(f"Error resolving poster for '{slug}': {error}")

        return None

    async def scrape_watchlist(self, username: str, force_refresh: bool = False) -> List[Movie]:
        """
        Scrapes the complete Letterboxd watchlist of a user across all pages.
        Cached in diskcache with 60-minute TTL.
        """
        # SSRF protection: Validate and sanitize username
        try:
            normalized_username = validate_username_safety(username).lower()
        except ValueError as validation_error:
            raise LetterboxdScraperError(str(validation_error))

        cache_key = f"watchlist:{normalized_username}"
        if not force_refresh:
            cached_watchlist = cache.get(cache_key)
            if cached_watchlist is not None:
                logger.info(f"Loaded cached watchlist for '{normalized_username}' ({len(cached_watchlist)} movies)")
                return [Movie(**item) for item in cached_watchlist]

        target_watchlist_url = f"https://letterboxd.com/{normalized_username}/watchlist/"
        if not await is_safe_scrape_url(target_watchlist_url):
            raise LetterboxdScraperError(f"SSRF protection rejected request for '{normalized_username}'.")

        async with httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=self.request_timeout) as http_client:
            # 1. Fetch first page
            try:
                response = await http_client.get(target_watchlist_url, follow_redirects=True)
                if response.history:
                    for redirect in response.history:
                        if not await is_safe_scrape_url(str(redirect.url)):
                            raise LetterboxdScraperError("SSRF protection: Unsafe redirect blocked.")
            except LetterboxdScraperError:
                raise
            except Exception as network_error:
                raise LetterboxdScraperError(f"Letterboxd connection error for '{username}': {network_error}")

            if response.status_code == 404:
                raise LetterboxdUserNotFoundError(f"User '{username}' was not found on Letterboxd.")
            elif response.status_code != 200:
                raise LetterboxdScraperError(
                    f"Error fetching profile for '{username}' (status code: {response.status_code})."
                )

            soup = BeautifulSoup(response.text, "html.parser")

            # 2. Check if watchlist is empty
            empty_indicator = soup.find(class_="empty-watchlist") or soup.find(class_="watchlist-empty")
            all_scraped_movies = _extract_movies_from_soup(soup)

            if not all_scraped_movies and empty_indicator:
                cache.set(cache_key, [], expire=WATCHLIST_TTL_SECONDS)
                return []

            # 3. Determine total number of pages from pagination
            pagination_links = soup.select(".paginate-pages a, .pagination a, .paginate-page a")
            page_numbers = [
                int(link.get_text(strip=True))
                for link in pagination_links
                if link.get_text(strip=True).isdigit()
            ]
            total_pages = max(page_numbers) if page_numbers else 1

            # 4. Concurrently fetch subsequent pages
            if total_pages > 1:
                page_semaphore = asyncio.Semaphore(self.max_concurrent_pages)

                async def fetch_subsequent_page(page_number: int) -> List[Dict[str, str]]:
                    page_url = f"https://letterboxd.com/{normalized_username}/watchlist/page/{page_number}/"
                    async with page_semaphore:
                        try:
                            page_response = await http_client.get(page_url, timeout=12.0, follow_redirects=True)
                            if page_response.status_code == 200:
                                page_soup = BeautifulSoup(page_response.text, "html.parser")
                                return _extract_movies_from_soup(page_soup)
                        except Exception as page_err:
                            logger.warning(f"Error on page {page_number} for {normalized_username}: {page_err}")
                    return []

                subsequent_page_tasks = [fetch_subsequent_page(p) for p in range(2, total_pages + 1)]
                results_per_page = await asyncio.gather(*subsequent_page_tasks)
                for page_movies in results_per_page:
                    all_scraped_movies.extend(page_movies)

            # Deduplicate while preserving original order
            seen_slugs: set = set()
            unique_raw_movies: List[Dict[str, str]] = []
            for movie_dict in all_scraped_movies:
                slug = movie_dict["slug"]
                if slug not in seen_slugs:
                    seen_slugs.add(slug)
                    unique_raw_movies.append(movie_dict)

            # 5. Build final Movie objects (apply cached posters)
            final_movies: List[Movie] = []
            for raw in unique_raw_movies:
                slug = raw["slug"]
                cached_poster = cache.get(f"poster:{slug}")
                final_movies.append(Movie(
                    slug=slug,
                    title=raw["title"],
                    poster_url=cached_poster,
                    poster_endpoint=raw.get("poster_endpoint"),
                ))

            # 6. Store in cache
            cache.set(
                cache_key,
                [movie.model_dump() for movie in final_movies],
                expire=WATCHLIST_TTL_SECONDS,
            )

            return final_movies

    async def resolve_posters(
        self,
        movies: List[MatchedMovie],
        endpoints: Dict[str, str],
    ) -> None:
        """Resolves high-resolution movie posters specifically for matched movies."""
        missing_poster_movies = [m for m in movies if not m.poster_url and endpoints.get(m.slug)]
        if not missing_poster_movies:
            return

        concurrency_limiter = asyncio.Semaphore(16)
        async with httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=8.0) as http_client:
            tasks = [
                self._resolve_single_poster_url(http_client, concurrency_limiter, m.slug, endpoints[m.slug])
                for m in missing_poster_movies
            ]
            resolved_urls = await asyncio.gather(*tasks)
            for movie, resolved_url in zip(missing_poster_movies, resolved_urls):
                if resolved_url:
                    movie.poster_url = resolved_url


# Default scraper service instance
default_scraper_service: WatchlistScraperProtocol = LetterboxdScraperService()


# Convenience module-level functions for direct invocation
async def scrape_user_watchlist_async(username: str, force_refresh: bool = False) -> List[Movie]:
    return await default_scraper_service.scrape_watchlist(username, force_refresh=force_refresh)


async def resolve_posters_for_matches(movies: List[MatchedMovie], movie_endpoints: Dict[str, str]) -> None:
    await default_scraper_service.resolve_posters(movies, movie_endpoints)
