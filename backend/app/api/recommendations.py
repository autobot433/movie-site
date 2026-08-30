"""Recommendation endpoints: genres, trending hero, filtered discover,
personalised "for you" rows, and the infinite-scroll feed."""

from __future__ import annotations

import random

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models import Rating, User, WatchlistItem
from app.services import tmdb

router = APIRouter()


FOR_YOU_ROW_COUNT = 4


@router.get("/genres")
async def genres():
    return {"genres": [{"id": gid, "name": name} for gid, name in tmdb.FEATURED_GENRE_IDS]}


@router.get("/trending")
async def trending():
    return {"items": await tmdb.get_trending("all", "week")}


@router.get("/discover")
async def discover(media_type: str = "movie", genre: int | None = None, time_window: str = "all"):
    return {"items": await tmdb.discover_filtered(media_type=media_type, genre_id=genre, time_window=time_window)}


@router.get("/feed")
async def feed(page: int = 1):
    return {"items": await tmdb.get_trending("all", "day", page=page)}


@router.get("/")
async def for_you(
    refresh_seed: int = 0, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    ratings_result = await db.execute(select(Rating).where(Rating.user_id == user.id))
    ratings = ratings_result.scalars().all()
    rated_items = [{"tmdb_id": r.tmdb_id, "media_type": r.media_type, "rating": r.rating} for r in ratings]

    exclude_ids = {r.tmdb_id for r in ratings}
    watchlist_result = await db.execute(select(WatchlistItem.tmdb_id).where(WatchlistItem.user_id == user.id))
    exclude_ids.update(watchlist_result.scalars().all())

    # "Refresh" reshuffles which genre rows show up, seeded so a given click
    # is reproducible rather than fully random.
    genre_pool = list(tmdb.FEATURED_GENRE_IDS)
    random.Random(refresh_seed).shuffle(genre_pool)

    rows = []
    for genre_id, genre_name in genre_pool[:FOR_YOU_ROW_COUNT]:
        items = await tmdb.get_recommendations_for_ids(rated_items, exclude_ids, genre_id=genre_id, count=8)
        if items:
            rows.append({"genre": genre_name, "media_type": "movie", "items": items})
    return {"genres": rows}
