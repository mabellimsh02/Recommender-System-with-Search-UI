"""
Request/response shapes for the API, defined as Pydantic models.

FastAPI uses these to: validate incoming data, convert Python objects to
JSON automatically, and generate the interactive API docs at /docs. Think
of each class below as "what a JSON object for X looks like" -- the field
names and types here are exactly what the frontend sees in the response.
"""

from pydantic import BaseModel


class MovieSummary(BaseModel):
    """One row in a search-results dropdown (title + year + genres only,
    no poster or recommendation reason -- those are only computed for
    full recommendations, not for every search suggestion)."""

    movie_id: int
    title: str
    year: int | None = None
    genres: list[str] = []


class SearchResult(BaseModel):
    """What GET /api/search returns: a list of matching movies."""

    results: list[MovieSummary]


class Recommendation(BaseModel):
    """One recommended movie, including its poster and a human-readable
    reason it was picked (e.g. "Shares Drama with Toy Story")."""

    movie_id: int
    title: str
    year: int | None = None
    genres: list[str] = []
    poster_url: str | None = None  # None if no poster could be found
    score: float
    reason: str


class RecommendResponse(BaseModel):
    """What GET /api/recommend returns: the movie that was searched for,
    which recommendation method was used ("content-based" or
    "collaborative filtering" -- see recommender.py), and the ranked
    list of recommendations."""

    query_title: str
    method: str
    recommendations: list[Recommendation]
