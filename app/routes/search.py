"""
Search routes for Ani-CLI FastAPI application
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from anipy_api.provider.providers import AllAnimeProvider
from anipy_api.provider.filter import Filters, Status

from app.models import SearchResponse, SearchResultModel
from app.config import get_provider

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

        search_results = [
            SearchResultModel(
                name=result.name,
                identifier=result.identifier,
                languages=[str(lang) for lang in result.languages]
            )
            for result in limited_results
        ]

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