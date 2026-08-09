"""
Precompute a compact, git-friendly dataset from the raw Kaggle "The Movies
Dataset" CSVs.

The raw dataset is ~230MB (credits.csv alone is 184MB, over GitHub's 100MB
file limit) and needs several seconds of ast.literal_eval parsing across 45k
rows on every process start. The recommender only ever needs a handful of
derived columns per movie, so this script builds those once, offline, and
writes a small CSV that the deployed app loads directly -- no Kaggle
credentials or raw dataset needed in production.

This is a one-off/offline script, not something the deployed app runs --
you run it yourself, locally, after downloading the raw dataset, whenever
the derived data needs to be rebuilt (e.g. after a code change to how the
"soup" is built). Its output (backend/data/processed/) is what actually
gets committed to git and deployed.

Usage (from backend/):
    python scripts/build_processed_dataset.py
"""

import ast
from pathlib import Path

import pandas as pd

# Where the raw ~230MB Kaggle download lives locally (gitignored).
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "the-movies-dataset"
# Where this script writes its small, git-tracked output.
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"


def parse_names(cell: str, key: str = "name", top_n: int | None = None) -> list[str]:
    """The raw CSVs store things like genres/cast as a Python-literal
    string, e.g. "[{'id': 16, 'name': 'Animation'}]" -- this turns one of
    those strings into a plain list of names, e.g. ["Animation"].
    `top_n` optionally keeps only the first N (used to grab just the top
    3 billed cast members instead of the entire cast list)."""
    try:
        items = ast.literal_eval(cell)
    except (ValueError, SyntaxError, TypeError):
        return []
    names = [item[key] for item in items]
    return names[:top_n] if top_n else names


def get_director(crew_cell: str) -> str:
    """Same idea as parse_names, but for the crew column: pull out just
    the director's name (crew also includes writers, producers, etc.)."""
    try:
        crew = ast.literal_eval(crew_cell)
    except (ValueError, SyntaxError, TypeError):
        return ""
    for member in crew:
        if member.get("job") == "Director":
            return member["name"]
    return ""


def clean_token(s: str) -> str:
    """Normalize a name/word for the "soup" text: lowercase, no spaces
    (so "Tom Hanks" becomes "tomhanks", one token instead of two -- this
    stops CountVectorizer from treating "Tom" as meaningfully similar to
    every other person also named Tom)."""
    return str(s).lower().replace(" ", "")


def main() -> None:
    # --- Load and clean the core movie metadata ---
    movies = pd.read_csv(RAW_DIR / "movies_metadata.csv", low_memory=False)
    # A handful of rows in the raw CSV have shifted/corrupted columns
    # (their "id" ends up being a date string) -- drop anything where id
    # isn't actually a number.
    movies = movies[pd.to_numeric(movies["id"], errors="coerce").notna()].copy()
    movies["id"] = movies["id"].astype(int)
    movies = movies.drop_duplicates(subset="id")
    movies["vote_count"] = pd.to_numeric(movies["vote_count"], errors="coerce").fillna(0)
    movies["year"] = pd.to_datetime(movies["release_date"], errors="coerce").dt.year

    # keywords.csv and credits.csv both have duplicate `id` rows in the raw
    # dataset (987 and 44 respectively) -- an inner merge without deduping
    # first silently multiplies those movies' rows (cartesian blowup)
    keywords = pd.read_csv(RAW_DIR / "keywords.csv").drop_duplicates(subset="id")
    credits = pd.read_csv(RAW_DIR / "credits.csv").drop_duplicates(subset="id")

    # Bring genres/keywords/cast/crew together into one table, one row per movie.
    movies = movies.merge(keywords, on="id").merge(credits, on="id")
    movies = movies.reset_index(drop=True)

    # Extract the plain-list versions of each field we care about.
    genre_names = movies["genres"].apply(parse_names)
    keyword_names = movies["keywords"].apply(parse_names)
    cast_names = movies["cast"].apply(lambda x: parse_names(x, top_n=3))  # top-3 billed only
    director = movies["crew"].apply(get_director)

    # Build the "soup": one string per movie combining all of its
    # genres/keywords/cast/director, which is what the content-based
    # recommender compares between movies. The director is repeated 3x so
    # it counts for more than any single genre or keyword when computing
    # similarity (two movies by the same director should rank as very
    # similar even if their genres differ a bit).
    soup = pd.Series(
        [
            " ".join(
                [clean_token(g) for g in genres]
                + [clean_token(k) for k in kws]
                + [clean_token(c) for c in cast]
                + [clean_token(d)] * 3  # weight director higher
            )
            for genres, kws, cast, d in zip(genre_names, keyword_names, cast_names, director)
        ]
    )

    # The actual output: only the columns the recommender needs at
    # runtime, nothing else. Genres are joined with "|" so they fit in a
    # single CSV cell (recommender.py splits them back into a list on load).
    compact = pd.DataFrame(
        {
            "id": movies["id"],
            "title": movies["title"],
            "year": movies["year"],
            "genres": genre_names.apply(lambda names: "|".join(names)),
            "director": director,
            "soup": soup,
            "vote_count": movies["vote_count"],
        }
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    compact.to_csv(OUT_DIR / "movies_compact.csv", index=False)

    # ratings_small.csv and links_small.csv are already small (~2.3MB, ~180KB)
    # -- copy as-is so all runtime data lives in one git-tracked directory
    for fname in ["ratings_small.csv", "links_small.csv"]:
        pd.read_csv(RAW_DIR / fname).to_csv(OUT_DIR / fname, index=False)

    print(f"Wrote {len(compact)} movies to {OUT_DIR / 'movies_compact.csv'}")


if __name__ == "__main__":
    main()
