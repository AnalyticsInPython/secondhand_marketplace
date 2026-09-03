"""Seed the database with plausible fake data — UX_SPEC.md §9.

    python -m scripts.seed --users 1000 --listings 1500 --reset
    python -m scripts.seed --reset --demo-email you@columbia.edu

Decisions in here that should survive edits:

1.  About 30% of users get no phone number. The email-only contact layout has to
    be exercised by the data, not just by a design state.
2.  Engagement is generated with one base rate for everyone. If the analysis
    finds an effect on seeded data, the effect is an artefact of this file. Do
    not put a thumb on the scale for the result we are hoping to see.

Every listing has a seller: the external tier was removed on 2026-09-02
(docs/DECISIONS.md). Photos are left empty on purpose — the frontend renders the
same deterministic gradient placeholder the Figma mockups use, so the seeded
feed looks like the design without depending on an image host. Real uploads
go through POST /photos.
"""

from __future__ import annotations

import argparse
import random
from datetime import datetime, timedelta, timezone

from app.db import SessionLocal, create_all, reset_all
from app.enums import (
    Category,
    Condition,
    EnquiryChannel,
    Grade,
    ListingStatus,
    School,
    ViewSurface,
)
from app.models import Enquiry, FilterEvent, Listing, ListingView, Save, User
from app.services import domains
from app.services.geo import ZIPS

rng = random.Random(20260902)

# ---------------------------------------------------------------- distributions

NATIONALITIES = (
    ["US"] * 35 + ["CN"] * 18 + ["KR"] * 10 + ["IN"] * 8 + ["CA"] * 4 + ["BR"] * 3
    + ["GB"] * 3 + ["JP"] * 3 + ["FR"] * 2 + ["DE"] * 2 + ["MX"] * 2 + ["NG"] * 2
    + ["TR"] * 2 + ["IT"] * 2 + ["ES"] * 1 + ["AU"] * 1 + ["SG"] * 1 + ["TH"] * 1
)

# CBS and SEAS over-represented: the KCA community we are seeding from skews that way.
SCHOOLS = (
    [School.CBS] * 22 + [School.SEAS_GRAD] * 18 + [School.COLUMBIA_COLLEGE] * 12
    + [School.SIPA] * 8 + [School.GSAS] * 8 + [School.TEACHERS_COLLEGE] * 7
    + [School.LAW] * 6 + [School.SEAS_UNDERGRAD] * 6 + [School.GENERAL_STUDIES] * 5
    + [School.PUBLIC_HEALTH] * 3 + [School.JOURNALISM] * 2 + [School.ARTS] * 1
    + [School.GSAPP] * 1 + [School.VPS] * 1
)

GRADES = [Grade.GRADUATE] * 60 + [Grade.UNDERGRADUATE] * 35 + [Grade.FACULTY_STAFF] * 5

ZIP_WEIGHTS = {"10027": 40, "10025": 15, "10031": 10, "10026": 8, "10024": 7, "10032": 5}
ZIPS_POOL = [z for zc, w in ZIP_WEIGHTS.items() for z in [zc] * w] + [
    z.zip_code for z in ZIPS if z.zip_code not in ZIP_WEIGHTS
]

CATEGORY_POOL = (
    [Category.FURNITURE] * 30 + [Category.TEXTBOOKS] * 20 + [Category.ELECTRONICS] * 15
    + [Category.KITCHEN_HOME] * 12 + [Category.CLOTHING] * 10
    + [Category.BIKES_TRANSPORT] * 6 + [Category.SPORTS] * 4 + [Category.FREE_STUFF] * 3
)

CONDITION_POOL = (
    [Condition.USED_GOOD] * 45 + [Condition.LIKE_NEW] * 30
    + [Condition.USED_FAIR] * 15 + [Condition.NEW] * 10
)

# (mu, sigma) of the underlying normal, plus a clamp — log-normal per category.
PRICE_MODEL = {
    Category.FURNITURE: (4.4, 0.8, 20, 400),
    Category.TEXTBOOKS: (3.4, 0.6, 10, 90),
    Category.ELECTRONICS: (4.8, 0.9, 30, 500),
    Category.KITCHEN_HOME: (3.6, 0.7, 10, 120),
    Category.CLOTHING: (4.0, 0.8, 15, 250),
    Category.BIKES_TRANSPORT: (5.0, 0.7, 60, 600),
    Category.SPORTS: (3.9, 0.8, 15, 200),
    Category.FREE_STUFF: (0, 0, 0, 0),
}

TITLES = {
    Category.FURNITURE: [
        "IKEA MALM desk 140×65, {colour}", "{colour} 3-seat sofa, must go",
        "Full mattress + metal frame", "Bookshelf, 5 shelves, {colour}",
        "Desk chair, adjustable", "Nightstand pair, {colour}",
        "Dining table + 2 chairs", "Standing desk, electric",
    ],
    Category.TEXTBOOKS: [
        "Corporate Finance (Berk) 5th ed.", "Intro to Statistical Learning",
        "Principles of Economics (Mankiw)", "Organic Chemistry, 8th ed. + solutions",
        "Python for Data Analysis (McKinney)", "Financial Accounting casebook",
    ],
    Category.ELECTRONICS: [
        "Dyson V8 cordless vacuum", "LG 27\" monitor, 1440p",
        "iPad Air 4 + Apple Pencil", "Sony WH-1000XM4 headphones",
        "Desk lamp with USB-C", "Mechanical keyboard, {colour}",
    ],
    Category.KITCHEN_HOME: [
        "Cuckoo 6-cup rice cooker", "Air fryer, barely used",
        "Full pot and pan set", "Espresso machine, {colour}",
        "Humidifier + filters", "Vacuum flask set",
    ],
    Category.CLOTHING: [
        "Canada Goose parka, size {size}", "Winter boots, size {size}",
        "Wool overcoat, size {size}", "North Face down jacket, size {size}",
        "Suit, {colour}, size {size}",
    ],
    Category.BIKES_TRANSPORT: [
        "Commuter bike, 54cm", "Folding bike + lock",
        "Electric scooter, 25km range", "Road bike, {colour}",
    ],
    Category.SPORTS: [
        "Yoga mat + blocks", "Adjustable dumbbells, 2×20lb",
        "Tennis racket, {colour}", "Climbing shoes, size {size}",
    ],
    Category.FREE_STUFF: [
        "Free moving boxes", "Free desk lamp, works fine",
        "Free plant, needs a home", "Free kitchen odds and ends",
    ],
}
COLOURS = ["white", "black", "grey", "oak", "navy", "beige"]
SIZES = ["S", "M", "L", "XL", "42", "9.5"]
SUBCATEGORY_FOR_TITLE = {
    "desk": "desks", "chair": "chairs", "mattress": "beds_mattresses",
    "bookshelf": "storage_shelving", "nightstand": "storage_shelving",
    "sofa": "sofas_tables", "table": "sofas_tables",
}

DESCRIPTIONS = [
    "Bought new last year, used for two semesters. Solid, no wobble — one small "
    "scuff you cannot see once it is against a wall. Pickup only.",
    "Moving out at the end of the month so it has to go before then. Elevator "
    "building, I can help carry it down to the street. Cash or Venmo.",
    "Barely used — I am graduating and cannot take it with me. Happy to hold it "
    "for a day if you can pick up this week.",
    "Works perfectly, I just upgraded. Original box included. Can meet on campus.",
]

# Two cohort spikes and a summer trough (UX_SPEC.md §9).
MONTH_WEIGHT = {1: 1.0, 2: 0.8, 3: 0.9, 4: 1.4, 5: 3.0, 6: 0.6, 7: 0.6,
                8: 3.0, 9: 1.6, 10: 1.0, 11: 0.9, 12: 1.2}


def _price_cents(category: Category) -> tuple[int, bool]:
    if category is Category.FREE_STUFF:
        return 0, True
    if rng.random() < 0.06:  # ~8% of everything ends up free
        return 0, True
    mu, sigma, lo, hi = PRICE_MODEL[category]
    usd = min(max(rng.lognormvariate(mu, sigma), lo), hi)
    return int(round(usd / 5) * 5 * 100), False


def _title(category: Category) -> str:
    return (
        rng.choice(TITLES[category])
        .replace("{colour}", rng.choice(COLOURS))
        .replace("{size}", rng.choice(SIZES))
    )


def _subcategory(category: Category, title: str) -> str | None:
    if category is not Category.FURNITURE:
        return None
    lower = title.lower()
    for word, sub in SUBCATEGORY_FOR_TITLE.items():
        if word in lower:
            return sub
    return "sofas_tables"


def _posted_at(now: datetime) -> datetime:
    """Weighted by month so May and August spike."""
    for _ in range(50):
        days_back = rng.randint(0, 420)
        candidate = now - timedelta(days=days_back)
        if rng.random() < MONTH_WEIGHT[candidate.month] / 3.0:
            return candidate
    return now - timedelta(days=rng.randint(0, 420))


# ---------------------------------------------------------------- seeding


def _make_user(i: int, now: datetime) -> User:
    username = f"cu_{i:04d}"
    has_phone = rng.random() > 0.30  # ~30% leave it blank, on purpose
    return User(
        email=f"{username}@columbia.edu",
        username=username,
        display_name=None,
        phone=f"+1646555{rng.randint(1000, 9999)}" if has_phone else None,
        phone_contact_enabled=has_phone and rng.random() > 0.1,
        nationality=rng.choice(NATIONALITIES),
        school=rng.choice(SCHOOLS),
        grade=rng.choice(GRADES),
        zip_code=rng.choice(ZIPS_POOL),
        is_verified=True,
        created_at=now - timedelta(days=rng.randint(1, 700)),
    )


def _make_listing(seller: User, now: datetime, *, fresh: bool = False) -> Listing:
    category = rng.choice(CATEGORY_POOL)
    price_cents, is_free = _price_cents(category)
    title = _title(category)
    posted = now - timedelta(hours=rng.randint(1, 72)) if fresh else _posted_at(now)
    listing = Listing(
        seller_id=seller.id,
        title=title,
        description=rng.choice(DESCRIPTIONS),
        category=category,
        subcategory=_subcategory(category, title),
        condition=rng.choice(CONDITION_POOL),
        price_cents=price_cents,
        is_free=is_free,
        is_negotiable=rng.random() < 0.45,
        zip_code=seller.zip_code,
        status=ListingStatus.ACTIVE,
        posted_at=posted,
    )
    if fresh:
        return listing
    # ~35% sell, median about six days; ~5% are reserved.
    if rng.random() < 0.35:
        listing.status = ListingStatus.SOLD
        listing.sold_at = posted + timedelta(days=max(0.2, rng.lognormvariate(1.7, 0.9)))
        if listing.sold_at > now:
            listing.status = ListingStatus.ACTIVE
            listing.sold_at = None
    elif rng.random() < 0.05:
        listing.status = ListingStatus.RESERVED
    return listing


def seed(n_users: int, n_listings: int, do_reset: bool, demo_email: str | None = None) -> None:
    if do_reset:
        reset_all()
    else:
        create_all()
    db = SessionLocal()
    now = datetime.now(timezone.utc)

    # ---- users
    users = [_make_user(i, now) for i in range(n_users)]

    demo: User | None = None
    if demo_email:
        demo_email = domains.normalize(demo_email)
        if not domains.is_allowed(demo_email):
            raise SystemExit(domains.rejection_reason(demo_email))
        demo = User(
            email=demo_email,
            username=demo_email.split("@")[0].replace(".", "_")[:20],
            phone="+16465550142",
            nationality="IN",
            school=domains.suggested_school(demo_email) or School.SEAS_GRAD,
            grade=Grade.GRADUATE,
            zip_code="10027",
            is_verified=True,
            created_at=now - timedelta(days=30),
        )
        users.append(demo)

    db.add_all(users)
    db.commit()

    # ---- listings
    listings = [_make_listing(rng.choice(users), now) for _ in range(n_listings)]
    if demo is not None:
        listings.extend(_make_listing(demo, now, fresh=True) for _ in range(3))
    db.add_all(listings)
    db.commit()

    # ---- events
    # One base rate for everyone. Any difference the analysis finds must come
    # from the data, not from this generator.
    views, saves, enquiries, filter_events = [], [], [], []
    for listing in listings:
        age_days = max(1, (now - listing.posted_at.replace(tzinfo=timezone.utc)).days)
        n_views = max(0, int(rng.lognormvariate(3.0, 0.9) * min(age_days, 30) / 30))
        listing.view_count = n_views

        for _ in range(n_views):
            viewer = rng.choice(users)
            views.append(
                ListingView(
                    listing_id=listing.id,
                    viewer_id=viewer.id,
                    surface=rng.choice([ViewSurface.FEED, ViewSurface.SEARCH, ViewSurface.DETAIL]),
                    badges_shown=True,
                    viewed_at=listing.posted_at + timedelta(hours=rng.randint(0, 24 * min(age_days, 30))),
                )
            )

        n_saves = sum(1 for _ in range(n_views) if rng.random() < 0.08)
        savers = rng.sample(users, min(n_saves, len(users)))
        listing.save_count = len(savers)
        saves.extend(Save(listing_id=listing.id, user_id=u.id) for u in savers)

        n_enq = sum(1 for _ in range(n_views) if rng.random() < 0.01)
        listing.enquiry_count = n_enq
        for _ in range(n_enq):
            buyer = rng.choice(users)
            channel = (
                EnquiryChannel.SMS
                if listing.seller.can_receive_sms and rng.random() < 0.35
                else EnquiryChannel.EMAIL
            )
            enquiries.append(Enquiry(listing_id=listing.id, buyer_id=buyer.id, channel=channel))

    # Filter events, so Q3 has something to read on a fresh database.
    keys = ["same_zip", "same_nationality", "same_school", "radius_mi", "category", "price"]
    for _ in range(n_listings * 2):
        key = rng.choice(keys)
        filter_events.append(
            FilterEvent(
                user_id=rng.choice(users).id,
                filter_key=key,
                value=(
                    rng.choice(["0.5", "1", "2.5", "5", "10"])
                    if key == "radius_mi"
                    else rng.choice(["true", "false"])
                ),
                result_count=rng.randint(3, 900),
                created_at=now - timedelta(days=rng.randint(0, 120)),
            )
        )

    db.add_all(views)
    db.add_all(saves)
    db.add_all(enquiries)
    db.add_all(filter_events)
    db.commit()

    print(
        f"Seeded {len(users)} users "
        f"({sum(1 for u in users if u.phone is None)} without a phone number), "
        f"{len(listings)} listings, {len(views)} views, {len(saves)} saves, "
        f"{len(enquiries)} enquiries."
    )
    if demo is not None:
        print(f"Demo account: {demo.email} (@{demo.username}) — sign in with a link from /signin.")
    db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--users", type=int, default=1000)
    parser.add_argument("--listings", type=int, default=1500)
    parser.add_argument("--reset", action="store_true", help="drop and recreate every table first")
    parser.add_argument("--demo-email", help="also create an account for this Columbia address")
    args = parser.parse_args()

    seed(args.users, args.listings, args.reset, args.demo_email)
