"""NYC metro ZIP reference table and the distance function.

UX_SPEC §4.6 asks for a static table -- "do not call a geocoding API at request
time" -- of ``(zip, neighbourhood, borough, lat, lon)``, and §5.2 defines distance
as haversine between ZIP centroids, rounded to one decimal.

Two different distances live here and they are not the same measurement:

``miles_from_campus``
    What the sign-up ZIP autocomplete shows (§6.1: "result shows neighbourhood +
    miles from campus"). For the eight ZIPs listed in §4.6 this is the spec's own
    number, kept verbatim even where it disagrees with the centroid arithmetic --
    it is display copy the design already committed to. For every other ZIP it is
    computed from the centroid.

``distance_mi(a, b)``
    The real one: viewer ZIP centroid to listing ZIP centroid, per §5.2. This is
    what the feed filter and the card metadata use. It is never read off the table.

The centroids are approximate ZCTA centres, good to roughly a tenth of a mile,
which is the precision §5.2 rounds to anyway. Replace them with US Census ZCTA
gazetteer values before this table is used for anything real.
"""

from __future__ import annotations

import importlib.util
import math
import os
import sys

# The ZIP table lives in the backend, at backend/app/services/geo.py, and is
# loaded from there rather than duplicated here.
#
# It used to be duplicated, and the two copies drifted: the backend knew 18 ZIPs
# and this file knew 47, so 26% of generated listings sat in ZIPs the API
# rejected — and because `geo.zips_within()` resolves the radius filter to a ZIP
# list, those listings were invisible to every distance query rather than failing
# loudly. One table, one place.
#
# Loaded by path rather than imported as a package: `backend/` is a separate
# deployable with its own dependencies, and this keeps the generator from
# depending on anything installed over there. geo.py imports only `dataclasses`
# and `math`, so this stays cheap.

_GEO_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), os.pardir,
                 "backend", "app", "services", "geo.py")
)


def _load_backend_geo():
    if not os.path.exists(_GEO_PATH):
        raise RuntimeError(
            "Cannot find the ZIP table at %s. It is the single source of truth "
            "for ZIP codes and centroids; if the backend moved, update _GEO_PATH "
            "rather than pasting the table back into this file." % _GEO_PATH
        )
    name = "_backend_geo"
    spec = importlib.util.spec_from_file_location(name, _GEO_PATH)
    module = importlib.util.module_from_spec(spec)
    # Register before executing: geo.py declares a @dataclass, and dataclasses
    # resolves field types through sys.modules[cls.__module__]. Without this the
    # import dies with "NoneType has no attribute __dict__".
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_geo = _load_backend_geo()

# 116th & Broadway, and the radius the backend measures with. Taken from geo.py
# too, so there is one campus and one earth rather than two of each.
CAMPUS_LAT = _geo.CAMPUS_LAT
CAMPUS_LON = _geo.CAMPUS_LON
EARTH_RADIUS_MI = _geo.EARTH_RADIUS_MI

# (zip, neighbourhood, borough, lat, lon), in the backend's order.
_ZIP_ROWS = tuple(
    (z.zip_code, z.neighbourhood, z.borough, z.lat, z.lon) for z in _geo.ZIPS
)

# §4.6 gives these eight explicitly. Kept verbatim as display copy even though a
# few disagree with the centroid arithmetic -- see MILES_FROM_CAMPUS_OVERRIDES in
# the audit below and §"Known divergences" in docs/mock_data_spec.md.
_SPEC_MILES_FROM_CAMPUS: dict[str, float] = {
    "10027": 0.2,
    "10025": 0.9,
    "10031": 1.1,
    "10026": 1.3,
    "10024": 1.6,
    "10036": 3.4,
    "10018": 4.1,
    "11106": 5.2,
}


def haversine_mi(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in miles. Unrounded -- callers decide precision."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_MI * math.asin(math.sqrt(a))


class Zip:
    """One row of the §4.6 reference table."""

    __slots__ = ("zip_code", "neighbourhood", "borough", "lat", "lon", "miles_from_campus")

    def __init__(self, zip_code, neighbourhood, borough, lat, lon, miles_from_campus):
        self.zip_code = zip_code
        self.neighbourhood = neighbourhood
        self.borough = borough
        self.lat = lat
        self.lon = lon
        self.miles_from_campus = miles_from_campus

    def __repr__(self):
        return "Zip(%s, %r, %.1f mi)" % (
            self.zip_code,
            self.neighbourhood,
            self.miles_from_campus,
        )


def _build() -> "dict[str, Zip]":
    table = {}
    for code, hood, borough, lat, lon in _ZIP_ROWS:
        if code in _SPEC_MILES_FROM_CAMPUS:
            miles = _SPEC_MILES_FROM_CAMPUS[code]
        else:
            miles = round(haversine_mi(CAMPUS_LAT, CAMPUS_LON, lat, lon), 1)
        table[code] = Zip(code, hood, borough, lat, lon, miles)
    return table


ZIPS: "dict[str, Zip]" = _build()
ZIP_CODES: tuple[str, ...] = tuple(ZIPS)

# §4.6: "Reject anything outside the NYC metro at sign-up". Membership in this
# table is that check.
def is_nyc_metro(zip_code: str) -> bool:
    return zip_code in ZIPS


def centroid(zip_code: str) -> "tuple[float, float]":
    z = ZIPS[zip_code]
    return z.lat, z.lon


def distance_mi(zip_a: str, zip_b: str) -> float:
    """§5.2 distance: centroid to centroid, rounded to one decimal.

    Same-ZIP pairs return 0.0. §5.2 notes the UI shows these as "0.0-0.5 mi" and
    says that is expected and "should not be special-cased", so the arithmetic is
    left alone here and the presentation is the frontend's business.
    """
    if zip_a == zip_b:
        return 0.0
    la, lo = centroid(zip_a)
    lb, lob = centroid(zip_b)
    return round(haversine_mi(la, lo, lb, lob), 1)


def within(zip_a: str, zip_b: str, radius_mi: float) -> bool:
    """§5.2: the radius filter is ``distance_mi <= radius``."""
    return distance_mi(zip_a, zip_b) <= radius_mi


def audit_against_spec() -> "list[tuple[str, float, float, float]]":
    """Compare §4.6's stated miles-from-campus to the centroid arithmetic.

    Returns ``(zip, spec_miles, computed_miles, delta)`` for the eight ZIPs the
    spec names. Reported rather than silently reconciled -- see the divergence
    note in docs/mock_data_spec.md.
    """
    rows = []
    for code, spec_miles in _SPEC_MILES_FROM_CAMPUS.items():
        z = ZIPS[code]
        computed = round(haversine_mi(CAMPUS_LAT, CAMPUS_LON, z.lat, z.lon), 1)
        rows.append((code, spec_miles, computed, round(computed - spec_miles, 1)))
    return sorted(rows, key=lambda r: r[1])


def _check() -> None:
    assert len(ZIPS) == len(_ZIP_ROWS), "duplicate ZIP in the table"
    for code, z in ZIPS.items():
        assert len(code) == 5 and code.isdigit(), "bad ZIP %r" % code
        assert 40.4 < z.lat < 41.1 and -74.3 < z.lon < -73.6, (
            "%s is not in the NYC metro box" % code
        )
    for code in _SPEC_MILES_FROM_CAMPUS:
        assert code in ZIPS, "§4.6 names %s but the table lacks it" % code
    # Distance must be symmetric and zero on the diagonal.
    assert distance_mi("10027", "10027") == 0.0
    assert distance_mi("10027", "11215") == distance_mi("11215", "10027")


_check()


if __name__ == "__main__":
    print("NYC metro ZIP table — %d ZIPs\n" % len(ZIPS))
    print("%-7s %-34s %-10s %8s" % ("ZIP", "NEIGHBOURHOOD", "BOROUGH", "MI FROM"))
    for z in sorted(ZIPS.values(), key=lambda z: z.miles_from_campus):
        print("%-7s %-34s %-10s %8.1f" % (z.zip_code, z.neighbourhood, z.borough, z.miles_from_campus))

    print("\n\nAudit — UX_SPEC §4.6 stated miles vs centroid arithmetic\n")
    print("%-7s %8s %10s %8s" % ("ZIP", "SPEC", "COMPUTED", "DELTA"))
    for code, spec_mi, computed, delta in audit_against_spec():
        flag = "  <-- differs" if abs(delta) >= 0.4 else ""
        print("%-7s %8.1f %10.1f %+8.1f%s" % (code, spec_mi, computed, delta, flag))

    print("\n\nDistance matrix from 10027 (the reference viewer's ZIP)\n")
    for z in sorted(ZIPS.values(), key=lambda z: distance_mi("10027", z.zip_code)):
        d = distance_mi("10027", z.zip_code)
        if d <= 10.0:
            print("  %-7s %-34s %5.1f mi" % (z.zip_code, z.neighbourhood, d))
