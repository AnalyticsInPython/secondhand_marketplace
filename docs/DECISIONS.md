# Decisions

A dated log of the decisions that changed a spec. Where this file and a spec
disagree, **this file wins**; the spec gets edited when its owner has time.

The repo carried three documents that disagreed on the data model —
`docs/UX_SPEC.md` (Brian, the Figma build), `LionsListBuildSpec.pdf` v2.0
(Vinayak, internal-only) and the README on `feat/lionslist-skeleton` (Jae,
"which spec governs: unresolved"). The entries below settle that.

---

## 2026-09-02 · Which spec governs

**`docs/UX_SPEC.md` is the build target for the data model and the screens**:
ZIP code with a distance slider, four conditions, eight categories, fourteen
schools, three grades, match badges, live facet counts. The Figma screens and
the Next.js app are built to it, and the backend assignment ("schema and
enums, the ZIP/distance service, `GET /listings` with live facet counts, auth")
is defined against it.

Two things from the v2.0 build spec are applied on top of it, below: the
external tier is gone, and the badge experiment is the causal analysis.

*Decided by Vinayak (backend owner).*

## 2026-09-02 · External tier removed

Every listing is posted by a verified member. Gone from the schema: the
`source` enum, `external_url`, the `is_external` flag and the check constraint
that tied them together; `listings.seller_id` is now `NOT NULL`. Gone from the
code: the 10% external share in the seed, the `EXTERNAL` pill and source tag on
cards, the `D11` redirect interstitial, the `source=` feed filter. Gone from
the analysis: Q1 (internal vs external engagement) and Q4 (in-group discount),
replaced by the badge experiment and by price guidance.

The Figma exports in `docs/screens/` still show two `EXTERNAL` cards on the
feed; ignore them.

**The one honest caveat** (v2.0 spec §1): the site launches empty. Recruit
roughly twenty real listings by hand before opening sign-ups.

## 2026-09-02 · Four sign-in domains

`columbia.edu`, `gsb.columbia.edu`, `cumc.columbia.edu`, `tc.columbia.edu` —
agreed by the team and first recorded on `feat/lionslist-skeleton`. Held in
`ALLOWED_EMAIL_DOMAINS` (backend `.env`), mirrored in `frontend/lib/domains.ts`
for instant feedback while typing. The match is exact on the domain:
`law.columbia.edu` and `columbia.edu.evil.com` are refused.

`gsb.columbia.edu` prefills Business (CBS) and `tc.columbia.edu` prefills
Teachers College in the school picker. `columbia.edu` and `cumc.columbia.edu`
prefill nothing — every school issues the former; the latter covers VP&S,
Mailman, Nursing and Dental alike.

Supersedes the `@columbia.edu`-only regex in `UX_SPEC.md` §4.1 and the copy in
§6.1 and §6.2.

## 2026-09-02 · Self-hosted magic links for the local MVP

Login tokens and sessions live in our own tables (`login_tokens`, `sessions`),
exactly as `UX_SPEC.md` §6.2 describes. Supabase Auth from the v2.0 spec is
deferred until hosting is decided; nothing in the flow depends on it. The
mailer is pluggable (`EMAIL_BACKEND=console|resend|smtp`), so a real inbox is
an environment change.

## 2026-09-02 · No browsing without an account

`GET /listings`, `GET /listings/facets` and `GET /listings/{id}` require a
session (`UX_SPEC.md` §6.2: "there is no browsing without an account in the
pilot"). The reference endpoints (`/zips`, `/reference/*`, `/auth/email-check`)
stay open because sign-up needs them.

## 2026-09-02 · `delisted` status added

Sellers need a way to take a listing down. `delisted` hides it from everyone
but the owner; the row stays because the event tables reference it. Sellers
change status through `PATCH /listings/{id}` (`active`, `reserved`, `sold`,
`delisted`). `draft` exists in the enum but nothing creates one yet, so the
"Save draft" button was removed from the posting form.

## 2026-09-02 · Photos are required and processed server-side

At least one photo to publish (`UX_SPEC.md` §6.5 marks photos required; the
v2.0 spec says the same). Uploads go through `POST /photos`: JPG, PNG or WebP
up to 10 MB, re-oriented, resized to 1600 px on the long side, re-encoded as
WebP, **all metadata stripped** (phone photos carry GPS). Each upload is
recorded against the member who sent it, and `POST /listings` refuses any URL
that is not that member's own upload. Files live on local disk under
`backend/media/` in the pilot; object storage is a deploy-time change.

## 2026-09-02 · Badge experiment instrumented, off by default

`listing_views.badges_shown` is recorded on every feed impression from day
one, because instrumentation cannot be retrofitted. With
`BADGE_EXPERIMENT_ENABLED=false` (the default) badges are always shown and the
flag is always true. Flip it on and half of feed requests hide badges; the
analysis in `app/analytics/questions.py` (Q1) compares contact rates between
the two arms.

## 2026-09-03 · Merged with main (PRs #5, #6, #7)

Three teammate PRs landed while the backend branch was open. What was kept
from each, and what was reconciled:

- **Jae's four-domain allowlist (#6)** — same decision, same env variable.
  His `app/emails.py` and the backend's `services/domains.py` implemented the
  same rule; only the latter survives, with his declaration-ordered message
  ("Columbia Market is open to @columbia.edu, @gsb.columbia.edu, … addresses.")
  and his `frontend/lib/domains.ts` as the frontend mirror. The backend module
  also does the school prefill for `GET /auth/email-check`.
- **Kobe's seed corpus (#5) and photos (#7)** — `seed/` and `data/` are the
  only generator now; the backend's own generator is gone and
  `scripts/seed.py` is a loader. The corpus still carries the external tier
  (150 rows); the loader skips them and every event that references them.
  **Open for Kobe:** make `--external 0` the generator default so the corpus
  matches the schema. Seeded photos are served by Next from
  `frontend/public/photos`; uploads through the app are served by the API from
  `/media`. Two more ZIPs (11354 Flushing, 11375 Forest Hills) joined the geo
  table because the corpus uses them.
- **Kobe's collections (#7)** — `/my-listings`, `/saved`, `/inbox` pages, the
  avatar menu, append-on-scroll paging and the status pill on cards are kept.
  The endpoints are `GET /me/listings`, `GET /me/saves`, `GET /me/enquiries`
  (his names, paginated). The profile page links to them instead of listing
  inline. His `same_zip` fix — compare the seller's ZIP, which is what the
  badge uses — is applied in `services/feed.py` for both the filter and the
  facet count.

---

## Still open

- **Product name.** The UI and API say "Columbia Market"; the repo, the v2.0
  spec and the course say "LionsList". Brian's call, since it changes the
  Figma lock-up.
- **Terms and research-consent checkbox at sign-up** needs a terms page.
- **`/search` and `/inbox`** on the mobile tab bar link to routes that do not
  exist yet.
- **Alembic** before the schema stabilises; **Postgres and object storage**
  before deployment.
- **Rate limiting** beyond the resend lock and the hourly enquiry cap.
