"""
This is the core of the app: the `Recommender` class that answers "given a
movie title, what should I watch next?"

It combines two different techniques, and picks whichever one fits the
requested movie best:

1. Content-based filtering: describe each movie as a bag of words built
   from its genres, keywords, top cast, and director (we call this the
   "soup"), then find other movies whose soup is most similar. This works
   for every movie in the dataset, even ones nobody has rated.

2. Collaborative filtering: look at which movies tend to get rated highly
   by the same users ("people who liked X also liked Y"), using a
   technique called ALS (Alternating Least Squares) matrix factorization
   via the `implicit` library. This captures a totally different kind of
   similarity that content alone can't (e.g. Star Wars and Toy Story share
   no genres, but the same people tend to like both) -- but it only works
   for movies that have enough ratings in the data.

`recommend()` below is the hybrid: it uses collaborative filtering when the
movie has enough ratings to trust that signal, and falls back to
content-based similarity otherwise. See
backend/notebooks/01_explore_and_compare.ipynb section 4 for the side-by-side
comparison this design decision is based on.

Data source: this loads a small, precomputed CSV (see
scripts/build_processed_dataset.py) rather than the raw ~230MB Kaggle
dataset -- that script already did the expensive one-time work of parsing
genre/cast/crew data for 45k movies, so this file just reads the result.
"""

from pathlib import Path

import pandas as pd
import scipy.sparse as sp
from implicit.als import AlternatingLeastSquares
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.api.schemas import MovieSummary, Recommendation
from app.core.config import settings
from app.services import tmdb

# A movie needs at least this many ratings in the dataset before we trust
# collaborative filtering for it. Below this, we don't have enough signal
# and fall back to content-based instead.
CF_MIN_RATINGS = 5


class Recommender:
    """Loads the movie data once at startup (see the bottom of this file)
    and answers search/recommend queries against it in memory. One shared
    instance (`recommender`) is used for every request -- see routes.py."""

    def __init__(self, data_dir: str) -> None:
        # Poster URLs are fetched live from TMDb (see tmdb.py) and cached
        # here so we don't re-fetch the same movie's poster on every request.
        self._poster_cache: dict[int, str | None] = {}
        self._load(Path(data_dir))

    def _load(self, data_dir: Path) -> None:
        """One-time setup: read the CSVs, build the lookup tables and the
        two similarity models (content-based and collaborative). This is
        the slow part (a few seconds) and only runs once, when the server
        starts -- not on every request."""

        # --- Movie metadata (title, genres, the "soup" text, etc.) ---
        movies = pd.read_csv(data_dir / "movies_compact.csv")
        # genres was stored as "Animation|Comedy|Family" to keep the CSV
        # simple; turn it back into a real Python list here.
        movies["genre_names"] = movies["genres"].fillna("").apply(
            lambda s: s.split("|") if s else []
        )
        movies["director"] = movies["director"].fillna("")
        movies["soup"] = movies["soup"].fillna("")

        links_small = pd.read_csv(data_dir / "links_small.csv")  # maps MovieLens id <-> TMDb id
        ratings = pd.read_csv(data_dir / "ratings_small.csv")  # who rated what, how highly

        self.movies = movies
        # Fast "title -> row" and "TMDb id -> row" lookups, used everywhere
        # below instead of scanning the whole table each time.
        self.title_to_idx = pd.Series(movies.index, index=movies["title"].str.lower()).drop_duplicates()
        self.id_to_idx = pd.Series(movies.index, index=movies["id"]).drop_duplicates()

        # --- Content-based model ---
        # CountVectorizer turns each movie's "soup" string into a row of
        # word counts (a sparse matrix -- mostly zeros, since any one movie
        # only uses a tiny fraction of the overall vocabulary). Comparing
        # two movies' rows with cosine similarity tells us how much their
        # genres/keywords/cast/director overlap.
        count = CountVectorizer(stop_words="english")
        self.count_matrix = count.fit_transform(movies["soup"])  # sparse, memory-safe

        # --- Collaborative filtering model ---
        # ratings_small.csv uses MovieLens ids, but our movie table is keyed
        # by TMDb id -- translate through links_small first so both sides
        # of everything below speak the same id.
        links_map = links_small.dropna(subset=["tmdbId"]).set_index("movieId")["tmdbId"].astype(int)
        ratings_mapped = ratings.copy()
        ratings_mapped["tmdbId"] = ratings_mapped["movieId"].map(links_map)
        ratings_mapped = ratings_mapped.dropna(subset=["tmdbId"])
        ratings_mapped["tmdbId"] = ratings_mapped["tmdbId"].astype(int)

        # Build a (users x movies) matrix where each cell is that user's
        # rating for that movie (0 if they never rated it). ALS factorizes
        # this matrix to learn a set of "taste dimensions" for every user
        # and movie -- two movies liked by similar users end up with
        # similar vectors, even if they share no genres/cast at all.
        user_cat = ratings_mapped["userId"].astype("category")
        movie_cat = ratings_mapped["tmdbId"].astype("category")
        user_item = sp.csr_matrix(
            (ratings_mapped["rating"], (user_cat.cat.codes, movie_cat.cat.codes))
        )
        self.tmdb_id_categories = movie_cat.cat.categories  # position in the matrix -> TMDb id
        self.tmdb_id_to_inner = {tid: i for i, tid in enumerate(self.tmdb_id_categories)}
        self.rating_counts = ratings_mapped["tmdbId"].value_counts()  # how many ratings each movie has

        self.als = AlternatingLeastSquares(
            factors=50, regularization=0.1, iterations=20, random_state=42
        )
        self.als.fit(user_item)

    def _resolve_poster(self, tmdb_id: int) -> str | None:
        """Get a movie's current poster URL, fetching it from TMDb the
        first time and reusing the cached value after that."""
        # note: the dataset's own `poster_path` column is from 2017 and is
        # largely stale -- TMDb rotates image file hashes when art gets
        # re-uploaded, so we fetch the current poster live instead (cached
        # per process since the catalog doesn't change during a run).
        if tmdb_id in self._poster_cache:
            return self._poster_cache[tmdb_id]
        url = tmdb.get_poster_url(tmdb_id)
        self._poster_cache[tmdb_id] = url
        return url

    def _to_summary(self, idx: int) -> MovieSummary:
        """Turn one row of the movies table (by its row number `idx`)
        into the lightweight object search results are made of."""
        row = self.movies.loc[idx]
        year = int(row["year"]) if pd.notna(row["year"]) else None
        return MovieSummary(
            movie_id=int(row["id"]), title=row["title"], year=year, genres=row["genre_names"]
        )

    def search(self, query: str, limit: int = 10) -> list[MovieSummary]:
        """Find movies whose title contains `query` (case-insensitive),
        most popular (highest vote_count) first. This is plain substring
        matching, not similarity -- it's what powers the autocomplete
        dropdown, so it needs to be fast and predictable."""
        q = query.lower().strip()
        matches = self.movies[self.movies["title"].str.lower().str.contains(q, na=False, regex=False)]
        matches = matches.sort_values("vote_count", ascending=False).head(limit)
        return [self._to_summary(i) for i in matches.index]

    def _content_based_indices(self, idx: int, n: int) -> list[int]:
        """Row numbers of the `n` movies most similar to row `idx` by
        genre/keyword/cast/director overlap.

        Deliberately does NOT precompute a full movie-by-movie similarity
        matrix -- with 45k movies that would be a ~16GB table and crash on
        most laptops. Instead we compare just the one query row against
        every other row, on demand, which only needs a single slice."""
        sims = cosine_similarity(self.count_matrix[idx], self.count_matrix).flatten()
        ranked = sims.argsort()[::-1]  # highest similarity first
        return [i for i in ranked if i != idx][:n]  # drop the movie itself

    def _collaborative_indices(self, tmdb_id: int, n: int) -> list[int]:
        """Row numbers of the `n` movies whose ALS "taste vector" is
        closest to the given movie's -- i.e. movies liked by a similar
        set of users, regardless of genre/cast overlap."""
        inner_id = self.tmdb_id_to_inner[tmdb_id]
        similar_ids, _scores = self.als.similar_items(inner_id, N=n + 1)
        top_tmdb_ids = [
            self.tmdb_id_categories[i] for i in similar_ids if i != inner_id  # drop itself
        ][:n]
        return [self.id_to_idx[tid] for tid in top_tmdb_ids if tid in self.id_to_idx.index]

    def recommend(self, title: str, n: int = 10) -> tuple[str, list[Recommendation]]:
        """The main entry point: given an exact movie title, return which
        method was used and up to `n` ranked recommendations.

        Raises ValueError if the title isn't found (routes.py turns that
        into an HTTP 404)."""
        idx = self.title_to_idx.get(title.lower())
        if idx is None:
            raise ValueError(f"'{title}' not found")

        query_row = self.movies.loc[idx]
        tmdb_id = int(query_row["id"])
        # The hybrid decision: only trust collaborative filtering if this
        # movie has enough ratings behind it (see CF_MIN_RATINGS above).
        has_cf_coverage = (
            tmdb_id in self.tmdb_id_to_inner
            and self.rating_counts.get(tmdb_id, 0) >= CF_MIN_RATINGS
        )

        if has_cf_coverage:
            method = "collaborative filtering"
            indices = self._collaborative_indices(tmdb_id, n)
        else:
            method = "content-based"
            indices = self._content_based_indices(idx, n)

        recommendations = [
            self._build_recommendation(i, query_row, method) for i in indices
        ]
        return method, recommendations

    def _build_recommendation(self, idx: int, query_row: pd.Series, method: str) -> Recommendation:
        """Turn one similar-movie row into a full Recommendation, including
        a plain-English reason explaining why it was picked."""
        row = self.movies.loc[idx]
        year = int(row["year"]) if pd.notna(row["year"]) else None

        if method == "collaborative filtering":
            reason = f"Liked by people who also liked {query_row['title']}"
        else:
            # Best-effort explanation for the content-based case: prefer
            # calling out a shared director, then shared genres, and only
            # fall back to a generic message if neither is available.
            shared_genres = set(row["genre_names"]) & set(query_row["genre_names"])
            if row["director"] and row["director"] == query_row["director"]:
                reason = f"Same director ({row['director']}) as {query_row['title']}"
            elif shared_genres:
                reason = f"Shares {', '.join(sorted(shared_genres))} with {query_row['title']}"
            else:
                reason = f"Similar cast/crew to {query_row['title']}"

        return Recommendation(
            movie_id=int(row["id"]),
            title=row["title"],
            year=year,
            genres=row["genre_names"],
            poster_url=self._resolve_poster(int(row["id"])),
            score=1.0,
            reason=reason,
        )


# A single Recommender is built when this module is first imported (i.e.
# when the server starts) and reused for every request after that --
# rebuilding it per-request would mean re-fitting the ALS model every time,
# which takes several seconds.
recommender = Recommender(settings.movies_data_dir)
