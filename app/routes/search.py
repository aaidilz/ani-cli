"""
Search routes for Ani-CLI FastAPI application
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from anipy_api.provider.providers import AllAnimeProvider
from anipy_api.provider.filter import Filters, Status

from app.models import SearchResponse, SearchResultModel
from app.config import get_provider
from app.utils import get_jikan_total_episodes, get_jikan_rating, get_jikan_image

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

            # best-effort: fetch metadata from Jikan
            try:
                total_eps = get_jikan_total_episodes(result.name)
                score, _, rating_str = get_jikan_rating(result.name)
                rating_score = score
                rating_classification = rating_str
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