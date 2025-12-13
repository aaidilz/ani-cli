"""
Configuration and provider setup for Ani-CLI FastAPI application
"""

import urllib3
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
    """Get configured AllAnime provider instance"""
    provider = AllAnimeProvider()
    provider.session.verify = False
    return provider