"""Columbia Market API.

    uvicorn app.main:app --reload --port 8000

Docs at http://localhost:8000/docs once it is up. Behaviour is specified in
docs/UX_SPEC.md; decisions that changed it are in docs/DECISIONS.md.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .db import create_all
from .routers import auth, insights, listings, photos, reference, users


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Fine for the pilot. Introduce Alembic before the schema stabilises.
    create_all()
    settings.media_dir.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="Columbia Market API",
    version="0.2.0",
    description="A used-goods marketplace for verified Columbia members. See docs/UX_SPEC.md.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,  # the session cookie
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(listings.router)
app.include_router(photos.router)
app.include_router(reference.router)
app.include_router(insights.router)

# Processed photos. Nothing here carries metadata (services/photos.py).
settings.media_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.media_dir), name="media")


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok", "version": app.version}
