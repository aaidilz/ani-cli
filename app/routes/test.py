from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool
from app.utils import get_jikan_top_anime
from app.config import get_provider
import asyncio

router = APIRouter()

@router.get("/test/popular")
async def test_popular_logic(page: int = 1):
    """
    Test the Jikan -> AllAnime mapping logic without the strict response model.
    """
    provider = get_provider()
    
    # 1. Get from Jikan
    jikan_data = await run_in_threadpool(get_jikan_top_anime, page=page, limit=5)
    
    results = []
    
    for item in jikan_data:
        title_en = item.get("title_english")
        title_default = item.get("title")
        search_query = title_en if title_en else title_default
        
        provider_matches = []
        try:
            search_res = await run_in_threadpool(provider.get_search, search_query)
            provider_matches = [
                {"name": r.name, "id": r.identifier, "languages": [str(l) for l in r.languages]} 
                for r in search_res[:3]
            ]
        except Exception as e:
            provider_matches = [str(e)]

        results.append({
            "jikan_title": title_default,
            "jikan_title_en": title_en,
            "search_query": search_query,
            "provider_matches": provider_matches
        })

    return {"results": results}
