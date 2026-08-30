# FilmRec

A personal movie and TV recommendation app: rate what you've watched, build a watchlist, and get picks tailored to your taste. Data comes from [TMDB](https://www.themoviedb.org).

```
public/index.html   Single-page app (React via CDN, no build step)
backend/app/         FastAPI backend — serves the API and the frontend itself
api/index.py         Entrypoint used only when deploying to Vercel
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

**1. Create a free Postgres database** at [neon.com](https://neon.com) (sign up, create a project). On the connection string screen, use the **pooled** connection option (toggle it on, or pick the host with `-pooler` in the name) — this matters for a serverless deploy, where many function instances can each open a connection at once; the pooled endpoint handles that, a direct one would run out of connections. It looks like:
```
postgresql://user:password@ep-something-pooler.neon.tech/dbname?sslmode=require
```
Change `postgresql://` to `postgresql+asyncpg://` at the start — that's the `DATABASE_URL` value you'll use below.

**2. Deploy on [Vercel](https://vercel.com), free, no sleep:**
- Sign up, connect your GitHub, **Add New → Project**, pick this repo
- Vercel should auto-detect it (via `vercel.json` and `api/index.py`) — no build settings to change
- Add three environment variables when prompted:
  - `TMDB_API_KEY` — your TMDB key
  - `DATABASE_URL` — the pooled Neon string from step 1 (with `+asyncpg`)
  - `JWT_SECRET` — any random string you make up
- Deploy. You'll get a URL like `https://filmrec.vercel.app` — that's the live site, and it never sleeps (each visit runs a fresh lightweight function instead of waking up a napping server).

This repo also has a `render.yaml` for [Render](https://render.com) as an alternative if Vercel ever gives you trouble — same Neon database works there too, just use the direct (non-pooled) connection string instead since Render runs one long-lived process rather than serverless functions. Render's free plan does sleep after 15 minutes idle, unlike Vercel.

**Heads up on this first deploy:** this Vercel setup is prepared based on their current documented conventions, but wasn't tested against a live Vercel deployment (no account access from where this was built). If the build log shows an error, paste it back and it'll get fixed fast — first-deploy hiccups here are normal and quick to resolve, not a sign anything is fundamentally wrong.
