"""ZIP reference table and distance — UX_SPEC.md §4.6 and §5.2.

Distance is measured between ZIP centroids. No GPS permission is ever requested
and no street address is stored, so this is the only geography the product has.

The table is deliberately static: it is small, it never changes at request time,
and a geocoding API call per listing would be both slow and pointless.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_MI = 3958.7613

# Columbia's Morningside campus, 116th & Broadway.
CAMPUS_LAT, CAMPUS_LON = 40.8075, -73.9626


@dataclass(frozen=True)
class Zip:
    zip_code: str
    neighbourhood: str
    borough: str
    lat: float
    lon: float


# NYC metro subset. Extend this list rather than adding a geocoding dependency;
# the pilot is NYC-only by design (UX_SPEC.md §11 open question 5).
ZIPS: list[Zip] = [
    Zip("10027", "Morningside Heights", "Manhattan", 40.8115, -73.9535),
    Zip("10025", "Upper West Side", "Manhattan", 40.7987, -73.9665),
    Zip("10026", "South Harlem", "Manhattan", 40.8027, -73.9526),
    Zip("10031", "Hamilton Heights", "Manhattan", 40.8251, -73.9500),
    Zip("10024", "Upper West Side (lower)", "Manhattan", 40.7864, -73.9764),
    Zip("10032", "Washington Heights", "Manhattan", 40.8387, -73.9425),
    Zip("10023", "Lincoln Square", "Manhattan", 40.7756, -73.9825),
    Zip("10019", "Midtown West", "Manhattan", 40.7654, -73.9870),
    Zip("10036", "Hell's Kitchen", "Manhattan", 40.7590, -73.9897),
    Zip("10018", "Midtown West", "Manhattan", 40.7549, -73.9930),
    Zip("10001", "Chelsea", "Manhattan", 40.7506, -73.9971),
    Zip("10011", "Chelsea / West Village", "Manhattan", 40.7420, -74.0002),
    Zip("10003", "East Village", "Manhattan", 40.7318, -73.9891),
    Zip("11106", "Astoria", "Queens", 40.7620, -73.9310),
    Zip("11101", "Long Island City", "Queens", 40.7447, -73.9485),
    Zip("11201", "Brooklyn Heights", "Brooklyn", 40.6940, -73.9903),
    Zip("11211", "Williamsburg", "Brooklyn", 40.7093, -73.9570),
    Zip("11215", "Park Slope", "Brooklyn", 40.6674, -73.9856),
]

_BY_CODE: dict[str, Zip] = {z.zip_code: z for z in ZIPS}


def haversine_mi(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in miles."""
    p1, p2 = radians(lat1), radians(lat2)
    dp, dl = p2 - p1, radians(lon2 - lon1)
    a = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_MI * asin(sqrt(a))


def lookup(zip_code: str) -> Zip | None:
    return _BY_CODE.get(zip_code)


def is_supported(zip_code: str) -> bool:
    """False for anything outside the NYC metro — rejected at sign-up (state A8)."""
    return zip_code in _BY_CODE


def distance_mi(zip_a: str | None, zip_b: str | None) -> float | None:
    """Distance between two ZIP centroids, rounded to one decimal.

    Returns None when either ZIP is unknown, which the UI renders as no distance
    rather than as zero — an unknown distance is not a nearby one.
    """
    a, b = lookup(zip_a or ""), lookup(zip_b or "")
    if a is None or b is None:
        return None
    return round(haversine_mi(a.lat, a.lon, b.lat, b.lon), 1)


def miles_from_campus(zip_code: str) -> float | None:
    z = lookup(zip_code)
    if z is None:
        return None
    return round(haversine_mi(z.lat, z.lon, CAMPUS_LAT, CAMPUS_LON), 1)


def zips_within(origin_zip: str, radius_mi: float) -> list[str]:
    """Every supported ZIP whose centroid is within `radius_mi` of `origin_zip`.

    The feed filters on this list rather than computing distance per row, which
    keeps the radius filter a plain `IN (...)` and lets the database use its
    index on `listings.zip_code`.
    """
    origin = lookup(origin_zip)
    if origin is None:
        return []
    return [
        z.zip_code
        for z in ZIPS
        if haversine_mi(origin.lat, origin.lon, z.lat, z.lon) <= radius_mi
    ]


def search(query: str, origin_zip: str | None = None, limit: int = 8) -> list[dict]:
    """Autocomplete for the sign-up ZIP field (state A7).

    Matches on the ZIP prefix or the neighbourhood name, and orders by distance
    from the user's current ZIP when we know it, otherwise from campus.
    """
    q = query.strip().lower()
    origin = lookup(origin_zip or "")
    olat, olon = (origin.lat, origin.lon) if origin else (CAMPUS_LAT, CAMPUS_LON)

    matches = [
        z
        for z in ZIPS
        if z.zip_code.startswith(q) or q in z.neighbourhood.lower()
    ]
    matches.sort(key=lambda z: haversine_mi(z.lat, z.lon, olat, olon))
    return [
        {
            "zip_code": z.zip_code,
            "neighbourhood": z.neighbourhood,
            "borough": z.borough,
            "miles_away": round(haversine_mi(z.lat, z.lon, olat, olon), 1),
            "miles_from_campus": miles_from_campus(z.zip_code),
        }
        for z in matches[:limit]
    ]
