"""ZIP reference table and distance — UX_SPEC.md §4.6 and §5.2.

Distance is measured between ZIP centroids. No GPS permission is ever requested
and no street address is stored, so this is the only geography the product has.

The table is deliberately static: it is small, it never changes at request time,
and a geocoding API call per listing would be both slow and pointless. The
centroids are approximate (within a few hundred feet), which is well inside the
0.1 mi rounding the product shows.
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


# The NYC metro set the pilot admits. Extend this list rather than adding a
# geocoding dependency; anything not here is refused at sign-up (state A8).
ZIPS: list[Zip] = [
    # ---- Manhattan, north to south
    Zip("10034", "Inwood", "Manhattan", 40.8672, -73.9213),
    Zip("10040", "Fort George", "Manhattan", 40.8583, -73.9296),
    Zip("10033", "Washington Heights", "Manhattan", 40.8501, -73.9339),
    Zip("10032", "Washington Heights", "Manhattan", 40.8387, -73.9425),
    Zip("10039", "Harlem", "Manhattan", 40.8268, -73.9375),
    Zip("10031", "Hamilton Heights", "Manhattan", 40.8251, -73.9500),
    Zip("10030", "Central Harlem", "Manhattan", 40.8183, -73.9426),
    Zip("10037", "Central Harlem", "Manhattan", 40.8128, -73.9375),
    Zip("10027", "Morningside Heights", "Manhattan", 40.8115, -73.9535),
    Zip("10026", "South Harlem", "Manhattan", 40.8027, -73.9526),
    Zip("10025", "Upper West Side", "Manhattan", 40.7987, -73.9665),
    Zip("10035", "East Harlem", "Manhattan", 40.7958, -73.9295),
    Zip("10029", "East Harlem", "Manhattan", 40.7917, -73.9439),
    Zip("10024", "Upper West Side (lower)", "Manhattan", 40.7864, -73.9764),
    Zip("10128", "Carnegie Hill", "Manhattan", 40.7816, -73.9500),
    Zip("10028", "Upper East Side", "Manhattan", 40.7764, -73.9536),
    Zip("10023", "Lincoln Square", "Manhattan", 40.7756, -73.9825),
    Zip("10075", "Upper East Side", "Manhattan", 40.7733, -73.9562),
    Zip("10021", "Upper East Side", "Manhattan", 40.7694, -73.9587),
    Zip("10019", "Midtown West", "Manhattan", 40.7654, -73.9870),
    Zip("10065", "Upper East Side", "Manhattan", 40.7647, -73.9633),
    Zip("10044", "Roosevelt Island", "Manhattan", 40.7618, -73.9500),
    Zip("10036", "Hell's Kitchen", "Manhattan", 40.7590, -73.9897),
    Zip("10022", "Midtown East", "Manhattan", 40.7585, -73.9677),
    Zip("10018", "Midtown West", "Manhattan", 40.7549, -73.9930),
    Zip("10017", "Midtown East", "Manhattan", 40.7523, -73.9725),
    Zip("10001", "Chelsea", "Manhattan", 40.7506, -73.9971),
    Zip("10016", "Murray Hill", "Manhattan", 40.7459, -73.9781),
    Zip("10011", "Chelsea / West Village", "Manhattan", 40.7420, -74.0002),
    Zip("10010", "Gramercy", "Manhattan", 40.7390, -73.9826),
    Zip("10014", "West Village", "Manhattan", 40.7340, -74.0053),
    Zip("10003", "East Village", "Manhattan", 40.7318, -73.9891),
    Zip("10009", "Alphabet City", "Manhattan", 40.7264, -73.9787),
    Zip("10012", "SoHo / NoHo", "Manhattan", 40.7256, -73.9983),
    Zip("10013", "Tribeca", "Manhattan", 40.7207, -74.0046),
    Zip("10002", "Lower East Side", "Manhattan", 40.7157, -73.9863),
    Zip("10038", "Financial District", "Manhattan", 40.7093, -74.0027),
    Zip("10280", "Battery Park City", "Manhattan", 40.7086, -74.0166),
    # ---- Bronx, near the 1 / 4 lines
    Zip("10463", "Kingsbridge / Riverdale", "Bronx", 40.8806, -73.9065),
    Zip("10468", "Kingsbridge Heights", "Bronx", 40.8663, -73.8999),
    Zip("10453", "Morris Heights", "Bronx", 40.8523, -73.9124),
    Zip("10452", "Highbridge", "Bronx", 40.8378, -73.9233),
    Zip("10451", "Mott Haven", "Bronx", 40.8203, -73.9247),
    # ---- Queens, western
    Zip("11105", "Astoria (Ditmars)", "Queens", 40.7788, -73.9067),
    Zip("11102", "Astoria", "Queens", 40.7721, -73.9260),
    Zip("11103", "Astoria (Steinway)", "Queens", 40.7627, -73.9130),
    Zip("11106", "Astoria", "Queens", 40.7620, -73.9310),
    Zip("11372", "Jackson Heights", "Queens", 40.7517, -73.8832),
    Zip("11377", "Woodside", "Queens", 40.7449, -73.9052),
    Zip("11101", "Long Island City", "Queens", 40.7447, -73.9485),
    # ---- Brooklyn, northern and brownstone
    Zip("11222", "Greenpoint", "Brooklyn", 40.7282, -73.9470),
    Zip("11249", "Williamsburg (north)", "Brooklyn", 40.7175, -73.9612),
    Zip("11211", "Williamsburg", "Brooklyn", 40.7093, -73.9570),
    Zip("11206", "Williamsburg (east)", "Brooklyn", 40.7014, -73.9426),
    Zip("11205", "Fort Greene / Clinton Hill", "Brooklyn", 40.6945, -73.9665),
    Zip("11201", "Brooklyn Heights / Downtown", "Brooklyn", 40.6940, -73.9903),
    Zip("11217", "Boerum Hill", "Brooklyn", 40.6822, -73.9784),
    Zip("11216", "Bedford-Stuyvesant", "Brooklyn", 40.6807, -73.9491),
    Zip("11238", "Prospect Heights", "Brooklyn", 40.6792, -73.9635),
    Zip("11231", "Carroll Gardens", "Brooklyn", 40.6785, -74.0046),
    Zip("11215", "Park Slope", "Brooklyn", 40.6674, -73.9856),
    # ---- New Jersey, one PATH ride away
    Zip("07030", "Hoboken", "Hoboken, NJ", 40.7440, -74.0324),
    Zip("07310", "Newport", "Jersey City, NJ", 40.7302, -74.0338),
    Zip("07302", "Downtown Jersey City", "Jersey City, NJ", 40.7195, -74.0470),
]

_BY_CODE: dict[str, Zip] = {z.zip_code: z for z in ZIPS}


def haversine_mi(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in miles."""
    p1, p2 = radians(lat1), radians(lat2)
    dp, dl = p2 - p1, radians(lon2 - lon1)
    a = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_MI * asin(sqrt(a))


def lookup(zip_code: str | None) -> Zip | None:
    return _BY_CODE.get(zip_code or "")


def is_supported(zip_code: str) -> bool:
    """False for anything outside the NYC metro — rejected at sign-up (state A8)."""
    return zip_code in _BY_CODE


def distance_mi(zip_a: str | None, zip_b: str | None) -> float | None:
    """Distance between two ZIP centroids, rounded to one decimal.

    Returns None when either ZIP is unknown, which the UI renders as no distance
    rather than as zero — an unknown distance is not a nearby one.
    """
    a, b = lookup(zip_a), lookup(zip_b)
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
    index on `listings.zip_code`. The origin is always included: same-ZIP
    listings are 0.0 mi away by definition.
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

    Matches on the ZIP prefix, the neighbourhood or the borough, and orders by
    distance from the user's current ZIP when we know it, otherwise from campus.
    """
    q = query.strip().lower()
    origin = lookup(origin_zip)
    olat, olon = (origin.lat, origin.lon) if origin else (CAMPUS_LAT, CAMPUS_LON)

    matches = [
        z
        for z in ZIPS
        if z.zip_code.startswith(q) or q in z.neighbourhood.lower() or q in z.borough.lower()
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
