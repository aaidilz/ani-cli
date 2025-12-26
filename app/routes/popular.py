"""
Popular/Trending routes for Ani-CLI FastAPI application
"""

import asyncio
from fastapi import APIRouter, HTTPException, Query
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from starlette.concurrency import run_in_threadpool

from anipy_api.provider import FilterCapabilities

from app.models import PaginatedResponse, AnimeCardModel
from app.utils import (
    get_jikan_image,
    get_jikan_total_episodes,
    get_anilist_score,
    get_kitsu_age_rating,
)
from app.config import get_provider
from app.cache import BROWSE_CACHE

router = APIRouter()

@router.get("/popular", response_model=PaginatedResponse, tags=["Discovery"])
async def get_popular_anime(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=50, description="Items per page")
):
    """
    Get popular/trending anime
    """
    try:
        provider = get_provider()
        
        # Strategy:
        # 1. Try get_browse (usually returns trending/latest)
        # 2. Try get_search with empty query (if NO_QUERY supported)
        
        has_browse = hasattr(provider, "get_browse")
        has_no_query = bool(provider.FILTER_CAPS & FilterCapabilities.NO_QUERY)
        
        if not has_browse and not has_no_query:
            raise HTTPException(
                status_code=501,
                detail="Provider does not support popular/trending search (no browse or empty query support)"
            )

        key = ("popular", page, limit)
        cached = BROWSE_CACHE.get(key)
        
        results_data = []
        has_next = False
        
        if cached is not None:
            result_obj = cached
            # Cached object structure depends on what we cached.
            # Let's align on caching the raw provider result or equivalent dict.
            # Here we assume we cached the standardized dict.
            results_data = result_obj["results"]
            has_next = result_obj["has_next"]
        else:
            if has_browse:
                # Expects dict with results list of dicts
                browse_res = await run_in_threadpool(provider.get_browse, page=page, limit=limit)
                results_data = browse_res["results"]
                has_next = browse_res["has_next"]
            elif has_no_query:
                # Expects list of ProviderSearchResult objects
                # We need to manually handle pagination if provider.get_search doesn't support page/limit in the same way 
                # or if it returns all results. 
                # But BaseProvider.get_search doesn't standardly take page/limit (AllAnimeProvider does but as extra args).
                # AllAnimeProvider.get_search(query, filters, max_pages, max_results)
                
                # Check if get_search accepts max_pages/max_results or if we need to slice
                # AllAnimeProvider implements extra args but they are not in BaseProvider signature.
                # To be safe, we just call get_search("") 
                # But wait, BaseProvider.get_search(query, filters)
                
                search_res = await run_in_threadpool(provider.get_search, "")
                
                # Manual pagination
                start = (page - 1) * limit
                end = start + limit
                sliced = search_res[start:end]
                has_next = len(search_res) > end
                
                # Convert ProviderSearchResult objects to dicts matching browse format
                results_data = []
                for item in sliced:
                    results_data.append({
                        "identifier": item.identifier,
                        "name": item.name,
                        "image": item.image,
                        "languages": [str(l) for l in item.languages],
                        "genres": item.genres,
                        "available_episodes": item.available_episodes
                    })
            
            # Cache the result
            to_cache = {
                "results": results_data,
                "has_next": has_next,
                "page": page
            }
            BROWSE_CACHE.set(key, to_cache)

        # Enhance with Jikan/Anilist data (logic reused from anime.py/search.py)
        
        # 1. Fetch images from Jikan if missing
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {}
            for item in results_data:
                image_url = item.get("image")
                if not image_url or not image_url.strip().lower().startswith("http"):
                    futures[executor.submit(get_jikan_image, item["name"])] = item
            
            for future in futures:
                item = futures[future]
                jikan_image = future.result()
                if jikan_image:
                    item["image"] = jikan_image
        
        semaphore = asyncio.Semaphore(10)

        async def build_card(item: dict) -> AnimeCardModel:
            async with semaphore:
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

        data_list = await asyncio.gather(*(build_card(item) for item in results_data))

        return PaginatedResponse(
            page=page,
            has_next=has_next,
            data=data_list
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get popular anime: {str(e)}"
        )
