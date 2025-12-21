"""
Utility functions for Ani-CLI FastAPI application
"""

import requests
from typing import Optional
from functools import lru_cache
from anipy_api.provider import LanguageTypeEnum


def parse_language(language: str) -> LanguageTypeEnum:
    """Parse language string to LanguageTypeEnum"""
    if language.lower() == "sub":
        return LanguageTypeEnum.SUB
    elif language.lower() == "dub":
        return LanguageTypeEnum.DUB
    else:
        raise ValueError(f"Invalid language '{language}', must be 'sub' or 'dub'")


def format_episode_number(episode: float) -> int | float:
    """Format episode number for API calls"""
    return int(episode) if episode.is_integer() else episode

@lru_cache(maxsize=128)
def get_jikan_image(anime_name: str) -> Optional[str]:
    """Fetch anime cover image from Jikan API v4"""
    try:
        url = "https://api.jikan.moe/v4/anime"
        params = {"q": anime_name, "limit": 1}
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if data.get("data"):
            images = data["data"][0]["images"]["jpg"]
            return images.get("large_image_url") or images.get("image_url")
        return None
    except Exception:
        return None
