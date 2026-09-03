"""Magic links and sessions. There is no password anywhere in this product."""

from tests.conftest import backdate_login_tokens, expire_login_tokens, make_client, signup


def test_signup_link_verify_me_signout(client):
    r = client.post(
        "/auth/signup",
        json={
            "email": "Vinayak@Columbia.edu",
            "username": "@vinayak",
            "phone": "(646) 555-0142",
            "nationality": "in",
            "school": "seas_grad",
            "grade": "graduate",
            "zip_code": "10027",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["sent"] is True and body["dev_link"].startswith("http://localhost:3000/signin/verify?token=")

    assert client.get("/auth/me").status_code == 401  # the link has not been opened yet

    token = body["dev_link"].split("token=")[1]
    r = client.post(f"/auth/verify?token={token}")
    assert r.status_code == 200
    me = r.json()
    assert me["email"] == "vinayak@columbia.edu"
    assert me["username"] == "vinayak"
    assert me["phone"] == "+16465550142"
    assert me["nationality"] == "IN"
    assert me["is_verified"] is True
    assert "cm_session" in client.cookies

    assert client.get("/auth/me").json()["id"] == me["id"]

    assert client.post("/auth/signout").status_code == 204
    assert client.get("/auth/me").status_code == 401


def test_link_is_single_use_and_expires(client):
    r = client.post(
        "/auth/signup",
        json={"email": "a@columbia.edu", "username": "aaa", "nationality": "US", "school": "cbs", "grade": "graduate", "zip_code": "10027"},
    )
    token = r.json()["dev_link"].split("token=")[1]
    assert client.post(f"/auth/verify?token={token}").status_code == 200
    r = client.post(f"/auth/verify?token={token}")
    assert r.status_code == 400 and r.json()["detail"] == "already_used"

    assert client.post("/auth/verify?token=nonsense").json()["detail"] == "unknown"

    backdate_login_tokens("a@columbia.edu")
    fresh = client.post("/auth/request-link", json={"email": "a@columbia.edu"}).json()["dev_link"]
    expire_login_tokens("a@columbia.edu")
    r = client.post(f"/auth/verify?token={fresh.split('token=')[1]}")
    assert r.status_code == 400 and r.json()["detail"] == "expired"


def test_request_link_is_indistinguishable_for_unknown_addresses(client):
    r = client.post("/auth/request-link", json={"email": "ghost@columbia.edu"})
    assert r.status_code == 202
    assert r.json() == {"sent": True, "resend_available_in_seconds": 60, "dev_link": None}


def test_resend_is_locked_for_a_minute(client):
    signup(client, "b@columbia.edu")
    r = client.post("/auth/request-link", json={"email": "b@columbia.edu"}).json()
    assert r["sent"] is False and 0 < r["resend_available_in_seconds"] <= 60
    backdate_login_tokens("b@columbia.edu")
    r = client.post("/auth/request-link", json={"email": "b@columbia.edu"}).json()
    assert r["sent"] is True and r["dev_link"]


def test_duplicate_email_and_username_are_conflicts(client):
    signup(client, "c@columbia.edu", username="carol")
    other = make_client()
    base = {"nationality": "US", "school": "cbs", "grade": "graduate", "zip_code": "10027"}
    assert other.post("/auth/signup", json={"email": "c@columbia.edu", "username": "someoneelse", **base}).status_code == 409
    assert other.post("/auth/signup", json={"email": "d@columbia.edu", "username": "carol", **base}).status_code == 409
    avail = other.get("/auth/username-available", params={"username": "@carol"}).json()
    assert avail["available"] is False and len(avail["suggestions"]) == 3


def test_validation_at_signup(client):
    base = {"email": "e@columbia.edu", "username": "eve", "nationality": "US", "school": "cbs", "grade": "graduate"}
    assert client.post("/auth/signup", json={**base, "zip_code": "90210"}).status_code == 422  # not NYC
    assert client.post("/auth/signup", json={**base, "zip_code": "1002"}).status_code == 422  # not a ZIP
    assert client.post("/auth/signup", json={**base, "zip_code": "10027", "nationality": "XX"}).status_code == 422
    assert client.post("/auth/signup", json={**base, "zip_code": "10027", "username": "x"}).status_code == 422
    assert client.post("/auth/signup", json={**base, "zip_code": "10027", "phone": "12"}).status_code == 422


def test_blank_phone_means_no_number(client):
    me = signup(client, "f@columbia.edu", phone="   ")
    assert me["phone"] is None


def test_deactivate_is_reversed_by_signing_in_again(client):
    signup(client, "g@columbia.edu")
    assert client.post("/me/deactivate").status_code == 204
    assert client.get("/auth/me").status_code == 401

    backdate_login_tokens("g@columbia.edu")
    link = client.post("/auth/request-link", json={"email": "g@columbia.edu"}).json()["dev_link"]
    r = client.post(f"/auth/verify?token={link.split('token=')[1]}")
    assert r.status_code == 200
    assert client.get("/auth/me").status_code == 200


def test_profile_update_and_validation(client):
    signup(client, "h@columbia.edu")
    r = client.patch("/me", json={"zip_code": "11215", "phone": "", "default_radius_mi": 5, "nationality": "kr"})
    assert r.status_code == 200, r.text
    me = r.json()
    assert me["zip_code"] == "11215" and me["phone"] is None and me["nationality"] == "KR"
    assert client.patch("/me", json={"zip_code": "90210"}).status_code == 422
    assert client.patch("/me", json={"default_radius_mi": 50}).status_code == 422
