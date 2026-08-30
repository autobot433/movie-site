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

## Deploying it publicly

The local setup uses SQLite, which doesn't survive on most hosting platforms (the disk resets on restart). For a real deployment, point `DATABASE_URL` at a Postgres database instead — the code supports both without any changes.

**1. Create a free Postgres database** at [neon.com](https://neon.com) (sign up, create a project, copy the connection string). It'll look like:
```
postgresql://user:password@ep-something.neon.tech/dbname?sslmode=require
```
Change `postgresql://` to `postgresql+asyncpg://` at the start — that's the `DATABASE_URL` value you'll use.

**2. Deploy the backend on [Render](https://render.com), on the free plan:**
- New → Blueprint → connect this GitHub repo
- Render reads `render.yaml` and pre-fills everything (free plan, root directory `backend`, build/start commands, Python version) — nothing to configure by hand
- When prompted for environment variables, set:
  - `TMDB_API_KEY` — your TMDB key
  - `DATABASE_URL` — the Neon connection string from step 1 (with `+asyncpg`)
  - `JWT_SECRET` — Render auto-generates this one, no action needed
- Deploy. Render gives you a URL like `https://filmrec.onrender.com` — that's the live site.

**The tradeoff of $0:** Render's free tier spins the server down after 15 minutes with no traffic. The next visit after that wakes it back up, which takes 30–50 seconds before the page loads — after that it's instant again until it goes idle once more. There's no free way around this; it's the one real cost of not paying anything.
