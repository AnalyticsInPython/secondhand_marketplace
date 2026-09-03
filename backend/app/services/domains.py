"""Membership rule — which addresses may sign in.

Four domains, agreed by the team on 2026-09-02 (docs/DECISIONS.md), held in
`ALLOWED_EMAIL_DOMAINS` rather than in code so a fifth school is an environment
change. The match is exact on the domain part: `columbia.edu.evil.com` and
`law.columbia.edu` are both refused.

This is the only place the rule lives. Sign-up (schemas.py), sign-in
(routers/auth.py) and the live email check all call it, and /reference/enums
publishes the list so the frontend validates against exactly what is enforced.
"""

from __future__ import annotations

from ..config import settings
from ..enums import School

# Which school an email subdomain proves. Used to prefill the dropdown at
# sign-up where it is unambiguous; the student can still change it.
# `columbia.edu` (every school issues these) and `cumc.columbia.edu` (VP&S,
# Mailman, Nursing and Dental alike) deliberately prefill nothing.
SUBDOMAIN_TO_SCHOOL: dict[str, School] = {
    "gsb.columbia.edu": School.CBS,
    "tc.columbia.edu": School.TEACHERS_COLLEGE,
}


def normalize(email: str) -> str:
    return email.strip().lower()


def domain_of(email: str) -> str | None:
    email = normalize(email)
    if email.count("@") != 1:
        return None
    local, domain = email.split("@")
    if not local or not domain:
        return None
    return domain


def allowed_domains() -> frozenset[str]:
    return settings.domains


def is_allowed(email: str, domains: frozenset[str] | None = None) -> bool:
    domain = domain_of(email)
    return domain is not None and domain in (domains or allowed_domains())


def rejection_reason(email: str, domains: frozenset[str] | None = None) -> str | None:
    """None when the address may sign in; otherwise the message to show."""
    if is_allowed(email, domains):
        return None
    if domain_of(email) is None:
        return "Enter a full email address."
    ordered = sorted(domains) if domains is not None else settings.domains_ordered
    listed = ", ".join("@" + d for d in ordered)
    # Mirrored verbatim by EMAIL_REJECTION in frontend/lib/domains.ts.
    return f"Columbia Market is open to {listed} addresses."


def suggested_school(email: str) -> School | None:
    return SUBDOMAIN_TO_SCHOOL.get(domain_of(email) or "")
