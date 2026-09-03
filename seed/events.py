"""The four event tables (UX_SPEC §4.4), and the counter backfill.

§9 fixes the funnel: "views >> saves >> enquiries (roughly 100 : 8 : 1)". The
important structural decision is that these are generated *as one funnel* -- a
save is drawn from a view that happened, an enquiry from a save-eligible view --
rather than as three independent per-listing numbers. That is what lets
``listings.view_count`` and friends be a true ``COUNT(*)`` over these tables
instead of three decorative integers that disagree with them.

Two couplings the spec forces:

* **§5.1** -- an ``sms`` enquiry is only possible when the seller supplied a phone
  *and* left texting enabled. Email is always available and "can never be turned
  off", so every other enquiry is email.
* **§5.5** -- external listings have no seller, so they collect views and saves
  but can never produce an enquiry; the contact button links out instead.

The one thing §9 explicitly forbids is planting the finding: "do not hard-code a
difference -- generate both tiers with the same base rates and let the analysis
find (or fail to find) the effect". So the view model below reads only from
listing age, photo count and price. It never looks at ``source``, and it never
looks at whether a badge would be shown.
"""

from __future__ import annotations

import bisect
import datetime as dt
import math
import uuid

from . import vocabularies as V
from . import zips as Z

# ---------------------------------------------------------------------------
# Funnel rates  (UX_SPEC §9: roughly 100 : 8 : 1)
# ---------------------------------------------------------------------------

# Slightly above 8% because the (user, listing) uniqueness constraint drops
# repeat saves; the realised rate lands on §9's 8%.
SAVE_RATE_PER_VIEW = 0.088
ENQUIRY_RATE_PER_VIEW = 0.010

# Of enquiries where the seller accepts texts, how many use it rather than email.
SMS_SHARE_WHEN_AVAILABLE = 0.35

# §4.4 surfaces. Most impressions are the feed itself.
SURFACE_WEIGHTS = {"feed": 0.70, "search": 0.20, "detail": 0.10}

# View volume model. Deliberately blind to source and to badges.
VIEW_BASE = 4.0
VIEW_PER_SQRT_DAY = 3.2
VIEW_SIGMA = 0.75

FILTER_SESSIONS = 900
FILTER_ACTIONS_PER_SESSION = (2, 6)

# ---------------------------------------------------------------------------
# Planted effects  (added 2026-09-03)
#
# Every number below puts structure into the data that the analysis will then
# "find". None of it is a discovery. They are listed here, in one block, so the
# write-up can state exactly what was assumed — see docs/mock_data_spec.md §9.
#
# The rule that decides whether an effect belongs here: would a reader mistake
# the chart for evidence about the real world? If yes, it must be declared.
# ---------------------------------------------------------------------------

# The badge experiment (UX_SPEC §5.3). Half of impressions show match badges;
# those impressions convert to an enquiry BADGE_LIFT times as often. This is the
# effect the two-proportion test in the notebook is meant to recover, so it has
# to be planted for the test to have anything to measure.
BADGE_SHOWN_RATE = 0.50
BADGE_LIFT = 1.35

# Sharing attributes with the seller raises engagement independently of whether
# the badge is displayed — the product's actual thesis. Multiplier per shared
# attribute (ZIP, nationality, school), compounding.
OVERLAP_ENGAGEMENT_LIFT = 1.18

# People look at things near them. Weight on choosing a viewer for a listing,
# by distance between their ZIPs.
DISTANCE_DECAY_MILES = 3.5

# Sellers discount for people they have something in common with. Applied to the
# sale price, per shared attribute.
IN_GROUP_DISCOUNT = 0.04

# Of listings that sell, the share where the buyer is someone who had enquired
# through the app. The rest sold to a friend or off-platform, and keep a NULL
# buyer — which is itself a number worth charting.
BUYER_FROM_ENQUIRY_RATE = 0.72

# Sessionisation: the industry-standard 30-minute inactivity gap. A person's
# events are grouped into visits, so the funnel is a real join rather than a
# guess over a time window.
SESSION_GAP_MINUTES = 30


def _weighted(rng, weights):
    total = sum(weights.values())
    r = rng.random() * total
    acc = 0.0
    for key, w in weights.items():
        acc += w
        if r <= acc:
            return key
    return next(reversed(list(weights)))


def _shared_attributes(viewer, seller) -> int:
    """How many of the three badge attributes this pair share (UX_SPEC §5.3)."""
    if seller is None or viewer["id"] == seller["id"]:
        return 0
    return sum((
        viewer["zip_code"] == seller["zip_code"],
        viewer["nationality"] == seller["nationality"],
        viewer["school"] == seller["school"],
    ))


def _live_days(listing, now):
    end = listing["sold_at"] or now
    return max((min(end, now) - listing["posted_at"]).total_seconds() / 86400.0, 0.02)


def _expected_views(rng, listing, photo_count, now):
    """Median views for a listing, from age, photos and price only."""
    days = _live_days(listing, now)
    median = VIEW_BASE + VIEW_PER_SQRT_DAY * math.sqrt(days)

    # More photos, more clicks -- the upload screen says as much in its own hint.
    if photo_count >= 5:
        median *= 1.25
    elif photo_count <= 1:
        median *= 0.70

    # Free things get looked at more than they get taken.
    if listing["price_cents"] == 0:
        median *= 1.6
    elif listing["price_cents"] > 25000:
        median *= 0.80

    return max(1.0, math.exp(rng.gauss(math.log(median), VIEW_SIGMA)))


def generate_events(rng, users, listings, photos, now):
    """Return ``(listing_views, saves, enquiries, filter_events, searches)``.

    Counters on the listing rows are updated in place, so after this call
    ``view_count`` equals the number of ``listing_views`` rows referencing it.
    """
    photo_counts: "dict[str, int]" = {}
    for photo in photos:
        photo_counts[photo["listing_id"]] = photo_counts.get(photo["listing_id"], 0) + 1

    users_by_id = {u["id"]: u for u in users}
    viewers = [u for u in users if u["is_verified"]]
    viewers.sort(key=lambda u: u["created_at"])
    joined = [u["created_at"] for u in viewers]

    views: "list[dict]" = []
    saves: "list[dict]" = []
    enquiries: "list[dict]" = []
    saved_pairs: "set[tuple[str, str]]" = set()

    for listing in listings:
        # §4.5: a draft was never published, so nobody has seen it.
        if listing["status"] == "draft":
            continue

        photo_count = photo_counts.get(listing["id"], 1)
        target = int(round(_expected_views(rng, listing, photo_count, now)))
        window_end = min(listing["sold_at"] or now, now)
        window = (window_end - listing["posted_at"]).total_seconds()
        if window <= 0:
            continue

        seller_id = listing["seller_id"]
        seller = users_by_id.get(seller_id) if seller_id else None

        for _ in range(target):
            # Views cluster early in a listing's life; sqrt biases towards the
            # first days without excluding the tail.
            at = listing["posted_at"] + dt.timedelta(
                seconds=window * (rng.random() ** 2)
            )
            if at > now:
                continue

            # §6.2: "There is no browsing without an account in the pilot", so a
            # viewer is always attributable. The column stays nullable because a
            # deactivated account's rows outlive its profile.
            limit = bisect.bisect_right(joined, at)
            if limit == 0:
                continue
            # People look at things near them. Rejection-sample a viewer against
            # distance rather than picking uniformly, so the feed's own radius
            # behaviour shows up in the event data too.
            viewer = None
            for _attempt in range(4):
                candidate = viewers[rng.randrange(limit)]
                miles = Z.distance_mi(candidate["zip_code"], listing["zip_code"])
                if rng.random() < math.exp(-miles / DISTANCE_DECAY_MILES):
                    viewer = candidate
                    break
            if viewer is None:
                continue
            # A seller looking at their own listing is the D10 owner view, not a
            # feed impression.
            if seller_id is not None and viewer["id"] == seller_id:
                continue

            # The experiment's coin flip, per impression (UX_SPEC §5.3).
            badges_shown = rng.random() < BADGE_SHOWN_RATE

            # How much this pair actually has in common, badge or no badge.
            shared = _shared_attributes(viewer, seller)
            engagement = OVERLAP_ENGAGEMENT_LIFT ** shared

            views.append({
                "id": str(uuid.UUID(int=rng.getrandbits(128), version=4)),
                "listing_id": listing["id"],
                "viewer_id": viewer["id"],
                "viewed_at": at,
                "surface": _weighted(rng, SURFACE_WEIGHTS),
                "badges_shown": badges_shown,
            })

            if rng.random() < SAVE_RATE_PER_VIEW * engagement:
                pair = (viewer["id"], listing["id"])
                if pair not in saved_pairs:
                    saved_pairs.add(pair)
                    saves.append({
                        "id": str(uuid.UUID(int=rng.getrandbits(128), version=4)),
                        "listing_id": listing["id"],
                        "user_id": viewer["id"],
                        # A save follows its view by a moment, but never lands
                        # after `now` -- a view at 17:59 must not save at 18:04.
                        "created_at": min(
                            at + dt.timedelta(seconds=rng.randint(5, 900)), now),
                    })

            # §5.5: no seller, no contact -- an external card links out instead.
            enquiry_p = ENQUIRY_RATE_PER_VIEW * engagement
            if badges_shown:
                enquiry_p *= BADGE_LIFT
            if seller is not None and rng.random() < enquiry_p:
                sms_possible = bool(seller["phone"]) and seller["phone_contact_enabled"]
                channel = "email"
                if sms_possible and rng.random() < SMS_SHARE_WHEN_AVAILABLE:
                    channel = "sms"
                enquiries.append({
                    "id": str(uuid.UUID(int=rng.getrandbits(128), version=4)),
                    "listing_id": listing["id"],
                    "buyer_id": viewer["id"],
                    "channel": channel,
                    "created_at": min(
                        at + dt.timedelta(seconds=rng.randint(30, 3600)), now),
                })

    _backfill_counters(listings, views, saves, enquiries)
    filter_events = _generate_filter_events(rng, users, listings, now)

    # Three passes that need the events to already exist.
    searches = generate_searches(rng, users, listings, views, now)
    assign_buyers(rng, listings, enquiries, views, users, now)
    cluster_into_visits(rng, users, listings, views, saves, enquiries,
                        filter_events, searches, now)
    sessionise(views, saves, enquiries, filter_events, searches)
    # Enquiries may have grown in assign_buyers, so recount.
    _backfill_counters(listings, views, saves, enquiries)

    return views, saves, enquiries, filter_events, searches


def _backfill_counters(listings, views, saves, enquiries):
    """§4.2's three counters are summaries of §4.4, so they are counted, not drawn."""
    by_id = {l["id"]: l for l in listings}
    for listing in listings:
        listing["view_count"] = 0
        listing["save_count"] = 0
        listing["enquiry_count"] = 0
    for row in views:
        by_id[row["listing_id"]]["view_count"] += 1
    for row in saves:
        by_id[row["listing_id"]]["save_count"] += 1
    for row in enquiries:
        by_id[row["listing_id"]]["enquiry_count"] += 1


# ---------------------------------------------------------------------------
# filter_events
# ---------------------------------------------------------------------------

_TOGGLE_KEYS = ("same_zip", "same_nationality", "same_school")


def _generate_filter_events(rng, users, listings, now):
    """Simulate short filtering sessions, logging the real count after each change.

    §4.4: "log every toggle and every slider release" -- this is what answers
    which filter is doing the work, and where people give up. The
    ``result_count`` on each row is evaluated against the corpus *as it stood at
    that moment*, so a toggle logged eight months ago does not see listings
    posted since.
    """
    from .feed import Feed

    feed = Feed(listings, users)
    candidates = [u for u in users if u["is_verified"] and u["status"] == "active"]
    if not candidates:
        return []

    rows: "list[dict]" = []
    earliest = min(l["posted_at"] for l in listings)

    for _ in range(FILTER_SESSIONS):
        user = rng.choice(candidates)
        start = max(user["created_at"], earliest)
        if start >= now:
            continue
        span = (now - start).total_seconds()
        at = start + dt.timedelta(seconds=rng.random() * span)

        state = feed.default_state_for(user)
        actions = rng.randint(*FILTER_ACTIONS_PER_SESSION)
        for _ in range(actions):
            key = rng.choice(_TOGGLE_KEYS + ("radius_mi", "category", "condition"))

            if key in _TOGGLE_KEYS:
                value = not getattr(state, key)
                state = state.replace(**{key: value})
                logged = "on" if value else "off"
            elif key == "radius_mi":
                value = rng.choice(V.RADIUS_PRESETS_MI)
                state = state.replace(radius_mi=value)
                logged = str(value)
            elif key == "category":
                value = rng.choice(V.CATEGORIES)
                current = set(state.categories or ())
                if value in current:
                    current.discard(value)
                else:
                    current.add(value)
                state = state.replace(categories=sorted(current) or None)
                logged = ",".join(sorted(current)) or "(cleared)"
            else:
                value = rng.choice(V.CONDITIONS)
                current = set(state.conditions or ())
                if value in current:
                    current.discard(value)
                else:
                    current.add(value)
                state = state.replace(conditions=sorted(current) or None)
                logged = ",".join(sorted(current)) or "(cleared)"

            at = at + dt.timedelta(seconds=rng.randint(3, 90))
            if at > now:
                break

            rows.append({
                "id": str(uuid.UUID(int=rng.getrandbits(128), version=4)),
                "user_id": user["id"],
                "filter_key": key,
                "value": logged,
                "result_count": feed.count(user, state, as_of=at),
                "created_at": at,
            })

    rows.sort(key=lambda r: r["created_at"])
    return rows


# ---------------------------------------------------------------------------
# Sessions, searches and buyers  (added 2026-09-03)
#
# Three passes that run after the event tables exist, because each one needs
# them: a session is a grouping of events, a search is compared against the
# corpus, and a buyer is chosen from the people who enquired.
# ---------------------------------------------------------------------------


# Target events per visit. Visits are derived from how much a member actually
# did, not from a fixed rate: with ~66 views each over two years, a fixed rate
# either invents visits with nothing in them or crams a year into one.
EVENTS_PER_VISIT = 7
VISIT_LENGTH_MINUTES = 18


def cluster_into_visits(rng, users, listings, views, saves, enquiries,
                        filter_events, searches, now):
    """Move each person's events onto a handful of browsing visits.

    Events are generated independently — a view is drawn from its listing's own
    lifetime — so a person's activity ends up scattered across two years and
    every event lands in a session of one. Real browsing is bursty: you open the
    app, look at eight things, and leave.

    So each member gets a set of visit timestamps, and every event of theirs is
    snapped to the nearest visit that is *legal for that event* — a view cannot
    move outside the window in which its listing was actually on the feed. When
    no visit fits, the event keeps its own time and becomes a session of one,
    which is a real pattern too.

    This changes timestamps by hours, never by which day-of-week or season they
    land in, so the seasonality and time-to-sale figures are unaffected.
    """
    window: "dict[str, tuple]" = {}
    for l in listings:
        end = min(l["sold_at"] or now, now)
        window[l["id"]] = (l["posted_at"], end)

    # How much each member did, so the number of visits matches it.
    load: "dict[str, int]" = {}
    for rows, key in ((views, "viewer_id"), (saves, "user_id"),
                      (enquiries, "buyer_id"), (filter_events, "user_id"),
                      (searches, "user_id")):
        for row in rows:
            uid = row.get(key)
            if uid:
                load[uid] = load.get(uid, 0) + 1

    visits: "dict[str, list]" = {}
    for u in users:
        events = load.get(u["id"], 0)
        if events == 0:
            continue
        span_days = max((now - u["created_at"]).days, 1)
        count = max(1, round(events / EVENTS_PER_VISIT))
        times = sorted(
            u["created_at"] + dt.timedelta(seconds=rng.random() * span_days * 86400)
            for _ in range(count)
        )
        visits[u["id"]] = times

    def snap(user_id, when, legal):
        times = visits.get(user_id)
        if not times:
            return when
        low, high = legal
        best, best_gap = None, None
        i = bisect.bisect_left(times, when)
        for j in (i - 1, i, i + 1):
            if 0 <= j < len(times):
                t = times[j]
                if low <= t <= high:
                    gap = abs((t - when).total_seconds())
                    if best_gap is None or gap < best_gap:
                        best, best_gap = t, gap
        if best is None:
            return when
        # Land somewhere inside the visit, not all at the same instant.
        out = best + dt.timedelta(seconds=rng.randint(0, VISIT_LENGTH_MINUTES * 60))
        return min(max(out, low), high)

    for row in views:
        legal = window.get(row["listing_id"])
        if legal:
            row["viewed_at"] = snap(row["viewer_id"], row["viewed_at"], legal)
    # A save or an enquiry follows its view, so it belongs to the same visit.
    for rows, user_key in ((saves, "user_id"), (enquiries, "buyer_id")):
        for row in rows:
            legal = window.get(row["listing_id"])
            if legal:
                row["created_at"] = snap(row[user_key], row["created_at"], legal)
    for rows in (filter_events, searches):
        for row in rows:
            if row.get("user_id"):
                row["created_at"] = snap(
                    row["user_id"], row["created_at"],
                    (row["created_at"] - dt.timedelta(days=30), now))


def sessionise(views, saves, enquiries, filter_events, searches):
    """Group every event into visits and stamp a `session_id` on each.

    Definition: one person's events, split wherever they go quiet for
    SESSION_GAP_MINUTES. That is the same rule Google Analytics uses, and it is
    chosen deliberately over inventing a session at generation time — the events
    were produced independently, so grouping them afterwards is both simpler and
    closer to how a real pipeline would derive sessions from a raw log.

    Returns the number of sessions created.
    """
    streams = (
        (views, "viewer_id", "viewed_at"),
        (saves, "user_id", "created_at"),
        (enquiries, "buyer_id", "created_at"),
        (filter_events, "user_id", "created_at"),
        (searches, "user_id", "created_at"),
    )

    by_user: "dict[str, list]" = {}
    for rows, user_key, time_key in streams:
        for row in rows:
            user = row.get(user_key)
            if user is None:
                row["session_id"] = None
                continue
            by_user.setdefault(user, []).append((row[time_key], row))

    gap = dt.timedelta(minutes=SESSION_GAP_MINUTES)
    sessions = 0
    for user, events in by_user.items():
        events.sort(key=lambda pair: pair[0])
        current = None
        previous = None
        for when, row in events:
            if previous is None or (when - previous) > gap:
                # A session id derived from the user and the visit's first
                # timestamp, so it is stable across regenerations.
                current = str(uuid.uuid5(
                    uuid.NAMESPACE_URL, "%s:%s" % (user, when.isoformat())))
                sessions += 1
            row["session_id"] = current
            previous = when
    return sessions


# What people type. Drawn from the catalogue's own vocabulary so the queries
# look like things this marketplace actually sells, plus a tail of misses that
# return nothing — the empty-result rate is one of the more useful charts.
_SEARCH_HITS = (
    "desk", "ikea desk", "standing desk", "office chair", "monitor", "laptop",
    "textbook", "corporate finance", "rice cooker", "microwave", "mini fridge",
    "winter coat", "parka", "boots", "bike", "mattress", "sofa", "coffee table",
    "bookshelf", "lamp", "kettle", "airpods", "headphones", "ipad", "yoga mat",
    "free", "vacuum", "dresser", "kitchen", "printer",
)
_SEARCH_MISSES = (
    "car", "apartment", "sublet", "concert tickets", "airpods max", "ps5",
    "iphone 15", "guitar", "cat", "textbook rental",
)
SEARCHES_PER_1000_VIEWS = 42
SEARCH_CLICK_RATE = 0.38


def generate_searches(rng, users, listings, views, now):
    """Free-text searches, with what came back and whether it led anywhere.

    `filter_events` already covers structured toggles; a typed query is a
    different act and answers different questions — what people look for by
    name, and which searches come back empty.
    """
    candidates = [u for u in users if u["is_verified"] and u["status"] == "active"]
    if not candidates or not views:
        return []

    # Match against real titles, so result_count is honest rather than invented.
    live = [l for l in listings if l["status"] in V.FEED_VISIBLE_STATUSES]
    titles = [(l["id"], l["title"].lower()) for l in live]

    total = max(1, int(len(views) * SEARCHES_PER_1000_VIEWS / 1000))
    rows = []
    for _ in range(total):
        user = rng.choice(candidates)
        miss = rng.random() < 0.18
        query = rng.choice(_SEARCH_MISSES if miss else _SEARCH_HITS)

        hits = [lid for lid, title in titles if query in title]
        at = user["created_at"] + dt.timedelta(
            seconds=rng.random() * max((now - user["created_at"]).total_seconds(), 1))
        if at > now:
            continue

        clicked = None
        if hits and rng.random() < SEARCH_CLICK_RATE:
            clicked = rng.choice(hits)

        rows.append({
            "id": str(uuid.UUID(int=rng.getrandbits(128), version=4)),
            "user_id": user["id"],
            "query": query,
            "result_count": len(hits),
            "clicked_listing_id": clicked,
            "created_at": at,
        })
    rows.sort(key=lambda r: r["created_at"])
    return rows


def assign_buyers(rng, listings, enquiries, views, users, now):
    """Give sold listings a buyer and a sale price.

    The buyer is drawn from the people who enquired *before* the sale, which is
    what makes enquiry-to-purchase conversion a real measurement rather than a
    coincidence. BUYER_FROM_ENQUIRY_RATE of sales get one; the rest keep a NULL
    buyer, standing for a sale to a friend or off-platform. That NULL is data,
    not a gap — the attributable share is worth charting on its own.

    The sale price starts from the asking price and comes down a little for each
    attribute the buyer and seller share (IN_GROUP_DISCOUNT). That is a planted
    effect and is declared as such.
    """
    users_by_id = {u["id"]: u for u in users}
    by_listing: "dict[str, list]" = {}
    for row in enquiries:
        by_listing.setdefault(row["listing_id"], []).append(row)
    views_by_listing: "dict[str, list]" = {}
    for row in views:
        views_by_listing.setdefault(row["listing_id"], []).append(row)

    matched = 0
    for listing in listings:
        listing.setdefault("buyer_id", None)
        listing.setdefault("sold_price_cents", None)
        if listing["status"] != "sold" or not listing["sold_at"]:
            continue

        seller = users_by_id.get(listing["seller_id"])
        buyer = None
        if rng.random() < BUYER_FROM_ENQUIRY_RATE:
            # Only somebody who asked before it sold could have bought it.
            asked = [e for e in by_listing.get(listing["id"], [])
                     if e["created_at"] <= listing["sold_at"]]
            if asked:
                buyer = users_by_id.get(rng.choice(asked)["buyer_id"])
            else:
                # Nobody had enquired, but somebody bought it — so the contact
                # happened and was simply not generated, because enquiries are
                # drawn per view at a flat rate with no knowledge of the sale.
                # Buying without ever contacting the seller is not a thing this
                # product supports, so the enquiry is added rather than the sale
                # left unattributed. This is why enquiry counts rise slightly.
                watchers = [v for v in views_by_listing.get(listing["id"], [])
                            if v["viewed_at"] < listing["sold_at"]
                            and v["viewer_id"] != listing["seller_id"]]
                if watchers:
                    chosen = rng.choice(watchers)
                    buyer = users_by_id.get(chosen["viewer_id"])
                    if buyer is not None and seller is not None:
                        sms_ok = bool(seller["phone"]) and seller["phone_contact_enabled"]
                        enquiries.append({
                            "id": str(uuid.UUID(int=rng.getrandbits(128), version=4)),
                            "listing_id": listing["id"],
                            "buyer_id": buyer["id"],
                            "channel": "sms" if (sms_ok and rng.random() < SMS_SHARE_WHEN_AVAILABLE) else "email",
                            "created_at": max(
                                chosen["viewed_at"],
                                listing["sold_at"] - dt.timedelta(
                                    seconds=rng.randint(600, 3 * 86400))),
                        })

        price = listing["price_cents"]
        if buyer is not None and seller is not None:
            shared = _shared_attributes(buyer, seller)
            price = int(round(price * (1 - IN_GROUP_DISCOUNT * shared) / 100.0)) * 100
            listing["buyer_id"] = buyer["id"]
            matched += 1
        # A free item stays free; everything else keeps a sale price even when
        # the buyer is unknown, because the seller still sold it for something.
        listing["sold_price_cents"] = max(price, 0)
    return matched
