"""Listing and photo generation (UX_SPEC §4.2/§4.3, distributions from §9).

Three things here are not independent draws, and each one exists because a screen
would otherwise show something impossible.

**Sellers are Zipf-shaped, not uniform.** §6.4 puts a "more from this seller" rail
on the item detail page, which only means anything if some people are liquidating
a whole apartment while most post once. Roughly half of all sellers post a single
item; the top few percent hold a quarter of the inventory.

**Sold-ness is derived from time, not assigned.** Drawing ``status`` directly
would produce listings posted twelve minutes ago and already sold. Instead each
internal listing gets a *will it ever sell* coin flip and a days-to-sale draw, and
becomes ``sold`` only if that date has already passed. Recent listings are
therefore mostly still active for the same reason they are in real life, and the
days-to-sale figures the analysis computes are honestly right-censored.

**Pickup ZIP equals the seller's ZIP.** §5.2 measures distance from
``listings.zip_code`` while §5.3 computes the SAME ZIP badge from
``users.zip_code``. If those can differ, a listing can carry a SAME ZIP badge
while displaying three miles. Locking them makes that unrepresentable. See the
open question in docs/mock_data_spec.md.
"""

from __future__ import annotations

import bisect
import datetime as dt
import math
import uuid

from . import catalog as C
from . import vocabularies as V
from . import zips as Z

# ---------------------------------------------------------------------------
# Seasonality  (UX_SPEC §9)
#
# "listing volume should spike in May (cohort liquidates) and August (cohort
# arrives). Make the spike roughly 3x the trough."
# ---------------------------------------------------------------------------

MONTH_MULTIPLIER: "dict[int, float]" = {
    1: 1.0,   # January intake, modest
    2: 0.9,
    3: 0.9,   # trough
    4: 1.3,   # move-out begins
    5: 3.0,   # cohort liquidates
    6: 1.6,
    7: 1.4,
    8: 3.0,   # cohort arrives
    9: 1.8,
    10: 1.0,
    11: 0.9,
    12: 1.1,
}

# Platform growth, separate from the season. §9's research question is whether the
# season is real "normalized so platform growth doesn't fake it", so the two
# effects have to be separable rather than baked into one curve.
GROWTH_DOUBLING_DAYS = 300.0

# §9: "~35% of internal listings get a sold_at, median ~6 days after posting".
# This is the *eventual* sell probability; censoring by `now` brings the realised
# share down to roughly the 35% the spec asks for.
SELL_EVENTUALLY_RATE = 0.36
DAYS_TO_SELL_MEDIAN = 6.0
DAYS_TO_SELL_SIGMA = 0.95

# Of the listings that have not sold: §4.5 has draft and reserved, and §6.4 gives
# reserved its own rendering, so both need rows.
DRAFT_RATE = 0.03
RESERVED_RATE = 0.07

# §4.3: max 10, position 0 is the cover. Median 4 matches the "4 / 10" counter on
# the upload screen and the five thumbnails on item detail.
PHOTO_COUNT_WEIGHTS: "dict[int, float]" = {
    1: 10.0, 2: 14.0, 3: 20.0, 4: 22.0, 5: 15.0,
    6: 8.0, 7: 5.0, 8: 3.0, 9: 2.0, 10: 1.0,
}

# §9: "~150 listings across ebay, facebook, karrot".
EXTERNAL_SOURCE_WEIGHTS: "dict[str, float]" = {
    "ebay": 45.0,
    "facebook": 40.0,
    "karrot": 15.0,
}

_EXTERNAL_URL_SHAPE = {
    "ebay": "https://www.ebay.com/itm/%d",
    "facebook": "https://www.facebook.com/marketplace/item/%d",
    "karrot": "https://us.karrotmarket.com/articles/%d",
}


def _weighted(rng, weights):
    total = sum(weights.values())
    r = rng.random() * total
    acc = 0.0
    for key, w in weights.items():
        acc += w
        if r <= acc:
            return key
    return next(reversed(list(weights)))


# ---------------------------------------------------------------------------
# Posting dates
# ---------------------------------------------------------------------------


def _day_weights(start: dt.date, end: dt.date) -> "tuple[list[dt.date], list[float]]":
    """One weight per day: month seasonality times the growth curve."""
    days, cumulative, acc = [], [], 0.0
    span_days = max((end - start).days, 1)
    day = start
    while day <= end:
        age = (day - start).days
        growth = 2.0 ** (age / GROWTH_DOUBLING_DAYS)
        acc += MONTH_MULTIPLIER[day.month] * growth
        days.append(day)
        cumulative.append(acc)
        day += dt.timedelta(days=1)
    del span_days
    return days, cumulative


def _draw_day(rng, days, cumulative) -> dt.date:
    r = rng.random() * cumulative[-1]
    return days[bisect.bisect_left(cumulative, r)]


# ---------------------------------------------------------------------------
# Seller assignment
# ---------------------------------------------------------------------------


class _SellerPool:
    """Users sorted by join date, with Zipf-ish posting propensities.

    Sampling is restricted to members who had already joined on the posting date,
    which is what enforces ``posted_at >= seller.created_at`` by construction
    rather than by a repair pass afterwards.
    """

    def __init__(self, rng, users):
        eligible = [u for u in users if u["status"] == "active" and u["is_verified"]]
        eligible.sort(key=lambda u: u["created_at"])
        self.users = eligible
        self.joined = [u["created_at"] for u in eligible]
        # Pareto tail: most people post once or twice, a few liquidate a flat.
        # alpha is 2.3 rather than the more conventional 1.2-1.5 because a heavier
        # tail hands one member 70+ listings, which is a warehouse, not a student
        # moving out. This keeps the biggest seller near 20.
        self.cumulative, acc = [], 0.0
        for _ in eligible:
            acc += rng.paretovariate(2.3)
            self.cumulative.append(acc)

    def draw(self, rng, when: dt.datetime):
        limit = bisect.bisect_right(self.joined, when)
        if limit == 0:
            return None
        ceiling = self.cumulative[limit - 1]
        r = rng.random() * ceiling
        return self.users[bisect.bisect_left(self.cumulative, r, 0, limit)]


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def _draw_condition(rng, category: str) -> str:
    return _weighted(rng, C.CONDITION_WEIGHTS[category])


def _draw_photo_count(rng, price_cents: int) -> int:
    """More photos on more expensive items -- people try harder for a $340 chair."""
    weights = dict(PHOTO_COUNT_WEIGHTS)
    if price_cents >= 15000:
        for n in (5, 6, 7, 8):
            weights[n] *= 2.0
        weights[1] *= 0.4
    elif price_cents == 0:
        weights[1] *= 2.5
        weights[2] *= 1.5
    return int(_weighted(rng, weights))


def _make_photos(rng, listing_id: str, count: int, posted_at: dt.datetime) -> "list[dict]":
    return [
        {
            "id": str(uuid.UUID(int=rng.getrandbits(128), version=4)),
            "listing_id": listing_id,
            # Root-relative. A bare "photos/..." resolves against the current
            # path, so it works on the feed at "/" and 404s on the detail page
            # at "/listings/<id>", which is exactly the bug it caused.
            "url": "/photos/%s/%d.webp" % (listing_id, position),
            "position": position,
            "created_at": posted_at,
        }
        for position in range(count)
    ]


def generate_listings(rng, users, internal_count, external_count, now):
    """Return ``(listings, photos)``.

    Counters (``view_count`` / ``save_count`` / ``enquiry_count``) are left at
    zero here and backfilled from the event tables in :mod:`seed.events` -- §4.2
    has them as columns, but they are summaries, not independent facts.
    """
    pool = _SellerPool(rng, users)
    if not pool.users:
        raise ValueError("no eligible sellers: every user is deactivated or unverified")

    start = min(u["created_at"] for u in users).date()
    days, cumulative = _day_weights(start, now.date())

    listings: "list[dict]" = []
    photos: "list[dict]" = []

    # ---- internal tier ----
    attempts = 0
    while len([l for l in listings if l["source"] == "internal"]) < internal_count:
        attempts += 1
        if attempts > internal_count * 20:
            raise RuntimeError("could not place %d internal listings" % internal_count)

        day = _draw_day(rng, days, cumulative)
        posted_at = dt.datetime.combine(day, dt.time(0)) + dt.timedelta(
            seconds=rng.randint(0, 86399)
        )
        if posted_at > now:
            continue
        seller = pool.draw(rng, posted_at)
        if seller is None:
            continue

        category = _weighted(rng, C.CATEGORY_WEIGHTS)
        subcategory, title, band, photo_query = C.draw_item(rng, category)
        condition = _draw_condition(rng, category)

        if category == "free_stuff":
            is_free = True
        else:
            is_free = rng.random() < C.FREE_GIVEAWAY_RATE
        price_cents = 0 if is_free else C.draw_price_cents(rng, category, condition, band)
        # §4.2: is_free is "mutually exclusive with a non-zero price". A price of
        # zero drawn any other way is still a giveaway, so keep the flag in step.
        if price_cents == 0:
            is_free = True

        status, sold_at = _resolve_status(rng, posted_at, now)

        listing_id = str(uuid.UUID(int=rng.getrandbits(128), version=4))
        listings.append({
            "id": listing_id,
            "seller_id": seller["id"],
            "source": "internal",
            "title": title,
            "description": C.draw_description(rng, condition),
            "category": category,
            "subcategory": subcategory,
            "condition": condition,
            "price_cents": price_cents,
            "is_free": is_free,
            "is_negotiable": (not is_free) and rng.random() < C.NEGOTIABLE_RATE,
            # Locked to the seller's ZIP -- see the module docstring.
            "zip_code": seller["zip_code"],
            "status": status,
            "view_count": 0,
            "save_count": 0,
            "enquiry_count": 0,
            "external_url": None,
            "posted_at": posted_at,
            "sold_at": sold_at,
            # Not a column. Generator metadata for scripts/fetch_photos.py,
            # written to data/photo_queries.csv rather than into listings.csv --
            # the schema in UX_SPEC §4.2 has no room for it and should not.
            "_photo_query": photo_query,
        })
        photos.extend(
            _make_photos(rng, listing_id, _draw_photo_count(rng, price_cents), posted_at)
        )

    # ---- external tier (§5.5) ----
    # No seller, no badges, always a link out. External listings are scraped
    # snapshots, so they are current by construction and never carry a sold_at.
    external_zip_weights = {
        z: 1.0 / (1.0 + Z.ZIPS[z].miles_from_campus) for z in Z.ZIP_CODES
    }
    for _ in range(external_count):
        source = _weighted(rng, EXTERNAL_SOURCE_WEIGHTS)
        category = _weighted(rng, C.CATEGORY_WEIGHTS)
        subcategory, title, band, photo_query = C.draw_item(rng, category)
        condition = _draw_condition(rng, category)
        is_free = category == "free_stuff"
        price_cents = 0 if is_free else C.draw_price_cents(rng, category, condition, band)
        if price_cents == 0:
            is_free = True

        posted_at = now - dt.timedelta(
            days=rng.expovariate(1 / 9.0), seconds=rng.randint(0, 86399)
        )
        listing_id = str(uuid.UUID(int=rng.getrandbits(128), version=4))
        listings.append({
            "id": listing_id,
            "seller_id": None,
            "source": source,
            "title": title,
            "description": C.draw_description(rng, condition),
            "category": category,
            "subcategory": subcategory,
            "condition": condition,
            "price_cents": price_cents,
            "is_free": is_free,
            "is_negotiable": False,
            "zip_code": _weighted(rng, external_zip_weights),
            "status": "active",
            "view_count": 0,
            "save_count": 0,
            "enquiry_count": 0,
            "external_url": _EXTERNAL_URL_SHAPE[source] % rng.randint(10**11, 10**12 - 1),
            "posted_at": posted_at,
            "sold_at": None,
            "_photo_query": photo_query,
        })
        photos.extend(
            _make_photos(rng, listing_id, rng.randint(1, 4), posted_at)
        )

    listings.sort(key=lambda l: l["posted_at"])
    return listings, photos


def _resolve_status(rng, posted_at: dt.datetime, now: dt.datetime):
    """Decide status and sold_at from elapsed time rather than by fiat."""
    if rng.random() < SELL_EVENTUALLY_RATE:
        days = math.exp(rng.gauss(math.log(DAYS_TO_SELL_MEDIAN), DAYS_TO_SELL_SIGMA))
        sold_at = posted_at + dt.timedelta(days=days)
        if sold_at <= now:
            return "sold", sold_at
        # It will sell, but not yet -- so today it is still on the feed.
    roll = rng.random()
    if roll < DRAFT_RATE:
        return "draft", None
    if roll < DRAFT_RATE + RESERVED_RATE:
        return "reserved", None
    return "active", None
