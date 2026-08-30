"""Ratings endpoints — a user's personal 1-10 score for a title."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models import Rating, User
from app.schemas import RatingIn, RatingOut

router = APIRouter()


@router.get("/", response_model=list[RatingOut])
async def list_ratings(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Rating).where(Rating.user_id == user.id).order_by(Rating.updated_at.desc()))
    return result.scalars().all()


@router.post("/", response_model=RatingOut, status_code=201)
async def rate(payload: RatingIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Rating).where(
            Rating.user_id == user.id,
            Rating.tmdb_id == payload.tmdb_id,
            Rating.media_type == payload.media_type,
        )
    )
    rating = result.scalar_one_or_none()
    if rating:
        rating.rating = payload.rating
    else:
        rating = Rating(
            user_id=user.id, tmdb_id=payload.tmdb_id, media_type=payload.media_type, rating=payload.rating
        )
        db.add(rating)
    await db.commit()
    await db.refresh(rating)
    return rating


@router.delete("/{tmdb_id}/{media_type}", status_code=204)
async def remove_rating(
    tmdb_id: int, media_type: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Rating).where(
            Rating.user_id == user.id, Rating.tmdb_id == tmdb_id, Rating.media_type == media_type
        )
    )
    rating = result.scalar_one_or_none()
    if rating:
        await db.delete(rating)
        await db.commit()
