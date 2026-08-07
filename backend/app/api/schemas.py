from pydantic import BaseModel


class MovieSummary(BaseModel):
    movie_id: int
    title: str
    year: int | None = None
    genres: list[str] = []


class SearchResult(BaseModel):
    results: list[MovieSummary]


class Recommendation(BaseModel):
    movie_id: int
    title: str
    year: int | None = None
    genres: list[str] = []
    poster_url: str | None = None
    score: float
    reason: str


class RecommendResponse(BaseModel):
    query_title: str
    method: str
    recommendations: list[Recommendation]
