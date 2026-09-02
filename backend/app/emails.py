"""Which email addresses may use Columbia Market.

The rule lives here and nowhere else. Sign-up (`schemas.py`) and sign-in
(`routers/auth.py`) both call it, and `/reference/enums` publishes the list so
the frontend validates against exactly what the API enforces.

The pilot admits four domains — see `ALLOWED_EMAIL_DOMAINS` in `.env.example`.
Adding a fifth school is an environment change and a redeploy, not an edit to
this file.

Matching is on the **whole** domain, never a suffix. `endswith("@columbia.edu")`
would reject `@gsb.columbia.edu` while quietly admitting nothing it should not;
worse, a suffix test against a bare `columbia.edu` would admit
`@evil-columbia.edu`. Compare the full domain and the question does not arise.
"""

from __future__ import annotations

from .config import settings


def domain_of(email: str) -> str:
    """The domain half, lowercased. Empty string when there isn't exactly one."""
    parts = (email or "").strip().lower().split("@")
    return parts[1] if len(parts) == 2 and parts[0] else ""


def is_allowed(email: str) -> bool:
    return domain_of(email) in settings.allowed_domains


def allowed_list() -> str:
    """`@a, @b, @c` — for error copy."""
    return ", ".join("@" + d for d in settings.allowed_domains_ordered)


def rejection_message() -> str:
    """One wording for both call sites; the UI copy mirrors it."""
    return f"Columbia Market is open to {allowed_list()} addresses."
