"""
Search routes for Ani-CLI FastAPI application
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from anipy_api.provider.providers import AllAnimeProvider
from anipy_api.provider.filter import Filters, Status

from app.models import SearchResponse, SearchResultModel
from app.config import get_provider
from app.utils import (
    get_jikan_total_episodes,
    get_jikan_image,
    get_anilist_score,
    get_kitsu_age_rating,
)
from anipy_api.provider import LanguageTypeEnum

router = APIRouter()


@router.get("/search", response_model=SearchResponse, tags=["Search"])
async def search_anime(
    query: str = Query(..., min_length=1, description="Anime name to search for"),
    limit: int = Query(10, ge=1, le=50, description="Number of results to return")
):
    """
    Search for anime by name

    - **query**: The anime name or query to search for
    - **limit**: Maximum number of results (1-50)
    """
    try:
        provider = get_provider()

        results = provider.get_search(query)

        # Limit results
        limited_results = results[:limit]

        search_results = []
        for result in limited_results:
            total_eps = None
            rating_score = None
            rating_classification = None
            image_url = None

            # Prefer total episodes from provider episodes list (same source as /anime/{identifier}/episodes)
            try:
                eps_list = provider.get_episodes(result.identifier, LanguageTypeEnum.SUB)
                if eps_list:
                    total_eps = len(eps_list)
            except Exception:
                total_eps = None

            # Ratings without Jikan: AniList for score, Kitsu for age classification
            try:
                rating_score = get_anilist_score(result.name)
            except Exception:
                rating_score = None

            try:
                rating_classification = get_kitsu_age_rating(result.name)
            except Exception:
                rating_classification = None

            # As a last resort only for total episodes, still allow Jikan fallback
            try:
                if total_eps is None:
                    total_eps = get_jikan_total_episodes(result.name)
            except Exception:
                pass

            # try to get image from provider result first (support attribute or dict), fallback to Jikan
            try:
                image_url = getattr(result, "image", None)
            except Exception:
                image_url = None

            if not image_url:
                try:
                    if isinstance(result, dict):
                        image_url = result.get("image")
                except Exception:
                    image_url = None

            if not image_url:
                try:
                    image_url = get_jikan_image(result.name)
                except Exception:
                    image_url = None

            search_results.append(
                SearchResultModel(
                    name=result.name,
                    identifier=result.identifier,
                    image=image_url,
                    languages=[str(lang) for lang in result.languages],
                    total_episode=total_eps,
                    rating_score=rating_score,
                    rating_classification=rating_classification,
                )
            )

        return SearchResponse(
            query=query,
            total_results=len(results),
            results=search_results
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )