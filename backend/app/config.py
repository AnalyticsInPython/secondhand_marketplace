"""Application settings, read once from the environment.

Everything has a working default for local development. Copy `.env.example`
to `.env` (in `backend/`) to override anything.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    # Anchored to backend/ so the same file is found no matter where uvicorn,
    # the seed script or pytest is launched from.
    database_url: str = f"sqlite:///{BACKEND_DIR / 'columbia_market.db'}"

    # Where the Next.js app runs (CORS + sign-in links) and where this API is
    # reachable (absolute photo URLs).
    frontend_origin: str = "http://localhost:3000"
    public_origin: str = "http://localhost:8000"
    cookie_secure: bool = False  # True behind HTTPS

    # ---- Membership rule. Everything about the product depends on this line.
    # The four domains agreed by the team on 2026-09-02 (docs/DECISIONS.md).
    # Comma-separated so a fifth school is an environment change, not a deploy.
    allowed_email_domains: str = "columbia.edu,gsb.columbia.edu,cumc.columbia.edu,tc.columbia.edu"

    @property
    def domains(self) -> frozenset[str]:
        return frozenset(d.strip().lower() for d in self.allowed_email_domains.split(",") if d.strip())

    # ---- Email. `console` prints the link, `resend` uses the Resend HTTP API,
    # `smtp` uses any SMTP relay. `email_dev_mode` additionally returns the
    # link in API responses so the team can click through without an inbox —
    # never enable that in production.
    email_backend: str = "console"
    email_dev_mode: bool = True
    email_from: str = "Columbia Market <no-reply@columbiamarket.app>"
    resend_api_key: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = True

    # ---- Sign-in (UX_SPEC.md §6.2)
    login_token_ttl_minutes: int = 15
    login_resend_lock_seconds: int = 60
    session_ttl_days: int = 30

    # ---- Distance (UX_SPEC.md §5.2)
    default_radius_mi: float = 2.5
    min_radius_mi: float = 0.5
    max_radius_mi: float = 10.0
    radius_steps_mi: list[float] = [0.5, 1, 2.5, 5, 10]

    # ---- Photos (UX_SPEC.md §4.3)
    max_photos_per_listing: int = 10
    max_photo_bytes: int = 10 * 1024 * 1024
    photo_max_edge_px: int = 1600
    photo_quality: int = 82
    media_dir: Path = BACKEND_DIR / "media"

    # ---- Abuse limits
    enquiries_per_hour: int = 30

    # ---- Research. When on, half of feed impressions hide badges and the
    # choice is recorded on every listing_views row (analytics Q1).
    badge_experiment_enabled: bool = False


settings = Settings()
