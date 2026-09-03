"""Controlled vocabularies and field constraints for Columbia Market.

Transcribed from ``docs/UX_SPEC.md`` §4 and §4.5 at commit ``6fa0597``. The spec
is explicit about why this file exists:

    "Adjust for your ORM, but keep the enum *values* exactly as written --
    the UI copy depends on them."

So every tuple below is a verbatim transcription, in the spec's own order, and
should not be edited to taste. Changing a value is a schema migration plus a
frontend change, not a rename.

Display labels are a weaker claim. Only a handful are fixed by evidence: the four
condition labels are written out in §4.5, "Business (CBS)" appears on the sign-up
and account screens, and "eBay" / "Facebook Marketplace" appear on the feed cards.
Everything else is marked PROVISIONAL and should be confirmed against the design
before it reaches a screen -- the values are what matter here, the labels are a
convenience so the generator can render human-readable previews.

Standard library only, so the generator, the validator and (later) the API can all
depend on this module without pulling anything else in.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Categories  (UX_SPEC §4.5)
# ---------------------------------------------------------------------------

CATEGORIES: tuple[str, ...] = (
    "furniture",
    "textbooks",
    "electronics",
    "kitchen_home",
    "clothing",
    "bikes_transport",
    "sports",
    "free_stuff",
)

# PROVISIONAL, except that these match the filter sidebar and category chips in
# docs/screens/03-feed-desktop.png.
CATEGORY_LABELS: dict[str, str] = {
    "furniture": "Furniture",
    "textbooks": "Textbooks",
    "electronics": "Electronics",
    "kitchen_home": "Kitchen & home",
    "clothing": "Clothing",
    "bikes_transport": "Bikes & transport",
    "sports": "Sports",
    "free_stuff": "Free stuff",
}

# §4.5: "furniture: desks, chairs, beds_mattresses, storage_shelving,
# sofas_tables (other categories are single-level for now)". Every category has
# an entry so callers can index without a KeyError; an empty tuple means the
# category is single-level and `listings.subcategory` must be NULL.
SUBCATEGORIES: dict[str, tuple[str, ...]] = {
    "furniture": (
        "desks",
        "chairs",
        "beds_mattresses",
        "storage_shelving",
        "sofas_tables",
    ),
    "textbooks": (),
    "electronics": (),
    "kitchen_home": (),
    "clothing": (),
    "bikes_transport": (),
    "sports": (),
    "free_stuff": (),
}

# PROVISIONAL. "Desks" is confirmed by the Furniture > Desks breadcrumb on
# docs/screens/04-detail-desktop.png.
SUBCATEGORY_LABELS: dict[str, str] = {
    "desks": "Desks",
    "chairs": "Chairs",
    "beds_mattresses": "Beds & mattresses",
    "storage_shelving": "Storage & shelving",
    "sofas_tables": "Sofas & tables",
}

# ---------------------------------------------------------------------------
# Condition  (UX_SPEC §4.5 -- labels are given verbatim in the spec)
# ---------------------------------------------------------------------------

CONDITIONS: tuple[str, ...] = ("new", "like_new", "used_good", "used_fair")

# Note the em dash. The spec writes these out, so they are not provisional.
CONDITION_LABELS: dict[str, str] = {
    "new": "New",
    "like_new": "Like new",
    "used_good": "Used — good",
    "used_fair": "Used — fair",
}

# ---------------------------------------------------------------------------
# Grade  (UX_SPEC §4.5)
# ---------------------------------------------------------------------------

GRADES: tuple[str, ...] = ("undergraduate", "graduate", "faculty_staff")

# "Faculty / Staff" is the label on the sign-up segmented control.
GRADE_LABELS: dict[str, str] = {
    "undergraduate": "Undergraduate",
    "graduate": "Graduate",
    "faculty_staff": "Faculty / Staff",
}

# ---------------------------------------------------------------------------
# School  (UX_SPEC §4.5, in the spec's order)
# ---------------------------------------------------------------------------

SCHOOLS: tuple[str, ...] = (
    "columbia_college",
    "seas_undergrad",
    "general_studies",
    "cbs",
    "law",
    "sipa",
    "seas_grad",
    "teachers_college",
    "journalism",
    "public_health",
    "gsas",
    "arts",
    "gsapp",
    "vps",
)

# §4.5: "grouped in the UI as UNDERGRADUATE / GRADUATE & PROFESSIONAL". §6.1
# confirms the sign-up dropdown is grouped this way. The split is also what makes
# the grade constraint below expressible -- it is why SEAS appears twice.
SCHOOL_GROUPS: dict[str, tuple[str, ...]] = {
    "UNDERGRADUATE": (
        "columbia_college",
        "seas_undergrad",
        "general_studies",
    ),
    "GRADUATE & PROFESSIONAL": (
        "cbs",
        "law",
        "sipa",
        "seas_grad",
        "teachers_college",
        "journalism",
        "public_health",
        "gsas",
        "arts",
        "gsapp",
        "vps",
    ),
}

UNDERGRADUATE_SCHOOLS: frozenset[str] = frozenset(SCHOOL_GROUPS["UNDERGRADUATE"])
GRADUATE_SCHOOLS: frozenset[str] = frozenset(SCHOOL_GROUPS["GRADUATE & PROFESSIONAL"])

# PROVISIONAL, except "Business (CBS)", which is the value shown on both the
# sign-up form and the account settings screen. The parenthetical-abbreviation
# style is copied from it.
SCHOOL_LABELS: dict[str, str] = {
    "columbia_college": "Columbia College (CC)",
    "seas_undergrad": "Engineering (SEAS)",
    "general_studies": "General Studies (GS)",
    "cbs": "Business (CBS)",
    "law": "Law School",
    "sipa": "International & Public Affairs (SIPA)",
    "seas_grad": "Engineering (SEAS)",
    "teachers_college": "Teachers College (TC)",
    "journalism": "Journalism",
    "public_health": "Public Health (Mailman)",
    "gsas": "Arts & Sciences (GSAS)",
    "arts": "The Arts",
    "gsapp": "Architecture (GSAPP)",
    "vps": "Physicians & Surgeons (VP&S)",
}

# ---------------------------------------------------------------------------
# Listing status  (UX_SPEC §4.5, rendering rules from §6.4)
# ---------------------------------------------------------------------------

LISTING_STATUSES: tuple[str, ...] = ("draft", "active", "reserved", "sold")

# PROVISIONAL. "ON SALE" is the pill on docs/screens/04-detail-desktop.png; the
# others follow §6.4's description of each state.
LISTING_STATUS_LABELS: dict[str, str] = {
    "draft": "Draft",
    "active": "On sale",
    "reserved": "Reserved",
    "sold": "Sold",
}

# §6.4: reserved is "still visible in the feed"; sold "drops out of search but the
# page stays reachable"; draft has never been published. This is the status filter
# the feed query applies.
FEED_VISIBLE_STATUSES: tuple[str, ...] = ("active", "reserved")

# ---------------------------------------------------------------------------
# Source  (UX_SPEC §4.5, two-tier feed rules in §5.5)
# ---------------------------------------------------------------------------

SOURCES: tuple[str, ...] = ("internal", "ebay", "facebook", "karrot")

EXTERNAL_SOURCES: tuple[str, ...] = ("ebay", "facebook", "karrot")

# "eBay" and "Facebook Marketplace" are the tags drawn on the feed cards.
# "Karrot" is PROVISIONAL -- the source exists in the enum but no card shows it.
EXTERNAL_SOURCE_LABELS: dict[str, str] = {
    "ebay": "eBay",
    "facebook": "Facebook Marketplace",
    "karrot": "Karrot",
}

# ---------------------------------------------------------------------------
# Smaller enumerations named in §4.1 and §4.4 rather than §4.5
# ---------------------------------------------------------------------------

USER_STATUSES: tuple[str, ...] = ("active", "deactivated")  # §4.1

VIEW_SURFACES: tuple[str, ...] = ("feed", "search", "detail")  # §4.4 listing_views

ENQUIRY_CHANNELS: tuple[str, ...] = ("email", "sms")  # §4.4 enquiries

# §5.4. The default is "newest", switching to "closest" when a text query is present.
SORT_OPTIONS: tuple[str, ...] = (
    "newest",
    "closest",
    "price_asc",
    "price_desc",
    "most_saved",
)
DEFAULT_SORT = "newest"
QUERY_SORT = "closest"

# ---------------------------------------------------------------------------
# Field constraints  (UX_SPEC §4.1-§4.3, §5.2, §6.5)
#
# Not vocabularies, but the same argument applies: one place, cited, so the
# generator and the validator cannot disagree about them.
# ---------------------------------------------------------------------------

# §4.1, as amended by the multi-domain fix. Four whole domains, never a suffix
# test: endswith("@columbia.edu") rejects @gsb.columbia.edu, and a looser suffix
# match against a bare columbia.edu would admit @evil-columbia.edu.
# backend/app/config.py is authoritative and publishes the list at
# /reference/enums; this copy exists so the generator has no backend dependency.
EMAIL_DOMAINS: tuple[str, ...] = (
    "columbia.edu",
    "gsb.columbia.edu",
    "cumc.columbia.edu",
    "tc.columbia.edu",
)
EMAIL_PATTERN = (
    r"^[a-z0-9._%+-]+@(?:"
    + "|".join(d.replace(".", r"\.") for d in EMAIL_DOMAINS)
    + r")$"
)

# Schools that issue their own address; everyone else is on plain columbia.edu.
# Seeding all four means the multi-domain sign-in path is exercised by the data
# rather than only by a hand-typed test -- the same argument §9 makes for the
# ~30% NULL phone numbers.
SCHOOL_EMAIL_DOMAIN: dict[str, str] = {
    "cbs": "gsb.columbia.edu",
    "teachers_college": "tc.columbia.edu",
    "public_health": "cumc.columbia.edu",
    "vps": "cumc.columbia.edu",
}


def email_domain_for(school: str) -> str:
    """The address a school issues. Mirrors backend/scripts/seed.py."""
    return SCHOOL_EMAIL_DOMAIN.get(school, "columbia.edu")

USERNAME_PATTERN = r"^[a-zA-Z0-9._]{3,20}$"  # §4.1
USERNAME_MIN_CHARS = 3
USERNAME_MAX_CHARS = 20

TITLE_MAX_CHARS = 60  # §4.2
DESCRIPTION_MAX_CHARS = 1000  # §4.2

MAX_PHOTOS_PER_LISTING = 10  # §4.3
MAX_PHOTO_BYTES = 10 * 1024 * 1024  # §4.3
PHOTO_FORMATS: tuple[str, ...] = ("jpg", "png", "heic")  # §4.3
COVER_PHOTO_POSITION = 0  # §4.3

# §5.2. The slider is continuous between these presets.
RADIUS_PRESETS_MI: tuple[float, ...] = (0.5, 1.0, 2.5, 5.0, 10.0)
DEFAULT_RADIUS_MI = 2.5
DISTANCE_DECIMAL_PLACES = 1

# §5.3. Grade is filterable but produces no badge (UX_SPEC §11 q2 is still open).
BADGE_ATTRIBUTES: tuple[str, ...] = ("zip_code", "nationality", "school")
BADGE_LABELS: dict[str, str] = {
    "zip_code": "SAME ZIP",
    "nationality": "SAME COUNTRY",
    "school": "SAME SCHOOL",
}

# §5.4 and §2. The four filterable attributes.
FILTER_ATTRIBUTES: tuple[str, ...] = ("zip_code", "nationality", "school", "grade")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def is_external(source: str) -> bool:
    """True for the aggregated tier, which carries no seller and no badges (§5.5)."""
    return source in EXTERNAL_SOURCES


def subcategories_for(category: str) -> tuple[str, ...]:
    """Legal subcategories for a category; empty when the category is single-level."""
    return SUBCATEGORIES[category]


def is_valid_subcategory(category: str, subcategory: str | None) -> bool:
    """§4.2: a subcategory "must belong to `category`".

    A single-level category requires ``None``; a two-level one accepts ``None``
    (the seller skipped it) or one of its own values -- never another category's.
    """
    if subcategory is None:
        return True
    return subcategory in SUBCATEGORIES.get(category, ())


def grades_for_school(school: str) -> tuple[str, ...]:
    """Grades that make sense at a given school.

    Not a rule the spec states outright, but the reason §4.5 splits SEAS into
    ``seas_undergrad`` and ``seas_grad`` at all. Faculty and staff are attached to
    every school, so they stay legal everywhere.
    """
    if school in UNDERGRADUATE_SCHOOLS:
        return ("undergraduate", "faculty_staff")
    return ("graduate", "faculty_staff")


def is_valid_grade_for_school(school: str, grade: str) -> bool:
    return grade in grades_for_school(school)


def schools_for_grade(grade: str) -> tuple[str, ...]:
    """Inverse of :func:`grades_for_school`, preserving the spec's school order."""
    return tuple(s for s in SCHOOLS if grade in grades_for_school(s))


def postgres_enum_ddl() -> str:
    """The ``CREATE TYPE`` statements for seed.sql, generated from this module.

    Emitting them here rather than hand-writing them in the SQL keeps a single
    source of truth: if a value changes above, the DDL changes with it.
    """
    types = (
        ("category", CATEGORIES),
        ("condition", CONDITIONS),
        ("grade", GRADES),
        ("school", SCHOOLS),
        ("listing_status", LISTING_STATUSES),
        ("source", SOURCES),
        ("user_status", USER_STATUSES),
        ("view_surface", VIEW_SURFACES),
        ("enquiry_channel", ENQUIRY_CHANNELS),
    )
    lines = []
    for name, values in types:
        rendered = ", ".join("'%s'" % v for v in values)
        lines.append("CREATE TYPE %s AS ENUM (%s);" % (name, rendered))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Self-check
#
# These run at import. They are not testing the spec -- they are testing that
# this transcription is internally consistent, which is the failure mode that
# actually bites (a value renamed in one dict and not the other).
# ---------------------------------------------------------------------------


def _check() -> None:
    def _labels_cover(values, labels, what):
        missing = [v for v in values if v not in labels]
        extra = [k for k in labels if k not in values]
        assert not missing, "%s: no label for %s" % (what, missing)
        assert not extra, "%s: label for unknown value %s" % (what, extra)

    for values, what in (
        (CATEGORIES, "CATEGORIES"),
        (CONDITIONS, "CONDITIONS"),
        (GRADES, "GRADES"),
        (SCHOOLS, "SCHOOLS"),
        (LISTING_STATUSES, "LISTING_STATUSES"),
        (SOURCES, "SOURCES"),
        (USER_STATUSES, "USER_STATUSES"),
        (VIEW_SURFACES, "VIEW_SURFACES"),
        (ENQUIRY_CHANNELS, "ENQUIRY_CHANNELS"),
        (SORT_OPTIONS, "SORT_OPTIONS"),
    ):
        assert len(set(values)) == len(values), "%s has a duplicate" % what

    _labels_cover(CATEGORIES, CATEGORY_LABELS, "CATEGORY_LABELS")
    _labels_cover(CONDITIONS, CONDITION_LABELS, "CONDITION_LABELS")
    _labels_cover(GRADES, GRADE_LABELS, "GRADE_LABELS")
    _labels_cover(SCHOOLS, SCHOOL_LABELS, "SCHOOL_LABELS")
    _labels_cover(LISTING_STATUSES, LISTING_STATUS_LABELS, "LISTING_STATUS_LABELS")
    _labels_cover(EXTERNAL_SOURCES, EXTERNAL_SOURCE_LABELS, "EXTERNAL_SOURCE_LABELS")

    # Every category is represented in SUBCATEGORIES, and no subcategory is
    # shared between two categories or missing a label.
    assert set(SUBCATEGORIES) == set(CATEGORIES), "SUBCATEGORIES must cover every category"
    flat = [s for subs in SUBCATEGORIES.values() for s in subs]
    assert len(set(flat)) == len(flat), "a subcategory is claimed by two categories"
    _labels_cover(tuple(flat), SUBCATEGORY_LABELS, "SUBCATEGORY_LABELS")

    # The school grouping partitions SCHOOLS exactly -- no school in both groups,
    # none left out.
    grouped = [s for group in SCHOOL_GROUPS.values() for s in group]
    assert sorted(grouped) == sorted(SCHOOLS), "SCHOOL_GROUPS must partition SCHOOLS"
    assert len(set(grouped)) == len(grouped), "a school is in two groups"

    # Every school admits at least one grade, and every grade at least one school.
    for school in SCHOOLS:
        assert grades_for_school(school), "no grade is legal at %s" % school
    for grade in GRADES:
        assert schools_for_grade(grade), "no school admits %s" % grade

    assert set(FEED_VISIBLE_STATUSES) <= set(LISTING_STATUSES)
    assert set(EXTERNAL_SOURCES) < set(SOURCES)
    assert "internal" not in EXTERNAL_SOURCES
    assert DEFAULT_RADIUS_MI in RADIUS_PRESETS_MI
    assert DEFAULT_SORT in SORT_OPTIONS and QUERY_SORT in SORT_OPTIONS
    assert set(BADGE_LABELS) == set(BADGE_ATTRIBUTES)
    assert set(BADGE_ATTRIBUTES) < set(FILTER_ATTRIBUTES), "grade filters but never badges"

    # Every school-issued domain is one the API actually admits, and every school
    # named in the mapping exists.
    import re as _re

    for school, domain in SCHOOL_EMAIL_DOMAIN.items():
        assert school in SCHOOLS, "unknown school in SCHOOL_EMAIL_DOMAIN: %s" % school
        assert domain in EMAIL_DOMAINS, "%s issues an inadmissible domain %s" % (school, domain)
    compiled = _re.compile(EMAIL_PATTERN)
    for school in SCHOOLS:
        probe = "ab1234@%s" % email_domain_for(school)
        assert compiled.match(probe), "%s produces an address the pattern rejects: %s" % (
            school, probe)
    # Suffix attacks the whole-domain rule must reject.
    for bad in ("x@evil-columbia.edu", "x@columbia.edu.evil.com", "x@barnard.edu"):
        assert not compiled.match(bad), "pattern admits %s" % bad


_check()


if __name__ == "__main__":

    def _show(title, values, labels=None):
        print("\n%s  (%d)" % (title, len(values)))
        for v in values:
            label = "  %s" % labels[v] if labels and v in labels else ""
            print("    %-18s%s" % (v, label))

    print("Columbia Market vocabularies — UX_SPEC.md §4.5")
    _show("category", CATEGORIES, CATEGORY_LABELS)
    print("\nsubcategory")
    for _cat, _subs in SUBCATEGORIES.items():
        if _subs:
            print("    %-18s%s" % (_cat, ", ".join(_subs)))
    _show("condition", CONDITIONS, CONDITION_LABELS)
    _show("grade", GRADES, GRADE_LABELS)
    for _group, _members in SCHOOL_GROUPS.items():
        _show("school · %s" % _group, _members, SCHOOL_LABELS)
    _show("listing_status", LISTING_STATUSES, LISTING_STATUS_LABELS)
    _show("source", SOURCES)
    _show("user_status", USER_STATUSES)
    print("\nDDL\n" + postgres_enum_ddl())
