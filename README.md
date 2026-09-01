# MarketPlace

A Columbia-only secondhand marketplace, filtered by what you have in common with
the seller. See [PROPOSAL.md](PROPOSAL.md) for the product case and
[WORKFLOW.md](WORKFLOW.md) for how the app actually flows.

**Team:** Brian (Dongwoo), Jaewon (Jae), Vinayak, Kobe

## Status

The entry flow works end to end: Columbia email gate → invitation (new user) or
one-time passcode (returning user) → onboarding → `/home`. `/home` is a
deliberately blank canvas; browse, the feed, and posting get built there.

Onboarding collects a display name only. The three self-declared attributes —
location, nationality, industry — are deferred until their option sets are
agreed. The `users` columns already exist, so adding the step back is a
template change.

## Running it

Requires Python 3.10+ from [python.org](https://www.python.org/downloads/) —
the Microsoft Store shim on Windows will not work.

```bash
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env          # then set SECRET_KEY
flask --app app init-db       # creates instance/marketplace.db
flask --app app run --debug
```

Open http://127.0.0.1:5000.

`init-db` **drops every table**. Run it once at the start, and again only when
you want a clean slate.

## Email

**Developing:** `MAIL_BACKEND=file` (the default) never sends anything. It
writes each message to `instance/outbox/` *and* prints it to the terminal you
ran `flask` in — so the invitation link and the 6-digit code are always right
there to copy.

**Pilot:** `MAIL_BACKEND=smtp` with a Gmail app password. Turn on 2-Step
Verification on the sending account, create a password at
[myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords),
and put it in `SMTP_PASSWORD`. No sender domain needed. Gmail caps at roughly
500 recipients a day and mail from a personal address can land in spam — both
fine at pilot size, neither fine at launch.

## Layout

```
app.py          app factory, config, the /home route
auth.py         the entire entry flow — gate, invites, OTP, onboarding
db.py           SQLite connection handling, event logging
mailer.py       console / file / smtp backends
schema.sql      users, invites, otp_codes, auth_events
templates/      gate, invite_sent, verify, onboarding, home
static/css/     one stylesheet
```

`instance/` holds the database and the dev outbox. It is gitignored — everyone
runs their own.

## Conventions

- Timestamps are ISO-8601 UTC strings everywhere.
- Auth policy (code length, TTLs, attempt caps) lives in the constants at the
  top of `auth.py`. Change it there, not inline.
- Every step of the funnel writes to `auth_events`; keep it that way, it is the
  data behind the drop-off analysis.
