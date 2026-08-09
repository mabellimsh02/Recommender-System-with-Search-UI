"""
Entry point for the backend API.

This is the file `uvicorn` actually runs (see the start command in
render.yaml: `uvicorn app.main:app`). It creates the FastAPI application,
turns on CORS so the separately-hosted frontend is allowed to call this
API from the browser, and plugs in all the routes defined in
app/api/routes.py under the "/api" prefix (e.g. "/api/health").
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings

app = FastAPI(title="Movie Recommendation Engine")

# Browsers block cross-origin requests by default. The frontend runs on a
# different domain/port than this API (e.g. localhost:5173 vs 8000, or
# vercel.app vs onrender.com in production), so without this the frontend's
# fetch() calls would be silently rejected by the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

# All endpoints (search, recommend, health) live under /api -- see routes.py.
app.include_router(router, prefix="/api")
