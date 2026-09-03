"""Sign up, sign in, sign out — UX_SPEC.md §6.1 and §6.2."""

from __future__ import annotations

import sys

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session as DbSession

from ..config import settings
from ..db import get_db
from ..models import User
from ..schemas import EmailCheckOut, LinkSentOut, MeOut, RequestLinkIn, SignupIn, UsernameAvailability
from ..security import (
    SESSION_COOKIE,
    LinkError,
    consume_login_token,
    current_user,
    end_session,
    issue_login_token,
    seconds_until_resend,
    start_session,
)
from ..services import domains, geo, mailer

router = APIRouter(prefix="/auth", tags=["auth"])


def _deliver(user: User, token: str) -> LinkSentOut:
    """Hand the link to the mailer. In dev mode it is also returned so the team
    can click through without an inbox."""
    link = f"{settings.frontend_origin}/signin/verify?token={token}"
    try:
        mailer.send_login_link(to=user.email, link=link, username=user.username)
    except mailer.MailError as exc:
        # The user gets a calm message; the operator gets the real reason.
        print(f"[mail] delivery to {user.email} failed: {exc}", file=sys.stderr, flush=True)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "We could not send the email right now. Try again in a minute.",
        ) from exc
    return LinkSentOut(
        sent=True,
        resend_available_in_seconds=settings.login_resend_lock_seconds,
        dev_link=link if settings.email_dev_mode else None,
    )


@router.get("/email-check", response_model=EmailCheckOut)
def email_check(email: str):
    """Live validation for the email field. Says nothing about whether an
    account exists — only whether the address *could* have one."""
    reason = domains.rejection_reason(email)
    return EmailCheckOut(
        email=domains.normalize(email),
        allowed=reason is None,
        reason=reason,
        suggested_school=domains.suggested_school(email),
    )


@router.get("/username-available", response_model=UsernameAvailability)
def username_available(username: str, db: DbSession = Depends(get_db)):
    """Powers the live availability check on the sign-up form (states A4–A6)."""
    clean = username.strip().lstrip("@")
    taken = db.query(User).filter(User.username == clean).first() is not None
    suggestions: list[str] = []
    if taken:
        # Three suggestions, as the design shows — not a generic "try again".
        for candidate in (f"{clean}01", f"{clean}.cu", f"cu_{clean}"):
            if db.query(User).filter(User.username == candidate).first() is None:
                suggestions.append(candidate)
    return UsernameAvailability(username=clean, available=not taken, suggestions=suggestions)


@router.post("/signup", response_model=LinkSentOut, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupIn, db: DbSession = Depends(get_db)):
    if not geo.is_supported(payload.zip_code):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"{payload.zip_code} is not in the New York metro area. "
            "Columbia Market is NYC-only during the pilot.",
        )
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "That email already has an account. Sign in instead.")
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "That username is taken")

    user = User(
        email=payload.email,
        username=payload.username,
        phone=payload.phone,  # None means email-only contact
        nationality=payload.nationality,
        school=payload.school,
        grade=payload.grade,
        zip_code=payload.zip_code,
        default_radius_mi=settings.default_radius_mi,
    )
    db.add(user)
    db.commit()

    token = issue_login_token(db, user)
    return _deliver(user, token.token)


@router.post("/request-link", response_model=LinkSentOut, status_code=status.HTTP_202_ACCEPTED)
def request_link(payload: RequestLinkIn, db: DbSession = Depends(get_db)):
    email = domains.normalize(payload.email)
    reason = domains.rejection_reason(email)
    if reason:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, reason)

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        # Deliberately indistinguishable from success: whether an address has an
        # account is not something an unauthenticated caller gets to learn.
        return LinkSentOut(sent=True, resend_available_in_seconds=settings.login_resend_lock_seconds)

    wait = seconds_until_resend(db, user)
    if wait > 0:
        return LinkSentOut(sent=False, resend_available_in_seconds=wait)

    token = issue_login_token(db, user)
    return _deliver(user, token.token)


@router.post("/verify", response_model=MeOut)
def verify(token: str, response: Response, db: DbSession = Depends(get_db)):
    """Opening the link. Single-use, fifteen minutes.

    The failure modes are reported separately so the UI can show B9 (expired)
    or B10 (already used) — both offer the same one-tap recovery.
    """
    try:
        user = consume_login_token(db, token)
    except LinkError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, exc.reason) from exc

    start_session(db, user, response)
    return MeOut.model_validate(user)


@router.post("/signout", status_code=status.HTTP_204_NO_CONTENT)
def signout(
    response: Response,
    cm_session: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    db: DbSession = Depends(get_db),
):
    end_session(db, cm_session, response)


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(current_user)):
    return MeOut.model_validate(user)
