# Recommendation Engine with Search UI

A movie recommender you can actually use: search for a movie you like, and
get back a ranked list of similar movies — each with its poster and a short
plain-English reason it was picked (e.g. "Shares Drama, Foreign with Live-In
Maid" or "Liked by people who also liked Toy Story").

**🎬 Live app**: https://recommender-system-with-search-ui.vercel.app
**⚙️ API**: https://recommender-backend-5trx.onrender.com/docs

> Note: the backend is on Render's free tier, which sleeps after 15 minutes
> with no traffic. If the app feels slow to respond to your first search,
> that's the server waking back up (~30-60s) — normal, not a bug.

## What it does and how

You type a movie title, pick it from a dropdown, and the app shows you 10
similar movies. Under the hood, "similar" is decided one of two ways:

1. **Content-based filtering** — describes each movie as a mix of its
   genres, keywords, top cast, and director, then finds other movies with
   the most overlap. This works for every movie in the dataset, even ones
   nobody has rated.
2. **Collaborative filtering** — looks at which movies tend to get rated
   highly by the *same people* ("people who liked X also liked Y"), using a
   technique called ALS (matrix factorization). This catches similarity
   content alone can't — e.g. Star Wars and Toy Story share no genres, but
   fans of one tend to like the other. It only works for movies with enough
   ratings in the data, though.

The app picks whichever one fits the requested movie: collaborative
filtering when there's enough rating data to trust it, content-based
otherwise. See [Approach](#approach-content-based-vs-collaborative-filtering-vs-hybrid)
below for the full reasoning and evidence behind that choice.

## Tech stack

- **Data**: [The Movies Dataset](https://www.kaggle.com/rounakbanik/the-movies-dataset)
  (Kaggle) — 45,000+ movies with descriptions, genres, keywords, cast/crew,
  plus a set of user ratings (from MovieLens) used for the collaborative
  filtering side.
- **Backend**: [FastAPI](https://fastapi.tiangolo.com/) (Python) — a small
  API with two real endpoints: search for a title, and get recommendations
  for one.
- **Recommender logic**: `scikit-learn` (content-based similarity) +
  `implicit` (collaborative filtering / ALS).
- **Posters**: fetched live from [TMDb's API](https://www.themoviedb.org/documentation/api)
  rather than the dataset's own image links, which turned out to be stale
  (more on that below).
- **Frontend**: React ([Vite](https://vitejs.dev/)) — a search bar with
  autocomplete and a grid of result cards.
- **Hosting**: [Render](https://render.com) for the backend, [Vercel](https://vercel.com)
  for the frontend.

## Project layout

```
backend/
  app/
    main.py          # starts the API, plugs everything together
    api/
      routes.py       # the actual endpoints (/api/search, /api/recommend, /api/health)
      schemas.py       # shapes of the request/response JSON
    core/
      config.py         # settings loaded from environment variables
    services/
      recommender.py    # the recommendation logic itself (the heart of the app)
      tmdb.py             # fetches poster images from TMDb
  scripts/
    build_processed_dataset.py  # turns the raw Kaggle CSVs into the small file the app actually loads
  notebooks/
    01_explore_and_compare.ipynb  # where content-based vs. collaborative filtering was built and compared
  data/
    processed/        # the small, ready-to-use dataset (this is what's committed to git)
  requirements.txt    # Python dependencies
  .env.example         # template for local secrets/config

frontend/
  src/
    App.jsx             # top-level page, holds the app's state
    api.js               # functions that call the backend
    components/
      SearchBar.jsx       # the search box + autocomplete dropdown
      ResultsGrid.jsx      # the grid of recommended movie cards
    index.css             # all the styling
  package.json         # Node dependencies

render.yaml    # tells Render how to deploy the backend
```

Every file above also has its own comments at the top explaining what it
does in more detail — this table of contents is just the map.

## Running it yourself

### 1. Get the data

You'll need a free [Kaggle](https://www.kaggle.com) account and an API
token (**kaggle.com/settings → API → "Create New Token"**).

```bash
cd backend
pip install kaggle
kaggle datasets download -d rounakbanik/the-movies-dataset -p data/the-movies-dataset --unzip
python scripts/build_processed_dataset.py
```

The last command turns the ~230MB raw download into a small ~11MB file at
`backend/data/processed/` — that's the only thing the app actually reads at
runtime, and it's small enough to commit to git (the raw download is not).

### 2. Run the backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit .env and add your TMDb API key
uvicorn app.main:app --reload
```

Get a free TMDb key at [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api)
("Developer" key type). It's required, not optional — the dataset's own
poster links are from 2017 and are almost all stale now (TMDb replaces
poster art over time, which changes the image's URL), so the app fetches
each movie's current poster from TMDb live instead.

Once it's running, interactive API docs are at http://localhost:8000/docs
— you can try the endpoints right there in the browser.

### 3. Run the frontend

Requires [Node.js](https://nodejs.org/).

```bash
cd frontend
npm install
npm run dev
```

Opens at http://localhost:5173. In development it automatically talks to
the backend on port 8000 (see the comment in `vite.config.js` for how).

## Approach: content-based vs. collaborative filtering vs. hybrid

This app takes a **movie title** as input rather than a specific user, so
plain user-based collaborative filtering doesn't quite fit — instead it uses
*item-item* collaborative filtering (which movies get similar ratings
patterns), compared side-by-side against content-based similarity.

The two approaches disagree in a way that's actually informative. For *Toy
Story*:
- **Collaborative filtering** suggests *Star Wars*, *Forrest Gump*, *Jurassic
  Park* — movies frequently rated highly by the same people, even though
  they share no genres with Toy Story.
- **Content-based** suggests *Toy Story 2*, *Tin Toy*, *Cars*, *A Bug's
  Life* — genuinely similar movies (same studio/director/genre), because it
  weights the shared director (John Lasseter) heavily.

The deciding factor for which one to trust: the ratings data only covers
about 9,000 of the dataset's 45,000+ movies. Collaborative filtering simply
can't say anything about a movie with no ratings — a classic "cold start"
problem. Content-based has no such gap, since it only needs a movie's own
description.

**Decision: a hybrid.** The app uses collaborative filtering when a movie
has at least 5 ratings in the data (enough to trust the signal), and falls
back to content-based similarity otherwise. Verified against the live API:
searching *Toy Story* (well-rated) uses collaborative filtering; searching
*Live-In Maid* (an obscure film with zero ratings in the dataset) correctly
falls back to content-based.

**Posters**: the dataset's built-in poster links are stale — I checked 5 of
them and all 5 returned a "not found" error. TMDb's poster images get
replaced over time, invalidating the old links. So instead, the app looks
up each movie's *current* poster from TMDb's API the first time it's
recommended, and remembers it for the rest of that server session (so it's
not re-fetching the same poster on every single request).

## Deployment notes

The backend is deployed on Render, configured entirely through
[`render.yaml`](render.yaml) (a "Blueprint" — Render reads this file and
sets everything up automatically from a fresh GitHub connection). Two
things are set as secrets in Render's dashboard rather than in the file:
`TMDB_API_KEY`, and `CORS_ORIGINS` (which URLs are allowed to call the API
from a browser — set to the Vercel URL below).

The frontend is deployed on Vercel, pointed at the `frontend/` folder of
this repo, with one environment variable: `VITE_API_BASE_URL` set to the
Render backend's URL.

One real bug hit and fixed during deployment: the backend originally
expected `CORS_ORIGINS` as a strict JSON array (e.g. `["url"]`) via the
environment variable — easy to mistype in a plain dashboard text box, and
it crashed the whole app at startup when the JSON didn't parse. Switched it
to a plain comma-separated string instead (see `app/core/config.py`), which
is much harder to get wrong.

## Status

- [x] Project scaffold + FastAPI skeleton
- [x] Content-based recommender (notebook)
- [x] Collaborative filtering recommender (notebook)
- [x] Decide + write up content-based vs. CF vs. hybrid (see Approach above)
- [x] Wire hybrid approach into `app/services/recommender.py`
- [x] TMDb poster integration (live lookup, cached — dataset's own poster paths are stale)
- [x] React search UI wired to live API (search-as-you-type + recommend, verified in browser)
- [x] Deploy backend (Render) + frontend (Vercel) — verified end-to-end in production
