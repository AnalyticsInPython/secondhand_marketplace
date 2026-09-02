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

import math

# 116th & Broadway -- the reference point for the §4.6 "miles from campus" column.
CAMPUS_LAT = 40.8075
CAMPUS_LON = -73.9626

EARTH_RADIUS_MI = 3958.7613


# (zip, neighbourhood, borough, lat, lon)
# Neighbourhood names for the eight ZIPs in §4.6 are the spec's own wording.
_ZIP_ROWS: tuple[tuple[str, str, str, float, float], ...] = (
    # ---- Manhattan, uptown (the pilot's centre of gravity) ----
    ("10027", "Morningside Heights", "Manhattan", 40.8117, -73.9532),
    ("10025", "Upper West Side", "Manhattan", 40.7986, -73.9680),
    ("10026", "South Harlem", "Manhattan", 40.8026, -73.9526),
    ("10031", "Hamilton Heights", "Manhattan", 40.8253, -73.9500),
    ("10030", "Central Harlem", "Manhattan", 40.8181, -73.9426),
    ("10037", "Harlem River", "Manhattan", 40.8129, -73.9370),
    ("10039", "Harlem", "Manhattan", 40.8264, -73.9365),
    ("10032", "Washington Heights", "Manhattan", 40.8386, -73.9424),
    ("10033", "Washington Heights North", "Manhattan", 40.8501, -73.9340),
    ("10040", "Fort George", "Manhattan", 40.8582, -73.9294),
    ("10034", "Inwood", "Manhattan", 40.8677, -73.9212),
    ("10029", "East Harlem", "Manhattan", 40.7919, -73.9441),
    ("10035", "East Harlem North", "Manhattan", 40.8021, -73.9297),
    # ---- Manhattan, Upper West and East ----
    ("10024", "Upper West Side (lower)", "Manhattan", 40.7862, -73.9776),
    ("10023", "Lincoln Square", "Manhattan", 40.7759, -73.9822),
    ("10128", "Upper East Side (Carnegie Hill)", "Manhattan", 40.7816, -73.9505),
    ("10028", "Upper East Side", "Manhattan", 40.7764, -73.9535),
    ("10021", "Upper East Side (Lenox Hill)", "Manhattan", 40.7695, -73.9585),
    # ---- Manhattan, midtown ----
    ("10019", "Midtown / Columbus Circle", "Manhattan", 40.7657, -73.9870),
    ("10036", "Hell's Kitchen", "Manhattan", 40.7597, -73.9900),
    ("10022", "Midtown East", "Manhattan", 40.7585, -73.9679),
    ("10018", "Midtown West", "Manhattan", 40.7549, -73.9930),
    ("10017", "Midtown East (Tudor City)", "Manhattan", 40.7522, -73.9723),
    ("10001", "Chelsea / Penn Station", "Manhattan", 40.7506, -73.9971),
    ("10016", "Murray Hill", "Manhattan", 40.7457, -73.9784),
    # ---- Manhattan, downtown ----
    ("10011", "Chelsea", "Manhattan", 40.7420, -74.0007),
    ("10010", "Gramercy", "Manhattan", 40.7388, -73.9821),
    ("10014", "West Village", "Manhattan", 40.7339, -74.0060),
    ("10003", "East Village / NoHo", "Manhattan", 40.7316, -73.9890),
    ("10009", "Alphabet City", "Manhattan", 40.7264, -73.9793),
    ("10012", "SoHo / NoHo", "Manhattan", 40.7255, -73.9976),
    ("10013", "Tribeca / Hudson Square", "Manhattan", 40.7202, -74.0050),
    ("10002", "Lower East Side", "Manhattan", 40.7157, -73.9870),
    ("10038", "Financial District", "Manhattan", 40.7092, -74.0027),
    ("10280", "Battery Park City", "Manhattan", 40.7089, -74.0170),
    # ---- Queens ----
    ("11101", "Long Island City", "Queens", 40.7505, -73.9370),
    ("11106", "Astoria", "Queens", 40.7620, -73.9310),
    ("11375", "Forest Hills", "Queens", 40.7210, -73.8458),
    ("11354", "Flushing", "Queens", 40.7678, -73.8331),
    # ---- Brooklyn ----
    ("11201", "Brooklyn Heights", "Brooklyn", 40.6939, -73.9903),
    ("11205", "Fort Greene", "Brooklyn", 40.6947, -73.9656),
    ("11211", "Williamsburg", "Brooklyn", 40.7141, -73.9535),
    ("11217", "Boerum Hill", "Brooklyn", 40.6829, -73.9787),
    ("11238", "Prospect Heights", "Brooklyn", 40.6790, -73.9640),
    ("11215", "Park Slope", "Brooklyn", 40.6672, -73.9857),
    # ---- Bronx ----
    ("10451", "South Bronx", "Bronx", 40.8203, -73.9224),
    ("10463", "Riverdale / Kingsbridge", "Bronx", 40.8807, -73.9065),
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
