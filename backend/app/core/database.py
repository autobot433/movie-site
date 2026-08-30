"""Async SQLAlchemy engine, session factory, and startup table creation."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from urllib.parse import parse_qs, urlencode

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
        #
        # This only ever touches the query string via plain str.partition,
        # deliberately never urllib.parse.urlsplit: recent CPython versions
        # (the one this runs on in production included) have a real bug
        # where urlsplit raises ValueError on ordinary user:pass@host
        # netlocs, misfiring a check meant only for bracketed IPv6 hosts.
        base, _, query_string = url.partition("?")
        query = parse_qs(query_string)
        query.pop("channel_binding", None)
        sslmode = query.pop("sslmode", [None])[0]
        if sslmode:
            connect_args["ssl"] = sslmode
        url = f"{base}?{urlencode(query, doseq=True)}" if query else base

    return create_async_engine(url, echo=False, connect_args=connect_args)


engine = _make_engine()
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    from app import models  # noqa: F401 — import registers tables on Base.metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
