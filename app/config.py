"""
Configuration and provider setup for Ani-CLI FastAPI application
"""

import urllib3
from functools import lru_cache
from anipy_api.provider.providers import AllAnimeProvider

# Disable SSL verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Config:
    """Application configuration"""

    # API settings
    TITLE = "Ani-CLI FastAPI"
    DESCRIPTION = "FastAPI wrapper for AllAnime provider"
    VERSION = "1.0.0"
    DOCS_URL = "/docs"
    REDOC_URL = "/redoc"

    # CORS settings
    ALLOW_ORIGINS = ["*"]
    ALLOW_CREDENTIALS = True
    ALLOW_METHODS = ["*"]
    ALLOW_HEADERS = ["*"]

    # Server settings
    HOST = "0.0.0.0"
    PORT = 8000
    RELOAD = True


def get_provider() -> AllAnimeProvider:
    """Get configured AllAnime provider instance

    Note: SSL verification is enabled by default for security.
    The AllAnime API supports proper SSL certificates.
    """
    return _get_cached_provider()


@lru_cache(maxsize=1)
def _get_cached_provider() -> AllAnimeProvider:
    """Create a single provider instance per process.

    This allows connection pooling inside the provider's requests.Session and
    avoids re-initialization cost on every request.
    """
    return AllAnimeProvider()