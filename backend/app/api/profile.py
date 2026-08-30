"""Profile endpoints — edit display name, bio, and avatar."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas import ProfilePatch, UserOut

router = APIRouter()


@router.patch("/", response_model=UserOut)
async def update_profile(
    payload: ProfilePatch, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user
