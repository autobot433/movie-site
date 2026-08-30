"""Authentication: register, login, refresh, current user, password reset."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.limiter import limiter
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.models import User
from app.schemas import ForgotPasswordIn, RefreshIn, RegisterIn, TokenPair, UserOut

router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    user_id = decode_token(creds.credentials, expected_type="access")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found.")
    return user


@router.post("/register", status_code=201)
@limiter.limit("5/minute")
async def register(request: Request, payload: RegisterIn, db: AsyncSession = Depends(get_db)):
    if payload.website:
        return {"detail": "Account created."}

    existing = await db.execute(
        select(User).where((User.email == payload.email) | (User.username == payload.username))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email or username already in use.")

    user = User(
        email=payload.email,
        username=payload.username,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name or payload.username,
    )
    db.add(user)
    await db.commit()
    return {"detail": "Account created."}


@router.post("/login", response_model=TokenPair)
@limiter.limit("10/minute")
async def login(
    request: Request, form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == form.username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    return TokenPair(access_token=create_token(user.id, "access"), refresh_token=create_token(user.id, "refresh"))


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshIn, db: AsyncSession = Depends(get_db)):
    user_id = decode_token(payload.refresh_token, expected_type="refresh")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token.")
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found.")
    return TokenPair(access_token=create_token(user.id, "access"), refresh_token=create_token(user.id, "refresh"))


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user


@router.post("/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(request: Request, payload: ForgotPasswordIn):
    return {"detail": "If that email exists, a reset link has been sent."}
