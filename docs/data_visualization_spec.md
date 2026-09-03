# Data & visualisation spec

**Owner:** Kobe · **Scope:** the behavioural ("user action") data and what can be
built on it · **Companion to:** [`mock_data_spec.md`](mock_data_spec.md), which
covers users, listings and photos.

> **If you are about to plot something from this data, read §6 first.** Several of
> the effects the charts will show were put there deliberately. Which ones, and
> how large, is written down — but a chart made without knowing that is a chart
> that claims more than it can.

---

## 1. What this covers

`mock_data_spec.md` describes the *content* of the marketplace — who the members
are and what they listed. This document describes what those members **did**:
every impression, save, contact, filter toggle, search and completed sale, and
how each was generated.

The syllabus asks for a data-analysis component involving Python. This is the
data that component runs on.

### Current volume

| Table | Rows | One row is |
|---|---:|---|
| `listing_views` | 64,020 | one listing shown to one person |
| `saves` | 6,105 | tapping the heart |
| `enquiries` | 1,079 | revealing a seller's contact details |
| `filter_events` | 3,129 | one filter toggle or slider release |
| `search_events` | 2,774 | one typed query |
| `listings` (sold) | 454 | a completed sale, 324 with an identified buyer |
| — sessions | 17,141 | one browsing visit, mean 3.7 events |

Roughly 77,000 behavioural rows over a two-year window (Aug 2024 → Sep 2026).

---

## 2. The event model

Five streams, each answering something the others cannot.

### `listing_views` — impressions

`id`, `listing_id`, `viewer_id`, `surface`, `badges_shown`, `viewed_at`, `session_id`

The top of every funnel. `surface` distinguishes feed / search / detail, so
browsing and searching can be compared. `badges_shown` carries the experiment's
coin flip — see §5.

Views cluster early in a listing's life (a square-law bias towards the first
days), scale with age, photo count and price, and are **blind to whether the
listing is any good** — there is no quality score putting a thumb on the scale.

### `saves` — private interest

`id`, `listing_id`, `user_id`, `created_at`, `session_id`

Drawn from a view that happened, at ~8% — never sampled independently, so every
save has a real impression behind it. Unique on `(user, listing)`.

### `enquiries` — the contact reveal

`id`, `listing_id`, `buyer_id`, `channel`, `created_at`, `session_id`

The strongest intent signal short of a sale, and the moment the seller's address
or number is released (UX_SPEC §5.1). `channel` is `sms` **only** where the
seller supplied a phone and left texting on — otherwise `email`, which is always
available.

### `filter_events` — structured narrowing

`id`, `user_id`, `filter_key`, `value`, `result_count`, `created_at`, `session_id`

Every toggle and slider release, each carrying **the count the feed actually
returned at that moment**. That number is not invented: the generator runs a
local reimplementation of the §5.4 feed query (`seed/feed.py`) against the corpus
*as it stood at that timestamp*. It is what makes "where do people give up"
answerable.

### `search_events` — free text

`id`, `user_id`, `session_id`, `query`, `result_count`, `clicked_listing_id`, `created_at`

Added 2026-09-03. `filter_events` covers structured filters; a typed query is a
different act. `result_count` is a real substring match against live listing
titles, so **907 of 2,774 searches (33%) return nothing** — the empty-result rate
is a genuine measurement of catalogue coverage, not a parameter.

---

## 3. Sessions

Every event carries a nullable `session_id`.

**Definition:** one person's events, split wherever they go quiet for **30
minutes**. That is the same rule Google Analytics uses.

Two things worth knowing about how they were produced:

1. **Sessions are derived, not generated.** Events are created independently —
   a view is drawn from its listing's own lifetime — and grouped afterwards.
   That mirrors how a real pipeline derives sessions from a raw log.

2. **Events are first clustered into visits.** Generated independently, a
   person's activity scatters across two years and every session ends up with
   one event in it, which is useless for funnel work. So each member gets a set
   of visit timestamps — derived from *how much they actually did*, targeting
   ~7 events per visit — and each event snaps to the nearest visit that is
   **legal for that event**. A view cannot move outside the window in which its
   listing was on the feed. Where no visit fits, the event keeps its own time
   and becomes a session of one, which is a real pattern too.

   Timestamps move by hours, never across a season or a day-of-week boundary, so
   seasonality and time-to-sale are unaffected.

Realised shape: **17,141 sessions**, mean 3.7 events, median 2, p90 11, max 54.
About 56% contain more than one event.

---

## 4. Sales, buyers and prices

The largest gap this work closed. Before it, a completed sale had only a date —
so *"how many items sold within 2.5 miles"* had no second endpoint and could not
be asked.

Two nullable columns on `listings`:

| Column | Meaning |
|---|---|
| `buyer_id` | who bought it, `NULL` if they never enquired through the app |
| `sold_price_cents` | what it actually went for |

**`sold_price_cents` exists because `price_cents` is overwritten when a seller
edits a listing.** Without it, the asking price at the moment of sale is lost and
the in-group discount question quietly breaks.

**`NULL` is data, not absence.** Plenty of real sales go to a friend or happen
off-platform. *What share of sales are attributable to an in-app enquiry* is
itself a chart worth making — currently **324 of 454, or 71%**.

### The rule: a purchase implies contact

A buyer is drawn from the people who enquired **before** the sale. That is what
makes enquiry-to-purchase conversion a measurement rather than a coincidence.

Where a listing sold but nobody had enquired, the enquiry is **added** rather
than the sale left unattributed — buying without ever contacting the seller is
not a path this product has. Enquiries rose from 824 to 1,079 as a result, and
that is the reason.

### In the product, not just the seed

The seed data would be worthless if real usage could not produce the same rows.
So the mark-sold flow now captures it:

- `GET /listings/{id}/enquirers` — who has contacted the seller. **Owner only.**
  No new disclosure: the seller already received these enquiries.
- `POST /listings/{id}/sold` takes an optional `{buyer_id, sold_price_cents}`.
  The body and every field in it are optional, so the original no-body call
  behaves exactly as before.
- The API **refuses a buyer who never enquired**, and refuses self-purchase.
- The UI adds one step to the existing owner controls: *"Who bought it?"* — the
  enquirers listed as buttons, plus **"Sold to someone else"**, which records
  the sale with a `NULL` buyer.

---

## 5. The badge experiment

`listing_views.badges_shown` is a per-impression coin flip at **50/50**. Before
2026-09-03 the loader hardcoded it to `True`, so the corpus had one arm and the
only causal question in the proposal had nothing to measure.

Realised, and recovered by the existing notebook:

```
badges hidden   28,760 impressions   637 contacts   2.21%
badges shown    28,804 impressions   777 contacts   2.70%
lift p-value: 0.0002
```

**That lift is planted.** See below.

---

## 6. Planted effects — read this before plotting

The analysis runs on data that was generated, so **any effect it "finds" is one
that was put there**. Every planted parameter lives in one block at the top of
`seed/events.py` and is reproduced here.

The rule used to decide what belongs on this list: *would a reader mistake the
chart for evidence about the real world?* If yes, it must be declared.

| Effect | Parameter | Value | Why it exists |
|---|---|---|---|
| Badge lift | `BADGE_LIFT` | ×1.35 on enquiry rate when badges shown | The two-proportion test needs something to recover |
| Overlap engagement | `OVERLAP_ENGAGEMENT_LIFT` | ×1.18 per shared attribute, compounding | The product's actual thesis, independent of badge display |
| Distance decay | `DISTANCE_DECAY_MILES` | 3.5 mi, exponential | People look at things near them |
| In-group discount | `IN_GROUP_DISCOUNT` | −4% of sale price per shared attribute | "People discount for their own" |
| Buyer attribution | `BUYER_FROM_ENQUIRY_RATE` | 72% of sales get an identified buyer | The rest are friends and off-platform sales |
| Seasonality | `MONTH_MULTIPLIER` | ×3 at May and August over the trough | Move-out and arrival, from UX_SPEC §9 |
| Funnel ratio | save 8%, enquiry 1% of views | 100 : 8 : 1 | UX_SPEC §9 |

### What is *not* planted

- **Search result counts** — real substring matches against live titles. The 33%
  empty-search rate is measured, not set.
- **`filter_events.result_count`** — the actual feed query, evaluated as of that
  timestamp.
- **Time to sale** — emerges from a per-listing draw and is honestly
  right-censored: a listing posted yesterday is almost never already sold.
- **Session shape** — a consequence of the clustering rule, not a target.

### How to write about it

Any chart of the badge lift or the in-group discount is **a test that the
pipeline works**, not a finding about Columbia students. State it that way. The
figures that *are* meaningful are the structural ones — inventory at each filter
depth, the empty-search rate, funnel drop-off between stages — because those come
from the corpus and the query, not from a coefficient.

---

## 7. What can be visualised

Grouped by the axis each one turns on. Everything here is computable from the
tables above today.

### Time
- Listings posted per week, with the May and August spikes
- Posts per *active seller* per week — normalises out platform growth, which is
  what makes the seasonality claim honest
- Sales per week; median days-to-sale by category and price band
- Activity by hour of day and day of week, from session start times

### Geography
- Sale distance: buyer ZIP → listing ZIP, now that buyers exist
- Share of sales inside 0.5 / 1 / 2.5 / 5 / 10 miles — **your original question**
- Listings and members per ZIP; a Manhattan-and-around map if you want one
- Distance decay: view probability against distance

### The funnel
- Impressions → detail views → saves → enquiries → sales, per session
- Drop-off between each pair, split by category, price band and distance
- Search vs browse: does arriving via search convert better?

### Trust and overlap
- Contact rate by number of shared attributes (0–3)
- Badge experiment: treated vs control, with a confidence interval
- Inventory at each filter depth — the trust/selection trade-off curve
- Which filter is dropped first when the feed runs thin (`result_count` at the
  moment a filter is switched off)

### Catalogue and price
- Price distribution by category and condition; the unused premium
- Asking price vs `sold_price_cents`
- In-group vs out-group sale prices
- Free items: how many, how fast they go

### Search
- Top queries; the 33% that return nothing — the clearest "what should we stock"
  signal in the dataset
- Click-through rate by result count

---

## 8. Regenerating

```bash
python3 -m seed.generate                    # writes data/*.csv, validates
cd backend && .venv/bin/python -m scripts.seed --reset
```

Deterministic under `--seed`. The generator refuses to export if any of its
**19 invariant groups** fail; four of them cover this document's tables:

- **17** — a buyer only on a sold listing, never the seller, always someone who
  enquired first, sale price never negative
- **18** — every event that has a user has a session, and no session spans two
  users (which would silently break every funnel join)
- **19** — search result counts non-negative, clicked listings resolve, and no
  click recorded on a search that returned nothing

---

## 9. Known gaps

Honest list of what still cannot be asked.

1. **No unsave events.** `saves` is current-state, so save-then-unsave churn is
   invisible. Would need a small events table.
2. **No status history.** A listing goes active → reserved → sold but only the
   end state and `sold_at` survive, so time-in-reserved and relist rates are out
   of reach.
3. **No price-change history**, so *"did dropping the price cause the sale"*
   cannot be answered — `sold_price_cents` captures the end, not the path.
4. **No feed position on impressions.** Click-through by rank is not available.
5. **Sessions are derived, not observed.** The 30-minute rule is a convention;
   real sessions would come from the app itself.
6. **The corpus is generated.** Every caveat in §6 applies to every chart.
