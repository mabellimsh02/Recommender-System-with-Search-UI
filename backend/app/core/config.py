"""
App configuration, loaded from environment variables (and from backend/.env
locally, via `python-dotenv`/pydantic-settings).

Every other file that needs a setting (a URL, a file path, a secret key)
imports the `settings` object at the bottom of this file rather than reading
os.environ directly -- that way there's exactly one place that knows the
env var names and their defaults.

To change a value: either set the environment variable (e.g. on Render's
dashboard) or edit backend/.env locally. Never hardcode secrets like API
keys directly into the code.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # TMDb ("The Movie Database") API is used to fetch current poster art.
    # Get a free key at https://www.themoviedb.org/settings/api
    tmdb_api_key: str = ""
    tmdb_base_url: str = "https://api.themoviedb.org/3"
    tmdb_image_base_url: str = "https://image.tmdb.org/t/p/w342"

    # Folder (relative to backend/) containing the precomputed movie data
    # this app loads at startup -- see scripts/build_processed_dataset.py.
    movies_data_dir: str = "data/processed"

    # Which frontend URLs are allowed to call this API from a browser.
    # Locally this is the Vite dev server; in production it should be set
    # (via the CORS_ORIGINS env var) to the deployed frontend's URL.
    #
    # Stored as a plain comma-separated string (e.g.
    # "http://localhost:5173,https://your-app.vercel.app") rather than a
    # list, because a list field here would require the env var to be
    # strict JSON (e.g. '["http://localhost:5173"]') -- easy to type
    # wrong in a dashboard text box (missing quotes/brackets), and it
    # fails loudly at startup if you do. A comma-separated string is much
    # harder to get wrong. See the cors_origins_list property below.
    cors_origins: str = "http://localhost:5173"

    class Config:
        # When running locally, also read variables from this file.
        env_file = ".env"

    @property
    def cors_origins_list(self) -> list[str]:
        """The parsed, whitespace-trimmed list of allowed origins --
        what CORSMiddleware in app/main.py actually needs."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


# A single shared instance, imported everywhere else in the app.
settings = Settings()
