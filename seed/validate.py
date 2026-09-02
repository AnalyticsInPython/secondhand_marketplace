"""Invariants the generated corpus must satisfy.

These are not tests of the generator's taste -- they are the constraints a backend
would enforce with NOT NULL, CHECK, UNIQUE and foreign keys, plus the handful that
UX_SPEC states in prose and no column type can express (§5.1's phone/text
coupling, §4.2's is_free/price equivalence, §4.4's counters being summaries).

Anything that fails here would either fail to load into Postgres or would render a
screen that contradicts itself. Run it after every regeneration; it is cheap.
"""

from __future__ import annotations

import re

from . import vocabularies as V
from . import zips as Z


class Failure:
    __slots__ = ("rule", "detail", "sample")

    def __init__(self, rule, detail, sample=None):
        self.rule = rule
        self.detail = detail
        self.sample = sample

    def __str__(self):
        tail = "  e.g. %s" % (self.sample,) if self.sample is not None else ""
        return "%-34s %s%s" % (self.rule, self.detail, tail)


def validate(users, listings, photos, views, saves, enquiries, filter_events, now):
    """Return a list of :class:`Failure`. Empty means the corpus is loadable."""
    failures: "list[Failure]" = []

    def fail(rule, detail, sample=None):
        failures.append(Failure(rule, detail, sample))

    users_by_id = {u["id"]: u for u in users}
    listings_by_id = {l["id"]: l for l in listings}

    # -- 01 email --------------------------------------------------------------
    email_re = re.compile(V.EMAIL_PATTERN)
    seen = set()
    for u in users:
        if not email_re.match(u["email"]):
            fail("01 email format", "does not match §4.1 pattern", u["email"])
            break
    dupes = [e for e in (u["email"] for u in users) if e in seen or seen.add(e)]
    if dupes:
        fail("01 email unique", "%d duplicates" % len(dupes), dupes[0])

    # -- 02 username -----------------------------------------------------------
    username_re = re.compile(V.USERNAME_PATTERN)
    seen = set()
    for u in users:
        if not username_re.match(u["username"]):
            fail("02 username charset", "violates [a-zA-Z0-9._]{3,20}", u["username"])
            break
    dupes = [n for n in (u["username"] for u in users) if n in seen or seen.add(n)]
    if dupes:
        fail("02 username unique", "%d duplicates" % len(dupes), dupes[0])

    # -- 03 phone is fictional --------------------------------------------------
    # §4.1 says phone_contact_enabled is "meaningless when phone IS NULL", so a
    # stored true against a null phone is legal -- §5.1's render rule is what
    # matters, and rule 15 checks the consequence. What is not negotiable is that
    # no generated number can dial a real person.
    phone_re = re.compile(r"^\+1\d{3}5550(?:1\d{2})$")
    offenders = [u["phone"] for u in users
                 if u["phone"] and not phone_re.match(u["phone"])]
    if offenders:
        fail("03 phone is fictional", "%d outside the reserved 555-01xx block"
             % len(offenders), offenders[0])

    # -- 04 grade x school -----------------------------------------------------
    offenders = [u for u in users if not V.is_valid_grade_for_school(u["school"], u["grade"])]
    if offenders:
        fail("04 grade legal for school", "%d users" % len(offenders),
             "%s @ %s" % (offenders[0]["grade"], offenders[0]["school"]))

    # -- 05 ZIPs resolve -------------------------------------------------------
    offenders = [u["zip_code"] for u in users if not Z.is_nyc_metro(u["zip_code"])]
    offenders += [l["zip_code"] for l in listings if not Z.is_nyc_metro(l["zip_code"])]
    if offenders:
        fail("05 ZIP in the metro table", "%d unknown" % len(offenders), offenders[0])

    # -- 06 subcategory belongs to category (§4.2) -----------------------------
    offenders = [l for l in listings
                 if not V.is_valid_subcategory(l["category"], l["subcategory"])]
    if offenders:
        fail("06 subcategory parentage", "%d listings" % len(offenders),
             "%s/%s" % (offenders[0]["category"], offenders[0]["subcategory"]))
    offenders = [l for l in listings
                 if not V.SUBCATEGORIES[l["category"]] and l["subcategory"] is not None]
    if offenders:
        fail("06 single-level categories", "%d carry a subcategory" % len(offenders),
             offenders[0]["category"])

    # -- 07 text lengths (§4.2) ------------------------------------------------
    offenders = [l for l in listings if len(l["title"]) > V.TITLE_MAX_CHARS]
    if offenders:
        fail("07 title <= 60", "%d over" % len(offenders), offenders[0]["title"])
    offenders = [l for l in listings
                 if l["description"] and len(l["description"]) > V.DESCRIPTION_MAX_CHARS]
    if offenders:
        fail("07 description <= 1000", "%d over" % len(offenders))

    # -- 08 is_free <=> price 0 (§4.2) -----------------------------------------
    offenders = [l for l in listings if l["is_free"] != (l["price_cents"] == 0)]
    if offenders:
        fail("08 is_free == (price == 0)", "%d disagree" % len(offenders),
             "%s: free=%s price=%d" % (offenders[0]["id"][:8],
                                       offenders[0]["is_free"],
                                       offenders[0]["price_cents"]))
    offenders = [l for l in listings if l["price_cents"] < 0]
    if offenders:
        fail("08 price >= 0", "%d negative" % len(offenders))

    # -- 09 sold_at iff sold ---------------------------------------------------
    offenders = [l for l in listings
                 if (l["status"] == "sold") != (l["sold_at"] is not None)]
    if offenders:
        fail("09 sold_at iff status sold", "%d disagree" % len(offenders),
             "%s: %s / %s" % (offenders[0]["id"][:8], offenders[0]["status"],
                              offenders[0]["sold_at"]))
    offenders = [l for l in listings if l["sold_at"] and l["sold_at"] < l["posted_at"]]
    if offenders:
        fail("09 sold_at >= posted_at", "%d inverted" % len(offenders))
    offenders = [l for l in listings if l["sold_at"] and l["sold_at"] > now]
    if offenders:
        fail("09 sold_at <= now", "%d in the future" % len(offenders))

    # -- 10 posted_at >= seller join ------------------------------------------
    offenders = []
    for l in listings:
        if not l["seller_id"]:
            continue
        seller = users_by_id.get(l["seller_id"])
        if seller is None or l["posted_at"] < seller["created_at"]:
            offenders.append(l)
    if offenders:
        fail("10 posted_at >= seller joined", "%d listings" % len(offenders),
             offenders[0]["id"][:8])

    # -- 11 external tier shape (§5.5) ----------------------------------------
    offenders = [l for l in listings
                 if (l["source"] != "internal") != (l["external_url"] is not None)]
    if offenders:
        fail("11 external_url iff external", "%d disagree" % len(offenders),
             "%s / %s" % (offenders[0]["source"], offenders[0]["external_url"]))
    offenders = [l for l in listings
                 if l["source"] != "internal" and l["seller_id"] is not None]
    if offenders:
        fail("11 external has no seller", "%d carry a seller_id" % len(offenders))
    offenders = [l for l in listings
                 if l["source"] == "internal" and l["seller_id"] is None]
    if offenders:
        fail("11 internal has a seller", "%d missing seller_id" % len(offenders))

    # -- 12 photos (§4.3) ------------------------------------------------------
    by_listing: "dict[str, list[int]]" = {}
    for p in photos:
        by_listing.setdefault(p["listing_id"], []).append(p["position"])
    missing = [l["id"] for l in listings if l["id"] not in by_listing]
    if missing:
        fail("12 every listing has a photo", "%d without" % len(missing), missing[0][:8])
    for listing_id, positions in by_listing.items():
        if listing_id not in listings_by_id:
            fail("12 photo FK resolves", "orphan photo", listing_id[:8])
            break
        if sorted(positions) != list(range(len(positions))):
            fail("12 positions contiguous from 0", "listing %s" % listing_id[:8],
                 sorted(positions))
            break
        if len(positions) > V.MAX_PHOTOS_PER_LISTING:
            fail("12 at most 10 photos", "listing %s has %d"
                 % (listing_id[:8], len(positions)))
            break

    # -- 13 counters are summaries (§4.2 vs §4.4) ------------------------------
    counted = {"view": {}, "save": {}, "enquiry": {}}
    for row in views:
        counted["view"][row["listing_id"]] = counted["view"].get(row["listing_id"], 0) + 1
    for row in saves:
        counted["save"][row["listing_id"]] = counted["save"].get(row["listing_id"], 0) + 1
    for row in enquiries:
        counted["enquiry"][row["listing_id"]] = counted["enquiry"].get(row["listing_id"], 0) + 1
    for kind, column in (("view", "view_count"), ("save", "save_count"),
                         ("enquiry", "enquiry_count")):
        offenders = [l for l in listings
                     if l[column] != counted[kind].get(l["id"], 0)]
        if offenders:
            fail("13 %s matches events" % column, "%d disagree" % len(offenders),
                 "%s: %d vs %d" % (offenders[0]["id"][:8], offenders[0][column],
                                   counted[kind].get(offenders[0]["id"], 0)))
    # Per listing, both saves and enquiries are drawn from views, so each is
    # bounded by the view count. They are NOT ordered against each other: a
    # buyer can email about an item without saving it first, so a listing with
    # one enquiry and no saves is correct, not a bug.
    offenders = [l for l in listings
                 if l["save_count"] > l["view_count"]
                 or l["enquiry_count"] > l["view_count"]]
    if offenders:
        fail("13 saves/enquiries <= views", "%d listings" % len(offenders),
             "%s: v=%d s=%d e=%d" % (offenders[0]["id"][:8], offenders[0]["view_count"],
                                     offenders[0]["save_count"],
                                     offenders[0]["enquiry_count"]))
    # The 100 : 8 : 1 ordering from §9 is an aggregate property.
    totals = (sum(l["view_count"] for l in listings),
              sum(l["save_count"] for l in listings),
              sum(l["enquiry_count"] for l in listings))
    if not totals[0] >= totals[1] >= totals[2]:
        fail("13 funnel ordering in aggregate", "views/saves/enquiries = %s" % (totals,))

    # -- 14 event integrity ----------------------------------------------------
    pairs = set()
    for row in saves:
        pair = (row["user_id"], row["listing_id"])
        if pair in pairs:
            fail("14 no duplicate save", "(user, listing) repeated", pair[0][:8])
            break
        pairs.add(pair)
    for table, rows, stamp in (("listing_views", views, "viewed_at"),
                               ("saves", saves, "created_at"),
                               ("enquiries", enquiries, "created_at")):
        offenders = [r for r in rows
                     if r["listing_id"] not in listings_by_id
                     or r[stamp] < listings_by_id[r["listing_id"]]["posted_at"]
                     or r[stamp] > now]
        if offenders:
            fail("14 %s within listing life" % table, "%d rows" % len(offenders))
    offenders = [r for r in views if r["surface"] not in V.VIEW_SURFACES]
    if offenders:
        fail("14 view surface in vocabulary", "%d rows" % len(offenders))

    # -- 15 sms only where a phone exists (§5.1) -------------------------------
    offenders = []
    for row in enquiries:
        if row["channel"] != "sms":
            continue
        listing = listings_by_id.get(row["listing_id"])
        seller = users_by_id.get(listing["seller_id"]) if listing else None
        if seller is None or not seller["phone"] or not seller["phone_contact_enabled"]:
            offenders.append(row)
    if offenders:
        fail("15 sms needs a phone", "%d enquiries" % len(offenders))
    offenders = [r for r in enquiries
                 if listings_by_id[r["listing_id"]]["seller_id"] is None]
    if offenders:
        fail("15 no enquiry on external", "%d rows" % len(offenders))

    # -- 16 enums and filter_events -------------------------------------------
    checks = (
        ("category", "category", V.CATEGORIES),
        ("condition", "condition", V.CONDITIONS),
        ("status", "status", V.LISTING_STATUSES),
        ("source", "source", V.SOURCES),
    )
    for label, column, allowed in checks:
        offenders = [l[column] for l in listings if l[column] not in allowed]
        if offenders:
            fail("16 %s in vocabulary" % label, "%d bad values" % len(offenders),
                 offenders[0])
    for label, column, allowed in (("school", "school", V.SCHOOLS),
                                   ("grade", "grade", V.GRADES),
                                   ("user status", "status", V.USER_STATUSES)):
        offenders = [u[column] for u in users if u[column] not in allowed]
        if offenders:
            fail("16 user %s in vocabulary" % label, "%d bad values" % len(offenders),
                 offenders[0])
    offenders = [r for r in filter_events if r["result_count"] < 0]
    if offenders:
        fail("16 result_count >= 0", "%d negative" % len(offenders))
    offenders = [r for r in filter_events if r["user_id"] not in users_by_id]
    if offenders:
        fail("16 filter_events FK", "%d orphans" % len(offenders))

    return failures
