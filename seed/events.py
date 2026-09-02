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


def _weighted(rng, weights):
    total = sum(weights.values())
    r = rng.random() * total
    acc = 0.0
    for key, w in weights.items():
        acc += w
        if r <= acc:
            return key
    return next(reversed(list(weights)))


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
    """Return ``(listing_views, saves, enquiries, filter_events)``.

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
            viewer = viewers[rng.randrange(limit)]
            # A seller looking at their own listing is the D10 owner view, not a
            # feed impression.
            if seller_id is not None and viewer["id"] == seller_id:
                continue

            views.append({
                "id": str(uuid.UUID(int=rng.getrandbits(128), version=4)),
                "listing_id": listing["id"],
                "viewer_id": viewer["id"],
                "viewed_at": at,
                "surface": _weighted(rng, SURFACE_WEIGHTS),
            })

            if rng.random() < SAVE_RATE_PER_VIEW:
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
            if seller is not None and rng.random() < ENQUIRY_RATE_PER_VIEW:
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
    return views, saves, enquiries, filter_events


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
