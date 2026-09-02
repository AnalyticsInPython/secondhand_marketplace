"""User generation (UX_SPEC §4.1, distributions from §9).

Two orderings matter here and both are deliberate.

**Grade first, then school.** §9 fixes the grade mix (60/35/5) but the grade and
the school are not independent -- there are no undergraduates at CBS. Drawing
grade first and then choosing among the schools that admit it gives the spec's
marginal exactly while making the illegal combinations unrepresentable. Doing it
the other way round would need a rejection loop and would drift off §9's numbers.

**Nationality before name.** ``seed.names`` maps each country to a name system, so
the name is drawn from the nationality rather than beside it.

Emails and usernames are independent of each other on purpose: the design's own
example pairs ``dl3729@columbia.edu`` with ``@brian_dw``, i.e. an email built from
a legal name and a handle built from something else entirely.
"""

from __future__ import annotations

import datetime as dt
import re
import uuid

from . import names as N
from . import vocabularies as V
from . import zips as Z

# ---------------------------------------------------------------------------
# Distributions
# ---------------------------------------------------------------------------

# §9: "60% graduate, 35% undergraduate, 5% faculty/staff"
GRADE_WEIGHTS: "dict[str, float]" = {
    "graduate": 60.0,
    "undergraduate": 35.0,
    "faculty_staff": 5.0,
}

# §9: "School: CBS and SEAS over-represented (the KCA community we are seeding
# from)". Within each grade, weights over the schools that admit it.
UNDERGRAD_SCHOOL_WEIGHTS: "dict[str, float]" = {
    "columbia_college": 50.0,
    "seas_undergrad": 35.0,
    "general_studies": 15.0,
}

GRAD_SCHOOL_WEIGHTS: "dict[str, float]" = {
    "cbs": 26.0,
    "seas_grad": 22.0,
    "gsas": 12.0,
    "sipa": 9.0,
    "teachers_college": 8.0,
    "law": 6.0,
    "public_health": 5.0,
    "journalism": 4.0,
    "arts": 3.0,
    "gsapp": 3.0,
    "vps": 2.0,
}

# §9: "ZIP: 10027 ~40%, 10025 ~15%, 10031 ~10%, remainder spread."
ZIP_WEIGHTS: "dict[str, float]" = {"10027": 40.0, "10025": 15.0, "10031": 10.0}
# The remaining 35% decays with distance from campus, so the corpus thins out
# towards Brooklyn rather than spreading uniformly across the metro.
_REMAINDER_SHARE = 35.0

# Undergraduates live on or beside campus far more than the population does, and
# everyone else is damped slightly to compensate -- otherwise the tilt pushes the
# 10027 marginal well past the 40% §9 asks for.
UNDERGRAD_ZIP_BOOST = {"10027": 1.20, "10025": 1.10, "10026": 1.15}
NON_UNDERGRAD_ZIP_DAMP = {"10027": 0.95}

# §9: "Leave ~30% of phone NULL"
PHONE_PRESENT_RATE = 0.70
# Not in the spec. Some people give a number and still turn texting off; §5.1
# says the toggle exists, so the data should contain both shapes.
PHONE_CONTACT_DISABLED_RATE = 0.15

# §4.1 marks display_name nullable and §6.3 says the username is "the only name
# buyers see", so a majority leaving it blank is the honest reading.
DISPLAY_NAME_PRESENT_RATE = 0.45

# §4.1: is_verified is "true once an email link has been opened". A few sign-ups
# never click, and the sign-in states (B9 expired, B10 already used) imply it.
VERIFIED_RATE = 0.95
DEACTIVATED_RATE = 0.03

# §4.1 defaults: all three trust filters start false. A minority have changed
# them, which is what makes the "returning user with a narrow feed" case exist.
FILTER_DEFAULT_ON_RATE = {
    "default_filter_same_zip": 0.10,
    "default_filter_same_nationality": 0.14,
    "default_filter_same_school": 0.09,
}
NON_DEFAULT_RADIUS_RATE = 0.22

# Reserved fictional range. No generated number can ever dial a real person.
_NYC_AREA_CODES = ("212", "646", "917", "347", "929")
_FICTIONAL_PREFIX = "555"
_FICTIONAL_LINE_MIN = 100
_FICTIONAL_LINE_MAX = 199

# Intake clusters. Sign-ups arrive with the academic calendar, and later intakes
# are larger because the platform is growing.
_INTAKES: "tuple[tuple[str, float], ...]" = (
    ("2024-08-26", 1.0),
    ("2025-01-21", 1.4),
    ("2025-08-25", 2.6),
    ("2026-01-20", 3.2),
    ("2026-08-31", 4.0),
)


def _weighted(rng, weights: "dict[str, float]") -> str:
    total = sum(weights.values())
    r = rng.random() * total
    acc = 0.0
    for key, w in weights.items():
        acc += w
        if r <= acc:
            return key
    return next(reversed(list(weights)))


def _zip_weights(grade: str) -> "dict[str, float]":
    """ZIP weights, with the §9 trio fixed and the tail decaying with distance."""
    tail = [z for z in Z.ZIP_CODES if z not in ZIP_WEIGHTS]
    # 1/(1 + miles) puts most of the remainder in upper Manhattan.
    raw = {z: 1.0 / (1.0 + Z.ZIPS[z].miles_from_campus) for z in tail}
    scale = _REMAINDER_SHARE / sum(raw.values())
    weights = dict(ZIP_WEIGHTS)
    for z, w in raw.items():
        weights[z] = w * scale
    if grade == "undergraduate":
        for z, boost in UNDERGRAD_ZIP_BOOST.items():
            weights[z] = weights.get(z, 0.0) * boost
    else:
        for z, damp in NON_UNDERGRAD_ZIP_DAMP.items():
            weights[z] = weights.get(z, 0.0) * damp
    return weights


def _draw_school(rng, grade: str) -> str:
    if grade == "undergraduate":
        return _weighted(rng, UNDERGRAD_SCHOOL_WEIGHTS)
    if grade == "graduate":
        return _weighted(rng, GRAD_SCHOOL_WEIGHTS)
    # Faculty and staff are attached to every school; weight by school size.
    combined = dict(GRAD_SCHOOL_WEIGHTS)
    for school, w in UNDERGRAD_SCHOOL_WEIGHTS.items():
        combined[school] = w * 0.6
    return _weighted(rng, combined)


def _draw_phone(rng) -> str:
    """E.164, NYC area code, inside the reserved 555-01xx block."""
    area = rng.choice(_NYC_AREA_CODES)
    line = rng.randint(_FICTIONAL_LINE_MIN, _FICTIONAL_LINE_MAX)
    return "+1%s%s%04d" % (area, _FICTIONAL_PREFIX, line)


def _draw_created_at(rng, now: dt.datetime) -> dt.datetime:
    anchors = [(dt.datetime.strptime(d, "%Y-%m-%d"), w) for d, w in _INTAKES]
    anchors = [(d, w) for d, w in anchors if d <= now]
    if not anchors:
        anchors = [(now - dt.timedelta(days=30), 1.0)]
    total = sum(w for _, w in anchors)
    r = rng.random() * total
    acc = 0.0
    chosen = anchors[-1][0]
    for anchor, w in anchors:
        acc += w
        if r <= acc:
            chosen = anchor
            break
    # Most people join in the fortnight around an intake; a tail trickles in.
    offset = rng.expovariate(1 / 18.0) - 4
    stamp = chosen + dt.timedelta(days=offset, seconds=rng.randint(0, 86399))
    return min(stamp, now - dt.timedelta(minutes=5))


def _slugify(text: str) -> str:
    """Reduce a name to the username charset in §4.1: [a-zA-Z0-9._]."""
    return re.sub(r"[^a-zA-Z0-9._]", "", text)


def _draw_username(rng, given: str, family: str, taken: "set[str]") -> str:
    g, f = _slugify(given).lower(), _slugify(family).lower()
    shapes = (
        "%s_%s" % (g, f[:2]),
        "%s.%s" % (g, f),
        "%s%s" % (g, f[:1]),
        "%s_%s" % (g[:1], f),
        "%s%d" % (g, rng.randint(2, 99)),
        "%s.%s%d" % (g[:1], f, rng.randint(10, 99)),
    )
    for shape in shapes:
        candidate = shape[: V.USERNAME_MAX_CHARS]
        if len(candidate) >= V.USERNAME_MIN_CHARS and candidate not in taken:
            return candidate
    # Everything collided: fall back to a numbered handle.
    n = 2
    base = (g or "member")[: V.USERNAME_MAX_CHARS - 4]
    while True:
        candidate = "%s%d" % (base, n)
        if candidate not in taken:
            return candidate
        n += 1


def _draw_email(rng, given: str, family: str, taken: "set[str]") -> str:
    initials = (_slugify(given)[:1] + _slugify(family)[:1]).lower() or "cu"
    while True:
        candidate = "%s%d@%s" % (initials, rng.randint(1000, 9999), V.EMAIL_DOMAIN)
        if candidate not in taken:
            return candidate


def generate_users(rng, count: int, now: dt.datetime) -> "list[dict]":
    """Generate ``count`` user rows matching §4.1 and §9."""
    users = []
    emails: "set[str]" = set()
    usernames: "set[str]" = set()

    for _ in range(count):
        grade = _weighted(rng, GRADE_WEIGHTS)
        school = _draw_school(rng, grade)
        nationality = _weighted(rng, N.NATIONALITY_WEIGHTS)
        given, family = N.draw_name(rng, nationality)

        email = _draw_email(rng, given, family, emails)
        emails.add(email)
        username = _draw_username(rng, given, family, usernames)
        usernames.add(username)

        has_phone = rng.random() < PHONE_PRESENT_RATE
        phone = _draw_phone(rng) if has_phone else None
        # §4.1: "Meaningless when phone IS NULL". Stored true in that case so the
        # column matches the spec's default; §5.1 gates rendering on the phone.
        contact_enabled = True
        if has_phone and rng.random() < PHONE_CONTACT_DISABLED_RATE:
            contact_enabled = False

        created = _draw_created_at(rng, now)
        updated = created + dt.timedelta(days=rng.expovariate(1 / 40.0))
        updated = min(updated, now)

        radius = V.DEFAULT_RADIUS_MI
        if rng.random() < NON_DEFAULT_RADIUS_RATE:
            radius = rng.choice([p for p in V.RADIUS_PRESETS_MI if p != V.DEFAULT_RADIUS_MI])

        users.append({
            "id": str(uuid.UUID(int=rng.getrandbits(128), version=4)),
            "email": email,
            "username": username,
            "display_name": ("%s %s" % (given, family))
                            if rng.random() < DISPLAY_NAME_PRESENT_RATE else None,
            "phone": phone,
            "phone_contact_enabled": contact_enabled,
            "nationality": nationality,
            "school": school,
            "grade": grade,
            "zip_code": _weighted(rng, _zip_weights(grade)),
            "default_radius_mi": radius,
            "default_filter_same_zip":
                rng.random() < FILTER_DEFAULT_ON_RATE["default_filter_same_zip"],
            "default_filter_same_nationality":
                rng.random() < FILTER_DEFAULT_ON_RATE["default_filter_same_nationality"],
            "default_filter_same_school":
                rng.random() < FILTER_DEFAULT_ON_RATE["default_filter_same_school"],
            "is_verified": rng.random() < VERIFIED_RATE,
            "status": "deactivated" if rng.random() < DEACTIVATED_RATE else "active",
            "created_at": created,
            "updated_at": updated,
            # Not a column -- carried through the pipeline so listings and
            # descriptions can stay consistent with the person. Dropped on export.
            "_given_name": given,
            "_family_name": family,
        })

    return users
