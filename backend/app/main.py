"""Columbia Market API.

    uvicorn app.main:app --reload --port 8000

Docs at http://localhost:8000/docs once it is up.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import create_all
from .routers import auth, listings, reference, users

app = FastAPI(
    title="Columbia Market API",
    version="0.1.0",
    description="See docs/UX_SPEC.md for the behaviour this API is meant to serve.",
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
app.include_router(reference.router)


@app.on_event("startup")
def on_startup() -> None:
    # Fine for the pilot. Introduce Alembic before the schema stabilises.
    create_all()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
