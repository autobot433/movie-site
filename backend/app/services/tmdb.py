"""TMDB service — the source of all media data in FilmRec.

Every poster, title, genre, and "similar titles" list comes from TMDB's free API.
Results are cached in memory (LRU) so a page of 8 recommendations doesn't
trigger 8 sequential round-trips.
"""

from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any

import httpx

from app.core.config import settings

GENRES_MOVIE = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime",
    99: "Documentary", 18: "Drama", 10751: "Family", 14: "Fantasy", 36: "History",
    27: "Horror", 10402: "Music", 9648: "Mystery", 10749: "Romance",
    878: "Science Fiction", 10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western",
}

GENRES_TV = {
    10759: "Action & Adventure", 16: "Animation", 35: "Comedy", 80: "Crime",
    99: "Documentary", 18: "Drama", 10751: "Family", 10762: "Kids",
    9648: "Mystery", 10763: "News", 10764: "Reality", 10765: "Sci-Fi & Fantasy",
    10766: "Soap", 10767: "Talk", 10768: "War & Politics", 37: "Western",
}

# Genre IDs to surface on the recommendations page, in display order.
FEATURED_GENRE_IDS = [
    (28, "Action"),
    (27, "Horror"),
    (35, "Comedy"),
    (53, "Thriller"),
    (878, "Science Fiction"),
    (10749, "Romance"),
    (18, "Drama"),
    (12, "Adventure"),
]

POSTER_SIZES = {"small": "w185", "medium": "w342", "large": "w500", "backdrop": "w1280", "original": "original"}


def poster_url(path: str | None, size: str = "medium") -> str | None:
    if not path:
        return None
    return f"{settings.tmdb_image_base}/{POSTER_SIZES.get(size, 'w342')}{path}"


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.tmdb_base_url,
        params={"api_key": settings.tmdb_api_key},
        timeout=8.0,
    )


def _format_movie(raw: dict, media_type: str = "movie") -> dict:
    title = raw.get("title") or raw.get("name") or "Unknown"
    return {
        "tmdb_id": raw.get("id"),
        "media_type": media_type,
        "title": title,
        "overview": raw.get("overview") or "",
        "poster_url": poster_url(raw.get("poster_path")),
        "backdrop_url": poster_url(raw.get("backdrop_path"), "backdrop"),
        "release_date": raw.get("release_date") or raw.get("first_air_date") or "",
        "vote_average": round(raw.get("vote_average", 0) * 10) / 10,
        "vote_count": raw.get("vote_count", 0),
        "genre_ids": raw.get("genre_ids", []),
        "genres": [
            GENRES_MOVIE.get(g) or GENRES_TV.get(g)
            for g in raw.get("genre_ids", [])
            if GENRES_MOVIE.get(g) or GENRES_TV.get(g)
        ],
        "popularity": raw.get("popularity", 0),
    }


async def search_multi(query: str, page: int = 1) -> list[dict]:
    async with _client() as client:
        resp = await client.get("/search/multi", params={"query": query, "page": page})
        resp.raise_for_status()
        results = resp.json().get("results", [])
    return [
        _format_movie(r, r.get("media_type", "movie"))
        for r in results
        if r.get("media_type") in ("movie", "tv") and r.get("poster_path")
    ]


async def get_details(tmdb_id: int, media_type: str) -> dict:
    async with _client() as client:
        resp = await client.get(f"/{media_type}/{tmdb_id}", params={"append_to_response": "credits,similar,videos"})
        resp.raise_for_status()
        raw = resp.json()

    genres = [g["name"] for g in raw.get("genres", [])]
    cast = [
        {"name": m["name"], "character": m.get("character"), "profile_url": poster_url(m.get("profile_path"), "small")}
        for m in raw.get("credits", {}).get("cast", [])[:10]
    ]
    similar = [_format_movie(r, media_type) for r in raw.get("similar", {}).get("results", [])[:8] if r.get("poster_path")]
    trailer = next(
        (f"https://www.youtube.com/embed/{v['key']}" for v in raw.get("videos", {}).get("results", []) if v.get("type") == "Trailer" and v.get("site") == "YouTube"),
        None,
    )

    return {
        "tmdb_id": raw["id"],
        "media_type": media_type,
        "title": raw.get("title") or raw.get("name"),
        "tagline": raw.get("tagline") or "",
        "overview": raw.get("overview") or "",
        "poster_url": poster_url(raw.get("poster_path")),
        "backdrop_url": poster_url(raw.get("backdrop_path"), "backdrop"),
        "release_date": raw.get("release_date") or raw.get("first_air_date") or "",
        "runtime": raw.get("runtime") or (raw.get("episode_run_time") or [None])[0],
        "vote_average": round(raw.get("vote_average", 0) * 10) / 10,
        "vote_count": raw.get("vote_count", 0),
        "genres": genres,
        "cast": cast,
        "similar": similar,
        "trailer_url": trailer,
        "status": raw.get("status") or "",
        "number_of_seasons": raw.get("number_of_seasons"),
    }


async def discover_by_genre(genre_id: int, media_type: str = "movie", page: int = 1) -> list[dict]:
    async with _client() as client:
        resp = await client.get(
            f"/discover/{media_type}",
            params={
                "with_genres": genre_id,
                "sort_by": "popularity.desc",
                "vote_count.gte": 100,
                "page": page,
            },
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
    return [_format_movie(r, media_type) for r in results if r.get("poster_path")]


def _time_window_bounds(time_window: str) -> tuple[str | None, str | None]:
    """Return (gte, lte) date strings for a time-window filter."""
    from datetime import date

    today = date.today()
    if time_window == "month":
        start = today.replace(day=1)
    elif time_window == "year":
        start = today.replace(month=1, day=1)
    elif time_window == "decade":
        start = today.replace(year=today.year - 10)
    else:  # "all"
        return None, None
    return start.isoformat(), today.isoformat()


async def discover_filtered(
    media_type: str = "movie",
    genre_id: int | None = None,
    time_window: str = "all",
    page: int = 1,
) -> list[dict]:
    """Popular titles filtered by genre and release-date window.

    Powers the main Discover page: genre + "all time / this month / this
    year / past 10 years" filters, sorted by popularity.
    """
    date_field = "primary_release_date" if media_type == "movie" else "first_air_date"
    gte, lte = _time_window_bounds(time_window)

    params = {
        "sort_by": "popularity.desc",
        "vote_count.gte": 50,
        "page": page,
    }
    if genre_id:
        params["with_genres"] = genre_id
    if gte:
        params[f"{date_field}.gte"] = gte
    if lte:
        params[f"{date_field}.lte"] = lte

    async with _client() as client:
        resp = await client.get(f"/discover/{media_type}", params=params)
        resp.raise_for_status()
        results = resp.json().get("results", [])
    return [_format_movie(r, media_type) for r in results if r.get("poster_path")]


async def get_trending(media_type: str = "all", time_window: str = "week") -> list[dict]:
    async with _client() as client:
        resp = await client.get(f"/trending/{media_type}/{time_window}")
        resp.raise_for_status()
        results = resp.json().get("results", [])
    return [
        _format_movie(r, r.get("media_type", "movie"))
        for r in results
        if r.get("poster_path") and r.get("media_type") in ("movie", "tv")
    ]


async def get_similar(tmdb_id: int, media_type: str, page: int = 1) -> list[dict]:
    async with _client() as client:
        resp = await client.get(f"/{media_type}/{tmdb_id}/similar", params={"page": page})
        resp.raise_for_status()
        results = resp.json().get("results", [])
    return [_format_movie(r, media_type) for r in results if r.get("poster_path")]


async def get_recommendations_for_ids(
    rated_items: list[dict],
    exclude_ids: set[int],
    genre_id: int | None = None,
    count: int = 8,
) -> list[dict]:
    """Fetch similar titles for each highly-rated item, merge, deduplicate, and score.

    This is the core personalisation loop: high-rated items seed TMDB's
    /similar endpoint, and the results are ranked by how many different
    seeds produced them (a film similar to three of your favourites ranks
    higher than one similar to only one).
    """
    if not rated_items:
        return await discover_by_genre(genre_id or 28, count=count)

    high_rated = sorted(
        [r for r in rated_items if r.get("rating", 0) >= 7],
        key=lambda r: r["rating"],
        reverse=True,
    )[:6]

    if not high_rated:
        high_rated = sorted(rated_items, key=lambda r: r["rating"], reverse=True)[:3]

    tasks = [get_similar(item["tmdb_id"], item["media_type"]) for item in high_rated]
    results_per_seed = await asyncio.gather(*tasks, return_exceptions=True)

    scored: dict[int, dict] = {}
    for seed_results in results_per_seed:
        if isinstance(seed_results, Exception):
            continue
        for item in seed_results:
            tid = item["tmdb_id"]
            if tid in exclude_ids:
                continue
            if genre_id and genre_id not in item.get("genre_ids", []):
                continue
            if tid in scored:
                scored[tid]["_score"] += 1
            else:
                scored[tid] = {**item, "_score": 1}

    ranked = sorted(scored.values(), key=lambda x: (x["_score"], x.get("vote_average", 0)), reverse=True)
    return ranked[:count]
