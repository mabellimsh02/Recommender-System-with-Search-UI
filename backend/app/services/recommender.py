"""
Hybrid movie recommender.

Content-based (genre/keyword/cast/director "soup" + cosine similarity) covers
the full catalog, including movies with no ratings. Collaborative filtering
(ALS on ratings_small.csv via `implicit`) only covers ~9k of the 45k movies
here, but captures "people who liked this also liked" signal content-based
similarity can't. `recommend()` uses CF when the queried movie has enough
rating coverage to trust it, and falls back to content-based otherwise --
see backend/notebooks/01_explore_and_compare.ipynb section 4 for the
comparison this decision is based on.

Loads from a precomputed compact dataset (see scripts/build_processed_dataset.py)
rather than the raw ~230MB Kaggle CSVs -- keeps the deployed app's data
footprint git-friendly and avoids parsing genre/cast/crew strings for 45k
rows on every process start.
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

CF_MIN_RATINGS = 5


class Recommender:
    def __init__(self, data_dir: str) -> None:
        self._poster_cache: dict[int, str | None] = {}
        self._load(Path(data_dir))

    def _load(self, data_dir: Path) -> None:
        movies = pd.read_csv(data_dir / "movies_compact.csv")
        movies["genre_names"] = movies["genres"].fillna("").apply(
            lambda s: s.split("|") if s else []
        )
        movies["director"] = movies["director"].fillna("")
        movies["soup"] = movies["soup"].fillna("")

        links_small = pd.read_csv(data_dir / "links_small.csv")
        ratings = pd.read_csv(data_dir / "ratings_small.csv")

        self.movies = movies
        self.title_to_idx = pd.Series(movies.index, index=movies["title"].str.lower()).drop_duplicates()
        self.id_to_idx = pd.Series(movies.index, index=movies["id"]).drop_duplicates()

        count = CountVectorizer(stop_words="english")
        self.count_matrix = count.fit_transform(movies["soup"])  # sparse, memory-safe

        links_map = links_small.dropna(subset=["tmdbId"]).set_index("movieId")["tmdbId"].astype(int)
        ratings_mapped = ratings.copy()
        ratings_mapped["tmdbId"] = ratings_mapped["movieId"].map(links_map)
        ratings_mapped = ratings_mapped.dropna(subset=["tmdbId"])
        ratings_mapped["tmdbId"] = ratings_mapped["tmdbId"].astype(int)

        user_cat = ratings_mapped["userId"].astype("category")
        movie_cat = ratings_mapped["tmdbId"].astype("category")
        user_item = sp.csr_matrix(
            (ratings_mapped["rating"], (user_cat.cat.codes, movie_cat.cat.codes))
        )
        self.tmdb_id_categories = movie_cat.cat.categories
        self.tmdb_id_to_inner = {tid: i for i, tid in enumerate(self.tmdb_id_categories)}
        self.rating_counts = ratings_mapped["tmdbId"].value_counts()

        self.als = AlternatingLeastSquares(
            factors=50, regularization=0.1, iterations=20, random_state=42
        )
        self.als.fit(user_item)

    def _resolve_poster(self, tmdb_id: int) -> str | None:
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
        row = self.movies.loc[idx]
        year = int(row["year"]) if pd.notna(row["year"]) else None
        return MovieSummary(
            movie_id=int(row["id"]), title=row["title"], year=year, genres=row["genre_names"]
        )

    def search(self, query: str, limit: int = 10) -> list[MovieSummary]:
        q = query.lower().strip()
        matches = self.movies[self.movies["title"].str.lower().str.contains(q, na=False, regex=False)]
        matches = matches.sort_values("vote_count", ascending=False).head(limit)
        return [self._to_summary(i) for i in matches.index]

    def _content_based_indices(self, idx: int, n: int) -> list[int]:
        sims = cosine_similarity(self.count_matrix[idx], self.count_matrix).flatten()
        ranked = sims.argsort()[::-1]
        return [i for i in ranked if i != idx][:n]

    def _collaborative_indices(self, tmdb_id: int, n: int) -> list[int]:
        inner_id = self.tmdb_id_to_inner[tmdb_id]
        similar_ids, _scores = self.als.similar_items(inner_id, N=n + 1)
        top_tmdb_ids = [
            self.tmdb_id_categories[i] for i in similar_ids if i != inner_id
        ][:n]
        return [self.id_to_idx[tid] for tid in top_tmdb_ids if tid in self.id_to_idx.index]

    def recommend(self, title: str, n: int = 10) -> tuple[str, list[Recommendation]]:
        idx = self.title_to_idx.get(title.lower())
        if idx is None:
            raise ValueError(f"'{title}' not found")

        query_row = self.movies.loc[idx]
        tmdb_id = int(query_row["id"])
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
        row = self.movies.loc[idx]
        year = int(row["year"]) if pd.notna(row["year"]) else None

        if method == "collaborative filtering":
            reason = f"Liked by people who also liked {query_row['title']}"
        else:
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


recommender = Recommender(settings.movies_data_dir)
