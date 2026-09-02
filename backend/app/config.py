"""Application settings, read once from the environment."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./columbia_market.db"
    secret_key: str = "dev-only-change-me"
    frontend_origin: str = "http://localhost:3000"

    # Dev convenience: return the magic link in the response instead of emailing.
    email_dev_mode: bool = True

    # Agreed by the team: the general university address plus Business, the
    # Medical Center and Teachers College. Comma-separated, so opening a fifth
    # school is an environment change and a redeploy, never a code edit.
    allowed_email_domains: str = (
        "columbia.edu,gsb.columbia.edu,cumc.columbia.edu,tc.columbia.edu"
    )

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

    @property
    def allowed_domains_ordered(self) -> tuple[str, ...]:
        """Declaration order, so every message lists them the same way."""
        return tuple(
            d.strip().lower()
            for d in self.allowed_email_domains.split(",")
            if d.strip()
        )

    @property
    def allowed_domains(self) -> frozenset[str]:
        return frozenset(self.allowed_domains_ordered)


settings = Settings()
