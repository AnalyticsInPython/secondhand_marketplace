"""A broken mailer must not lock the team out of a local build."""

from app.config import settings
from tests.conftest import backdate_login_tokens, signup


def _with_broken_smtp(monkeypatch, dev_mode: bool):
    monkeypatch.setattr(settings, "email_backend", "smtp")
    monkeypatch.setattr(settings, "smtp_host", "")  # nothing to connect to
    monkeypatch.setattr(settings, "email_dev_mode", dev_mode)


def test_dev_mode_still_hands_over_the_link(client, monkeypatch):
    signup(client, "m1@columbia.edu")
    backdate_login_tokens("m1@columbia.edu")
    _with_broken_smtp(monkeypatch, dev_mode=True)
    r = client.post("/auth/request-link", json={"email": "m1@columbia.edu"})
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["sent"] is False
    assert body["dev_link"] and "token=" in body["dev_link"]
    assert "SMTP_HOST" in body["delivery_error"]
    # And the link works.
    token = body["dev_link"].split("token=")[1]
    assert client.post(f"/auth/verify?token={token}").status_code == 200


def test_production_mode_reports_the_outage(client, monkeypatch):
    signup(client, "m2@columbia.edu")
    backdate_login_tokens("m2@columbia.edu")
    _with_broken_smtp(monkeypatch, dev_mode=False)
    r = client.post("/auth/request-link", json={"email": "m2@columbia.edu"})
    assert r.status_code == 503
    assert "could not send" in r.json()["detail"]
