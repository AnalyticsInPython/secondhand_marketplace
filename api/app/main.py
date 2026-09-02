"""LionsList API.

Every product rule lives in this service. The browser never talks to Postgres
directly, and the Next.js layer holds no logic beyond rendering.

Endpoints are numbered as in build spec section 3. Only the two auth routes
exist so far -- see api/README.md for what is still to come.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth

settings = get_settings()

app = FastAPI(
    title="LionsList API",
    version="0.1.0",
    description="A used-goods marketplace for verified Columbia students.",
)

# The Vercel domains only. Never "*" -- the session cookie rides these calls.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)


@app.get("/health", tags=["ops"])
def health():
    """Render pings this to decide whether a deploy came up."""
    return {"status": "ok"}
