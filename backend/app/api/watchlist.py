"""Watchlist endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models import User, WatchlistItem
from app.schemas import WatchlistIn, WatchlistOut

router = APIRouter()


@router.get("/", response_model=list[WatchlistOut])
async def list_watchlist(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WatchlistItem).where(WatchlistItem.user_id == user.id).order_by(WatchlistItem.created_at.desc())
    )
    return result.scalars().all()


@router.post("/", response_model=WatchlistOut, status_code=201)
async def add_to_watchlist(
    payload: WatchlistIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.user_id == user.id,
            WatchlistItem.tmdb_id == payload.tmdb_id,
            WatchlistItem.media_type == payload.media_type,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already in watchlist.")
    item = WatchlistItem(user_id=user.id, tmdb_id=payload.tmdb_id, media_type=payload.media_type)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
async def remove_from_watchlist(
    item_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    item = await db.get(WatchlistItem, item_id)
    if item and item.user_id == user.id:
        await db.delete(item)
        await db.commit()
