# Backend — Columbia Market API

FastAPI + SQLAlchemy, with the analysis layer in pandas. Behaviour is specified
in [`../docs/UX_SPEC.md`](../docs/UX_SPEC.md); this README only covers running it.

## Run it

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate     # Python 3.12 or 3.13
pip install -r requirements.txt
cp .env.example .env

python -m scripts.seed --users 1000 --listings 1500 --reset
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

There is no password anywhere. In dev, `EMAIL_DEV_MODE=true` means the sign-in
link is returned in the API response and printed to the console instead of being
emailed — so you can click through without an SMTP server.

## The analysis

```bash
python -m app.analytics.questions
```

Prints all five research questions from `PROPOSAL.md`. `app/analytics/frames.py`
loads the tables into pandas; a notebook can call `load()` and get the same
DataFrames the CLI prints.

## Layout

```
app/
  config.py       settings, all with working defaults
  enums.py        the contractual enum values (UX_SPEC §4.5)
  models.py       ORM schema (UX_SPEC §4)
  schemas.py      request/response shapes (UX_SPEC §8)
  security.py     magic links and sessions — no passwords
  services/
    geo.py        ZIP table, haversine, radius → ZIP list
    badges.py     overlap-only disclosure. Read this one.
  routers/
    auth.py       signup, request-link, verify, signout
    users.py      profile & account
    listings.py   feed, facets, detail, posting, saves, enquiries
    reference.py  ZIP autocomplete and enum lists for the pickers
  analytics/
    frames.py     database → pandas
    questions.py  the five research questions
scripts/
  seed.py         fake data (UX_SPEC §9)
```

## Three things that are easy to break

1. **`services/badges.py` is the product.** An attribute that does not match is
   absent from the payload — not `false`, not `null`. If a seller's raw
   nationality or school ever reaches the client, the disclosure rule is broken
   regardless of what the UI renders.
2. **Facet counts are live.** Each count is "what you would get if you applied
   this one filter, with everything else still on". They are meant to move.
   Caching them into static numbers removes the only honest signal the user has
   about the trust-versus-selection trade.
3. **`phone` is nullable and that is a feature.** A user with no number gets a
   single full-width Email button, not a disabled Text button. The seed data
   leaves ~30% of users without one so this path is always exercised.

## Database

SQLite by default. Moving to Postgres (Neon) is a `DATABASE_URL` change and
nothing else — no vendor-specific SQL is used anywhere.

`create_all()` runs at startup, which is fine while the schema is still moving.
Introduce Alembic before it stabilises.
