"""Settings, read from the environment.

The email allowlist lives here rather than in code because the spec says so:
opening LionsList to another Columbia school should be an environment change
and a redeploy, not a pull request.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Which addresses may create an account -----------------------------
    # Agreed by the team: the university address plus Business, the Medical
    # Center and Teachers College. Note this supersedes the regex in
    # docs/UX_SPEC.md §6.1, which admits @columbia.edu only.
    allowed_email_domains: str = (
        "columbia.edu,gsb.columbia.edu,cumc.columbia.edu,tc.columbia.edu"
    )

    # --- Supabase ----------------------------------------------------------
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""
    supabase_jwt_issuer: str = ""

    # --- Postgres ----------------------------------------------------------
    database_url: str = ""

    # --- CORS: the Vercel domains only, never "*" --------------------------
    cors_origins: str = "http://localhost:3000"

    @property
    def domains(self) -> set[str]:
        return {d.strip().lower() for d in self.allowed_email_domains.split(",") if d.strip()}

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
