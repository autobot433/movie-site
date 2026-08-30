"""FilmRec API — FastAPI backend."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import auth, recommendations, ratings, watchlist, profile, search
from app.core.config import settings
from app.core.database import init_db
from app.core.limiter import limiter

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="FilmRec API",
    version="1.0.0",
    lifespan=lifespan,
    debug=False,
)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    response = JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please wait a moment and try again."},
    )
    return limiter._inject_headers(response, request.state.view_rate_limit)


app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all safety net: no unexpected exception ever reaches a client.

    Without this, an unanticipated bug (a bad TMDB response, a DB error)
    could surface Python internals — file paths, query text, library
    versions — to whoever triggered it. The full detail still goes to the
    server log for debugging; the client only ever sees a generic message.
    """
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


@app.exception_handler(StarletteHTTPException)
async def custom_404_handler(request: Request, exc: StarletteHTTPException):
    """A visit to an unknown URL never hits the browser's bare, unbranded 404.

    This app is a single-page app with no server-side routing — every real
    page lives at "/" and is chosen by client-side state, not by URL. So an
    unmatched non-API path (a stale bookmark, a typo, a shared link with a
    trailing slug) is still the *app*; the frontend's own "not found" UI
    can handle it far better than a blank browser error page ever could.
    API paths keep returning plain JSON, since nothing there renders HTML.
    """
    if exc.status_code == 404 and not request.url.path.startswith(("/api/", "/static/")) and FRONTEND.is_dir():
        return FileResponse(FRONTEND / "index.html", status_code=200)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# Registered under both prefixes: locally this process serves "/api/..."
# directly, with nothing else in front of it. On Vercel, api/index.py is
# itself conceptually mounted at "/api" — different sources describe
# inconsistently whether that prefix reaches this app or gets stripped
# first, so both are covered rather than guessing which one is real.
for prefix in ("/api", ""):
    app.include_router(auth.router, prefix=f"{prefix}/auth", tags=["auth"])
    app.include_router(recommendations.router, prefix=f"{prefix}/recommendations", tags=["recommendations"])
    app.include_router(ratings.router, prefix=f"{prefix}/ratings", tags=["ratings"])
    app.include_router(watchlist.router, prefix=f"{prefix}/watchlist", tags=["watchlist"])
    app.include_router(profile.router, prefix=f"{prefix}/profile", tags=["profile"])
    app.include_router(search.router, prefix=f"{prefix}/search", tags=["search"])


FRONTEND = Path(__file__).resolve().parents[2] / "public"

# On Vercel, public/ is served directly by their CDN and never bundled into
# this function (nor does it need to be) — only mount it locally, where this
# process is responsible for serving the frontend itself.
if FRONTEND.is_dir():
    @app.get("/")
    async def serve_frontend():
        return FileResponse(FRONTEND / "index.html")

    app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
