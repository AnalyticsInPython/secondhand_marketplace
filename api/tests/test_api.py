"""The auth router as it stands.

Supabase is not wired yet, so the only behaviour that is real is the domain
gate and the fact that a valid address gets past it.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_gmail_is_refused_with_an_explanation():
    r = client.post("/v1/auth/magic-link", json={"email": "someone@gmail.com"})
    assert r.status_code == 400
    assert "Columbia students only" in r.json()["detail"]


def test_columbia_address_passes_the_gate():
    """501, not 400 -- it cleared the check and stopped at unwired Supabase."""
    r = client.post("/v1/auth/magic-link", json={"email": "uni1234@columbia.edu"})
    assert r.status_code == 501


def test_response_shape_does_not_leak_whether_the_account_exists():
    """One flow for everyone. Two unrelated addresses, identical responses."""
    a = client.post("/v1/auth/magic-link", json={"email": "aaa1@columbia.edu"})
    b = client.post("/v1/auth/magic-link", json={"email": "zzz9@gsb.columbia.edu"})
    assert a.status_code == b.status_code
    assert a.json() == b.json()
