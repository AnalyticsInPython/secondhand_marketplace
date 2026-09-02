"""The domain gate, spec step 03.

The demo gate for that step is: a Columbia address gets in, a Gmail address is
turned away with a message that explains why. These are that check.
"""

import pytest

from app.domains import college_from_email, domain_of, normalize, rejection_reason
from app.enums import College

LAUNCH_DOMAINS = {
    "columbia.edu",
    "gsb.columbia.edu",
    "cumc.columbia.edu",
    "tc.columbia.edu",
}


@pytest.mark.parametrize("email", [
    "uni1234@columbia.edu",
    "UNI1234@Columbia.EDU",
    "  student@gsb.columbia.edu  ",
    "resident@cumc.columbia.edu",
    "student@tc.columbia.edu",
])
def test_columbia_addresses_are_accepted(email):
    assert rejection_reason(normalize(email), LAUNCH_DOMAINS) is None


def test_the_agreed_allowlist_is_the_default():
    """The four domains the team settled on, and nothing else.

    _env_file=None so a teammate's local .env cannot fail this -- the point is
    what someone gets with no configuration at all.
    """
    from app.config import Settings

    assert Settings(_env_file=None).domains == LAUNCH_DOMAINS


@pytest.mark.parametrize("email", [
    "someone@gmail.com",
    "someone@columbia.edu.evil.com",
    "someone@notcolumbia.edu",
])
def test_outside_addresses_are_rejected(email):
    reason = rejection_reason(normalize(email), LAUNCH_DOMAINS)
    assert reason is not None
    assert "Columbia students only" in reason


def test_rejection_names_every_domain_that_would_work():
    reason = rejection_reason("someone@gmail.com", LAUNCH_DOMAINS)
    for domain in LAUNCH_DOMAINS:
        assert "@" + domain in reason


@pytest.mark.parametrize("email,expected", [
    ("", "Enter your Columbia email address."),
    ("not-an-email", "That does not look like a valid email address."),
    ("@columbia.edu", "That does not look like a valid email address."),
])
def test_malformed_input_gets_its_own_message(email, expected):
    assert rejection_reason(normalize(email), LAUNCH_DOMAINS) == expected


def test_other_columbia_subdomains_are_still_refused():
    """barnard and law are Columbia-adjacent but not on the agreed list."""
    for email in ("someone@barnard.edu", "someone@law.columbia.edu"):
        assert rejection_reason(email, LAUNCH_DOMAINS) is not None


@pytest.mark.parametrize("email,expected", [
    ("student@gsb.columbia.edu", College.CBS),
    ("student@tc.columbia.edu", College.TC),
])
def test_unambiguous_subdomains_prefill_the_college_dropdown(email, expected):
    assert college_from_email(email) is expected


@pytest.mark.parametrize("email", [
    "uni1234@columbia.edu",      # every school issues these
    "resident@cumc.columbia.edu",  # VP&S, Mailman, Nursing and Dental alike
])
def test_ambiguous_domains_prefill_nothing(email):
    """These say nothing about which school, so the member picks."""
    assert college_from_email(email) is None


def test_domain_of():
    assert domain_of("a@b.columbia.edu") == "b.columbia.edu"
    assert domain_of("garbage") == ""
