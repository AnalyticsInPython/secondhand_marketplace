"""The domain gate, spec step 03.

The demo gate for that step is: a Columbia address gets in, a Gmail address is
turned away with a message that explains why. These are that check.
"""

import pytest

from app.domains import college_from_email, domain_of, normalize, rejection_reason
from app.enums import College

LAUNCH_DOMAINS = {"columbia.edu", "gsb.columbia.edu"}


@pytest.mark.parametrize("email", [
    "uni1234@columbia.edu",
    "UNI1234@Columbia.EDU",
    "  student@gsb.columbia.edu  ",
])
def test_columbia_addresses_are_accepted(email):
    assert rejection_reason(normalize(email), LAUNCH_DOMAINS) is None


@pytest.mark.parametrize("email", [
    "someone@gmail.com",
    "someone@columbia.edu.evil.com",
    "someone@notcolumbia.edu",
])
def test_outside_addresses_are_rejected(email):
    reason = rejection_reason(normalize(email), LAUNCH_DOMAINS)
    assert reason is not None
    assert "Columbia students only" in reason


def test_rejection_names_the_domains_that_would_work():
    reason = rejection_reason("someone@gmail.com", LAUNCH_DOMAINS)
    assert "@columbia.edu" in reason
    assert "@gsb.columbia.edu" in reason


@pytest.mark.parametrize("email,expected", [
    ("", "Enter your Columbia email address."),
    ("not-an-email", "That does not look like a valid email address."),
    ("@columbia.edu", "That does not look like a valid email address."),
])
def test_malformed_input_gets_its_own_message(email, expected):
    assert rejection_reason(normalize(email), LAUNCH_DOMAINS) == expected


def test_domains_not_yet_open_are_refused():
    """cumc and tc are in the spec's vocabulary but not the launch allowlist."""
    assert rejection_reason("someone@tc.columbia.edu", LAUNCH_DOMAINS) is not None


def test_subdomain_prefills_the_college_dropdown():
    assert college_from_email("student@gsb.columbia.edu") is College.CBS


def test_plain_columbia_address_prefills_nothing():
    """@columbia.edu says nothing about which school, so the student picks."""
    assert college_from_email("uni1234@columbia.edu") is None


def test_domain_of():
    assert domain_of("a@b.columbia.edu") == "b.columbia.edu"
    assert domain_of("garbage") == ""
