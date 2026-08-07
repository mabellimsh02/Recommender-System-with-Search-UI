"""Thin client for fetching poster art from TMDb."""

import requests

from app.core.config import settings


def get_poster_url(tmdb_id: int) -> str | None:
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
