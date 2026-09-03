"""GET /listings, its live facet counts, posting, saving and enquiries."""

from app.db import SessionLocal
from app.models import ListingView
from tests.conftest import make_client, post_listing, signup, upload_photo


def _world():
    """Two sellers, one viewer, four listings (one already sold)."""
    a = make_client()
    signup(a, "alice@columbia.edu", nationality="KR", school="cbs", zip_code="10027")
    a_desk = post_listing(a, title="IKEA desk, white", category="furniture", subcategory="desks", price_cents=6000)
    a_book = post_listing(a, title="Corporate Finance textbook", category="textbooks", subcategory=None, condition="like_new", price_cents=3000)

    b = make_client()
    signup(b, "bob@columbia.edu", nationality="US", school="seas_grad", zip_code="10025", phone="")
    b_lamp = post_listing(b, title="IKEA lamp", category="electronics", subcategory=None, condition="new", price_cents=20000, zip_code="10025")
    b_sold = post_listing(b, title="Old chair", category="furniture", subcategory="chairs", price_cents=1000, zip_code="10025")
    assert b.post(f"/listings/{b_sold['id']}/sold").status_code == 204

    v = make_client()
    signup(v, "vik@columbia.edu", nationality="KR", school="seas_grad", zip_code="10027")
    return dict(a=a, b=b, v=v, a_desk=a_desk, a_book=a_book, b_lamp=b_lamp, b_sold=b_sold)


def test_feed_requires_sign_in(client):
    assert client.get("/listings").status_code == 401
    assert client.get("/listings/facets").status_code == 401


def test_feed_carries_computed_badges_and_distance():
    w = _world()
    assert w["v"].get("/listings").json()["items"][0]["status"] == "active"
    page = w["v"].get("/listings").json()
    assert page["total"] == 3  # the sold chair is out
    by_title = {i["title"]: i for i in page["items"]}
    assert by_title["IKEA desk, white"]["badges"] == ["SAME ZIP", "SAME COUNTRY"]
    assert by_title["IKEA desk, white"]["distance_mi"] == 0.0
    assert by_title["IKEA lamp"]["badges"] == ["SAME SCHOOL"]
    assert 0.5 < by_title["IKEA lamp"]["distance_mi"] < 2.0
    assert by_title["IKEA lamp"]["neighbourhood"] == "Upper West Side"
    assert by_title["IKEA desk, white"]["cover_photo_url"].endswith(".webp")
    # Nothing raw about the seller is on a card.
    assert not {"nationality", "school", "grade", "email", "phone", "seller"} & by_title["IKEA lamp"].keys()


def test_facets_agree_with_the_feed():
    w = _world()
    v = w["v"]
    facets = v.get("/listings/facets").json()
    assert facets["total"] == v.get("/listings").json()["total"] == 3

    for c in facets["categories"]:
        assert c["count"] == v.get("/listings", params={"category": c["key"]}).json()["total"], c
    for c in facets["conditions"]:
        assert c["count"] == v.get("/listings", params={"condition": c["key"]}).json()["total"], c
    for s in facets["subcategories"]:
        assert s["count"] == v.get("/listings", params={"subcategory": s["key"]}).json()["total"], s
    assert facets["same_zip"] == v.get("/listings", params={"same_zip": True}).json()["total"] == 2
    assert facets["same_nationality"] == v.get("/listings", params={"same_nationality": True}).json()["total"] == 2
    assert facets["same_school"] == v.get("/listings", params={"same_school": True}).json()["total"] == 1
    for step in facets["radius_steps"]:
        assert step["count"] == v.get("/listings", params={"radius_mi": step["key"]}).json()["total"], step
    assert [s["key"] for s in facets["radius_steps"]] == ["0.5", "1", "2.5", "5", "10"]
    assert facets["radius_steps"][0]["count"] == 2  # 0.5 mi: only the two in 10027


def test_facets_are_live_against_the_other_filters():
    w = _world()
    v = w["v"]
    f = v.get("/listings/facets", params={"category": "furniture"}).json()
    assert f["total"] == 1
    # Category counts are "if only this were ticked" — the other categories keep their numbers.
    assert {c["key"]: c["count"] for c in f["categories"]}["textbooks"] == 1
    # Everything else respects the category filter.
    assert sum(c["count"] for c in f["conditions"]) == 1
    assert f["same_school"] == 0

    f = v.get("/listings/facets", params={"same_school": True}).json()
    assert f["total"] == 1 and f["same_zip"] == 0 and f["same_nationality"] == 0
    assert {c["key"]: c["count"] for c in f["categories"]}["electronics"] == 1

    f = v.get("/listings/facets", params={"subcategory": "desks"}).json()
    assert f["total"] == 1
    assert {s["key"]: s["count"] for s in f["subcategories"]}["desks"] == 1


def test_search_defaults_to_closest_and_filters_apply():
    w = _world()
    v = w["v"]
    hits = v.get("/listings", params={"q": "ikea"}).json()
    assert hits["total"] == 2
    assert hits["items"][0]["title"] == "IKEA desk, white"  # 0.0 mi beats 1.1 mi
    newest = v.get("/listings", params={"q": "ikea", "sort": "newest"}).json()
    assert newest["items"][0]["title"] == "IKEA lamp"

    assert v.get("/listings", params={"price_max_cents": 5000}).json()["total"] == 1
    assert v.get("/listings", params={"radius_mi": 0.5}).json()["total"] == 2
    assert v.get("/listings", params={"sort": "price_desc"}).json()["items"][0]["title"] == "IKEA lamp"
    assert v.get("/listings", params={"limit": 2}).json()["next_cursor"] == "2"


def test_impressions_are_logged_with_the_badge_flag():
    w = _world()
    w["v"].get("/listings")
    w["v"].get("/listings", params={"q": "ikea"})
    db = SessionLocal()
    try:
        rows = db.query(ListingView).all()
    finally:
        db.close()
    assert sorted(r.surface.value for r in rows) == ["feed"] * 3 + ["search"] * 2
    assert all(r.badges_shown is True for r in rows)


def test_detail_page_view_counting_and_seller_block():
    w = _world()
    lid = w["a_desk"]["id"]
    d = w["v"].get(f"/listings/{lid}").json()
    assert d["view_count"] == 1 and d["is_owner"] is False and d["is_saved"] is False
    assert d["seller"].keys() == {"username", "display_name", "is_verified", "member_since", "badges", "can_receive_sms"}
    assert d["seller"]["badges"] == ["SAME ZIP", "SAME COUNTRY"]
    assert d["photo_urls"] and d["photos"][0]["width"] == 800

    own = w["a"].get(f"/listings/{lid}").json()
    assert own["is_owner"] is True and own["view_count"] == 1  # owner views are not counted
    assert own["seller"]["badges"] == []

    assert w["v"].get("/listings/nope").status_code == 404


def test_posting_rules():
    c = make_client()
    signup(c, "poster@columbia.edu")
    base = {"title": "Thing", "category": "furniture", "condition": "new", "price_cents": 1000, "zip_code": "10027"}
    assert c.post("/listings", json={**base, "photo_urls": []}).status_code == 422  # a photo is required
    assert c.post("/listings", json={**base, "photo_urls": ["http://testserver/media/nope.webp"]}).status_code == 422
    assert c.post("/listings", json={**base, "photo_urls": [upload_photo(c)], "price_cents": 0}).status_code == 422
    assert c.post("/listings", json={**base, "photo_urls": [upload_photo(c)], "subcategory": "chairs", "category": "textbooks"}).status_code == 422
    assert c.post("/listings", json={**base, "photo_urls": [upload_photo(c)], "zip_code": "90210"}).status_code == 422

    other = make_client()
    signup(other, "thief@columbia.edu")
    someone_elses = upload_photo(c)
    assert other.post("/listings", json={**base, "photo_urls": [someone_elses]}).status_code == 422

    free = c.post("/listings", json={**base, "photo_urls": [upload_photo(c)], "price_cents": 0, "is_free": True}).json()
    assert free["is_free"] is True and free["price_cents"] == 0 and free["view_count"] == 0


def test_owner_edits_and_status_transitions():
    w = _world()
    a, v, lid = w["a"], w["v"], w["a_desk"]["id"]
    assert v.patch(f"/listings/{lid}", json={"title": "hijack"}).status_code == 404

    r = a.patch(f"/listings/{lid}", json={"title": "IKEA desk, oak", "price_cents": 5000, "status": "sold"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "sold" and r.json()["sold_at"]
    assert v.get("/listings").json()["total"] == 2  # sold drops out of the feed
    assert v.get(f"/listings/{lid}").status_code == 200  # but the page stays reachable

    r = a.patch(f"/listings/{lid}", json={"status": "active"})
    assert r.json()["sold_at"] is None and v.get("/listings").json()["total"] == 3

    a.patch(f"/listings/{lid}", json={"status": "delisted"})
    assert v.get(f"/listings/{lid}").status_code == 404
    assert a.get(f"/listings/{lid}").status_code == 200
    mine = a.get("/me/listings").json()
    assert mine["total"] == 2
    assert {m["title"]: m["status"] for m in mine["items"]}["IKEA desk, oak"] == "delisted"

    # Photos: add a second, make it the cover.
    second = upload_photo(a)
    first = w["a_desk"]["photo_urls"][0]
    r = a.patch(f"/listings/{lid}", json={"photo_urls": [second, first]})
    assert r.json()["photo_urls"] == [second, first] and r.json()["photo_count"] == 2


def test_save_and_unsave():
    w = _world()
    v, lid = w["v"], w["a_desk"]["id"]
    assert v.post(f"/listings/{lid}/save").status_code == 204
    assert v.post(f"/listings/{lid}/save").status_code == 204  # idempotent
    d = v.get(f"/listings/{lid}").json()
    assert d["is_saved"] is True and d["save_count"] == 1
    saved = v.get("/me/saves").json()
    assert saved["total"] == 1 and [s["id"] for s in saved["items"]] == [lid]
    assert v.delete(f"/listings/{lid}/save").status_code == 204
    assert v.get(f"/listings/{lid}").json()["save_count"] == 0


def test_enquiry_is_the_only_place_contact_details_appear():
    w = _world()
    v = w["v"]
    r = v.post(f"/listings/{w['a_desk']['id']}/enquiry", json={"channel": "email"})
    assert r.status_code == 200 and r.json() == {"channel": "email", "address": "alice@columbia.edu", "phone": None}
    assert v.get(f"/listings/{w['a_desk']['id']}").json()["enquiry_count"] == 1
    inbox = v.get("/me/enquiries").json()
    assert [(row["listing"]["id"], row["channel"], row["seller_username"]) for row in inbox] == [
        (w["a_desk"]["id"], "email", "alice")
    ]

    # Bob has no number: the SMS channel is refused even if asked for.
    r = v.post(f"/listings/{w['b_lamp']['id']}/enquiry", json={"channel": "sms"})
    assert r.status_code == 409

    assert v.post(f"/listings/{w['b_sold']['id']}/enquiry", json={"channel": "email"}).status_code == 409
    assert w["a"].post(f"/listings/{w['a_desk']['id']}/enquiry", json={"channel": "email"}).status_code == 409


def test_filter_events_are_recorded(client):
    signup(client, "log@columbia.edu")
    assert client.post("/listings/events/filter", params={"filter_key": "same_zip", "result_count": 12, "value": "true"}).status_code == 204
