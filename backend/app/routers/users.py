"""Profile & account — UX_SPEC.md §6.6, plus the two lists behind the avatar
menu: my listings and saved items."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession, selectinload

from ..db import get_db
from ..enums import UserStatus
from ..models import Listing, Save, User
from ..schemas import ListingCard, MeOut, ProfileUpdate
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


@router.get("/listings", response_model=list[ListingCard])
def my_listings(user: User = Depends(current_user), db: DbSession = Depends(get_db)):
    """Everything I have posted, every status, newest first."""
    rows = db.scalars(
        select(Listing)
        .where(Listing.seller_id == user.id)
        .options(selectinload(Listing.photos))
        .order_by(Listing.posted_at.desc())
    ).all()
    return [feed.to_card(listing, user, user) for listing in rows]


@router.get("/saved", response_model=list[ListingCard])
def saved_listings(user: User = Depends(current_user), db: DbSession = Depends(get_db)):
    rows = db.execute(
        select(Listing, Save.created_at)
        .join(Save, Save.listing_id == Listing.id)
        .where(Save.user_id == user.id)
        .options(selectinload(Listing.photos), selectinload(Listing.seller))
        .order_by(Save.created_at.desc())
    ).all()
    return [feed.to_card(listing, listing.seller, user) for listing, _ in rows]
