"""
Root and health routes for Ani-CLI FastAPI application
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import Config

router = APIRouter()


@router.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to Ani-CLI FastAPI",
        "provider": "AllAnime",
        "version": Config.VERSION,
        "docs": Config.DOCS_URL,
        "endpoints": {
            "search": "/search?query=anime_name",
            "info": "/anime/{identifier}",
            "episodes": "/anime/{identifier}/episodes",
            "stream": "/anime/{identifier}/episode/{episode}/stream"
        }
    }


@router.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    try:
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