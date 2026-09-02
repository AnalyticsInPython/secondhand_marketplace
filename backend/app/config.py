"""Application settings, read once from the environment."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./columbia_market.db"
    secret_key: str = "dev-only-change-me"
    frontend_origin: str = "http://localhost:3000"

    # Dev convenience: return the magic link in the response instead of emailing.
    email_dev_mode: bool = True

    allowed_email_domain: str = "columbia.edu"

    # UX_SPEC.md §6.2
    login_token_ttl_minutes: int = 15
    login_resend_lock_seconds: int = 60
    session_ttl_days: int = 30

    # UX_SPEC.md §5.2
    default_radius_mi: float = 2.5
    max_radius_mi: float = 10.0
    min_radius_mi: float = 0.5

    # UX_SPEC.md §4.3
    max_photos_per_listing: int = 10
    max_photo_bytes: int = 10 * 1024 * 1024


settings = Settings()
