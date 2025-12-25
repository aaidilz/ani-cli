"""
Search routes for Ani-CLI FastAPI application
"""

import asyncio
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from starlette.concurrency import run_in_threadpool

from anipy_api.provider.providers import AllAnimeProvider
from anipy_api.provider.filter import Filters, Status

from app.models import SearchResponse, SearchResultModel
from app.config import get_provider
from app.cache import SEARCH_CACHE
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

        key = (query.strip().lower(),)
        cached = SEARCH_CACHE.get(key)
        if cached is not None:
            results = cached
        else:
            # Provider calls are blocking (requests); run in threadpool.
            # Provider search itself has internal page limiting for responsiveness.
            results = await run_in_threadpool(provider.get_search, query)
            SEARCH_CACHE.set(key, results)

        # Limit results
        limited_results = results[:limit]

        semaphore = asyncio.Semaphore(10)

        async def build_result(result):
            async with semaphore:
                # Prefer provider-provided values; avoid heavy per-item calls.
                image_url = getattr(result, "image", None)

                total_eps = None
                available = getattr(result, "available_episodes", None)
                if isinstance(available, dict):
                    # best-effort: use sub count if present, else max of known.
                    try:
                        sub_count = available.get("sub")
                        dub_count = available.get("dub")
                        candidates = [c for c in [sub_count, dub_count] if isinstance(c, int)]
                        total_eps = max(candidates) if candidates else None
                    except Exception:
                        total_eps = None

                rating_score_task = run_in_threadpool(get_anilist_score, result.name)
                rating_class_task = run_in_threadpool(get_kitsu_age_rating, result.name)

                # Only hit Jikan if we still miss these fields.
                total_eps_task = (
                    run_in_threadpool(get_jikan_total_episodes, result.name)
                    if total_eps is None
                    else None
                )
                image_task = (
                    run_in_threadpool(get_jikan_image, result.name)
                    if not image_url
                    else None
                )

                if total_eps_task is not None and image_task is not None:
                    rating_score, rating_classification, total_eps_fallback, image_fallback = await asyncio.gather(
                        rating_score_task,
                        rating_class_task,
                        total_eps_task,
                        image_task,
                    )
                elif total_eps_task is not None:
                    rating_score, rating_classification, total_eps_fallback = await asyncio.gather(
                        rating_score_task,
                        rating_class_task,
                        total_eps_task,
                    )
                    image_fallback = None
                elif image_task is not None:
                    rating_score, rating_classification, image_fallback = await asyncio.gather(
                        rating_score_task,
                        rating_class_task,
                        image_task,
                    )
                    total_eps_fallback = None
                else:
                    rating_score, rating_classification = await asyncio.gather(
                        rating_score_task,
                        rating_class_task,
                    )
                    total_eps_fallback = None
                    image_fallback = None

                if total_eps is None:
                    total_eps = total_eps_fallback
                if not image_url:
                    image_url = image_fallback

                return SearchResultModel(
                    name=result.name,
                    identifier=result.identifier,
                    image=image_url,
                    languages=[str(lang) for lang in result.languages],
                    total_episode=total_eps,
                    rating_score=rating_score,
                    rating_classification=rating_classification,
                )

        search_results = await asyncio.gather(*(build_result(r) for r in limited_results))

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