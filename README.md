# FilmRec

A personal movie and TV recommendation app: rate what you've watched, build a watchlist, and get picks tailored to your taste. Data comes from [TMDB](https://www.themoviedb.org).

```
frontend/index.html   Single-page app (React via CDN, no build step)
backend/app/          FastAPI backend — serves the API and the frontend itself
```

## Running it locally

1. **Get a TMDB API key** (free): create an account at [themoviedb.org](https://www.themoviedb.org), then generate one under Settings → API.

2. **Set up the backend:**

   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env
   ```

   Open `.env` and paste your TMDB key into `TMDB_API_KEY`. Also swap `JWT_SECRET` for any random string.

3. **Run the server:**

   ```bash
   uvicorn app.main:app --reload
   ```

4. Open **http://localhost:8000** — the backend serves the frontend too, so that's the only URL you need. Sign up for an account (it's a real local account, stored in `backend/filmrec.db`; no email actually gets sent) and start browsing.

Ratings, watchlist, and account data persist in a local SQLite file (`backend/filmrec.db`) — delete it to start fresh.
