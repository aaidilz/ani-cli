"""
Pydantic models for the Ani-CLI FastAPI application
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class AnimeInfoModel(BaseModel):
    """Model for anime info"""
    name: Optional[str] = None
    image: Optional[str] = None
    genres: Optional[List[str]] = None
    synopsis: Optional[str] = None
    release_year: Optional[int] = None
    status: Optional[str] = None
    alternative_names: Optional[List[str]] = None
    total_episode: Optional[int] = None
    rating_score: Optional[float] = None
    rating_count: Optional[int] = None
    rating_classification: Optional[str] = None


class EpisodeStreamModel(BaseModel):
    """Model for episode stream"""
    url: str
    resolution: int
    language: str
    subtitle: Optional[Dict[str, Any]] = None
    referer: Optional[str] = None


class EpisodesResponse(BaseModel):
    """Model for episodes response"""
    identifier: str
    name: str
    episodes: Dict[str, List[EpisodeStreamModel]]


class ErrorResponse(BaseModel):
    """Model for error responses"""
    detail: str
    error_type: str


class AnimeCardModel(BaseModel):
    """Model for anime card in list views"""
    identifier: str
    name: str
    image: Optional[str] = None
    languages: List[str]
    genres: Optional[List[str]] = None
    total_episode: Optional[int] = None
    rating_score: Optional[float] = None
    rating_classification: Optional[str] = None


class PaginatedResponse(BaseModel):
    """Model for paginated response"""
    page: int
    has_next: bool
    data: List[AnimeCardModel]
