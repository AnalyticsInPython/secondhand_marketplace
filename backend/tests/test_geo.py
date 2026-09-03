"""ZIP table and distance."""

from app.services import geo


def test_table_is_well_formed():
    codes = [z.zip_code for z in geo.ZIPS]
    assert len(codes) == len(set(codes)), "duplicate ZIP in the table"
    assert all(len(c) == 5 and c.isdigit() for c in codes)
    assert len(codes) >= 42, "the spec asks for the NYC metro set"


def test_distance_is_symmetric_and_zero_for_same_zip():
    assert geo.distance_mi("10027", "10027") == 0.0
    assert geo.distance_mi("10027", "10025") == geo.distance_mi("10025", "10027")
    assert 0.5 < geo.distance_mi("10027", "10025") < 2.0
    assert geo.distance_mi("10027", "11215") > 8


def test_unknown_zip_is_none_not_zero():
    assert geo.distance_mi("10027", "90210") is None
    assert geo.distance_mi(None, "10027") is None
    assert geo.miles_from_campus("90210") is None
    assert not geo.is_supported("90210")


def test_campus_is_near_morningside():
    assert geo.miles_from_campus("10027") < 1.0


def test_zips_within_includes_origin_and_grows_with_radius():
    steps = [0.5, 1, 2.5, 5, 10]
    sets = [set(geo.zips_within("10027", r)) for r in steps]
    assert "10027" in sets[0]
    for smaller, larger in zip(sets, sets[1:]):
        assert smaller <= larger
    assert len(sets[-1]) >= 40
    assert geo.zips_within("90210", 10) == []


def test_search_matches_prefix_neighbourhood_and_borough():
    assert all(r["zip_code"].startswith("100") for r in geo.search("100"))
    assert {r["zip_code"] for r in geo.search("astoria")} >= {"11106", "11102"}
    assert all(r["borough"] == "Brooklyn" for r in geo.search("brooklyn"))
    assert geo.search("zzz") == []


def test_search_orders_by_distance_from_origin():
    results = geo.search("1", origin_zip="11215")
    assert results[0]["zip_code"] == "11215"
    assert results[0]["miles_away"] == 0.0


def test_zips_endpoint_works_signed_out(client):
    r = client.get("/zips", params={"q": "1002"})
    assert r.status_code == 200
    assert {"zip_code", "neighbourhood", "borough", "miles_away", "miles_from_campus"} <= r.json()[0].keys()
