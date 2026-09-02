"""The feed, the detail page and posting — UX_SPEC.md §6.3 to §6.5."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session as DbSession, aliased

from ..config import settings
from ..db import get_db
from ..enums import (
    CATEGORY_LABELS,
    CONDITION_LABELS,
    Category,
    Condition,
    EnquiryChannel,
    ListingStatus,
    Source,
    SortOrder,
    ViewSurface,
)
from ..models import Enquiry, FilterEvent, Listing, ListingPhoto, ListingView, Save, User
from ..schemas import (
    EnquiryIn,
    EnquiryOut,
    FacetCount,
    FacetCounts,
    ListingCard,
    ListingCreate,
    ListingDetail,
    ListingPage,
)
from ..security import current_user, current_user_optional
from ..services import geo
from ..services.badges import badges_for, public_seller

router = APIRouter(prefix="/listings", tags=["listings"])

Seller = aliased(User)


# ---------------------------------------------------------------- filtering


def _filtered(
    db: DbSession,
    viewer: User | None,
    *,
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
    source: list[Source],
):
    """One place where every filter is expressed, so the feed and the facet
    counts can never disagree about what a filter means."""
    query = (
        db.query(Listing, Seller)
        .outerjoin(Seller, Listing.seller_id == Seller.id)
        .filter(Listing.status.in_([ListingStatus.ACTIVE, ListingStatus.RESERVED]))
    )

    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(Listing.title.ilike(like), Listing.description.ilike(like)))
    if category:
        query = query.filter(Listing.category.in_(category))
    if subcategory:
        query = query.filter(Listing.subcategory.in_(subcategory))
    if condition:
        query = query.filter(Listing.condition.in_(condition))
    if price_min_cents is not None:
        query = query.filter(Listing.price_cents >= price_min_cents)
    if price_max_cents is not None:
        query = query.filter(Listing.price_cents <= price_max_cents)
    if source:
        query = query.filter(Listing.source.in_(source))

    # Radius. Resolved to a ZIP list rather than a per-row distance calculation,
    # so the database can still use its index on listings.zip_code.
    if radius_mi is not None and viewer is not None:
        query = query.filter(Listing.zip_code.in_(geo.zips_within(viewer.zip_code, radius_mi)))

    # Trust filters. Each one implicitly excludes external listings, because an
    # aggregated eBay item has no seller to share anything with. That is the
    # intended behaviour, not a bug: "same country" means a person.
    if viewer is not None:
        if same_zip:
            query = query.filter(Listing.zip_code == viewer.zip_code)
        if same_nationality:
            query = query.filter(Seller.nationality == viewer.nationality)
        if same_school:
            query = query.filter(Seller.school == viewer.school)

    return query


def to_card(listing: Listing, seller: User | None, viewer: User | None) -> ListingCard:
    return ListingCard(
        id=listing.id,
        title=listing.title,
        price_cents=listing.price_cents,
        is_free=listing.is_free,
        condition=listing.condition,
        category=listing.category,
        subcategory=listing.subcategory,
        zip_code=listing.zip_code,
        distance_mi=geo.distance_mi(viewer.zip_code, listing.zip_code) if viewer else None,
        posted_at=listing.posted_at,
        status=listing.status,
        cover_photo_url=listing.cover_photo_url,
        badges=badges_for(viewer, seller),
        is_external=listing.is_external,
        source=listing.source,
        source_label=listing.source.label(),
    )


# ---------------------------------------------------------------- routes
# Declared before /{listing_id} so "facets" is not read as an id.


@router.get("/facets", response_model=FacetCounts)
def facets(
    q: str | None = None,
    category: list[Category] = Query(default=[]),
    condition: list[Condition] = Query(default=[]),
    price_min_cents: int | None = None,
    price_max_cents: int | None = None,
    radius_mi: float | None = None,
    same_zip: bool = False,
    same_nationality: bool = False,
    same_school: bool = False,
    viewer: User | None = Depends(current_user_optional),
    db: DbSession = Depends(get_db),
):
    """Every number in the filter sidebar.

    Each count is "what you would get if you turned this one filter on, with
    everything else you have already chosen still applied". The counts move as
    filters change, and that is the whole point — the trade between trust and
    selection is never hidden. Do not cache these.
    """
    common = dict(
        q=q,
        subcategory=[],
        price_min_cents=price_min_cents,
        price_max_cents=price_max_cents,
        radius_mi=radius_mi,
        source=[],
    )

    def count(**overrides) -> int:
        params = dict(
            category=category,
            condition=condition,
            same_zip=same_zip,
            same_nationality=same_nationality,
            same_school=same_school,
            **common,
        )
        params.update(overrides)
        return _filtered(db, viewer, **params).count()

    return FacetCounts(
        total=count(),
        categories=[
            FacetCount(key=c.value, label=CATEGORY_LABELS[c], count=count(category=[c]))
            for c in Category
        ],
        conditions=[
            FacetCount(key=c.value, label=CONDITION_LABELS[c], count=count(condition=[c]))
            for c in Condition
        ],
        same_zip=count(same_zip=True),
        same_nationality=count(same_nationality=True),
        same_school=count(same_school=True),
        radius_steps=[
            FacetCount(key=str(step), label=f"{step} mi", count=count(radius_mi=step))
            for step in (0.5, 1, 2.5, 5, 10)
        ],
    )


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
    source: list[Source] = Query(default=[]),
    sort: SortOrder = SortOrder.NEWEST,
    limit: int = Query(default=24, le=100),
    offset: int = 0,
    viewer: User | None = Depends(current_user_optional),
    db: DbSession = Depends(get_db),
):
    query = _filtered(
        db,
        viewer,
        q=q,
        category=category,
        subcategory=subcategory,
        condition=condition,
        price_min_cents=price_min_cents,
        price_max_cents=price_max_cents,
        radius_mi=radius_mi,
        same_zip=same_zip,
        same_nationality=same_nationality,
        same_school=same_school,
        source=source,
    )
    total = query.count()

    if sort is SortOrder.CLOSEST:
        # Distance is not a column — it depends on who is asking. At pilot scale
        # sorting in Python is honest and fast enough. If this ever gets slow,
        # the fix is a materialised zip-distance table, not a subquery.
        rows = query.all()
        rows.sort(key=lambda r: (geo.distance_mi(viewer.zip_code, r[0].zip_code) if viewer else 0) or 999)
        rows = rows[offset : offset + limit]
    else:
        order = {
            SortOrder.NEWEST: Listing.posted_at.desc(),
            SortOrder.PRICE_ASC: Listing.price_cents.asc(),
            SortOrder.PRICE_DESC: Listing.price_cents.desc(),
            SortOrder.MOST_SAVED: Listing.save_count.desc(),
        }[sort]
        rows = query.order_by(order).offset(offset).limit(limit).all()

    return ListingPage(
        items=[to_card(listing, seller, viewer) for listing, seller in rows],
        total=total,
        next_cursor=str(offset + limit) if offset + limit < total else None,
    )


@router.get("/{listing_id}", response_model=ListingDetail)
def get_listing(
    listing_id: str,
    viewer: User | None = Depends(current_user_optional),
    db: DbSession = Depends(get_db),
):
    listing = db.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such listing")
    seller = listing.seller

    db.add(ListingView(listing_id=listing.id, viewer_id=viewer.id if viewer else None, surface=ViewSurface.DETAIL))
    listing.view_count += 1
    db.commit()

    is_saved = False
    if viewer:
        is_saved = (
            db.query(Save).filter(Save.listing_id == listing.id, Save.user_id == viewer.id).first()
            is not None
        )

    card = to_card(listing, seller, viewer)
    return ListingDetail(
        **card.model_dump(),
        description=listing.description,
        is_negotiable=listing.is_negotiable,
        photo_urls=[p.url for p in listing.photos],
        view_count=listing.view_count,
        save_count=listing.save_count,
        enquiry_count=listing.enquiry_count,
        external_url=listing.external_url,
        seller=public_seller(viewer, seller),
        is_saved=is_saved,
        is_owner=bool(viewer and seller and viewer.id == seller.id),
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
    if not payload.is_free and payload.price_cents <= 0:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            'Enter a price, or tick "give it away for free". $0 on its own is ambiguous to buyers.',
        )

    listing = Listing(
        seller_id=user.id,
        source=Source.INTERNAL,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        subcategory=payload.subcategory,
        condition=payload.condition,
        price_cents=0 if payload.is_free else payload.price_cents,
        is_free=payload.is_free,
        is_negotiable=payload.is_negotiable,
        zip_code=payload.zip_code,
        status=ListingStatus.ACTIVE,
    )
    db.add(listing)
    db.flush()
    for i, url in enumerate(payload.photo_urls[: settings.max_photos_per_listing]):
        db.add(ListingPhoto(listing_id=listing.id, url=url, position=i))
    db.commit()

    return get_listing(listing.id, viewer=user, db=db)


@router.post("/{listing_id}/sold", status_code=status.HTTP_204_NO_CONTENT)
def mark_sold(listing_id: str, user: User = Depends(current_user), db: DbSession = Depends(get_db)):
    """The event the whole analysis counts."""
    listing = db.get(Listing, listing_id)
    if listing is None or listing.seller_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such listing")
    listing.status = ListingStatus.SOLD
    listing.sold_at = datetime.now(timezone.utc)
    db.commit()


@router.post("/{listing_id}/save", status_code=status.HTTP_204_NO_CONTENT)
def save_listing(listing_id: str, user: User = Depends(current_user), db: DbSession = Depends(get_db)):
    listing = db.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such listing")
    existing = db.query(Save).filter(Save.listing_id == listing_id, Save.user_id == user.id).first()
    if existing is None:
        db.add(Save(listing_id=listing_id, user_id=user.id))
        listing.save_count += 1
        db.commit()


@router.delete("/{listing_id}/save", status_code=status.HTTP_204_NO_CONTENT)
def unsave_listing(listing_id: str, user: User = Depends(current_user), db: DbSession = Depends(get_db)):
    existing = db.query(Save).filter(Save.listing_id == listing_id, Save.user_id == user.id).first()
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
    if listing is None or listing.seller is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such listing")
    if listing.status is ListingStatus.SOLD:
        raise HTTPException(status.HTTP_409_CONFLICT, "This item is sold")

    seller = listing.seller
    channel = EnquiryChannel(payload.channel)
    if channel is EnquiryChannel.SMS and not seller.can_receive_sms:
        # The frontend should not have offered the button; refuse anyway.
        raise HTTPException(status.HTTP_409_CONFLICT, "This seller has no number on file")

    db.add(Enquiry(listing_id=listing.id, buyer_id=user.id, channel=channel))
    listing.enquiry_count += 1
    db.commit()

    if channel is EnquiryChannel.EMAIL:
        return EnquiryOut(channel=channel.value, address=seller.email)
    return EnquiryOut(channel=channel.value, phone=seller.phone)


@router.post("/events/filter", status_code=status.HTTP_204_NO_CONTENT)
def log_filter_event(
    filter_key: str,
    result_count: int,
    value: str | None = None,
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
            result_count=result_count,
        )
    )
    db.commit()
