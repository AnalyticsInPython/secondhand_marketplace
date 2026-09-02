"""The Columbia domain check.

This is the first of the two gates in spec step 03. It exists to produce a
clear error message before any email is sent. It is NOT the real gate -- the
`before-user-created` hook in Supabase is, because nothing that reaches the
database should be able to create a non-Columbia account whatever the app
layer does.

Keep the two in step. If you change the allowlist here, change the hook.
"""

import re

from app.enums import SUBDOMAIN_TO_COLLEGE, College

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def normalize(raw: str | None) -> str:
    return (raw or "").strip().lower()


def domain_of(email: str) -> str:
    return email.rsplit("@", 1)[-1] if "@" in email else ""


def rejection_reason(email: str, allowed: set[str]) -> str | None:
    """Return a message to show the student, or None if the address is fine."""
    if not email:
        return "Enter your Columbia email address."
    if not EMAIL_RE.match(email):
        return "That does not look like a valid email address."
    if domain_of(email) not in allowed:
        pretty = ", ".join("@" + d for d in sorted(allowed))
        return (
            "LionsList is open to Columbia students only. "
            f"Sign in with an address at {pretty}."
        )
    return None


def college_from_email(email: str) -> College | None:
    """Prefill for the onboarding dropdown, where the subdomain is unambiguous.

    Returns None for plain @columbia.edu -- that address says nothing about
    which school the student is at, so they pick it themselves.
    """
    return SUBDOMAIN_TO_COLLEGE.get(domain_of(email))
