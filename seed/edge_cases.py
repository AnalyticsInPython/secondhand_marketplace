"""Rows that exist so a screen state can be demoed.

UX_SPEC §7 gives every interaction state an ID, and §10 says "a screen is not done
until its states render". A state with no matching row cannot be built against, and
random draws do not reliably produce the awkward ones -- a 10-photo listing, a
seller who shares nothing with the viewer, a filter combination that returns zero.

§9 makes the same argument for the one case it cares about: "leave ~30% of phone
NULL -- the email-only contact layout must be exercised by the data, not just by a
design state."

So this module runs after generation and before events, mutates a small number of
rows to guarantee each state, and returns a manifest naming the row that covers
each one. Nothing is appended, so the corpus size stays exactly what was asked for.

It also installs **the reference member**: the user the Figma mockups are drawn
for (``@brian_dw``, 10027, South Korea, CBS, graduate). Having a fixed identity to
sign in as makes every screenshot reproducible.
"""

from __future__ import annotations

import datetime as dt

from . import vocabularies as V

# The identity the design screens are drawn for.
REFERENCE = {
    "username": "brian_dw",
    "display_name": "Brian Lee",
    "email": "dl3729@columbia.edu",
    "nationality": "KR",
    "school": "cbs",
    "grade": "graduate",
    "zip_code": "10027",
    "phone": "+16465550142",
}

_MAX_TITLE = "IKEA MALM desk 140×65 in white, barely used, moving out May"
_LONG_DESCRIPTION_SEED = (
    "Selling my IKEA MALM desk (140 × 65 cm, white). Bought new in August 2024 "
    "when I moved into Morningside Heights, used it for two semesters of CBS "
    "coursework. Solid, no wobble — one small scuff on the back left leg that "
    "you cannot see once it is against a wall. "
)


def _pick(rows, predicate, default=None):
    for row in rows:
        if predicate(row):
            return row
    return default


def install(rng, users, listings, photos, now):
    """Mutate rows so every §7 state has data. Returns a manifest of what covers what."""
    manifest: "dict[str, str]" = {}
    notes: "list[str]" = []

    users_by_id = {u["id"]: u for u in users}
    photos_by_listing: "dict[str, list[dict]]" = {}
    for photo in photos:
        photos_by_listing.setdefault(photo["listing_id"], []).append(photo)
    for group in photos_by_listing.values():
        group.sort(key=lambda p: p["position"])

    internal = [l for l in listings if l["source"] == "internal"]

    # ---- the reference member -------------------------------------------------
    # Choose someone who already has several listings so the "more from this
    # seller" rail (§6.4) has something in it.
    counts: "dict[str, int]" = {}
    for listing in internal:
        counts[listing["seller_id"]] = counts.get(listing["seller_id"], 0) + 1
    busiest = sorted(counts.items(), key=lambda kv: -kv[1])
    reference = users_by_id[busiest[0][0]] if busiest else users[0]

    # Free the username and email in case another row already holds them.
    for user in users:
        if user is reference:
            continue
        if user["username"] == REFERENCE["username"]:
            user["username"] = user["username"] + "1"
        if user["email"] == REFERENCE["email"]:
            user["email"] = "x" + user["email"]

    reference.update(REFERENCE)
    reference["phone_contact_enabled"] = True
    reference["is_verified"] = True
    reference["status"] = "active"
    reference["default_radius_mi"] = V.DEFAULT_RADIUS_MI
    manifest["reference_member"] = reference["id"]
    notes.append("reference member is @%s (%s, %s, %s)" % (
        reference["username"], reference["zip_code"],
        reference["nationality"], reference["school"]))

    # Their listings move with them -- pickup ZIP is locked to the seller's ZIP.
    own = [l for l in internal if l["seller_id"] == reference["id"]]
    for listing in own:
        listing["zip_code"] = reference["zip_code"]
    if own:
        own[0]["status"] = "active"
        own[0]["sold_at"] = None
        manifest["D10_owner_view"] = own[0]["id"]

    # ---- D12: contact block with and without a phone --------------------------
    no_phone_seller = _pick(
        users,
        lambda u: u["phone"] is None and u["status"] == "active" and u["is_verified"]
        and counts.get(u["id"], 0) > 0,
    )
    if no_phone_seller is None:
        no_phone_seller = _pick(users, lambda u: counts.get(u["id"], 0) > 0)
        no_phone_seller["phone"] = None
    no_phone_seller["phone_contact_enabled"] = True
    target = _pick(internal, lambda l: l["seller_id"] == no_phone_seller["id"])
    if target is not None:
        target["status"] = "active"
        target["sold_at"] = None
        manifest["D12_email_only"] = target["id"]

    with_phone = _pick(
        internal,
        lambda l: l["seller_id"] and users_by_id[l["seller_id"]]["phone"]
        and users_by_id[l["seller_id"]]["phone_contact_enabled"]
        and l["status"] == "active",
    )
    if with_phone is not None:
        manifest["D12_email_and_text"] = with_phone["id"]

    # ---- D3 / D4 / D5: the three listing states -------------------------------
    for state, key in (("active", "D3_on_sale"), ("reserved", "D4_reserved"),
                       ("sold", "D5_sold")):
        row = _pick(internal, lambda l, s=state: l["status"] == s)
        if row is None:
            row = internal[len(manifest) % len(internal)]
            row["status"] = state
            row["sold_at"] = (
                row["posted_at"] + dt.timedelta(days=4) if state == "sold" else None
            )
        manifest[key] = row["id"]

    # ---- D6 / D7 / D8: overlap depth against the reference member -------------
    def overlap(listing):
        seller = users_by_id.get(listing["seller_id"]) if listing["seller_id"] else None
        if seller is None or seller["id"] == reference["id"]:
            return -1
        return sum((
            seller["zip_code"] == reference["zip_code"],
            seller["nationality"] == reference["nationality"],
            seller["school"] == reference["school"],
        ))

    active_internal = [l for l in internal if l["status"] == "active"]
    for wanted, key in ((3, "D6_full_overlap"), (1, "D7_partial_overlap"),
                        (0, "D8_no_overlap")):
        row = _pick(active_internal, lambda l, w=wanted: overlap(l) == w)
        if row is None and active_internal:
            # Force it by moving a seller onto (or off) the reference attributes.
            row = active_internal[wanted]
            seller = users_by_id[row["seller_id"]]
            if wanted == 3:
                seller["zip_code"] = reference["zip_code"]
                seller["nationality"] = reference["nationality"]
                seller["school"] = reference["school"]
                row["zip_code"] = seller["zip_code"]
            elif wanted == 0:
                seller["zip_code"] = "11215"
                seller["nationality"] = "BR"
                seller["school"] = "journalism"
                seller["grade"] = "graduate"
                row["zip_code"] = seller["zip_code"]
            notes.append("forced %s by editing a seller's attributes" % key)
        if row is not None:
            manifest[key] = row["id"]

    # ---- D11: one live listing per external source ----------------------------
    for source in V.EXTERNAL_SOURCES:
        row = _pick(listings, lambda l, s=source: l["source"] == s and l["status"] == "active")
        if row is not None:
            manifest["D11_external_%s" % source] = row["id"]

    # ---- E4 / photo bounds ----------------------------------------------------
    ten = _pick(internal, lambda l: len(photos_by_listing.get(l["id"], [])) >= 6)
    if ten is not None:
        group = photos_by_listing[ten["id"]]
        while len(group) < V.MAX_PHOTOS_PER_LISTING:
            clone = dict(group[-1])
            clone["position"] = len(group)
            clone["id"] = "%s-x%d" % (clone["id"][:8], clone["position"])
            clone["url"] = "photos/%s/%d.webp" % (ten["id"], clone["position"])
            group.append(clone)
            photos.append(clone)
        manifest["E4_ten_photos"] = ten["id"]

    single = _pick(internal, lambda l: len(photos_by_listing.get(l["id"], [])) == 1)
    if single is not None:
        manifest["D1_single_photo"] = single["id"]

    # ---- E6: a free listing ---------------------------------------------------
    free = _pick(listings, lambda l: l["is_free"] and l["status"] == "active")
    if free is not None:
        manifest["E6_free"] = free["id"]

    # ---- field bounds ---------------------------------------------------------
    long_title = _pick(internal, lambda l: l["status"] == "active"
                       and l["category"] == "furniture")
    if long_title is not None:
        long_title["title"] = _MAX_TITLE[:V.TITLE_MAX_CHARS]
        body = _LONG_DESCRIPTION_SEED
        while len(body) < V.DESCRIPTION_MAX_CHARS:
            body += _LONG_DESCRIPTION_SEED
        long_title["description"] = body[:V.DESCRIPTION_MAX_CHARS]
        manifest["max_length_fields"] = long_title["id"]

    # ---- non-ASCII ------------------------------------------------------------
    korean = _pick(users, lambda u: u["nationality"] == "KR" and u is not reference)
    if korean is not None:
        korean["display_name"] = "김지우 (Jiwoo Kim)"
        manifest["non_ascii_display_name"] = korean["id"]

    # ---- A5: a username collision to suggest against --------------------------
    manifest["A5_taken_username"] = reference["username"]

    return manifest, notes


def audit(feed, reference, now):
    """Post-generation checks that a state is actually reachable, not just present.

    Two of the §7 states are properties of the corpus rather than of any one row:
    ``C4`` needs a filter combination that genuinely returns nothing, and ``C6``
    needs every radius preset to return something.
    """
    from .feed import FilterState

    findings = []

    # C6 -- the distance slider must have results at all five stops.
    radius_counts = {}
    for preset in V.RADIUS_PRESETS_MI:
        radius_counts[preset] = feed.count(reference, FilterState(radius_mi=preset))
    empty = [str(p) for p, c in radius_counts.items() if c == 0]
    findings.append((
        "C6_radius_steps",
        not empty,
        "counts at 0.5/1/2.5/5/10 mi = %s" % list(radius_counts.values()),
    ))

    # C4 -- an empty feed has to be reachable from filters a person would
    # plausibly set. Searched rather than hard-coded, because what is empty
    # depends on the corpus size: a probe that returns nothing at 300 listings
    # returns one or two at 1,500.
    probes = (
        FilterState(radius_mi=0.5, same_school=True, same_nationality=True,
                    categories=["sports"], price_max_cents=2000),
        FilterState(radius_mi=0.5, same_school=True, same_nationality=True,
                    categories=["free_stuff"], conditions=["new"]),
        FilterState(radius_mi=0.5, same_zip=True, same_school=True,
                    same_nationality=True, categories=["bikes_transport"],
                    conditions=["new"]),
        FilterState(radius_mi=0.5, same_zip=True, same_school=True,
                    same_nationality=True, categories=["sports"],
                    conditions=["new", "used_fair"], price_max_cents=1500),
    )
    empty_probe = None
    tried = []
    for probe in probes:
        count = feed.count(reference, probe)
        tried.append(count)
        if count == 0:
            empty_probe = probe
            break
    findings.append((
        "C4_empty_state",
        empty_probe is not None,
        ("%s -> 0 results" % empty_probe.describe()) if empty_probe
        else "no probe emptied the feed; counts were %s" % tried,
    ))

    return findings
