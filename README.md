# Recommendation Engine with Search UI

A movie recommender: search for a title you like, get back a ranked list of
similar movies with poster art and a short explanation of why each was picked.

## Stack

- **Data**: [The Movies Dataset](https://www.kaggle.com/rounakbanik/the-movies-dataset) (Kaggle) — 45k movies with overview/genres/keywords/cast/crew, plus MovieLens-derived ratings for collaborative filtering. Poster art is fetched live from the [TMDb API](https://www.themoviedb.org/documentation/api) rather than the dataset's own `poster_path` column — see the poster note in Approach below
- **Backend**: FastAPI serving search + recommend endpoints
- **Recommenders**: hybrid of content-based (CountVectorizer + cosine similarity over a genre/keyword/cast/director "soup") and collaborative filtering (ALS matrix factorization via `implicit`) — see [Approach](#approach-content-based-vs-collaborative-filtering-vs-hybrid) below
- **Frontend**: React (Vite) with a search bar and results grid

## Project layout

```
backend/
  app/
    api/          # routes, request/response schemas
    core/          # config (env vars, settings)
    services/      # recommender logic, TMDb client
    main.py        # FastAPI app entrypoint
  notebooks/       # exploration: build + evaluate content-based vs CF
  data/            # dataset CSVs go here (gitignored)
  requirements.txt
  .env.example
frontend/
  src/
    components/    # SearchBar, ResultsGrid
    App.jsx
    api.js         # fetch wrappers for the backend API
  package.json
```

## Setup

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your TMDb API key -- required, see note below
uvicorn app.main:app --reload
```

Get a free TMDb API key at [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api)
(request the "Developer" key type) and set `TMDB_API_KEY` in `.env`. It's
required, not optional: the dataset's own `poster_path` values are from 2017
and are mostly stale now (TMDb rotates image file hashes when poster art gets
re-uploaded — verified 0/5 dataset poster URLs still resolve), so posters are
fetched live from TMDb instead and cached in memory per process.

API docs at http://localhost:8000/docs.

### Data

Requires a free [Kaggle](https://www.kaggle.com) account and an API token
(kaggle.com/settings → API → "Create New Token").

```bash
cd backend
pip install kaggle
kaggle datasets download -d rounakbanik/the-movies-dataset -p data/the-movies-dataset --unzip
```

`backend/notebooks/01_explore_and_compare.ipynb` builds and evaluates both
recommenders against this dataset; `backend/app/services/recommender.py` has
the hybrid approach ported from it and wired into the API.

### Frontend

Requires Node.js (not currently installed on this machine — `brew install node`
or use nvm).

```bash
cd frontend
npm install
npm run dev
```

Runs at http://localhost:5173 and proxies `/api` requests to the backend on
port 8000 (see `vite.config.js`).

## Approach: content-based vs. collaborative filtering vs. hybrid

This app takes a **title** as input rather than a user id, so pure user-based
CF isn't a natural fit — item-item CF (similarity between the learned latent
item vectors) is used instead, alongside content-based item-item similarity.

The two approaches disagree in an instructive way. For *Toy Story*, CF
surfaces *Star Wars*, *Forrest Gump*, *Jurassic Park* — movies frequently
rated highly by the same users, not thematically similar films. Content-based
surfaces *Toy Story 2*, *Tin Toy*, *Cars*, *A Bug's Life* — actually similar
movies by genre/cast/director, since it weights the shared director
(John Lasseter) heavily.

The deciding constraint: `ratings_small.csv` only covers ~9k of the dataset's
45k movies (671 users), so CF alone can't recommend for most of the catalog —
a hard cold-start gap. Content-based has no such gap since it only needs the
movie's own metadata.

**Decision: hybrid.** `recommend()` in `app/services/recommender.py` uses
collaborative filtering when the queried movie has at least 5 ratings in the
dataset (trustworthy CF signal), and falls back to content-based similarity
otherwise. Verified against the live API: *Toy Story* (well-rated) → CF path;
*Live-In Maid* (zero ratings) → content-based path, correctly.

**Poster art**: the dataset's `poster_path` column is stale (2017 snapshot),
so `Recommender._resolve_poster()` fetches the current poster from the TMDb
API per movie instead, caching results in memory. Verified end-to-end in a
real browser: search-as-you-type against `/api/search`, select a title, and
all 10 recommendation posters render correctly.

## Status

- [x] Project scaffold + FastAPI skeleton
- [x] Content-based recommender (notebook)
- [x] Collaborative filtering recommender (notebook)
- [x] Decide + write up content-based vs. CF vs. hybrid in this README
- [x] Wire hybrid approach into `app/services/recommender.py`
- [x] TMDb poster integration (live lookup, cached — dataset's own poster paths are stale)
- [x] React search UI wired to live API (search-as-you-type + recommend, verified in browser)
- [ ] Deploy backend + frontend
