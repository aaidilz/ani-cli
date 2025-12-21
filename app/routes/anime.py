"""
Anime routes for Ani-CLI FastAPI application
"""

from fastapi import APIRouter, HTTPException, Path, Query
from typing import Optional, Dict, List
from concurrent.futures import ThreadPoolExecutor

from anipy_api.provider.providers import AllAnimeProvider
from anipy_api.provider import LanguageTypeEnum

from app.models import AnimeInfoModel, EpisodesResponse, EpisodeStreamModel, PaginatedResponse, AnimeCardModel
from app.utils import parse_language, get_jikan_image
from app.config import get_provider

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

        result = provider.get_browse(page=page, limit=limit, genres=genres)
        
        # Fetch images from Jikan in parallel for items with missing or invalid images
        with ThreadPoolExecutor() as executor:
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
                    print(f"[DEBUG] Updated image for '{item['name']}' -> {jikan_image}")
                    item["image"] = jikan_image
                else:
                    print(f"[DEBUG] Jikan failed for '{item['name']}', clearing invalid image")
                    item["image"] = None
        
        return PaginatedResponse(
            page=result["page"],
            has_next=result["has_next"],
            data=[
                AnimeCardModel(
                    identifier=item["identifier"],
                    name=item["name"],
                    image=item["image"],
                    languages=item["languages"],
                    genres=item.get("genres")
                ) for item in result["results"]
            ]
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

        info = provider.get_info(identifier)

        return AnimeInfoModel(
            name=info.name,
            image=info.image,
            genres=info.genres,
            synopsis=info.synopsis,
            release_year=info.release_year,
            status=str(info.status) if info.status else None,
            alternative_names=info.alternative_names
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

        episodes = provider.get_episodes(identifier, lang_enum)

        # Organize episodes by language
        episodes_by_lang: Dict[str, List[EpisodeStreamModel]] = {}

        for episode_num in episodes:
            episodes_by_lang[str(episode_num)] = []

        info = provider.get_info(identifier)
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


