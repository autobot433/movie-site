"""Async SQLAlchemy engine, session factory, and startup table creation."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    pass


def _make_engine():
    url = settings.database_url
    connect_args: dict = {}

    if url.startswith("postgresql+asyncpg://"):
        # Postgres hosts (Neon included) commonly hand out connection strings
        # with `sslmode=`/`channel_binding=` — libpq/psycopg conventions that
        # asyncpg's connect() doesn't recognize as keyword arguments and
        # rejects outright. `channel_binding` has no asyncpg equivalent and
        # is dropped; `sslmode`'s value maps directly onto asyncpg's own
        # `ssl` kwarg, which accepts the same mode strings under a different
        # name — so translate it there instead of just discarding it.
        parts = urlsplit(url)
        query = parse_qs(parts.query)
        query.pop("channel_binding", None)
        sslmode = query.pop("sslmode", [None])[0]
        if sslmode:
            connect_args["ssl"] = sslmode
        url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query, doseq=True), parts.fragment))

    return create_async_engine(url, echo=False, connect_args=connect_args)


engine = _make_engine()
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    from app import models  

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
