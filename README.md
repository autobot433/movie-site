# FilmRec

A personal movie and TV recommendation app: rate what you've watched, build a watchlist, and get picks tailored to your taste. Data comes from [TMDB](https://www.themoviedb.org).

```
frontend/index.html        Single-page app (React via CDN, no build step)
backend/app/main.py        FastAPI entrypoint
backend/app/services/tmdb.py   TMDB API client
```

The backend also expects `app/core/{config,database,limiter}.py` and `app/api/{auth,recommendations,ratings,watchlist,profile,search}.py`, which aren't in this repo yet — `main.py` won't import until those exist.
