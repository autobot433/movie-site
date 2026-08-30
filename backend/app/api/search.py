"""Search endpoints — thin wrappers around the TMDB service."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.auth import get_current_user
from app.models import User
from app.services import tmdb

router = APIRouter()


@router.get("/")
async def search(q: str, user: User = Depends(get_current_user)):
    return {"results": await tmdb.search_multi(q)}


@router.get("/details/{media_type}/{tmdb_id}")
async def details(media_type: str, tmdb_id: int, user: User = Depends(get_current_user)):
    return await tmdb.get_details(tmdb_id, media_type)
