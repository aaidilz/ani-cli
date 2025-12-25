"""Utility functions for Ani-CLI FastAPI application."""

from __future__ import annotations

from functools import lru_cache
from typing import Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from anipy_api.provider import LanguageTypeEnum


_HTTP_SESSION: requests.Session | None = None


def _get_http_session() -> requests.Session:
    """Shared requests session with connection pooling + light retries."""
    global _HTTP_SESSION
    if _HTTP_SESSION is not None:
        return _HTTP_SESSION

    session = requests.Session()
    retry = Retry(
        total=2,
        connect=2,
        read=2,
        backoff_factor=0.2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "POST"),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(pool_connections=50, pool_maxsize=50, max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    _HTTP_SESSION = session
    return session


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
        response = _get_http_session().get(url, params=params, timeout=5)
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
        response = _get_http_session().get(url, params=params, timeout=5)
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
        response = _get_http_session().get(url, params=params, timeout=5)
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


@lru_cache(maxsize=128)
def get_anilist_score(anime_name: str) -> Optional[float]:
    """Fetch average score from AniList GraphQL and normalize to 0-10.

    Returns a float score (0-10) or None if unavailable.
    """
    try:
        url = "https://graphql.anilist.co"
        query = (
            "query ($search: String) {"
            "  Media(search: $search, type: ANIME) {"
            "    averageScore"
            "    meanScore"
            "  }"
            "}"
        )
        payload = {"query": query, "variables": {"search": anime_name}}
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        response = _get_http_session().post(url, json=payload, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        media = data.get("data", {}).get("Media")
        if media:
            score100 = media.get("averageScore") or media.get("meanScore")
            if isinstance(score100, (int, float)):
                return float(score100) / 10.0
        return None
    except Exception:
        return None


@lru_cache(maxsize=128)
def get_kitsu_age_rating(anime_name: str) -> Optional[str]:
    """Fetch age rating classification from Kitsu API v2.

    Maps Kitsu ratings to readable strings.
    """
    try:
        url = "https://kitsu.io/api/edge/anime"
        params = {"filter[text]": anime_name, "page[limit]": 1}
        response = _get_http_session().get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data.get("data"):
            attrs = data["data"][0].get("attributes", {})
            rating = attrs.get("ageRating")  # G, PG, R, R18
            if not rating:
                return None
            mapping = {
                "G": "G - All Ages",
                "PG": "PG - Children",
                "R": "R - 17+",
                "R18": "R18+ - Adults Only",
            }
            return mapping.get(str(rating).upper(), str(rating))
        return None
    except Exception:
        return None
