"""
Utility functions for Ani-CLI FastAPI application
"""

from anipy_api.provider import LanguageTypeEnum


def parse_language(language: str) -> LanguageTypeEnum:
    """Parse language string to LanguageTypeEnum"""
    if language.lower() == "sub":
        return LanguageTypeEnum.SUB
    elif language.lower() == "dub":
        return LanguageTypeEnum.DUB
    else:
        raise ValueError(f"Invalid language '{language}', must be 'sub' or 'dub'")


def format_episode_number(episode: float) -> int | float:
    """Format episode number for API calls"""
    return int(episode) if episode.is_integer() else episode