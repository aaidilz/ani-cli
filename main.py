#!/usr/bin/env python3
"""
Main entry point for Ani-CLI FastAPI application
"""

import uvicorn
from app import create_app
from app.config import Config

# Create FastAPI application instance
app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.RELOAD
    )
