"""The membership rule: who may sign in."""

import pytest

from app.enums import School
from app.services.domains import (
    domain_of,
    is_allowed,
    normalize,
    rejection_reason,
    suggested_school,
)

AGREED = frozenset({"columbia.edu", "gsb.columbia.edu", "cumc.columbia.edu", "tc.columbia.edu"})


@pytest.mark.parametrize(
    "email",
    [
        "uni1234@columbia.edu",
        "UNI1234@Columbia.EDU",
        "  student@gsb.columbia.edu  ",
        "resident@cumc.columbia.edu",
        "student@tc.columbia.edu",
    ],
)
def test_agreed_domains_are_accepted(email):
    assert is_allowed(email, AGREED)
    assert rejection_reason(email, AGREED) is None


@pytest.mark.parametrize(
    "email",
    [
        "someone@gmail.com",
        "someone@columbia.edu.evil.com",
        "someone@law.columbia.edu",
        "someone@barnard.edu",
        "columbia.edu",
        "@columbia.edu",
        "two@@columbia.edu",
    ],
)
def test_everything_else_is_refused(email):
    assert not is_allowed(email, AGREED)
    assert rejection_reason(email, AGREED) is not None


def test_rejection_names_every_domain_that_would_work():
    reason = rejection_reason("someone@gmail.com", AGREED)
    for domain in AGREED:
        assert "@" + domain in reason


def test_the_agreed_allowlist_is_the_default():
    from app.config import settings

    assert settings.domains == AGREED


def test_normalize_and_domain():
    assert normalize("  A@Columbia.EDU ") == "a@columbia.edu"
    assert domain_of("a@columbia.edu") == "columbia.edu"
    assert domain_of("nope") is None


@pytest.mark.parametrize(
    "email,expected",
    [
        ("student@gsb.columbia.edu", School.CBS),
        ("student@tc.columbia.edu", School.TEACHERS_COLLEGE),
        ("uni1234@columbia.edu", None),  # every school issues these
        ("resident@cumc.columbia.edu", None),  # VP&S, Mailman, Nursing, Dental alike
    ],
)
def test_subdomain_prefills_the_school_only_where_unambiguous(email, expected):
    assert suggested_school(email) is expected


# ---------------------------------------------------------------- through the API


def test_email_check_endpoint(client):
    ok = client.get("/auth/email-check", params={"email": "Someone@GSB.columbia.edu"}).json()
    assert ok == {
        "email": "someone@gsb.columbia.edu",
        "allowed": True,
        "reason": None,
        "suggested_school": "cbs",
    }
    bad = client.get("/auth/email-check", params={"email": "someone@gmail.com"}).json()
    assert bad["allowed"] is False and "open to" in bad["reason"]


def test_signup_and_request_link_refuse_outside_addresses(client):
    r = client.post(
        "/auth/signup",
        json={
            "email": "x@gmail.com",
            "username": "outsider",
            "nationality": "US",
            "school": "cbs",
            "grade": "graduate",
            "zip_code": "10027",
        },
    )
    assert r.status_code == 422
    r = client.post("/auth/request-link", json={"email": "x@gmail.com"})
    assert r.status_code == 422
    assert "open to" in r.json()["detail"]


def test_gsb_addresses_can_sign_up(client):
    from tests.conftest import signup

    me = signup(client, "mba@gsb.columbia.edu")
    assert me["email"] == "mba@gsb.columbia.edu"
