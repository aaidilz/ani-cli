"""
Utility functions for Ani-CLI FastAPI application
"""

import requests
from typing import Optional, Tuple
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


@lru_cache(maxsize=128)
def get_jikan_total_episodes(anime_name: str) -> Optional[int]:
    """Fetch total episodes from Jikan API v4 (returns None if unknown)"""
    try:
        url = "https://api.jikan.moe/v4/anime"
        params = {"q": anime_name, "limit": 1}
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data.get("data"):
            ep = data["data"][0].get("episodes")
            return ep if isinstance(ep, int) else None
        return None
    except Exception:
        return None


@lru_cache(maxsize=128)
def get_jikan_rating(anime_name: str) -> Tuple[Optional[float], Optional[int], Optional[str]]:
    """Fetch rating info from Jikan API v4.

    Returns a tuple: (score, scored_by, rating_str)
    """
    try:
        url = "https://api.jikan.moe/v4/anime"
        params = {"q": anime_name, "limit": 1}
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data.get("data"):
            item = data["data"][0]
            score = item.get("score")
            scored_by = item.get("scored_by")
            rating_str = item.get("rating")
            # Normalize types
            score_val = float(score) if isinstance(score, (int, float)) else None
            scored_by_val = int(scored_by) if isinstance(scored_by, int) else None
            rating_val = str(rating_str) if rating_str is not None else None
            return score_val, scored_by_val, rating_val
        return None, None, None
    except Exception:
        return None, None, None
