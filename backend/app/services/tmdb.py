"""
Small helper for fetching a movie's current poster image from the TMDb API.

Why this exists instead of just using the poster path from the Kaggle
dataset: the dataset is from 2017 and its poster_path values are mostly
stale (TMDb replaces poster art over time, which changes the image file's
URL). Fetching live from TMDb's API gets the poster that's actually online
right now. Called from recommender.py, which also caches the result so we
don't re-fetch the same movie's poster on every request.
"""

import requests

from app.core.config import settings


def get_poster_url(tmdb_id: int) -> str | None:
    """Look up one movie's current poster URL by its TMDb id.

    Returns None (never raises) if no API key is configured, the movie
    has no poster, or the request fails for any reason -- a missing
    poster shouldn't ever break the recommend/search endpoints, it should
    just mean the frontend shows a placeholder instead of an image.
    """
    if not settings.tmdb_api_key:
        return None

    try:
        resp = requests.get(
            f"{settings.tmdb_base_url}/movie/{tmdb_id}",
            params={"api_key": settings.tmdb_api_key},
            timeout=5,
        )
        resp.raise_for_status()
        poster_path = resp.json().get("poster_path")
    except requests.RequestException:
        return None
    return f"{settings.tmdb_image_base_url}{poster_path}" if poster_path else None
