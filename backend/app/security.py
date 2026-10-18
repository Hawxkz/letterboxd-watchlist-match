import ipaddress
import logging
import re
import socket
from urllib.parse import urlparse
from typing import Optional, Set

logger = logging.getLogger(__name__)

# Valid Letterboxd usernames are 1-64 chars: alphanumeric, underscores, hyphens
LETTERBOXD_USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

# Letterboxd top-level path segments that are NOT valid usernames
RESERVED_LETTERBOXD_PATHS = {
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

# Whitelist of hosts permitted for external HTTP scraping requests (SSRF protection)
ALLOWED_SCRAPE_HOSTS: Set[str] = {
    "letterboxd.com",
    "www.letterboxd.com",
    "a.ltrbxd.com",
}


def validate_username_safety(username: str) -> str:
    """
    Validates that a username conforms strictly to Letterboxd format
    and prevents directory traversal or URL injection via the username path parameter.
    Raises ValueError if invalid.
    """
    if not username:
        raise ValueError("Der Letterboxd-Nutzername darf nicht leer sein.")

    clean = username.strip()

    if not LETTERBOXD_USERNAME_REGEX.match(clean):
        raise ValueError(
            f"Ungültiges Nutzername-Format: '{clean}'. Nur Buchstaben, Zahlen, '-' und '_' sind erlaubt."
        )

    if clean.lower() in RESERVED_LETTERBOXD_PATHS:
        raise ValueError(f"'{clean}' ist ein reservierter Letterboxd-Pfad und kein gültiger Nutzername.")

    return clean


def is_safe_ip(ip_str: str) -> bool:
    """
    Returns False if the given IP address is private, loopback, link-local,
    multicast, or reserved (prevents SSRF against internal cloud/infrastructure targets).
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
    Validates that an outbound request URL:
    1. Uses HTTPS scheme.
    2. Belongs to an approved host (Letterboxd domains).
    3. Does not contain embedded credentials (user:pass@host).
    4. Does not resolve to a private or loopback IP address (SSRF mitigation).
    """
    if not url:
        return False

    allowed = allowed_hosts or ALLOWED_SCRAPE_HOSTS

    try:
        parsed = urlparse(url)
    except Exception:
        return False

    if parsed.scheme.lower() != "https":
        logger.warning(f"SSRF Check: Insecure scheme rejected for URL: {url}")
        return False

    hostname = parsed.hostname
    if not hostname:
        logger.warning(f"SSRF Check: Missing hostname for URL: {url}")
        return False

    # Block credentials in URL (e.g. https://user:pass@letterboxd.com)
    if parsed.username or parsed.password:
        logger.warning(f"SSRF Check: Embedded credentials rejected for URL: {url}")
        return False

    hostname_lower = hostname.lower()
    if hostname_lower not in allowed:
        logger.warning(f"SSRF Check: Host '{hostname_lower}' not in allowed scrape hosts: {url}")
        return False

    # Verify that resolved DNS IPs are public (guards against DNS rebinding & private IP aliases)
    try:
        resolved_info = socket.getaddrinfo(hostname_lower, 443, proto=socket.IPPROTO_TCP)
        for entry in resolved_info:
            sockaddr = entry[4]
            ip_str = sockaddr[0]
            if not is_safe_ip(ip_str):
                logger.warning(f"SSRF Check: Host '{hostname_lower}' resolved to unsafe IP '{ip_str}'")
                return False
    except Exception as e:
        logger.warning(f"SSRF Check: DNS resolution failed for '{hostname_lower}': {e}")
        return False

    return True
