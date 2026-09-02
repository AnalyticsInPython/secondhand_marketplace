"""Endpoints 1 and 3 from spec section 3: the magic-link request and sign-out.

There is one sign-in path and it is the same for everyone. A student who has
never been here and a student who signs in daily both type an address and get
a link. Nothing in the response distinguishes them, so nothing here reveals
whether an address already has an account.

Endpoint 2 (/auth/callback) is a Next.js route, not one of ours: it trades the
link code for a session cookie in the browser.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.domains import normalize, rejection_reason

router = APIRouter(prefix="/v1/auth", tags=["auth"])


class MagicLinkRequest(BaseModel):
    email: str = Field(..., max_length=254)


class MagicLinkResponse(BaseModel):
    # Deliberately says nothing about whether the account existed.
    message: str = "Check your inbox for a sign-in link."


@router.post("/magic-link", response_model=MagicLinkResponse)
def request_magic_link(
    body: MagicLinkRequest,
    settings: Settings = Depends(get_settings),
):
    """Check the domain, then ask Supabase to email a single-use link.

    The check here exists to give a clear error before any email is sent. The
    real gate is the `before-user-created` hook in Supabase -- see
    app/domains.py.
    """
    email = normalize(body.email)
    reason = rejection_reason(email, settings.domains)
    if reason:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=reason)

    # TODO(step 03): call Supabase signInWithOtp(email) so Resend delivers the
    # link. Blocked on the Supabase project and the Resend sender domain.
    raise HTTPException(
        status.HTTP_501_NOT_IMPLEMENTED,
        detail="Supabase project not configured yet.",
    )


@router.post("/sign-out", status_code=status.HTTP_204_NO_CONTENT)
def sign_out():
    """Ends the session. The cookie itself is cleared by the Next.js route."""
    # TODO(step 03): revoke the Supabase session for the bearer token.
    raise HTTPException(
        status.HTTP_501_NOT_IMPLEMENTED,
        detail="Supabase project not configured yet.",
    )
