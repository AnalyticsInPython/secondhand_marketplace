# Mock data — implementation spec

**Owner:** Kobe · **Branch:** `feat/seed-data` · **Generator:** `seed/` · **Output:** `data/`

**Source of truth:** [`docs/UX_SPEC.md`](UX_SPEC.md). Every column, enum value and
distribution below is traceable to a section of it, and every section reference in
this document is a real one you can go and check. Where UX_SPEC is silent I have
made a choice and said so; where UX_SPEC and the Figma disagree, UX_SPEC wins.

> **If you are building the backend, read §5, §6 and §7.** §5 is the column-by-column
> reference. §6 is the logic that is deliberately *not* in the data and which the API
> has to compute. §7 is the list of constraints your DDL should enforce — the
> generator already guarantees all of them, so any violation you see later came from
> application code, not from the seed.

---

## 1. What this is

A deterministic generator that produces a full working corpus for Columbia Market:
1,000 members, 1,500 listings, their photos, and the four event tables from
UX_SPEC §4.4. It exists so the feed, the item page and the analysis notebook all
have something real to run against before a single member signs up.

It is not a fixture file. It is a program with the spec's distributions written
into it, so the corpus can be regenerated at any size, and so every number in it
can be traced to a rule rather than to a typo.

**Scope decision:** the four event tables are included. UX_SPEC §10 puts the §9
generator *and* the `filter_events` / `enquiries` pipelines on data/analysis, and
`listings.view_count` and friends are summaries of those tables — generating the
counters without the events would guarantee they disagree with whatever anyone
produced later.

---

## 2. Running it

```bash
python3 -m seed.generate                            # §9 defaults, writes data/
python3 -m seed.generate --users 5000 --listings 8000
python3 -m seed.generate --seed 42 --out /tmp/out
python3 -m seed.generate --no-export                # report + validate only
```

No third-party dependencies. Standard library only, Python 3.9+. A full run takes
about a second.

| Flag | Default | Notes |
|---|---|---|
| `--seed` | `20260902` | Same seed + same counts ⇒ byte-identical files |
| `--users` | `1000` | UX_SPEC §9 |
| `--listings` | `1500` | Total, internal + external |
| `--external` | `150` | How many of `--listings` come from the aggregated tier (§9) |
| `--now` | `2026-09-02T18:00:00` | Treated as the present. Fixed so "3 hours ago" does not drift between runs |
| `--out` | `data` | |
| `--no-export` | off | Generate and validate without writing |

**Determinism is verified, not assumed** — two consecutive runs produce identical
MD5s for every CSV. If you change a generator parameter the whole stream shifts,
which is expected; pin `--seed` and the counts when you need stability.

Each module also runs standalone for inspection:

```bash
python3 -m seed.vocabularies   # every enum + the CREATE TYPE statements
python3 -m seed.zips           # the ZIP table, and the §4.6 audit in §11 below
python3 -m seed.names          # nationality weights and name systems
python3 -m seed.catalog        # sample titles, prices and descriptions
```

### Photos

The ~5,800 placeholder images are **not committed** — they carry no information
and would dominate the repo. Rebuild them from the CSV:

```bash
pip install Pillow                  # optional; without it you get SVGs
python3 scripts/make_photos.py --out web/public/photos
```

Each image is a soft gradient in an `01 · Foundations` tint, keyed off a hash of
the listing id, so a listing's gallery is a coherent set and the same listing
always gets the same colour. `listing_photos.url` is `photos/<listing_id>/<position>.webp`.

---

## 3. What is in `data/`

| File | Rows | Size | Table |
|---|---:|---:|---|
| `users.csv` | 1,000 | 201 KB | `users` (§4.1) |
| `listings.csv` | 1,500 | 589 KB | `listings` (§4.2) |
| `listing_photos.csv` | 5,849 | 880 KB | `listing_photos` (§4.3) |
| `listing_views.csv` | 72,602 | 10.2 MB | `listing_views` (§4.4) |
| `saves.csv` | 6,370 | 859 KB | `saves` (§4.4) |
| `enquiries.csv` | 742 | 104 KB | `enquiries` (§4.4) |
| `filter_events.csv` | 3,197 | 378 KB | `filter_events` (§4.4) |
| `zip_reference.csv` | 47 | 2.5 KB | `zip_reference` (§4.6) |
| `seed.sql` | — | 14.9 MB | All of the above as `INSERT`s |

Total ≈ 26 MB. `listing_views.csv` and `seed.sql` are the bulk of it. If that
becomes awkward in git, the cheapest fix is to drop `seed.sql` and load from the
CSVs — it is a convenience, not a second source of truth.

**Formats**, chosen once so the loader never has to guess:

- timestamps: ISO-8601 with a `+00:00` offset (columns are `timestamptz`)
- booleans: `true` / `false`
- NULL: the empty field
- header row uses the exact column names from UX_SPEC §4

---

## 4. Loading it

### Postgres, from CSV (recommended)

```sql
\copy zip_reference   from 'data/zip_reference.csv'   with (format csv, header, null '');
\copy users           from 'data/users.csv'           with (format csv, header, null '');
\copy listings        from 'data/listings.csv'        with (format csv, header, null '');
\copy listing_photos  from 'data/listing_photos.csv'  with (format csv, header, null '');
\copy listing_views   from 'data/listing_views.csv'   with (format csv, header, null '');
\copy saves           from 'data/saves.csv'           with (format csv, header, null '');
\copy enquiries       from 'data/enquiries.csv'       with (format csv, header, null '');
\copy filter_events   from 'data/filter_events.csv'   with (format csv, header, null '');
```

Load in that order — the foreign keys require it.

### Postgres, from SQL

```bash
psql "$DATABASE_URL" -f data/seed.sql
```

`seed.sql` creates the **enum types** and the **`zip_reference` table**, then
inserts everything inside one transaction. It deliberately does **not** contain
DDL for `users`, `listings`, `listing_photos` or the event tables — that is your
schema and your migrations, and having two definitions of it is how they drift.
Run your migrations first, then this.

### pandas

```python
import pandas as pd
users = pd.read_csv("data/users.csv", parse_dates=["created_at", "updated_at"])
listings = pd.read_csv("data/listings.csv", parse_dates=["posted_at", "sold_at"])
```

---

## 5. Column reference

Types are what I would put in the DDL. "Generated by" is how the value is
produced, which matters when you are deciding whether a field is worth trusting.

### 5.1 `users` — 1,000 rows (UX_SPEC §4.1)

| Column | Type | Null | Generated by |
|---|---|---|---|
| `id` | `uuid` PK | no | Seeded UUIDv4 |
| `email` | `text` UNIQUE | no | `{initials}{4 digits}@columbia.edu`, matching §4.1's regex. Initials come from the **legal name**, not the handle — the design's own example pairs `dl3729@columbia.edu` with `@brian_dw`, so they are independent by construction |
| `username` | `text` UNIQUE | no | Derived from the name, `[a-zA-Z0-9._]{3,20}`. Deliberately mixed shapes: `wei_zh`, `grace.miller`, `j.kim42`. One row sits at exactly 20 chars |
| `display_name` | `text` | **yes** | 45% populated. §6.3 says the username is "the only name buyers see", so most people leave it blank. Names are drawn from a pool **keyed to nationality** |
| `phone` | `text` | **yes** | 30% NULL per §9. E.164, NYC area codes, always inside the reserved fictional `555-01xx` block |
| `phone_contact_enabled` | `bool` | no | Default `true`; ~15% of members *with* a number turn it off. §4.1 says it is "meaningless when phone IS NULL", so it stays `true` on phoneless rows — **do not read it alone**, see §6.3 |
| `nationality` | `char(2)` | no | ISO-3166 alpha-2. 40 countries |
| `school` | `enum school` | no | 14 values from §4.5, CBS and SEAS over-weighted per §9 |
| `grade` | `enum grade` | no | Drawn **before** school, then school chosen among those that admit it. See §6.5 |
| `zip_code` | `char(5)` | no | Weighted per §9; every value resolves in `zip_reference` |
| `default_radius_mi` | `numeric(3,1)` | no | 2.5 for 78%, otherwise another slider preset |
| `default_filter_same_zip` | `bool` | no | §4.1 default is `false`; ~10% have flipped it |
| `default_filter_same_nationality` | `bool` | no | ~14% on |
| `default_filter_same_school` | `bool` | no | ~9% on |
| `is_verified` | `bool` | no | 95% true. The rest signed up and never opened the link |
| `status` | `enum user_status` | no | `active` / `deactivated`, ~3% deactivated |
| `created_at` | `timestamptz` | no | Clustered on August and January intakes, later intakes larger |
| `updated_at` | `timestamptz` | no | ≥ `created_at`, ≤ now |

### 5.2 `listings` — 1,500 rows (UX_SPEC §4.2)

| Column | Type | Null | Generated by |
|---|---|---|---|
| `id` | `uuid` PK | no | Seeded UUIDv4 |
| `seller_id` | `uuid` FK → `users` | **yes** | NULL for every external row (§5.5). Internal sellers are Zipf-shaped, not uniform — see §6.6 |
| `source` | `enum source` | no | `internal` 90%, then `ebay` / `facebook` / `karrot` |
| `title` | `text` | no | Category-specific templates with brand/size/colour slots, ≤ 60 chars enforced at draw time |
| `description` | `text` | **yes** | 85% populated. Drawn **after** condition so a `new` item never mentions a scuff |
| `category` | `enum category` | no | §9 weights |
| `subcategory` | `text` | **yes** | Furniture only (§4.5 is single-level elsewhere). NULL for every other category |
| `condition` | `enum condition` | no | §9 skew, tilted per category — textbooks skew unused, furniture skews used |
| `price_cents` | `integer` | no | Log-uniform inside a per-*template* band, then a condition multiplier, then clamped to §9's category range, then rounded to $5/$10 |
| `is_free` | `bool` | no | Exactly equivalent to `price_cents = 0`, both ways |
| `is_negotiable` | `bool` | no | 40% of priced listings; never on a free one |
| `zip_code` | `char(5)` | no | **Locked equal to the seller's ZIP.** See §11 item 2 — this is a decision, not an accident |
| `status` | `enum listing_status` | no | Derived from elapsed time, not assigned. See §6.7 |
| `view_count` | `integer` | no | `COUNT(*)` over `listing_views`. Not drawn |
| `save_count` | `integer` | no | `COUNT(*)` over `saves` |
| `enquiry_count` | `integer` | no | `COUNT(*)` over `enquiries` |
| `external_url` | `text` | **yes** | Non-null iff `source != 'internal'`. Plausible per-source shapes; not live links |
| `posted_at` | `timestamptz` | no | Seasonality × growth; see §6.8 |
| `sold_at` | `timestamptz` | **yes** | Non-null iff `status = 'sold'` |

### 5.3 `listing_photos` — 5,849 rows (§4.3)

| Column | Type | Null | Generated by |
|---|---|---|---|
| `id` | `uuid` PK | no | |
| `listing_id` | `uuid` FK | no | ON DELETE CASCADE |
| `url` | `text` | no | `photos/<listing_id>/<position>.webp` |
| `position` | `smallint` | no | Contiguous from 0; `0` is the cover |
| `created_at` | `timestamptz` | no | Equals the listing's `posted_at` |

1–10 per listing, median 4, count correlated with price. Every listing has at
least one — §6.5 of UX_SPEC refuses to publish without.

### 5.4 The event tables (§4.4)

| Table | Rows | Columns |
|---|---:|---|
| `listing_views` | 72,602 | `id`, `listing_id`, `viewer_id`, `viewed_at`, `surface` ∈ `feed/search/detail` |
| `saves` | 6,370 | `id`, `listing_id`, `user_id`, `created_at` |
| `enquiries` | 742 | `id`, `listing_id`, `buyer_id`, `channel` ∈ `email/sms`, `created_at` |
| `filter_events` | 3,197 | `id`, `user_id`, `filter_key`, `value`, `result_count`, `created_at` |

Realised funnel **100 : 8.8 : 1**, against §9's 100 : 8 : 1.

Notes that matter to the API:

- `viewer_id` is populated on every row. §6.2 says there is no browsing without an
  account in the pilot, so an anonymous view should not occur. The column stays
  nullable because a deactivated account's event rows outlive its profile.
- A seller never generates a view of their own listing — that is the `D10` owner
  view, a different thing.
- `draft` listings have no events at all. They were never published.
- `channel = 'sms'` only ever appears where the seller has a phone **and**
  `phone_contact_enabled`. §5.1 makes email always available, so everything else
  is `email`.
- External listings collect views and saves but **never** enquiries — there is no
  seller to contact, the card links out instead (§5.5).
- `filter_events.result_count` is the count the feed query really returns for that
  user, with that filter state, **as the corpus stood at that timestamp**. It is
  not a random number. See §6.2.

### 5.5 `zip_reference` — 47 rows (§4.6)

`zip_code` PK, `neighbourhood`, `borough`, `lat`, `lon`, `miles_from_campus`.

Manhattan is covered densely, plus the Brooklyn, Queens and Bronx ZIPs a student
plausibly lives in. §4.6 asks for ~42; there are 47.

**`miles_from_campus` and inter-ZIP distance are different measurements.**
`miles_from_campus` is display copy for the sign-up autocomplete (§6.1). The
distance the feed filters on is computed between the *viewer's* and the
*listing's* centroids (§5.2) and is never read off this table.

---

## 6. Logic that is not in the data

These are computed at read time. The generator implements them in `seed/feed.py`
so it could produce honest `result_count` values — **that file is a reference
implementation, not the product**. Building the real one against it and comparing
is worthwhile; if `GET /filters/counts` and `seed.feed.Feed.facet_counts` disagree,
one of them is wrong.

### 6.1 Distance (§5.2)

```
distance_mi = round(haversine(centroid(viewer.zip_code),
                              centroid(listing.zip_code)), 1)
```

Same-ZIP is `0.0`. §5.2 says the UI renders that as "0.0–0.5 mi" and that it
"should not be special-cased", so the arithmetic stays literal and the
presentation is the frontend's problem. The radius filter is `distance_mi <= radius`.

### 6.2 Facet counts are conditional (§5.4)

> "every count shown next to a filter is the count *if you applied it*, evaluated
> against all other active filters"

So the number beside **Furniture** is *how many results you would have if you also
ticked Furniture*, given everything already on. It is **not** `SELECT category,
count(*) GROUP BY category`. Getting this wrong is easy and silently wrong —
the numbers look reasonable and are meaningless.

`seed/feed.py:Feed.facet_counts` does it the right way for `category`,
`condition`, `trust` and `radius`.

### 6.3 The contact block has two shapes (§5.1)

```python
can_text = seller.phone is not None and seller.phone_contact_enabled
```

`phone_contact_enabled` alone is **not** the condition — it is stored `true` on
members who never supplied a number, because §4.1 says it is meaningless there.
When `can_text` is false the design wants **one full-width Email button**, not a
disabled second button (state `D12`). ~30% of the seed exercises this.

### 6.4 Badges, and overlap-only disclosure (§5.3)

Computed per `(viewer, listing)` pair, never stored on the listing. An attribute
that does not match is **absent from the response** — not `false`, not `null`.
External listings have no seller and therefore always return `[]`.

No seller attribute is denormalised onto any listing row in this dataset, so
editing a member's profile correctly changes every badge on everything they have
posted, with no backfill.

### 6.5 Grade and school are not independent

There are no undergraduates at CBS. The generator draws grade first, then picks a
school from those that admit it — undergraduate only at `columbia_college`,
`seas_undergrad`, `general_studies`; graduate only at the other eleven;
`faculty_staff` legal anywhere. `seed.vocabularies.grades_for_school()` is the
rule, and it is why §4.5 lists SEAS twice.

This is not stated in UX_SPEC. If you enforce it, enforce it there too, or a
profile edit can create a combination the seed data does not contain.

### 6.6 Sellers are Zipf-shaped

39% of sellers have posted exactly one item and the top 5% hold 23% of the
inventory; the busiest single member has 31 listings. §6.4's "more from this seller" rail only means anything
because of this — with a uniform assignment it would be empty for nearly everyone.

### 6.7 Sold-ness is derived from time

Each internal listing gets a *will it ever sell* coin flip and a days-to-sale draw
(log-normal, median 6 days per §9). It becomes `sold` only if that date has already
passed. So recent listings are mostly still active for the same reason they are in
real life, and the days-to-sale distribution is **honestly right-censored** —
important, because "how fast does anything sell" is one of §4's research questions
and an uncensored dataset would answer it wrongly.

Realised: 32.1% of internal listings sold, median 5.5 days (§9 asks ~35% / ~6).

### 6.8 Seasonality is planted; everything else is not

§9 asks for a May and August spike "roughly 3× the trough", and that is deliberately
built in — see §9 below for what that means for the analysis.

---

## 7. Constraints your DDL should enforce

The generator guarantees all of these and `seed/validate.py` checks them on every
run. If you add them to the schema, the seed will load clean — and anything that
violates one later came from application code.

| # | Constraint | Where it comes from |
|---|---|---|
| 1 | `email` UNIQUE, matches `^[a-z0-9._%+-]+@columbia\.edu$` | §4.1 |
| 2 | `username` UNIQUE, matches `^[a-zA-Z0-9._]{3,20}$` | §4.1 |
| 3 | No phone outside the reserved `555-01xx` block | Ours — safety |
| 4 | `grade` legal for `school` | §6.5 above |
| 5 | `users.zip_code` and `listings.zip_code` FK → `zip_reference` | §4.6 |
| 6 | `subcategory` belongs to `category`; NULL for single-level categories | §4.2 |
| 7 | `length(title) <= 60`, `length(description) <= 1000` | §4.2 |
| 8 | `is_free = (price_cents = 0)`, and `price_cents >= 0` | §4.2 |
| 9 | `sold_at IS NOT NULL` iff `status = 'sold'`; `sold_at >= posted_at`; `sold_at <= now()` | §4.2 |
| 10 | `posted_at >= seller.created_at` | Ours — nobody posts before joining |
| 11 | `external_url IS NOT NULL` iff `source != 'internal'`; external rows have no `seller_id`, internal rows must have one | §5.5 |
| 12 | Every listing has ≥ 1 photo; `position` contiguous from 0; ≤ 10 photos | §4.3, §6.5 |
| 13 | `view_count` / `save_count` / `enquiry_count` equal their event-table counts; each ≤ `view_count` | §4.2 vs §4.4 |
| 14 | `saves` unique on `(user_id, listing_id)`; no event before its listing's `posted_at` or after now | §4.4 |
| 15 | No `sms` enquiry against a seller with no phone; no enquiry at all against an external listing | §5.1, §5.5 |
| 16 | Every enum value in vocabulary; `result_count >= 0`; all FKs resolve | §4.5 |

**One of these is weaker than it looks.** Constraint 13 does *not* say
`views >= saves >= enquiries` per row — saves and enquiries are independent draws
from views, so a listing with one enquiry and no saves is correct, not corrupt
(somebody emailed without saving). The 100 : 8 : 1 ordering is an aggregate
property and is checked as one.

---

## 8. Fixtures for building against

### The reference member

The Figma screens are drawn for one identity, so it exists in the data with fixed
attributes. Sign in as this user and the screens should look like the mockups.

```
username    brian_dw
email       dl3729@columbia.edu
display     Brian Lee
nationality KR        school  cbs        grade  graduate
zip_code    10027     phone   +16465550142   texting on
```

What they see: **1,036** visible listings overall, **791** within 2.5 miles, of
which **369** same-ZIP, **151** same-school, **89** same-nationality.

### §7 state coverage

Every state in UX_SPEC §7 that needs a row has one. The generator prints the
covering row's id on each run, so you can navigate straight to it:

| State | What it is |
|---|---|
| `D3` / `D4` / `D5` | on sale · reserved · sold |
| `D6` / `D7` / `D8` | full overlap · partial · none — against the reference member |
| `D10` | a listing the reference member owns (owner view) |
| `D11` | one live external listing per source: eBay, Facebook, Karrot |
| `D12` | both contact shapes — email-only, and email + text |
| `D1` | a listing with exactly one photo (no thumbnail strip) |
| `E4` | a listing with all 10 photos |
| `E6` | a free ($0) listing |
| `A5` | a taken username to collide against (`brian_dw`) |
| `C4` | a filter combination that genuinely returns zero, *searched for* rather than assumed — what is empty depends on corpus size |
| `C6` | non-zero counts at all five radius presets: 379 / 548 / 791 / 890 / 1033 |
| — | max-length title (60) and description (1000) |
| — | non-ASCII: a Korean display name, and the `×` in "140×65" |

---

## 9. Realised distributions vs UX_SPEC §9

| Quantity | §9 | Realised |
|---|---|---|
| graduate / undergraduate / faculty | 60 / 35 / 5 | 58.8 / 36.5 / 4.7 |
| nationality US / CN / KR / IN | 35 / 18 / 10 / 8 | 35.6 / 18.1 / 8.9 / 8.0 |
| ZIP 10027 / 10025 / 10031 | 40 / 15 / 10 | 42.9 / 14.1 / 9.1 |
| `phone` NULL | ~30% | 31.1% |
| furniture / textbooks / electronics / kitchen / clothing | 30 / 20 / 15 / 12 / 10 | 30.1 / 18.3 / 14.3 / 13.3 / 10.3 |
| condition `used_good` / `like_new` | 45 / 30 | 46.0 / 28.7 |
| free | ~8% | 6.7% |
| sold (internal) | ~35% | 32.1% |
| median days to sell | ~6 | 5.5 |
| funnel views : saves : enquiries | 100 : 8 : 1 | 100 : 8.8 : 1 |
| May / August spike | ~3× trough | 178 and 332 against a 32 trough |
| external listings | ~150 | 150 |

### What is planted and what is not

**Planted deliberately, because it is scenery:** the May/August seasonality, the
category and condition mixes, the price bands, the funnel ratio, the nationality
and ZIP distributions. All of it is §9's, and all of it is in this document.

**Not planted, deliberately:** any difference between the internal and external
tiers. §9 is explicit — "do not hard-code a difference; generate both tiers with
the same base rates and let the analysis find (or fail to find) the effect". The
view model in `seed/events.py` reads only listing age, photo count and price. It
never looks at `source`, and it never looks at whether a badge would be shown.

> **Therefore:** any effect the notebook reports on this data is a test of the
> pipeline, not a result. The badge/no-badge comparison in particular will find
> nothing, because there is nothing there to find. That is the correct outcome for
> generated data and should be stated that way in the write-up.

---

## 10. Generator layout

| File | What it holds |
|---|---|
| `seed/vocabularies.py` | Every enum from §4.5 transcribed verbatim, plus field limits and `postgres_enum_ddl()` |
| `seed/zips.py` | The 47-ZIP table, haversine, and the §4.6 audit |
| `seed/names.py` | Nationality weights and name pools keyed to them |
| `seed/catalog.py` | 49 item templates, price bands, description fragments |
| `seed/users.py` | §4.1 rows |
| `seed/listings.py` | §4.2 and §4.3 rows, seasonality, seller skew, status derivation |
| `seed/feed.py` | Reference implementation of §5.3–§5.5 (badges, filters, facet counts) |
| `seed/events.py` | The four §4.4 tables, and the counter backfill |
| `seed/edge_cases.py` | The §7 fixtures and the reference member |
| `seed/validate.py` | The 16 constraint groups in §7 above |
| `seed/export.py` | CSV and `seed.sql` writers |
| `seed/generate.py` | CLI, report, and the pipeline order |
| `scripts/make_photos.py` | Placeholder image regeneration |

Each vocabulary module self-checks at import — labels covering exactly their
values, `SCHOOL_GROUPS` partitioning `SCHOOLS`, no subcategory claimed by two
categories, no template escaping its category's price range. Those assertions
have already caught two real mistakes, so leave them in.

---

## 11. Known divergences and open questions

### 1. §4.6's stated distances do not all match the centroid arithmetic

`python3 -m seed.zips` prints this audit. Five of the eight agree within 0.3 mi;
three do not:

| ZIP | §4.6 says | Centroid haversine | Δ |
|---|---:|---:|---:|
| 10027 | 0.2 | 0.6 | +0.4 |
| 10026 | 1.3 | 0.6 | −0.7 |
| 11106 Astoria | 5.2 | 3.6 | −1.6 |

Astoria is the tell: it is 3.6 miles away in a straight line but across the East
River, so any actual journey is 5+. **The §4.6 figures look like travel distance;
§5.2 specifies great-circle.** I have kept §4.6's numbers verbatim as the sign-up
display value and compute the feed's distances from centroids, but these are two
different measures and the design should probably pick one.

*(This also resolves the thing I flagged before UX_SPEC existed: the Figma feed
shows ZIP 10024 at both 1.2 mi and 1.6 mi. §4.6 fixes it at 1.6, so the card
distances in the mockup are decorative.)*

### 2. Pickup ZIP is locked to the seller's ZIP

§5.2 measures distance from `listings.zip_code`; §5.3 computes the SAME ZIP badge
from `users.zip_code`. If those can differ, a listing can display a SAME ZIP badge
next to "3.2 mi", which reads as a bug to any user who sees it.

**Decision: they are equal in every generated row.** That makes the contradiction
unrepresentable. If the product genuinely wants people listing from an office or a
friend's place, say so and I will unlock it — but the badge rule should then be
restated in terms of one column or the other.

### 3. `free_stuff` category vs the `is_free` flag

Both exist. A free sofa qualifies for either. **Decision:** `free_stuff` is only
for items with no resale value (moving boxes, a pothos, a drying rack) and is
always free; a giveaway in any other category keeps its real category and carries
`is_free`. Otherwise the category counts stop meaning anything. 6.7% of listings
are free, split between the two.

### 4. "4 min average reply" has nothing behind it

The seller card in the design shows it. No table in §4 records a reply, and in-app
chat is out of scope, so it cannot be derived from anything we store. **It is not
in this dataset.** Either the card drops it, or `users` gets a denormalised column
that we all agree is decorative. I would drop it — a fabricated responsiveness
stat on a product whose whole thesis is trust is a bad thing to ship.

### 5. Do deactivated members' listings stay in the feed?

§4.1 has `status = deactivated` and says it is reversible, but nothing says whether
their listings remain visible, and the §5.4 query has no `users.status` clause.
~3% of members are deactivated and hold listings in every status, so whichever rule
you choose has data to test it. **The generator does not filter them** — decide and
implement it in the query.

### 6. UX_SPEC §11's own open questions

- **q2, a `SAME YEAR` badge for grade.** Assumed no. Grade is generated properly
  regardless, so adding it is free.
- **q3, `reserved` and the queue.** Assumed no queue table. `reserved` rows exist
  (4.2%) so state `D4` renders; if a `listing_queue` arrives it is a fifth table
  to seed.
- **q4, external dedupe.** Not modelled. No two external rows are deliberately the
  same item, so a dedupe key cannot be tested against this data yet.

---

## 12. What would make this better

Honest list, in the order I would do them:

1. **Real ZIP centroids** from the US Census ZCTA gazetteer, replacing my
   approximations (good to ~0.1 mi, which is the precision §5.2 rounds to, but
   they are still hand-entered).
2. **More catalogue depth.** 49 templates carry 1,500 listings comfortably; at
   8,000 the repetition starts to show.
3. **Sessions.** `filter_events` currently simulates short filtering runs but the
   schema has no session id, so a funnel analysis has to approximate one from
   `user_id` + time. If §4.4 gains a `session_id`, this gets much better.
4. **A profile notebook** rendering the distributions as charts rather than as the
   text report `seed.generate` prints.
