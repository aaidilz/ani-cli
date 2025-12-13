"""
Ani-CLI FastAPI application package
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import HTTPException

from app.config import Config, get_provider
from app.models import ErrorResponse
from app.routes.root import router as root_router
from app.routes.search import router as search_router
from app.routes.anime import router as anime_router
from app.routes.stream import router as stream_router


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""

    # Initialize FastAPI app
    app = FastAPI(
        title=Config.TITLE,
        description=Config.DESCRIPTION,
        version=Config.VERSION,
        docs_url=Config.DOCS_URL,
        redoc_url=Config.REDOC_URL
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=Config.ALLOW_ORIGINS,
        allow_credentials=Config.ALLOW_CREDENTIALS,
        allow_methods=Config.ALLOW_METHODS,
        allow_headers=Config.ALLOW_HEADERS,
    )

    # Include routers
    app.include_router(root_router)
    app.include_router(search_router)
    app.include_router(anime_router)
    app.include_router(stream_router)

    # Exception handlers
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

    return app