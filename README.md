# FilmRec

FilmRec is a full-stack movie and TV recommendation app. Users can create an account, search for movies and shows, rate what they have watched, build a watchlist, and get personalized recommendations using TMDB data.

Live site: https://movie-site-mu-ruby.vercel.app

## Features

- Search for movies and TV shows
- Create an account and log in
- Rate watched titles
- Save movies and shows to a watchlist
- Get personalized recommendations
- View posters, genres, release dates, and descriptions

## Tech Stack

- Frontend: HTML, CSS, JavaScript, React
- Backend: Python, FastAPI
- Database: SQLite locally, PostgreSQL in production
- Authentication: JWT
- API: TMDB API
- Deployment: Vercel

## Project Structure

```text
public/index.html       Frontend single-page app
backend/app/            FastAPI backend
backend/app/api/        API routes
backend/app/services/   TMDB data and recommendation logic
backend/app/core/       Config, database, security, and rate limiting
api/index.py            Vercel entrypoint
```

## Running Locally

Clone the repository:

```bash
git clone https://github.com/autobot433/movie-site.git
cd movie-site
```

Set up the backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add your environment variables to `backend/.env`:

```env
TMDB_API_KEY=your_tmdb_api_key
JWT_SECRET=your_random_secret
DATABASE_URL=sqlite+aiosqlite:///./filmrec.db
```

Run the app:

```bash
uvicorn app.main:app --reload
```

Then open:

```text
http://localhost:8000
```

## Environment Variables

This project uses the following environment variables:

- `TMDB_API_KEY`
- `JWT_SECRET`
- `DATABASE_URL`

## Credits

Movie and TV data is provided by [TMDB](https://www.themoviedb.org/).
