"""
The three HTTP endpoints this API exposes, all mounted under "/api" (see
app/main.py). This file is intentionally thin -- it just parses the
request, calls into `recommender` (app/services/recommender.py) to do the
actual work, and shapes the result into the response models from
schemas.py. All the real logic (search matching, content-based vs.
collaborative filtering) lives in the recommender, not here.
"""

from fastapi import APIRouter, HTTPException, Query

from app.api.schemas import RecommendResponse, SearchResult
from app.services.recommender import recommender

router = APIRouter()


@router.get("/health")
def health() -> dict:
    """Simple uptime check -- used by Render to confirm the server is
    alive and ready to take traffic (see healthCheckPath in render.yaml)."""
    return {"status": "ok"}


@router.get("/search", response_model=SearchResult)
def search(q: str = Query(..., min_length=1)) -> SearchResult:
    """GET /api/search?q=toy -> movies whose title contains "toy", most
    popular first. Powers the autocomplete dropdown in the search bar."""
    results = recommender.search(q)
    return SearchResult(results=results)


@router.get("/recommend", response_model=RecommendResponse)
def recommend(title: str, n: int = 10) -> RecommendResponse:
    """GET /api/recommend?title=Toy Story -> up to `n` similar movies.
    `title` must match a movie exactly (case-insensitive) -- the frontend
    gets this from a search suggestion the user clicked, not raw typed
    text. Returns 404 if the title isn't in the dataset."""
    try:
        method, recs = recommender.recommend(title, n)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RecommendResponse(query_title=title, method=method, recommendations=recs)
