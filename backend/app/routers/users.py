"""Profile & account — UX_SPEC.md §6.6."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession

from sqlalchemy import desc
from sqlalchemy.orm import aliased

from ..db import get_db
from ..enums import UserStatus
from ..models import Enquiry, Listing, Save, User
from ..schemas import EnquiryRow, ListingPage, MeOut, ProfileUpdate
from ..security import current_user
from ..services import geo

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

    if "nationality" in data and data["nationality"]:
        data["nationality"] = data["nationality"].upper()

    if "phone" in data and not data["phone"]:
        data["phone"] = None  # explicit clear

    for key, value in data.items():
        setattr(user, key, value)
    db.commit()
    return MeOut.model_validate(user)


@router.post("/deactivate", status_code=status.HTTP_204_NO_CONTENT)
def deactivate(user: User = Depends(current_user), db: DbSession = Depends(get_db)):
    """Reversible: signing in with the same Columbia email brings it back."""
    user.status = UserStatus.DEACTIVATED
    db.commit()


# --------------------------------------------------------------------------
# The three "my stuff" collections behind the avatar menu (UX_SPEC.md §6.6).
#
# All of them reuse `to_card` from the listings router, so a card looks and
# behaves identically wherever it appears -- same badges, same distance, same
# overlap-only disclosure. Importing it here rather than duplicating the
# serialiser is the whole point.
# --------------------------------------------------------------------------


def _page(rows, viewer, total) -> ListingPage:
    from .listings import to_card

    return ListingPage(
        items=[to_card(listing, seller, viewer) for listing, seller in rows],
        total=total,
    )


@router.get("/listings", response_model=ListingPage)
def my_listings(
    limit: int = 24,
    offset: int = 0,
    user: User = Depends(current_user),
    db: DbSession = Depends(get_db),
):
    """Everything this member has posted, in every status.

    Deliberately unfiltered by status: drafts and sold items are exactly what the
    owner came here to see, even though the feed hides both.
    """
    query = (
        db.query(Listing, User)
        .join(User, Listing.seller_id == User.id)
        .filter(Listing.seller_id == user.id)
    )
    total = query.count()
    rows = query.order_by(desc(Listing.posted_at)).offset(offset).limit(limit).all()
    return _page(rows, user, total)


@router.get("/saves", response_model=ListingPage)
def my_saves(
    limit: int = 24,
    offset: int = 0,
    user: User = Depends(current_user),
    db: DbSession = Depends(get_db),
):
    """Saved items, newest save first.

    A save outlives the listing's availability, so sold and reserved rows stay
    here -- vanishing silently when a seller marks something sold would read as
    data loss.
    """
    Seller = aliased(User)
    query = (
        db.query(Listing, Seller)
        .join(Save, Save.listing_id == Listing.id)
        .outerjoin(Seller, Listing.seller_id == Seller.id)
        .filter(Save.user_id == user.id)
    )
    total = query.count()
    rows = query.order_by(desc(Save.created_at)).offset(offset).limit(limit).all()
    return _page(rows, user, total)


@router.get("/enquiries", response_model=list[EnquiryRow])
def my_enquiries(
    limit: int = 50,
    user: User = Depends(current_user),
    db: DbSession = Depends(get_db),
):
    """The inbox: every listing this member has contacted a seller about.

    There is no in-app chat (UX_SPEC.md §1), so this is a record of contacts
    made, not a thread list. It is the honest version of an inbox for a product
    whose contact step hands you an address and gets out of the way.
    """
    Seller = aliased(User)
    rows = (
        db.query(Enquiry, Listing, Seller)
        .join(Listing, Enquiry.listing_id == Listing.id)
        .outerjoin(Seller, Listing.seller_id == Seller.id)
        .filter(Enquiry.buyer_id == user.id)
        .order_by(desc(Enquiry.created_at))
        .limit(limit)
        .all()
    )
    from .listings import to_card

    return [
        EnquiryRow(
            id=enquiry.id,
            channel=enquiry.channel,
            created_at=enquiry.created_at,
            listing=to_card(listing, seller, user),
            seller_username=seller.username if seller else None,
        )
        for enquiry, listing, seller in rows
    ]
