"""A local reimplementation of the §5.3-§5.5 feed rules.

The generator needs this for one reason: ``filter_events.result_count`` (§4.4) is
what answers "where do people give up", and a made-up number there would mean the
analysis is measuring my noise rather than the product. So the count logged
against every simulated toggle is the count this query actually returns.

It is deliberately a *separate* implementation from whatever the API ends up
doing, so the two can be compared. If ``GET /filters/counts`` and this disagree,
one of them has a bug -- that is a feature of having both.

Three rules from the spec are implemented here:

* **§5.3 badges** -- computed per ``(viewer, listing)`` pair, never stored. An
  attribute that does not match is absent, not false.
* **§5.4 filters** -- and specifically the honesty rule: "every count shown next
  to a filter is the count *if you applied it*, evaluated against all other
  active filters". So facet counts are conditional, not absolute.
* **§5.5 two-tier** -- external listings have no seller, therefore no badges, and
  the three trust filters exclude them entirely.
"""

from __future__ import annotations

from . import vocabularies as V
from . import zips as Z


class FilterState:
    """The filter state §8 exposes as query parameters on ``GET /listings``."""

    __slots__ = (
        "radius_mi", "same_zip", "same_nationality", "same_school",
        "categories", "conditions", "price_min_cents", "price_max_cents",
        "sources",
    )

    def __init__(self, radius_mi=None, same_zip=False, same_nationality=False,
                 same_school=False, categories=None, conditions=None,
                 price_min_cents=None, price_max_cents=None, sources=None):
        self.radius_mi = radius_mi
        self.same_zip = same_zip
        self.same_nationality = same_nationality
        self.same_school = same_school
        self.categories = frozenset(categories) if categories else None
        self.conditions = frozenset(conditions) if conditions else None
        self.price_min_cents = price_min_cents
        self.price_max_cents = price_max_cents
        self.sources = frozenset(sources) if sources else None

    def replace(self, **changes) -> "FilterState":
        current = {slot: getattr(self, slot) for slot in self.__slots__}
        current.update(changes)
        return FilterState(**current)

    def describe(self) -> str:
        on = []
        if self.radius_mi is not None:
            on.append("radius=%s" % self.radius_mi)
        for name in ("same_zip", "same_nationality", "same_school"):
            if getattr(self, name):
                on.append(name)
        if self.categories:
            on.append("category=%s" % ",".join(sorted(self.categories)))
        if self.conditions:
            on.append("condition=%s" % ",".join(sorted(self.conditions)))
        if self.price_min_cents is not None or self.price_max_cents is not None:
            on.append("price=%s-%s" % (self.price_min_cents, self.price_max_cents))
        return " ".join(on) or "(no filters)"


def badges(viewer: dict, seller: "dict | None") -> "list[str]":
    """§5.3, transcribed.

    Returns only the attributes that match. A viewer with no overlap gets an
    empty list, which is state ``D8``. External listings have no seller and
    therefore never produce badges.
    """
    if seller is None:
        return []
    out = []
    if viewer["zip_code"] == seller["zip_code"]:
        out.append(V.BADGE_LABELS["zip_code"])
    if viewer["nationality"] == seller["nationality"]:
        out.append(V.BADGE_LABELS["nationality"])
    if viewer["school"] == seller["school"]:
        out.append(V.BADGE_LABELS["school"])
    return out


class Feed:
    """Indexes the corpus once so repeated filter evaluation stays cheap."""

    def __init__(self, listings, users):
        self.listings = listings
        self.users_by_id = {u["id"]: u for u in users}
        # Distance is a pure function of two ZIPs, so the whole matrix is small
        # enough to precompute -- 47 ZIPs is ~2,200 pairs.
        self._distance = {
            (a, b): Z.distance_mi(a, b)
            for a in Z.ZIP_CODES
            for b in Z.ZIP_CODES
        }
        # Ordered by posted_at so an as-of query can stop early.
        self._by_time = sorted(listings, key=lambda l: l["posted_at"])

    def distance(self, zip_a: str, zip_b: str) -> float:
        return self._distance[(zip_a, zip_b)]

    def seller_of(self, listing: dict) -> "dict | None":
        seller_id = listing["seller_id"]
        return self.users_by_id.get(seller_id) if seller_id else None

    def is_visible(self, listing: dict, as_of=None) -> bool:
        """§6.4 feed visibility: active and reserved are in, draft and sold are out.

        ``sold`` "drops out of search but the page stays reachable", and a draft
        was never published.
        """
        if listing["status"] not in V.FEED_VISIBLE_STATUSES:
            return False
        if as_of is not None and listing["posted_at"] > as_of:
            return False
        return True

    def matches(self, viewer: dict, listing: dict, state: "FilterState", as_of=None) -> bool:
        if not self.is_visible(listing, as_of):
            return False

        if state.sources is not None and listing["source"] not in state.sources:
            return False
        if state.categories is not None and listing["category"] not in state.categories:
            return False
        if state.conditions is not None and listing["condition"] not in state.conditions:
            return False
        if state.price_min_cents is not None and listing["price_cents"] < state.price_min_cents:
            return False
        if state.price_max_cents is not None and listing["price_cents"] > state.price_max_cents:
            return False

        if state.radius_mi is not None:
            # §5.2: the radius filter is distance_mi <= radius.
            if self.distance(viewer["zip_code"], listing["zip_code"]) > state.radius_mi:
                return False

        if state.same_zip or state.same_nationality or state.same_school:
            seller = self.seller_of(listing)
            # §5.5: an external listing has no seller, so it cannot satisfy a
            # trust filter and drops out as soon as one is on.
            if seller is None:
                return False
            if state.same_zip and seller["zip_code"] != viewer["zip_code"]:
                return False
            if state.same_nationality and seller["nationality"] != viewer["nationality"]:
                return False
            if state.same_school and seller["school"] != viewer["school"]:
                return False

        return True

    def results(self, viewer: dict, state: "FilterState", as_of=None) -> "list[dict]":
        source = self._by_time if as_of is None else [
            l for l in self._by_time if l["posted_at"] <= as_of
        ]
        return [l for l in source if self.matches(viewer, l, state, as_of)]

    def count(self, viewer: dict, state: "FilterState", as_of=None) -> int:
        total = 0
        for listing in self._by_time:
            if as_of is not None and listing["posted_at"] > as_of:
                break
            if self.matches(viewer, listing, state, as_of):
                total += 1
        return total

    def facet_counts(self, viewer: dict, state: "FilterState", key: str, as_of=None) -> "dict[str, int]":
        """§5.4: "the count *if you applied it*, evaluated against all other active filters".

        Conditional, not absolute -- this is the behaviour the sidebar numbers
        have to follow, and the reason a naive "count by category" query is wrong.
        """
        out = {}
        if key == "category":
            for value in V.CATEGORIES:
                out[value] = self.count(viewer, state.replace(categories=[value]), as_of)
        elif key == "condition":
            for value in V.CONDITIONS:
                out[value] = self.count(viewer, state.replace(conditions=[value]), as_of)
        elif key == "trust":
            out["same_zip"] = self.count(viewer, state.replace(same_zip=True), as_of)
            out["same_nationality"] = self.count(
                viewer, state.replace(same_nationality=True), as_of)
            out["same_school"] = self.count(viewer, state.replace(same_school=True), as_of)
        elif key == "radius":
            for preset in V.RADIUS_PRESETS_MI:
                out[str(preset)] = self.count(viewer, state.replace(radius_mi=preset), as_of)
        else:
            raise ValueError("unknown facet %r" % key)
        return out

    def default_state_for(self, viewer: dict) -> "FilterState":
        """The state a member's first feed load starts in, per §4.1's defaults."""
        return FilterState(
            radius_mi=viewer["default_radius_mi"],
            same_zip=viewer["default_filter_same_zip"],
            same_nationality=viewer["default_filter_same_nationality"],
            same_school=viewer["default_filter_same_school"],
        )
