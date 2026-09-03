"""Profile & account — UX_SPEC.md §6.6, plus the three collections behind the
avatar menu: my listings, saved items and the inbox.

All three reuse `feed.to_card`, so a card carries identical badges, distance and
overlap-only disclosure wherever it appears.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession, selectinload

from ..db import get_db
from ..enums import UserStatus
from ..models import Enquiry, Listing, Save, User
from ..schemas import EnquiryRow, ListingPage, MeOut, ProfileUpdate
from ..security import current_user
from ..services import feed, geo

router = APIRouter(prefix="/me", tags=["profile"])


@router.get("", response_model=MeOut)
def get_profile(user: User = Depends(current_user)):
    return MeOut.model_validate(user)


@router.patch("", response_model=MeOut)
def update_profile(
    payload: ProfileUpdate,
    user: User = Depends(current_user),
    db: DbSession = Depends(get_db),
):
    """Everything on the settings screen except the email, which has no route.

    Clearing `phone` is a supported operation, not an error: it moves the user's
    listings to the single full-width Email button (UX_SPEC.md §5.1).
    """
    data = payload.model_dump(exclude_unset=True)

    if "zip_code" in data and not geo.is_supported(data["zip_code"]):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"{data['zip_code']} is not in the New York metro area.",
        )

    if "username" in data and data["username"] != user.username:
        clash = db.query(User).filter(User.username == data["username"]).first()
        if clash is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "That username is taken")

    for key, value in data.items():
        setattr(user, key, value)
    db.commit()
    return MeOut.model_validate(user)


@router.post("/deactivate", status_code=status.HTTP_204_NO_CONTENT)
def deactivate(user: User = Depends(current_user), db: DbSession = Depends(get_db)):
    """Reversible: signing in with the same Columbia email brings it back.
    Listings stay but drop out of the feed with the account."""
    user.status = UserStatus.DEACTIVATED
    db.commit()


# --------------------------------------------------------------------------
# Collections
# --------------------------------------------------------------------------


def _page(items, total: int, limit: int, offset: int) -> ListingPage:
    return ListingPage(
        items=items,
        total=total,
        next_cursor=str(offset + limit) if offset + limit < total else None,
    )


@router.get("/listings", response_model=ListingPage)
def my_listings(
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(current_user),
    db: DbSession = Depends(get_db),
):
    """Everything this member has posted, in every status.

    Deliberately unfiltered: drafts, sold and taken-down items are exactly what
    the owner came here to see, even though the feed hides them all.
    """
    base = select(Listing).where(Listing.seller_id == user.id)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.scalars(
        base.options(selectinload(Listing.photos))
        .order_by(Listing.posted_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return _page([feed.to_card(listing, user, user) for listing in rows], total, limit, offset)


@router.get("/saves", response_model=ListingPage)
def my_saves(
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(current_user),
    db: DbSession = Depends(get_db),
):
    """Saved items, newest save first.

    A save outlives the listing's availability, so sold and reserved rows stay
    here — vanishing silently when a seller marks something sold would read as
    data loss.
    """
    base = select(Listing).join(Save, Save.listing_id == Listing.id).where(Save.user_id == user.id)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.scalars(
        base.options(selectinload(Listing.photos), selectinload(Listing.seller))
        .order_by(Save.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return _page([feed.to_card(listing, listing.seller, user) for listing in rows], total, limit, offset)


@router.get("/enquiries", response_model=list[EnquiryRow])
def my_enquiries(
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(current_user),
    db: DbSession = Depends(get_db),
):
    """The inbox: every listing this member has contacted a seller about.

    There is no in-app chat (UX_SPEC.md §1), so this is a record of contacts
    made, not a thread list. It is the honest version of an inbox for a product
    whose contact step hands you an address and gets out of the way.
    """
    rows = db.execute(
        select(Enquiry, Listing)
        .join(Listing, Enquiry.listing_id == Listing.id)
        .where(Enquiry.buyer_id == user.id)
        .options(selectinload(Listing.photos), selectinload(Listing.seller))
        .order_by(Enquiry.created_at.desc())
        .limit(limit)
    ).all()
    return [
        EnquiryRow(
            id=enquiry.id,
            channel=enquiry.channel,
            created_at=enquiry.created_at,
            listing=feed.to_card(listing, listing.seller, user),
            seller_username=listing.seller.username if listing.seller else None,
        )
        for enquiry, listing in rows
    ]
