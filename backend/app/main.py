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
    # Explicit, not just the (already-safe) default: guarantees Starlette
    # never renders a debug traceback page to a client under any config.
    debug=False,
)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    # Match the shape ({"detail": ...}) every other error on this API uses,
    # instead of slowapi's default {"error": ...} — the frontend's error
    # handling only ever looks at `detail`, so this keeps rate-limit
    # messages from silently falling back to a generic "Request failed".
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
    if exc.status_code == 404 and not request.url.path.startswith(("/api/", "/static/")):
        return FileResponse(FRONTEND / "index.html", status_code=200)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(recommendations.router, prefix="/api/recommendations", tags=["recommendations"])
app.include_router(ratings.router, prefix="/api/ratings", tags=["ratings"])
app.include_router(watchlist.router, prefix="/api/watchlist", tags=["watchlist"])
app.include_router(profile.router, prefix="/api/profile", tags=["profile"])
app.include_router(search.router, prefix="/api/search", tags=["search"])


FRONTEND = Path(__file__).resolve().parents[2] / "public"

@app.get("/")
async def serve_frontend():
    return FileResponse(FRONTEND / "index.html")

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}

app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")
