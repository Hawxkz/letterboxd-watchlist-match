import ipaddress
import logging
import re
import socket
from urllib.parse import urlparse
from typing import Optional, Set

logger = logging.getLogger(__name__)

# Valid Letterboxd usernames: 1 to 64 alphanumeric characters, hyphens, or underscores
LETTERBOXD_USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

# Reserved Letterboxd root paths that are not user profiles (prevents URL routing ambiguity)
RESERVED_LETTERBOXD_PATHS: Set[str] = {
    "film",
    "films",
    "list",
    "lists",
    "search",
    "members",
    "journal",
    "activity",
    "api",
    "admin",
    "settings",
    "about",
    "legal",
    "crew",
    "apps",
    "ajax",
}

# Permitted destination hosts for outbound scraping requests (SSRF mitigation)
ALLOWED_SCRAPE_HOSTS: Set[str] = {
    "letterboxd.com",
    "www.letterboxd.com",
    "a.ltrbxd.com",
}


def extract_letterboxd_username(input_val: str) -> str:
    """
    Extracts a normalized Letterboxd username from:
    - 'alice' -> 'alice'
    - '@alice' -> 'alice'
    - 'https://letterboxd.com/alice/' -> 'alice'
    - 'https://letterboxd.com/alice/watchlist/' -> 'alice'
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


def validate_username_safety(username: str) -> str:
    """
    Validates that a username conforms strictly to the Letterboxd schema.
    Rejects directory traversal (e.g. '../admin'), special characters, and reserved paths.
    """
    if not username:
        raise ValueError("The Letterboxd username cannot be empty.")

    clean = username.strip()

    if not LETTERBOXD_USERNAME_REGEX.match(clean):
        raise ValueError(
            f"Invalid username format: '{clean}'. Only letters, numbers, '-' and '_' are allowed."
        )

    if clean.lower() in RESERVED_LETTERBOXD_PATHS:
        raise ValueError(f"'{clean}' is a reserved Letterboxd path and cannot be used as a username.")

    return clean


def is_safe_ip(ip_str: str) -> bool:
    """
    Returns False if an IP is private, loopback, link-local, multicast, or reserved.
    Protects against SSRF targeted at internal infrastructure (e.g. 127.0.0.1, 169.254.169.254).
    """
    try:
        ip = ipaddress.ip_address(ip_str)
        return not (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        )
    except ValueError:
        return False


def is_safe_scrape_url(url: str, allowed_hosts: Optional[Set[str]] = None) -> bool:
    """
    Validates an outbound request URL for SSRF security:
    1. Must use HTTPS.
    2. Host must be present on the scraping allowlist.
    3. Must not contain embedded credentials (user:pass@host).
    4. Resolved DNS IPs must be publicly routable (rejects private/cloud metadata IPs).
    """
    if not url:
        return False

    allowed = allowed_hosts or ALLOWED_SCRAPE_HOSTS

    try:
        parsed = urlparse(url)
    except Exception:
        return False

    if parsed.scheme.lower() != "https":
        logger.warning(f"SSRF Check: Insecure protocol rejected: {url}")
        return False

    hostname = parsed.hostname
    if not hostname:
        logger.warning(f"SSRF Check: Missing hostname in URL: {url}")
        return False

    # Block embedded credentials
    if parsed.username or parsed.password:
        logger.warning(f"SSRF Check: URL contains credentials: {url}")
        return False

    hostname_lower = hostname.lower()
    if hostname_lower not in allowed:
        logger.warning(f"SSRF Check: Host '{hostname_lower}' not in scrape allowlist: {url}")
        return False

    # Resolve DNS and verify that resolved IPs are public
    try:
        resolved_info = socket.getaddrinfo(hostname_lower, 443, proto=socket.IPPROTO_TCP)
        for entry in resolved_info:
            sockaddr = entry[4]
            ip_str = sockaddr[0]
            if not is_safe_ip(ip_str):
                logger.warning(f"SSRF Check: Host '{hostname_lower}' resolved to non-public IP '{ip_str}'.")
                return False
    except Exception as e:
        logger.warning(f"SSRF Check: DNS resolution failed for '{hostname_lower}': {e}")
        return False

    return True
