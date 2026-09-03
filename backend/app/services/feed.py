"""The feed and its live facet counts — UX_SPEC.md §5.4 and §6.3.

One place where every filter is expressed (`where_clauses`), so the page of
results and the numbers in the sidebar can never disagree about what a filter
means. Facet counts are computed with grouped queries — five statements for
the whole sidebar regardless of how many enum values there are.

Every count is "what you would get if you applied this one filter, with all the
other active filters still on". They are meant to move. Do not cache them.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, replace

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session as DbSession, aliased, selectinload

from ..config import settings
from ..enums import (
    CATEGORY_LABELS,
    CONDITION_LABELS,
    FEED_STATUSES,
    SUBCATEGORIES,
    SUBCATEGORY_LABELS,
    Category,
    Condition,
    SortOrder,
    UserStatus,
    ViewSurface,
)
from ..models import Listing, ListingView, Save, User
from ..schemas import FacetCount, FacetCounts, ListingCard, ListingDetail, PhotoOut
from . import geo
from .badges import badges_for, public_seller
from .photos import absolute_url

Seller = aliased(User, name="seller")


@dataclass(frozen=True)
class FeedFilters:
    """Mirrors the query string of GET /listings and GET /listings/facets."""

    q: str | None = None
    category: tuple[Category, ...] = ()
    subcategory: tuple[str, ...] = ()
    condition: tuple[Condition, ...] = ()
    price_min_cents: int | None = None
    price_max_cents: int | None = None
    radius_mi: float | None = None
    same_zip: bool = False
    same_nationality: bool = False
    same_school: bool = False

    def with_(self, **changes) -> FeedFilters:
        return replace(self, **changes)


# ---------------------------------------------------------------- filtering


def where_clauses(viewer: User, f: FeedFilters, exclude: frozenset[str] = frozenset()) -> list:
    """Every filter as a WHERE clause. `exclude` drops named filters — that is
    how a facet count asks "and if this one were not applied?"."""

    def on(key: str) -> bool:
        return key not in exclude

    conds = [Listing.status.in_(FEED_STATUSES), Seller.status == UserStatus.ACTIVE]

    if f.q and on("q"):
        like = f"%{f.q.strip()}%"
        conds.append(or_(Listing.title.ilike(like), Listing.description.ilike(like)))
    if f.category and on("category"):
        conds.append(Listing.category.in_(f.category))
    if f.subcategory and on("subcategory"):
        conds.append(Listing.subcategory.in_(f.subcategory))
    if f.condition and on("condition"):
        conds.append(Listing.condition.in_(f.condition))
    if f.price_min_cents is not None and on("price"):
        conds.append(Listing.price_cents >= f.price_min_cents)
    if f.price_max_cents is not None and on("price"):
        conds.append(Listing.price_cents <= f.price_max_cents)

    # Radius. Resolved to a ZIP list rather than a per-row distance calculation,
    # so the database can still use its index on listings.zip_code.
    if f.radius_mi is not None and on("radius_mi"):
        conds.append(Listing.zip_code.in_(geo.zips_within(viewer.zip_code, f.radius_mi)))

    # Trust filters — "same X" means the seller shares X with *this* viewer.
    if f.same_zip and on("same_zip"):
        conds.append(Listing.zip_code == viewer.zip_code)
    if f.same_nationality and on("same_nationality"):
        conds.append(Seller.nationality == viewer.nationality)
    if f.same_school and on("same_school"):
        conds.append(Seller.school == viewer.school)

    return conds


def _joined(stmt):
    return stmt.join(Seller, Listing.seller_id == Seller.id)


def _count_stmt(viewer: User, f: FeedFilters, exclude: frozenset[str] = frozenset()):
    return _joined(select(func.count(Listing.id))).where(*where_clauses(viewer, f, exclude))


# ---------------------------------------------------------------- the page


def page(
    db: DbSession,
    viewer: User,
    f: FeedFilters,
    *,
    sort: SortOrder | None,
    limit: int,
    offset: int,
) -> tuple[list[tuple[Listing, User]], int, SortOrder]:
    """Rows for one page, the total, and the sort actually used.

    With a text query the default sort switches to `closest` (UX_SPEC.md §5.4).
    """
    if sort is None:
        sort = SortOrder.CLOSEST if f.q else SortOrder.NEWEST

    total = db.scalar(_count_stmt(viewer, f)) or 0
    stmt = (
        _joined(select(Listing, Seller))
        .where(*where_clauses(viewer, f))
        .options(selectinload(Listing.photos))
    )

    if sort is SortOrder.CLOSEST:
        # Distance is not a column — it depends on who is asking. At pilot scale
        # sorting in Python is honest and fast enough. If this ever gets slow,
        # the fix is a materialised zip-distance table, not a subquery.
        rows = db.execute(stmt).all()
        rows.sort(
            key=lambda r: (
                geo.distance_mi(viewer.zip_code, r[0].zip_code) if geo.distance_mi(viewer.zip_code, r[0].zip_code) is not None else 999.0,
                -r[0].posted_at.timestamp(),
            )
        )
        rows = rows[offset : offset + limit]
    else:
        order = {
            SortOrder.NEWEST: Listing.posted_at.desc(),
            SortOrder.PRICE_ASC: Listing.price_cents.asc(),
            SortOrder.PRICE_DESC: Listing.price_cents.desc(),
            SortOrder.MOST_SAVED: Listing.save_count.desc(),
        }[sort]
        rows = db.execute(stmt.order_by(order, Listing.posted_at.desc()).offset(offset).limit(limit)).all()

    return [(r[0], r[1]) for r in rows], total, sort


# ---------------------------------------------------------------- facets


def facets(db: DbSession, viewer: User, f: FeedFilters) -> FacetCounts:
    """Every number in the filter sidebar, in five grouped queries."""
    steps = settings.radius_steps_mi

    # 1. The total plus the three trust toggles, in one pass over the result set.
    total, n_zip, n_nat, n_school = db.execute(
        _joined(
            select(
                func.count(Listing.id),
                func.count(case((Listing.zip_code == viewer.zip_code, 1))),
                func.count(case((Seller.nationality == viewer.nationality, 1))),
                func.count(case((Seller.school == viewer.school, 1))),
            )
        ).where(*where_clauses(viewer, f))
    ).one()

    # 2. Categories: "if only this category were ticked" — so the category
    #    filter (and its dependent subcategory filter) is lifted.
    by_category = dict(
        db.execute(
            _joined(select(Listing.category, func.count(Listing.id)))
            .where(*where_clauses(viewer, f, frozenset({"category", "subcategory"})))
            .group_by(Listing.category)
        ).all()
    )

    # 3. Subcategories, within whatever categories are ticked.
    by_subcategory = dict(
        db.execute(
            _joined(select(Listing.subcategory, func.count(Listing.id)))
            .where(*where_clauses(viewer, f, frozenset({"subcategory"})), Listing.subcategory.is_not(None))
            .group_by(Listing.subcategory)
        ).all()
    )

    # 4. Conditions.
    by_condition = dict(
        db.execute(
            _joined(select(Listing.condition, func.count(Listing.id)))
            .where(*where_clauses(viewer, f, frozenset({"condition"})))
            .group_by(Listing.condition)
        ).all()
    )

    # 5. The distance presets, as conditional counts over the radius-free set.
    step_counts = db.execute(
        _joined(
            select(
                *[
                    func.count(case((Listing.zip_code.in_(geo.zips_within(viewer.zip_code, s)), 1)))
                    for s in steps
                ]
            )
        ).where(*where_clauses(viewer, f, frozenset({"radius_mi"})))
    ).one()

    return FacetCounts(
        total=total,
        categories=[
            FacetCount(key=c.value, label=CATEGORY_LABELS[c], count=by_category.get(c, 0))
            for c in Category
        ],
        subcategories=[
            FacetCount(key=s, label=SUBCATEGORY_LABELS[s], count=by_subcategory.get(s, 0))
            for subs in SUBCATEGORIES.values()
            for s in subs
        ],
        conditions=[
            FacetCount(key=c.value, label=CONDITION_LABELS[c], count=by_condition.get(c, 0))
            for c in Condition
        ],
        same_zip=n_zip,
        same_nationality=n_nat,
        same_school=n_school,
        radius_steps=[
            FacetCount(key=f"{s:g}", label=f"{s:g} mi", count=n) for s, n in zip(steps, step_counts)
        ],
    )


# ---------------------------------------------------------------- serializers


def to_card(listing: Listing, seller: User | None, viewer: User | None, *, show_badges: bool = True) -> ListingCard:
    z = geo.lookup(listing.zip_code)
    return ListingCard(
        id=listing.id,
        title=listing.title,
        price_cents=listing.price_cents,
        is_free=listing.is_free,
        condition=listing.condition,
        category=listing.category,
        subcategory=listing.subcategory,
        zip_code=listing.zip_code,
        neighbourhood=z.neighbourhood if z else None,
        distance_mi=geo.distance_mi(viewer.zip_code, listing.zip_code) if viewer else None,
        posted_at=listing.posted_at,
        status=listing.status,
        cover_photo_url=absolute_url(listing.cover_photo_url),
        photo_count=len(listing.photos),
        badges=badges_for(viewer, seller) if show_badges else [],
    )


def to_detail(db: DbSession, listing: Listing, viewer: User | None) -> ListingDetail:
    seller = listing.seller
    card = to_card(listing, seller, viewer)
    is_saved = False
    if viewer is not None:
        is_saved = (
            db.scalar(select(Save.id).where(Save.listing_id == listing.id, Save.user_id == viewer.id))
            is not None
        )
    urls = [absolute_url(p.url) for p in listing.photos]
    return ListingDetail(
        **card.model_dump(),
        description=listing.description,
        is_negotiable=listing.is_negotiable,
        photos=[PhotoOut(url=u, width=p.width, height=p.height) for u, p in zip(urls, listing.photos)],
        photo_urls=urls,
        view_count=listing.view_count,
        save_count=listing.save_count,
        enquiry_count=listing.enquiry_count,
        sold_at=listing.sold_at,
        seller=public_seller(viewer, seller),
        is_saved=is_saved,
        is_owner=bool(viewer and seller and viewer.id == seller.id),
    )


# ---------------------------------------------------------------- events


def badge_treatment() -> bool:
    """Whether this request renders badges. Always yes unless the experiment is on."""
    if not settings.badge_experiment_enabled:
        return True
    return random.random() < 0.5


def log_impressions(
    db: DbSession,
    viewer: User | None,
    listings: list[Listing],
    surface: ViewSurface,
    badges_shown: bool,
) -> None:
    """One listing_views row per card shown. The funnel starts here."""
    if not listings:
        return
    db.add_all(
        ListingView(
            listing_id=listing.id,
            viewer_id=viewer.id if viewer else None,
            surface=surface,
            badges_shown=badges_shown,
        )
        for listing in listings
    )
    db.commit()
