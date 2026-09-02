"""Sign up, sign in, sign out — UX_SPEC.md §6.1 and §6.2."""

from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session as DbSession

from .. import emails
from ..config import settings
from ..db import get_db
from ..models import User
from ..schemas import LinkSentOut, MeOut, RequestLinkIn, SignupIn, UsernameAvailability
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
from ..services import geo

router = APIRouter(prefix="/auth", tags=["auth"])


def _send_link(user: User, token: str) -> str:
    """In dev we do not send mail — the link is returned and printed.

    Replace the body of this function with a real transactional-email call and
    nothing else in the flow has to change.
    """
    link = f"{settings.frontend_origin}/signin/verify?token={token}"
    if settings.email_dev_mode:
        print(f"[dev] sign-in link for {user.email}: {link}")
    return link


@router.get("/username-available", response_model=UsernameAvailability)
def username_available(username: str, db: DbSession = Depends(get_db)):
    """Powers the live availability check on the sign-up form (states A4–A6)."""
    clean = username.lstrip("@")
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
        raise HTTPException(status.HTTP_409_CONFLICT, "That email already has an account")
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "That username is taken")

    user = User(
        email=payload.email,
        username=payload.username,
        phone=payload.phone or None,  # optional — blank means email-only contact
        nationality=payload.nationality.upper(),
        school=payload.school,
        grade=payload.grade,
        zip_code=payload.zip_code,
        default_radius_mi=settings.default_radius_mi,
    )
    db.add(user)
    db.commit()

    token = issue_login_token(db, user)
    link = _send_link(user, token.token)
    return LinkSentOut(
        sent=True,
        resend_available_in_seconds=settings.login_resend_lock_seconds,
        dev_link=link if settings.email_dev_mode else None,
    )


@router.post("/request-link", response_model=LinkSentOut, status_code=status.HTTP_202_ACCEPTED)
def request_link(payload: RequestLinkIn, db: DbSession = Depends(get_db)):
    email = payload.email.lower()
    if not emails.is_allowed(email):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            emails.rejection_message(),
        )

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        # Deliberately indistinguishable from success: whether an address has an
        # account is not something an unauthenticated caller gets to learn.
        return LinkSentOut(sent=True, resend_available_in_seconds=settings.login_resend_lock_seconds)

    wait = seconds_until_resend(db, user)
    if wait > 0:
        return LinkSentOut(sent=False, resend_available_in_seconds=wait)

    token = issue_login_token(db, user)
    link = _send_link(user, token.token)
    return LinkSentOut(
        sent=True,
        resend_available_in_seconds=settings.login_resend_lock_seconds,
        dev_link=link if settings.email_dev_mode else None,
    )


@router.post("/verify", response_model=MeOut)
def verify(token: str, response: Response, db: DbSession = Depends(get_db)):
    """Opening the link. Single-use, fifteen minutes.

    The two failure modes are reported separately so the UI can show B9
    (expired) or B10 (already used) — both of which offer the same one-tap
    recovery rather than an error page.
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
