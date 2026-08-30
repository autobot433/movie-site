"""Pydantic request/response models for the API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8)
    display_name: str = ""
    website: str = ""


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str


class RefreshIn(BaseModel):
    refresh_token: str


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class UserOut(BaseModel):
    username: str
    display_name: str
    bio: str
    avatar_url: str | None

    model_config = {"from_attributes": True}


class ProfilePatch(BaseModel):
    display_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None


class RatingIn(BaseModel):
    tmdb_id: int
    media_type: str
    rating: float = Field(ge=1, le=10)


class RatingOut(BaseModel):
    id: int
    tmdb_id: int
    media_type: str
    rating: float
    updated_at: datetime

    model_config = {"from_attributes": True}


class WatchlistIn(BaseModel):
    tmdb_id: int
    media_type: str


class WatchlistOut(BaseModel):
    id: int
    tmdb_id: int
    media_type: str
    created_at: datetime

    model_config = {"from_attributes": True}
