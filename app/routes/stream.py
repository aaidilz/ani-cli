"""
Stream routes for Ani-CLI FastAPI application
"""

from fastapi import APIRouter, HTTPException, Path, Query

from anipy_api.provider.providers import AllAnimeProvider

from app.models import EpisodeStreamModel
from app.utils import parse_language, format_episode_number
from app.config import get_provider

router = APIRouter()


@router.get("/anime/{identifier}/episode/{episode}/stream", tags=["Streams"])
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
        provider = get_provider()

        # Parse language
        lang_enum = parse_language(language)

        # Format episode number
        episode_val = format_episode_number(episode)

        streams = provider.get_video(identifier, episode_val, lang_enum)

        stream_list = [
            EpisodeStreamModel(
                url=stream.url,
                resolution=stream.resolution,
                language=str(stream.language),
                subtitle=stream.subtitle if hasattr(stream, 'subtitle') else None,
                referer=stream.referrer
            )
            for stream in streams
        ]

        return {
            "identifier": identifier,
            "episode": episode,
            "language": language,
            "streams": stream_list
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get streams: {str(e)}"
        )