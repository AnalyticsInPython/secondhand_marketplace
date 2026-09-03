"""The feed, the detail page and posting — UX_SPEC.md §6.3 to §6.5.

Thin on purpose: filtering, counting and serialising live in services/feed.py
so the page and the sidebar can never disagree.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from ..config import settings
from ..db import get_db
from ..enums import (
    Category,
    Condition,
    EnquiryChannel,
    ListingStatus,
    SortOrder,
    ViewSurface,
    subcategory_belongs_to,
)
from ..models import Enquiry, FilterEvent, Listing, ListingPhoto, ListingView, Save, Upload, User
from ..schemas import (
    EnquiryIn,
    EnquiryOut,
    FacetCounts,
    ListingCreate,
    ListingDetail,
    ListingPage,
    ListingUpdate,
)
from ..security import current_user, current_user_optional
from ..services import feed, geo

router = APIRouter(prefix="/listings", tags=["listings"])


# ---------------------------------------------------------------- helpers


def _filters(
    q: str | None,
    category: list[Category],
    subcategory: list[str],
    condition: list[Condition],
    price_min_cents: int | None,
    price_max_cents: int | None,
    radius_mi: float | None,
    same_zip: bool,
    same_nationality: bool,
    same_school: bool,
) -> feed.FeedFilters:
    if radius_mi is not None:
        radius_mi = min(max(radius_mi, settings.min_radius_mi), settings.max_radius_mi)
    return feed.FeedFilters(
        q=q.strip() if q and q.strip() else None,
        category=tuple(category),
        subcategory=tuple(subcategory),
        condition=tuple(condition),
        price_min_cents=price_min_cents,
        price_max_cents=price_max_cents,
        radius_mi=radius_mi,
        same_zip=same_zip,
        same_nationality=same_nationality,
        same_school=same_school,
    )


def _own_listing(db: DbSession, listing_id: str, user: User) -> Listing:
    listing = db.get(Listing, listing_id)
    if listing is None or listing.seller_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such listing")
    return listing


def _relative(url: str) -> str:
    """Accept the absolute URL the upload endpoint returned, store it relative."""
    origin = settings.public_origin.rstrip("/")
    return url[len(origin) :] if url.startswith(origin + "/") else url


def _attach_photos(db: DbSession, user: User, listing: Listing, urls: list[str]) -> None:
    """Replace the listing's photos with `urls`, in order. Position 0 is the cover.

    Every URL must be one of this member's own uploads (or already on this
    listing), so nobody can post with somebody else's picture or with an
    arbitrary address.
    """
    wanted: list[str] = []
    for u in urls:
        rel = _relative(u)
        if rel not in wanted:
            wanted.append(rel)
    wanted = wanted[: settings.max_photos_per_listing]

    current = {p.url for p in listing.photos}
    uploads: dict[str, Upload] = {}
    for rel in wanted:
        if rel in current:
            continue
        upload = db.scalar(
            select(Upload).where(Upload.url == rel, Upload.user_id == user.id, Upload.listing_id.is_(None))
        )
        if upload is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "One of the photos was not uploaded by you. Add it again from the form.",
            )
        uploads[rel] = upload

    # The (listing, position) pair is unique, so reorder by clearing first.
    old = {p.url: p for p in listing.photos}
    for photo in list(listing.photos):
        db.delete(photo)
    db.flush()

    for position, rel in enumerate(wanted):
        prior = old.get(rel)
        upload = uploads.get(rel)
        db.add(
            ListingPhoto(
                listing_id=listing.id,
                url=rel,
                position=position,
                width=prior.width if prior else upload.width if upload else None,
                height=prior.height if prior else upload.height if upload else None,
            )
        )
        if upload is not None:
            upload.listing_id = listing.id
    db.flush()
    db.expire(listing, ["photos"])


# ---------------------------------------------------------------- routes
# Static paths first, so "facets" and "events" are never read as an id.


@router.get("/facets", response_model=FacetCounts)
def facets(
    q: str | None = None,
    category: list[Category] = Query(default=[]),
    subcategory: list[str] = Query(default=[]),
    condition: list[Condition] = Query(default=[]),
    price_min_cents: int | None = None,
    price_max_cents: int | None = None,
    radius_mi: float | None = None,
    same_zip: bool = False,
    same_nationality: bool = False,
    same_school: bool = False,
    viewer: User = Depends(current_user),
    db: DbSession = Depends(get_db),
):
    """Every number in the filter sidebar. Same parameters as GET /listings."""
    f = _filters(
        q, category, subcategory, condition, price_min_cents, price_max_cents,
        radius_mi, same_zip, same_nationality, same_school,
    )
    return feed.facets(db, viewer, f)


@router.post("/events/filter", status_code=status.HTTP_204_NO_CONTENT)
def log_filter_event(
    filter_key: str = Query(max_length=40),
    result_count: int = 0,
    value: str | None = Query(default=None, max_length=80),
    viewer: User | None = Depends(current_user_optional),
    db: DbSession = Depends(get_db),
):
    """Called on every toggle and every slider release.

    This is the table that answers "which of the filters is doing the work", and
    it cannot be reconstructed after the fact — so log eagerly and prune later.
    """
    db.add(
        FilterEvent(
            user_id=viewer.id if viewer else None,
            filter_key=filter_key,
            value=value,
            result_count=max(0, result_count),
        )
    )
    db.commit()


@router.get("", response_model=ListingPage)
def list_listings(
    q: str | None = None,
    category: list[Category] = Query(default=[]),
    subcategory: list[str] = Query(default=[]),
    condition: list[Condition] = Query(default=[]),
    price_min_cents: int | None = None,
    price_max_cents: int | None = None,
    radius_mi: float | None = None,
    same_zip: bool = False,
    same_nationality: bool = False,
    same_school: bool = False,
    sort: SortOrder | None = None,
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    viewer: User = Depends(current_user),
    db: DbSession = Depends(get_db),
):
    """The feed. Every card carries `distance_mi` and `badges[]` already
    computed for the viewer; the client never sees a seller's raw attributes."""
    f = _filters(
        q, category, subcategory, condition, price_min_cents, price_max_cents,
        radius_mi, same_zip, same_nationality, same_school,
    )
    rows, total, _ = feed.page(db, viewer, f, sort=sort, limit=limit, offset=offset)

    show_badges = feed.badge_treatment()
    feed.log_impressions(
        db, viewer, [listing for listing, _ in rows],
        ViewSurface.SEARCH if f.q else ViewSurface.FEED, show_badges,
    )
    return ListingPage(
        items=[feed.to_card(listing, seller, viewer, show_badges=show_badges) for listing, seller in rows],
        total=total,
        next_cursor=str(offset + limit) if offset + limit < total else None,
    )


@router.post("", response_model=ListingDetail, status_code=status.HTTP_201_CREATED)
def create_listing(
    payload: ListingCreate,
    user: User = Depends(current_user),
    db: DbSession = Depends(get_db),
):
    """Posting. Note what is *not* here: an audience.

    Who sees a listing is decided by each buyer's own filters, so the seller has
    no visibility control to submit (UX_SPEC.md §2).
    """
    if not geo.is_supported(payload.zip_code):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Pickup ZIP must be in the NYC metro")

    listing = Listing(
        seller_id=user.id,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        subcategory=payload.subcategory,
        condition=payload.condition,
        price_cents=payload.price_cents,
        is_free=payload.is_free,
        is_negotiable=payload.is_negotiable,
        zip_code=payload.zip_code,
        status=ListingStatus.ACTIVE,
    )
    db.add(listing)
    db.flush()
    _attach_photos(db, user, listing, payload.photo_urls)
    db.commit()
    db.refresh(listing)
    return feed.to_detail(db, listing, user)


@router.get("/{listing_id}", response_model=ListingDetail)
def get_listing(
    listing_id: str,
    viewer: User = Depends(current_user),
    db: DbSession = Depends(get_db),
):
    listing = db.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such listing")
    is_owner = listing.seller_id == viewer.id
    if listing.status in (ListingStatus.DELISTED, ListingStatus.DRAFT) and not is_owner:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such listing")

    if not is_owner:
        db.add(ListingView(listing_id=listing.id, viewer_id=viewer.id, surface=ViewSurface.DETAIL))
        listing.view_count += 1
        db.commit()

    return feed.to_detail(db, listing, viewer)


@router.patch("/{listing_id}", response_model=ListingDetail)
def update_listing(
    listing_id: str,
    payload: ListingUpdate,
    user: User = Depends(current_user),
    db: DbSession = Depends(get_db),
):
    """Edit, mark sold, reserve, relist or delist. Owner only."""
    listing = _own_listing(db, listing_id, user)
    data = payload.model_dump(exclude_unset=True)

    if "zip_code" in data and not geo.is_supported(data["zip_code"]):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Pickup ZIP must be in the NYC metro")

    category = data.get("category", listing.category)
    subcategory = data["subcategory"] if "subcategory" in data else listing.subcategory
    if "category" in data and "subcategory" not in data and not subcategory_belongs_to(subcategory, category):
        subcategory = None  # the old subcategory does not fit the new category
    if not subcategory_belongs_to(subcategory, category):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"{subcategory!r} is not a {category.label()} subcategory")

    is_free = data.get("is_free", listing.is_free)
    price = data.get("price_cents", listing.price_cents)
    if is_free:
        price = 0
    elif price <= 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, 'Enter a price, or tick "give it away for free".')

    photo_urls = data.pop("photo_urls", None)
    new_status = data.pop("status", None)
    data.update(category=category, subcategory=subcategory, is_free=is_free, price_cents=price)
    for key, value in data.items():
        setattr(listing, key, value)

    if photo_urls is not None:
        _attach_photos(db, user, listing, photo_urls)

    if new_status is not None and new_status != listing.status:
        listing.status = new_status
        # sold_at is the event the whole analysis counts (UX_SPEC.md §4.2).
        listing.sold_at = datetime.now(timezone.utc) if new_status is ListingStatus.SOLD else None

    db.commit()
    db.refresh(listing)
    return feed.to_detail(db, listing, user)


@router.post("/{listing_id}/sold", status_code=status.HTTP_204_NO_CONTENT)
def mark_sold(listing_id: str, user: User = Depends(current_user), db: DbSession = Depends(get_db)):
    """Shorthand for PATCH {status: sold} — the event the whole analysis counts."""
    listing = _own_listing(db, listing_id, user)
    listing.status = ListingStatus.SOLD
    listing.sold_at = datetime.now(timezone.utc)
    db.commit()


@router.post("/{listing_id}/save", status_code=status.HTTP_204_NO_CONTENT)
def save_listing(listing_id: str, user: User = Depends(current_user), db: DbSession = Depends(get_db)):
    listing = db.get(Listing, listing_id)
    if listing is None or listing.status in (ListingStatus.DELISTED, ListingStatus.DRAFT):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such listing")
    existing = db.scalar(select(Save).where(Save.listing_id == listing_id, Save.user_id == user.id))
    if existing is None:
        db.add(Save(listing_id=listing_id, user_id=user.id))
        listing.save_count += 1
        db.commit()


@router.delete("/{listing_id}/save", status_code=status.HTTP_204_NO_CONTENT)
def unsave_listing(listing_id: str, user: User = Depends(current_user), db: DbSession = Depends(get_db)):
    existing = db.scalar(select(Save).where(Save.listing_id == listing_id, Save.user_id == user.id))
    if existing is not None:
        listing = db.get(Listing, listing_id)
        if listing and listing.save_count > 0:
            listing.save_count -= 1
        db.delete(existing)
        db.commit()


@router.post("/{listing_id}/enquiry", response_model=EnquiryOut)
def start_enquiry(
    listing_id: str,
    payload: EnquiryIn,
    user: User = Depends(current_user),
    db: DbSession = Depends(get_db),
):
    """The one and only place a contact detail crosses the wire.

    The buyer has tapped Email or Text; only now is the address or the number
    released. Neither is ever included in the listing payload, so a page that
    was merely *viewed* never carried them.
    """
    listing = db.get(Listing, listing_id)
    if listing is None or listing.status in (ListingStatus.DELISTED, ListingStatus.DRAFT):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such listing")
    if listing.status is ListingStatus.SOLD:
        raise HTTPException(status.HTTP_409_CONFLICT, "This item is sold")
    if listing.seller_id == user.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "This is your own listing")

    # A modest ceiling. The reveal is the measurement, and also the only thing
    # worth scraping.
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    recent = db.scalar(
        select(func.count(Enquiry.id)).where(Enquiry.buyer_id == user.id, Enquiry.created_at >= since)
    ) or 0
    if recent >= settings.enquiries_per_hour:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many contact requests. Try again later.")

    seller = listing.seller
    if payload.channel is EnquiryChannel.SMS and not seller.can_receive_sms:
        # The frontend should not have offered the button; refuse anyway.
        raise HTTPException(status.HTTP_409_CONFLICT, "This seller has no number on file")

    db.add(Enquiry(listing_id=listing.id, buyer_id=user.id, channel=payload.channel))
    listing.enquiry_count += 1
    db.commit()

    if payload.channel is EnquiryChannel.EMAIL:
        return EnquiryOut(channel=payload.channel, address=seller.email)
    return EnquiryOut(channel=payload.channel, phone=seller.phone)
