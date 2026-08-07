from fastapi import APIRouter, HTTPException, Query

from app.api.schemas import RecommendResponse, SearchResult
from app.services.recommender import recommender

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/search", response_model=SearchResult)
def search(q: str = Query(..., min_length=1)) -> SearchResult:
    results = recommender.search(q)
    return SearchResult(results=results)


@router.get("/recommend", response_model=RecommendResponse)
def recommend(title: str, n: int = 10) -> RecommendResponse:
    try:
        method, recs = recommender.recommend(title, n)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RecommendResponse(query_title=title, method=method, recommendations=recs)
