"""The one test that must exist (build spec step 10):

    No API response to member B ever contains an attribute of member A that B
    does not share.

Alice is built from values that cannot appear anywhere else in a response —
then every payload B can fetch is checked for them as raw text.
"""

import json

from tests.conftest import make_client, post_listing, signup

ALICE = dict(
    email="alice.disclosure@columbia.edu",
    username="alicedisc",
    phone="+16465559911",
    nationality="KR",
    school="law",
    grade="faculty_staff",
    zip_code="10031",
)
RAW = [ALICE["email"], ALICE["phone"], '"KR"', '"law"', '"faculty_staff"', "alice.disclosure"]


def _everything_bob_can_see(bob, listing_id):
    bob.post(f"/listings/{listing_id}/save")
    pages = [
        bob.get("/listings").json(),
        bob.get("/listings", params={"q": "lamp"}).json(),
        bob.get("/listings/facets").json(),
        bob.get(f"/listings/{listing_id}").json(),
        bob.get("/me/saved").json(),
    ]
    return json.dumps(pages)


def test_no_overlap_reveals_nothing():
    alice = make_client()
    signup(alice, **ALICE)
    listing = post_listing(alice, title="Desk lamp", category="electronics", subcategory=None, zip_code="10031")

    bob = make_client()
    signup(bob, "bob.disclosure@columbia.edu", nationality="BR", school="gsapp", grade="undergraduate", zip_code="11215")
    text = _everything_bob_can_see(bob, listing["id"])
    for raw in RAW:
        assert raw not in text, raw
    assert bob.get(f"/listings/{listing['id']}").json()["seller"]["badges"] == []


def test_partial_overlap_reveals_only_the_badge_not_the_value():
    alice = make_client()
    signup(alice, **ALICE)
    listing = post_listing(alice, title="Desk lamp", category="electronics", subcategory=None, zip_code="10031")

    carol = make_client()
    signup(carol, "carol.disclosure@columbia.edu", nationality="KR", school="gsapp", grade="undergraduate", zip_code="11215")
    text = _everything_bob_can_see(carol, listing["id"])
    for raw in RAW:
        assert raw not in text, raw
    assert carol.get(f"/listings/{listing['id']}").json()["seller"]["badges"] == ["SAME COUNTRY"]


def test_contact_details_appear_only_after_the_button():
    alice = make_client()
    signup(alice, **ALICE)
    listing = post_listing(alice, title="Desk lamp", category="electronics", subcategory=None, zip_code="10031")
    bob = make_client()
    signup(bob, "bob.disclosure@columbia.edu", nationality="BR", school="gsapp", grade="undergraduate", zip_code="11215")

    r = bob.post(f"/listings/{listing['id']}/enquiry", json={"channel": "sms"}).json()
    assert r == {"channel": "sms", "address": None, "phone": ALICE["phone"]}
    # And still nothing raw about Alice on the page itself.
    assert ALICE["phone"] not in json.dumps(bob.get(f"/listings/{listing['id']}").json())
