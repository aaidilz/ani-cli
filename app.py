#!/usr/bin/env python3
"""
FastAPI application for anime streaming using AllAnime provider
"""

from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import urllib3

from anipy_api.provider.providers import AllAnimeProvider
from anipy_api.anime import Anime
from anipy_api.provider import LanguageTypeEnum

# Disable SSL verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Initialize FastAPI app
app = FastAPI(
    title="Ani-CLI FastAPI",
    description="FastAPI wrapper for AllAnime provider",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize provider
provider = AllAnimeProvider()
provider.session.verify = False


# ==================== Pydantic Models ====================

class SearchResultModel(BaseModel):
    """Model for search results"""
    name: str
    identifier: str
    languages: List[str]


class SearchResponse(BaseModel):
    """Model for search response"""
    query: str
    total_results: int
    results: List[SearchResultModel]


class AnimeInfoModel(BaseModel):
    """Model for anime info"""
    name: Optional[str] = None
    image: Optional[str] = None
    genres: Optional[List[str]] = None
    synopsis: Optional[str] = None
    release_year: Optional[int] = None
    status: Optional[str] = None
    alternative_names: Optional[List[str]] = None


class EpisodeStreamModel(BaseModel):
    """Model for episode stream"""
    url: str
    resolution: int
    language: str
    subtitle: Optional[Dict[str, Any]] = None


class EpisodesResponse(BaseModel):
    """Model for episodes response"""
    identifier: str
    name: str
    episodes: Dict[str, List[EpisodeStreamModel]]


class ErrorResponse(BaseModel):
    """Model for error responses"""
    detail: str
    error_type: str


# ==================== Helper Functions ====================

def get_provider_instance() -> AllAnimeProvider:
    """Get AllAnime provider instance"""
    global provider
    return provider


# ==================== Routes ====================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to Ani-CLI FastAPI",
        "provider": "AllAnime",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "search": "/search?query=anime_name",
            "info": "/anime/{identifier}",
            "episodes": "/anime/{identifier}/episodes",
            "stream": "/anime/{identifier}/episode/{episode}/stream"
        }
    }


@app.get("/search", response_model=SearchResponse, tags=["Search"])
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
        provider_instance = get_provider_instance()
        results = provider_instance.get_search(query)
        
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


@app.get("/anime/{identifier}", response_model=AnimeInfoModel, tags=["Anime Info"])
async def get_anime_info(
    identifier: str = Path(..., description="Anime identifier")
):
    """
    Get detailed information about an anime
    
    - **identifier**: The anime identifier from search results
    """
    try:
        provider_instance = get_provider_instance()
        info = provider_instance.get_info(identifier)
        
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


@app.get("/anime/{identifier}/episodes", response_model=EpisodesResponse, tags=["Episodes"])
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
        provider_instance = get_provider_instance()
        episodes = provider_instance.get_episodes(identifier)
        
        # Organize episodes by language
        episodes_by_lang: Dict[str, List[EpisodeStreamModel]] = {}
        
        for episode_num in episodes:
            episodes_by_lang[str(episode_num)] = []
        
        return EpisodesResponse(
            identifier=identifier,
            name="",
            episodes=episodes_by_lang
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get episodes: {str(e)}"
        )


@app.get("/anime/{identifier}/episode/{episode}/stream", tags=["Streams"])
async def get_episode_stream(
    identifier: str = Path(..., description="Anime identifier"),
    episode: float = Path(..., description="Episode number"),
    language: str = Query("sub", description="Language (sub or dub)")
):
    """
    Get streaming links for a specific episode
    
    - **identifier**: The anime identifier
    - **episode**: Episode number
    - **language**: Language (sub or dub)
    """
    try:
        provider_instance = get_provider_instance()
        
        # Get streams for the episode
        streams = provider_instance.get_streams(
            identifier=identifier,
            episode=episode,
            language=LanguageTypeEnum.SUB if language.lower() == "sub" else LanguageTypeEnum.DUB
        )
        
        stream_list = [
            EpisodeStreamModel(
                url=stream.url,
                resolution=stream.resolution,
                language=str(stream.language),
                subtitle=stream.subtitle if hasattr(stream, 'subtitle') else None
            )
            for stream in streams
        ]
        
        return {
            "identifier": identifier,
            "episode": episode,
            "language": language,
            "streams": stream_list
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get streams: {str(e)}"
        )


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    try:
        provider_instance = get_provider_instance()
        # Try a simple operation to verify provider is working
        return {
            "status": "healthy",
            "provider": "AllAnime",
            "message": "API is running"
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            detail=exc.detail,
            error_type="HTTPException"
        ).dict()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
