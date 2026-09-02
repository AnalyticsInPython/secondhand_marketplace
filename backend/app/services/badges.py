"""Overlap-only disclosure — UX_SPEC.md §5.3.

The single most important rule in the product, and the easiest one to break by
accident. A viewer is shown one of a seller's attributes *only where they
already share it*.

An attribute that does not match is not returned as `false` and not returned as
`null` — it is absent from the payload entirely. If the client ever receives the
seller's raw nationality or school, the rule is broken no matter what the UI
chooses to render.
"""

from __future__ import annotations

from ..models import User

SAME_ZIP = "SAME ZIP"
SAME_COUNTRY = "SAME COUNTRY"
SAME_SCHOOL = "SAME SCHOOL"


def badges_for(viewer: User | None, seller: User | None) -> list[str]:
    """Badges to show `viewer` on a listing sold by `seller`.

    Signed-out viewers and external listings both get an empty list: there is no
    overlap to speak of, so nothing is disclosed.
    """
    if viewer is None or seller is None:
        return []
    if viewer.id == seller.id:
        return []  # your own listing needs no badges

    out: list[str] = []
    if viewer.zip_code == seller.zip_code:
        out.append(SAME_ZIP)
    if viewer.nationality == seller.nationality:
        out.append(SAME_COUNTRY)
    if viewer.school == seller.school:
        out.append(SAME_SCHOOL)
    return out


def public_seller(viewer: User | None, seller: User | None) -> dict | None:
    """The seller block for a listing response.

    Everything here is safe for any viewer. Note what is *not* in it: email,
    phone, nationality, school, grade, and the raw ZIP. The contact address and
    number are released only by POST /listings/{id}/enquiry, at the moment the
    buyer taps the button.
    """
    if seller is None:
        return None
    return {
        "username": seller.username,
        "display_name": seller.display_name,
        "is_verified": seller.is_verified,
        "member_since": seller.created_at.isoformat(),
        "badges": badges_for(viewer, seller),
        # Drives the two contact shapes in UX_SPEC.md §5.1. It is a boolean, not
        # the number itself, precisely so the number never reaches the page.
        "can_receive_sms": seller.can_receive_sms,
    }
