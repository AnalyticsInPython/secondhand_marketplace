"""Test harness.

Settings are read once at import, so the environment is pinned *before* the
app is imported: a throwaway SQLite file, the console mailer (the link comes
back in the response), and a scratch media directory. Every test starts from an
empty schema.
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="columbia-market-tests-"))
os.environ.update(
    {
        "DATABASE_URL": f"sqlite:///{_TMP / 'test.db'}",
        "EMAIL_BACKEND": "console",
        "EMAIL_DEV_MODE": "true",
        "MEDIA_DIR": str(_TMP / "media"),
        "BADGE_EXPERIMENT_ENABLED": "false",
        "ALLOWED_EMAIL_DOMAINS": "columbia.edu,gsb.columbia.edu,cumc.columbia.edu,tc.columbia.edu",
        "PUBLIC_ORIGIN": "http://testserver",
    }
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app.db import SessionLocal, reset_all  # noqa: E402
from app.main import app  # noqa: E402
from app.models import LoginToken, User  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    reset_all()
    yield


def make_client() -> TestClient:
    """A browser: its own cookie jar."""
    return TestClient(app, base_url="http://testserver")


@pytest.fixture
def client() -> TestClient:
    return make_client()


# ---------------------------------------------------------------- helpers


def _default_username(email: str) -> str:
    local = email.split("@")[0].replace(".", "_")
    return (local if len(local) >= 3 else f"{local}_user")[:20]


def signup(client: TestClient, email: str, **attrs) -> dict:
    """Sign up, open the link, come back signed in. Returns the /auth/me payload."""
    payload = {
        "email": email,
        "username": attrs.pop("username", _default_username(email)),
        "nationality": "US",
        "school": "cbs",
        "grade": "graduate",
        "zip_code": "10027",
    }
    payload.update(attrs)
    r = client.post("/auth/signup", json=payload)
    assert r.status_code == 201, r.text
    token = r.json()["dev_link"].split("token=")[1]
    r = client.post(f"/auth/verify?token={token}")
    assert r.status_code == 200, r.text
    return r.json()


def png_bytes(width: int = 800, height: int = 600, mode: str = "RGB", fmt: str = "PNG", exif: bool = False) -> bytes:
    img = Image.new(mode, (width, height), (30, 80, 150) if mode == "RGB" else (30, 80, 150, 128))
    buf = BytesIO()
    kwargs = {}
    if exif:
        ex = Image.Exif()
        ex[0x010F] = "TestPhone"  # Make
        ex[0x0112] = 6  # Orientation: rotate 90
        kwargs["exif"] = ex.tobytes()
    img.save(buf, fmt, **kwargs)
    return buf.getvalue()


def upload_photo(client: TestClient, data: bytes | None = None, name: str = "photo.png") -> str:
    r = client.post("/photos", files={"file": (name, data or png_bytes(), "image/png")})
    assert r.status_code == 201, r.text
    return r.json()["url"]


def post_listing(client: TestClient, **overrides) -> dict:
    body = {
        "title": "IKEA MALM desk",
        "description": "Solid, no wobble.",
        "category": "furniture",
        "subcategory": "desks",
        "condition": "used_good",
        "price_cents": 6000,
        "is_free": False,
        "is_negotiable": True,
        "zip_code": "10027",
    }
    body.update(overrides)
    if "photo_urls" not in body:
        body["photo_urls"] = [upload_photo(client)]
    r = client.post("/listings", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def backdate_login_tokens(email: str, minutes: int = 5) -> None:
    """Move a member's login tokens into the past so the resend lock has expired."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).one()
        for token in db.query(LoginToken).filter(LoginToken.user_id == user.id):
            token.created_at = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        db.commit()
    finally:
        db.close()


def expire_login_tokens(email: str) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).one()
        for token in db.query(LoginToken).filter(LoginToken.user_id == user.id):
            token.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
    finally:
        db.close()
