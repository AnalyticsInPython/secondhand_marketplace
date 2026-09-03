"""Sessions and magic links — UX_SPEC.md §6.2.

There is no password anywhere in this product. A sign-in is: prove you can open
a Columbia inbox, once, within fifteen minutes.

Tokens and session ids are opaque random strings stored in the database rather
than signed blobs, because both need to be *revocable*: a link must stop working
the instant it is used, and "sign out" must drop the session for good.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session as DbSession

from .config import settings
from .db import get_db
from .enums import UserStatus
from .models import LoginToken, Session, User

SESSION_COOKIE = "cm_session"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    """SQLite hands back naive datetimes; compare in UTC either way."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------- login links


def issue_login_token(db: DbSession, user: User) -> LoginToken:
    token = LoginToken(
        token=secrets.token_urlsafe(32),
        user_id=user.id,
        expires_at=_now() + timedelta(minutes=settings.login_token_ttl_minutes),
    )
    db.add(token)
    db.commit()
    return token


def seconds_until_resend(db: DbSession, user: User) -> int:
    """Resend stays locked for a minute — long enough for the first mail to
    arrive, short enough that a stuck user is not stranded."""
    latest = (
        db.query(LoginToken)
        .filter(LoginToken.user_id == user.id)
        .order_by(LoginToken.created_at.desc())
        .first()
    )
    if latest is None:
        return 0
    elapsed = (_now() - _aware(latest.created_at)).total_seconds()
    return max(0, int(settings.login_resend_lock_seconds - elapsed))


class LinkError(Exception):
    """The ways a link fails, kept apart because the UI says different
    things for each (states B9 and B10)."""

    def __init__(self, reason: str):
        self.reason = reason  # "expired" | "already_used" | "unknown"
        super().__init__(reason)


def consume_login_token(db: DbSession, raw_token: str) -> User:
    token = db.get(LoginToken, raw_token)
    if token is None:
        raise LinkError("unknown")
    if token.used_at is not None:
        raise LinkError("already_used")
    if _aware(token.expires_at) < _now():
        raise LinkError("expired")

    user = db.get(User, token.user_id)
    if user is None:
        raise LinkError("unknown")

    token.used_at = _now()
    user.is_verified = True
    # Deactivation is reversible: signing in with the same Columbia email
    # brings the account back (UX_SPEC.md §6.6).
    user.status = UserStatus.ACTIVE
    db.commit()
    return user


# ---------------------------------------------------------------- sessions


def start_session(db: DbSession, user: User, response: Response) -> Session:
    session = Session(
        id=secrets.token_urlsafe(32),
        user_id=user.id,
        expires_at=_now() + timedelta(days=settings.session_ttl_days),
    )
    db.add(session)
    db.commit()
    response.set_cookie(
        SESSION_COOKIE,
        session.id,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=settings.session_ttl_days * 86400,
        path="/",
    )
    return session


def end_session(db: DbSession, session_id: str | None, response: Response) -> None:
    if session_id:
        existing = db.get(Session, session_id)
        if existing:
            db.delete(existing)
            db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")


# ---------------------------------------------------------------- dependencies


def current_user_optional(
    cm_session: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    db: DbSession = Depends(get_db),
) -> User | None:
    """The viewer, if there is one. Reference endpoints take this; anything
    that shows listings requires `current_user` — there is no browsing
    without an account in the pilot (UX_SPEC.md §6.2)."""
    if not cm_session:
        return None
    session = db.get(Session, cm_session)
    if session is None or _aware(session.expires_at) < _now():
        return None
    user = db.get(User, session.user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        return None
    return user


def current_user(user: User | None = Depends(current_user_optional)) -> User:
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in first")
    return user
