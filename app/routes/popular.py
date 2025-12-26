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
    get_jikan_total_episodes, # kept but might be unused if jikan gives us this directly
    get_anilist_score,
    get_kitsu_age_rating,
    get_jikan_top_anime,
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
        
        # New Strategy:
        # 1. Fetch top anime from Jikan (MyAnimeList)
        # 2. For each result, search in AllAnime to find a match (mapping)
        # 3. Return combined data
        
        key = ("popular", page, limit)
        cached = BROWSE_CACHE.get(key)
        
        results_data = []
        has_next = False
        
        if cached is not None:
            results_data = cached["results"]
            has_next = cached["has_next"]
        else:
            # 1. Get from Jikan
            jikan_data = await run_in_threadpool(get_jikan_top_anime, page=page, limit=limit)
            
            # 2. Map to AllAnime
            semaphore = asyncio.Semaphore(10) # Limit concurrent searches

            async def map_to_provider(jikan_item):
                async with semaphore:
                    title_en = jikan_item["title_english"] if jikan_item.get("title_english") else jikan_item["title"]
                    title_default = jikan_item["title"]
                    
                    # Try searching with english title first then default
                    search_query = title_en if title_en else title_default
                    
                    try:
                        # Use provider search. 
                        # We use run_in_threadpool because provider.get_search is synchronous/blocking
                        search_results = await run_in_threadpool(provider.get_search, search_query)
                        
                        if search_results:
                            # Take the first/best match
                            # Since provider.get_search already sorts by similarity, first is usually best.
                            best_match = search_results[0]
                            
                            # Construct unified result item
                            return {
                                "identifier": best_match.identifier,
                                "name": best_match.name,
                                "image": jikan_item["images"]["jpg"]["large_image_url"] or best_match.image,
                                "languages": [str(l) for l in best_match.languages],
                                "genres": [g["name"] for g in jikan_item.get("genres", [])],
                                "total_episodes": jikan_item.get("episodes"),
                                "rating_score": jikan_item.get("score"),
                                "rating_rating": jikan_item.get("rating"), # e.g. "PG-13"
                                "available_episodes": best_match.available_episodes
                            }
                    except Exception:
                        pass
                    return None

            mapped_results = await asyncio.gather(*(map_to_provider(item) for item in jikan_data))
            
            # Filter out failures (None)
            results_data = [r for r in mapped_results if r is not None]
            
            has_next = len(jikan_data) >= limit # Approximation
            
            # Cache partial result
            to_cache = {
                "results": results_data,
                "has_next": has_next,
                "page": page
            }
            BROWSE_CACHE.set(key, to_cache)

        # Build Card Models
        data_list = []
        for item in results_data:
            # item has already enriched data from Jikan mapping step
            data_list.append(AnimeCardModel(
                identifier=item["identifier"],
                name=item["name"],
                image=item["image"],
                languages=item["languages"],
                genres=item["genres"],
                total_episode=item["total_episodes"],
                rating_score=float(item["rating_score"]/10.0) if item["rating_score"] else None, # normalized to 0-1
                rating_classification=item["rating_rating"]
            ))

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
