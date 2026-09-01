# MarketPlace — Application Workflow

Source of truth for how a person moves through the app. Update this file in the
same PR as any change to the flow.

**Status:** the entry flow (screens 1–4) is built. Everything after `/home` is
not.

---

## 1. The entry flow

Everything starts at one screen and one input: a Columbia email address. That
address is both the identity and the eligibility check — there is no password
anywhere in the system.

```
                        ┌──────────────────────────┐
                        │  1. GATE   ·  GET/POST / │
                        │  "Enter your Columbia    │
                        │   email"                 │
                        └────────────┬─────────────┘
                                     │ submit
                                     ▼
                        ┌──────────────────────────┐
                        │  Valid format?           │
                        │  Domain on allowlist?    │──── no ──┐
                        └────────────┬─────────────┘          │
                                     │ yes                    │
                                     ▼                        ▼
                        ┌──────────────────────────┐    re-render gate
                        │  Look up users.email     │    with an error
                        └────────────┬─────────────┘
                                     │
              ┌──────────────────────┴───────────────────────┐
              │                                              │
       no row, or                                      row exists,
       status = pending                                status = active
              │                                              │
              ▼                                              ▼
  ┌───────────────────────────┐                ┌──────────────────────────┐
  │ BRANCH A — NEW USER       │                │ BRANCH B — RETURNING     │
  │ create user (pending)     │                │ generate 6-digit OTP     │
  │ mint signed invite token  │                │ store hash, 10 min TTL   │
  │ email the link            │                │ email the code           │
  └────────────┬──────────────┘                └────────────┬─────────────┘
               ▼                                            ▼
  ┌───────────────────────────┐                ┌──────────────────────────┐
  │ 2A. INVITE SENT           │                │ 2B. VERIFY  ·  /verify   │
  │ /invite/sent              │                │ enter the 6 digits       │
  │ "check your email"        │                │ resend after 60s         │
  └────────────┬──────────────┘                └────────────┬─────────────┘
               │ clicks emailed link                        │ correct code
               ▼                                            │
  ┌───────────────────────────┐                              │
  │ /invite/accept?token=…    │                              │
  │ verify signature + single │                              │
  │ use, then start session   │                              │
  └────────────┬──────────────┘                              │
               ▼                                            │
  ┌───────────────────────────┐                              │
  │ 3. ONBOARDING             │                              │
  │ /onboarding               │                              │
  │ display name only for now │                              │
  │ (school is derived from   │                              │
  │ the email domain)         │                              │
  │ → status = active         │                              │
  └────────────┬──────────────┘                              │
               └──────────────────┬─────────────────────────┘
                                  ▼
                     ┌──────────────────────────┐
                     │  4. HOME  ·  /home       │
                     │  blank canvas — the rest │
                     │  of the app builds here  │
                     └──────────────────────────┘
```

### Screen inventory

| # | Route | Who sees it | Exits to |
|---|---|---|---|
| 1 | `GET/POST /` | everyone signed out | `/invite/sent` or `/verify` |
| 2A | `GET /invite/sent` | new addresses | the emailed link |
| — | `GET /invite/accept` | link click | `/onboarding` |
| 2B | `GET/POST /verify` | returning users | `/home` |
| 3 | `GET/POST /onboarding` | `status = pending` | `/home` |
| 4 | `GET /home` | `status = active` | *(to be built)* |

---

## 2. Account states

```
   (no row)  ──enters email──▶  pending  ──completes onboarding──▶  active
                                   ▲                                  │
                                   └──── re-invited on re-entry ──────┘
                                        (suspended is a manual admin state)
```

A `pending` user is one we have emailed but who has never finished onboarding.
Re-entering their email at the gate sends a **fresh invitation**, not an OTP —
they are still on Branch A until they have a profile.

---

## 3. Credential rules

| | Invitation link | One-time passcode |
|---|---|---|
| Form | signed URL token (`itsdangerous`) | 6 digits |
| Lifetime | 7 days | 10 minutes |
| Uses | one | one |
| Stored as | HMAC-SHA256 hash | HMAC-SHA256 hash |
| Wrong-attempt cap | n/a (signature) | 5, then the code dies |
| Re-issue | on every gate entry while pending | 60-second cooldown |

Issuing a new OTP consumes any outstanding one, so only the newest code in an
inbox ever works.

---

## 4. Decisions already made

**No passwords, ever.** The email address *is* the account. It removes password
storage, reset flows, and credential reuse from scope, and the Columbia domain
check we need for eligibility is the same check that authenticates.

**The gate reveals which branch you are on.** A visitor learns whether an
address is already registered. That is textbook user enumeration, and we are
accepting it: the two branches send genuinely different emails and need
different next screens, and hiding it would mean a single vague "check your
email" page that makes the new-user path materially worse. The exposure is
limited to `@columbia.edu` addresses, which are already directory-listed.
Revisit if we ever open past Columbia.

**School is verified; the other three are self-declared.** Straight from the
proposal. The domain proves the school, which is exactly why the gate is a
domain check rather than a generic email check.

**Four domains are in scope.** `columbia.edu`, `gsb.columbia.edu`,
`cumc.columbia.edu`, `tc.columbia.edu`. Barnard is out. Alumni addresses are a
separate question nobody has raised yet.

**The self-declared attributes are deferred.** Onboarding asks for a display
name and nothing else. Location, nationality and industry are unfilterable as
free text — "Korea" and "South Korea" never match — so collecting them before
their option sets exist would produce data we would have to throw away. The
`users` columns are already in place; adding the step back is a change to
`templates/onboarding.html` and the `UPDATE` in `auth.onboarding`.

**Gmail with an app password sends the pilot mail.** No sender domain, no
provider account, no DNS. It caps at roughly 500 recipients a day and can land
in spam, which is acceptable at pilot size and not at launch.

**Onboarding sits on the invite branch only.** Returning users already have a
profile, so the OTP branch goes straight to `/home`.

---

## 5. Open decisions

Each needs a team call.

1. **What does the invitation carry?** The token holds `user_id` and `email`
   today. If we want to know which recruiting channel produced which users, it
   needs a referrer or cohort tag before the first invite goes out — this is
   not recoverable after the fact.
2. **Option sets for location, nationality and industry.** Deferred, not
   dropped. Browse cannot be built until these lists exist, so they are the
   real blocker on the next phase.
3. **Session length.** No expiry is set, so it currently runs a month. A
   semester-long cookie is friendlier for a campus tool; 30 days is easier to
   defend.
4. **Rate limiting per address and per IP.** Only the 60-second OTP cooldown
   exists. Nothing stops someone walking the alphabet through the gate.

---

## 6. What gets built next

In proposal order, all on the `/home` canvas:

1. **Filtered browse** — the four attribute toggles, with a live listing count
   so the trust/selection trade-off stays visible.
2. **Two-tier feed** — internal listings with match badges above external
   scraped listings, clearly labelled and linking out to their source.
3. **Listing detail.**
4. **Posting, with audience selection** — the seller picks which circle sees a
   listing, with the reach count shown per option.

The `auth_events` table is already logging every step of the funnel, so the
drop-off analysis is available the moment there are real users.
