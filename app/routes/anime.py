"""
Anime routes for Ani-CLI FastAPI application
"""

import asyncio
from fastapi import APIRouter, HTTPException, Path, Query
from typing import Optional, Dict, List
from concurrent.futures import ThreadPoolExecutor

from starlette.concurrency import run_in_threadpool

from anipy_api.provider.providers import AllAnimeProvider
from anipy_api.provider import LanguageTypeEnum

from app.models import AnimeInfoModel, EpisodesResponse, EpisodeStreamModel, PaginatedResponse, AnimeCardModel
from app.utils import (
    parse_language,
    get_jikan_image,
    get_jikan_total_episodes,
    get_anilist_score,
    get_kitsu_age_rating,
)
from app.config import get_provider
from app.cache import BROWSE_CACHE

router = APIRouter()


@router.get("/anime/browse", response_model=PaginatedResponse, tags=["Discovery"])
async def browse_anime(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=50, description="Items per page"),
    genres: Optional[List[str]] = Query(None, description="Filter by genres")
):
    """
    Browse anime with pagination and filters
    """
    try:
        provider = get_provider()
        
        # Check if provider supports browse
        if not hasattr(provider, "get_browse"):
             raise HTTPException(
                status_code=501,
                detail="Provider does not support browsing"
            )

        genres_key = tuple(genres) if genres else None
        key = (page, limit, genres_key)
        cached = BROWSE_CACHE.get(key)
        if cached is not None:
            result = cached
        else:
            result = await run_in_threadpool(provider.get_browse, page, limit, genres)
            BROWSE_CACHE.set(key, result)
        
        # Fetch images from Jikan in parallel for items with missing or invalid images
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {}
            for item in result["results"]:
                image_url = item.get("image")
                # Check if image is missing, empty, or not an absolute URL (doesn't start with http)
                if not image_url or not image_url.strip().lower().startswith("http"):
                    futures[executor.submit(get_jikan_image, item["name"])] = item
            
            # Collect results
            for future in futures:
                item = futures[future]
                jikan_image = future.result()
                if jikan_image:
                    item["image"] = jikan_image
                else:
                    item["image"] = None
        
        semaphore = asyncio.Semaphore(10)

        async def build_card(item: dict) -> AnimeCardModel:
            async with semaphore:
                # Prefer provider episode counts if present to avoid Jikan fan-out.
                total_eps = None
                available = item.get("available_episodes")
                if isinstance(available, dict):
                    try:
                        sub_count = available.get("sub")
                        dub_count = available.get("dub")
                        candidates = [c for c in [sub_count, dub_count] if isinstance(c, int)]
                        total_eps = max(candidates) if candidates else None
                    except Exception:
                        total_eps = None

                rating_score_task = run_in_threadpool(get_anilist_score, item["name"])
                rating_class_task = run_in_threadpool(get_kitsu_age_rating, item["name"])
                total_eps_task = (
                    run_in_threadpool(get_jikan_total_episodes, item["name"])
                    if total_eps is None
                    else None
                )

                if total_eps_task is not None:
                    rating_score, rating_classification, total_eps_fallback = await asyncio.gather(
                        rating_score_task,
                        rating_class_task,
                        total_eps_task,
                    )
                    total_eps = total_eps_fallback
                else:
                    rating_score, rating_classification = await asyncio.gather(
                        rating_score_task,
                        rating_class_task,
                    )

                return AnimeCardModel(
                    identifier=item["identifier"],
                    name=item["name"],
                    image=item["image"],
                    languages=item["languages"],
                    genres=item.get("genres"),
                    total_episode=total_eps,
                    rating_score=rating_score,
                    rating_classification=rating_classification,
                )

        data_list = await asyncio.gather(*(build_card(item) for item in result["results"]))

        return PaginatedResponse(
            page=result["page"],
            has_next=result["has_next"],
            data=data_list
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to browse anime: {str(e)}"
        )


@router.get("/anime/{identifier}", response_model=AnimeInfoModel, tags=["Anime Info"])
async def get_anime_info(
    identifier: str = Path(..., description="Anime identifier")
):
    """
    Get detailed information about an anime

    - **identifier**: The anime identifier from search results
    """
    try:
        provider = get_provider()

        info = await run_in_threadpool(provider.get_info, identifier)

        # Best-effort: try to fetch total episodes from Jikan and ratings from AniList/Kitsu by name
        total_eps = None
        rating_score = None
        rating_count = None
        rating_classification = None

        if getattr(info, "name", None):
            total_eps_task = run_in_threadpool(get_jikan_total_episodes, info.name)
            rating_score_task = run_in_threadpool(get_anilist_score, info.name)
            rating_class_task = run_in_threadpool(get_kitsu_age_rating, info.name)

            total_eps, rating_score, rating_classification = await asyncio.gather(
                total_eps_task,
                rating_score_task,
                rating_class_task,
            )
            # We don't have a strict scored_by equivalent without Jikan; leave None

        return AnimeInfoModel(
            name=info.name,
            image=info.image,
            genres=info.genres,
            synopsis=info.synopsis,
            release_year=info.release_year,
            status=str(info.status) if info.status else None,
            alternative_names=info.alternative_names,
            total_episode=total_eps,
            rating_score=rating_score,
            rating_count=rating_count,
            rating_classification=rating_classification,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get anime info: {str(e)}"
        )


@router.get("/anime/{identifier}/episodes", response_model=EpisodesResponse, tags=["Episodes"])
async def get_episodes(
    identifier: str = Path(..., description="Anime identifier"),
    language: Optional[str] = Query(None, description="Filter by language (sub/dub)")
):
    """
    Get all available episodes for an anime

    - **identifier**: The anime identifier
    - **language**: Optional filter for language (sub or dub)
    """
    try:
        provider = get_provider()

        # Validate and coerce language query parameter
        lang_enum = parse_language(language) if language else LanguageTypeEnum.SUB

        episodes = await run_in_threadpool(provider.get_episodes, identifier, lang_enum)

        # Organize episodes by language
        episodes_by_lang: Dict[str, List[EpisodeStreamModel]] = {}

        for episode_num in episodes:
            episodes_by_lang[str(episode_num)] = []

        info = await run_in_threadpool(provider.get_info, identifier)
        return EpisodesResponse(
            identifier=identifier,
            name=info.name or "",
            episodes=episodes_by_lang,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get episodes: {str(e)}"
        )


