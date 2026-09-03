# Columbia Market

A secondhand marketplace for verified Columbia members. Karrot (당근마켓)'s
proximity feed, but the trust signal is ZIP-code distance plus three affiliation
attributes instead of GPS — and every listing comes from a verified student.

ENGI 4503 · Analytics in Python — Brian (Dongwoo), Jaewon (Jae), Vinayak, Kobe

## Where to start

| Document | Read it for |
|---|---|
| **[docs/UX_SPEC.md](docs/UX_SPEC.md)** | **The build spec.** Data model, enums, derived logic, all six screens, every interaction state. |
| **[docs/DECISIONS.md](docs/DECISIONS.md)** | **What changed after the spec was written** — the external tier is gone, four sign-in domains, and more. Where the two disagree, this wins. |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | How the pieces fit: request flow, the disclosure rule, the feed and its live counts, auth, photos, data model. |
| [docs/API.md](docs/API.md) | Every endpoint with its shape. |
| [PROPOSAL.md](PROPOSAL.md) | The research proposal — the problem, the questions the data should answer. Both specs have moved past it. |
| [docs/screens/](docs/screens/) | 19 exported PNGs — six screens × desktop/mobile, the user-flow map, the design foundations, and the interaction states. |
| [backend/README.md](backend/README.md) | Running the API and the analysis, and the four things that are easy to break. |
| [frontend/README.md](frontend/README.md) | Running the app and the conventions the components follow. |

The Figma file is the visual source of truth, but only one team member has the
connection, so the exports and the spec are written to stand on their own.

## Run it

One command, from the repo root:

```bash
./dev.sh                                   # API on :8000, app on :3000, seeds on first run
DEMO_EMAIL=you@columbia.edu ./dev.sh --reseed
```

Then open http://localhost:3000/signin, enter the demo address, and click the
sign-in link that appears on screen (development mode shows the link instead of
emailing it). Or run the halves by hand:

```bash
# API — http://localhost:8000/docs
cd backend
uv venv --python 3.12 .venv && source .venv/bin/activate      # Python 3.12 or 3.13
uv pip install -r requirements.txt && cp .env.example .env
python -m scripts.seed --reset --demo-email you@columbia.edu   # loads Kobe's corpus from data/
uvicorn app.main:app --reload

# Listing photos — run once, from the repo root. They are not committed (200MB,
# reproducible), so without this every seeded card shows a gradient placeholder.
cd .. && python3 scripts/fetch_photos.py      # real photos from Openverse, ~2 min, no key
#          python3 scripts/make_photos.py     # or offline gradients, seconds

# App — http://localhost:3000
cd frontend && npm install && npm run dev
```

There is no password anywhere. To receive the link in a real Columbia inbox, set
`EMAIL_BACKEND=resend` (with `RESEND_API_KEY`) or `EMAIL_BACKEND=smtp` in
`backend/.env`.

```bash
cd backend && pytest -q                            # 59 tests
cd backend && python -m app.analytics.questions    # the research questions
```

## Stack

- **Backend** — FastAPI + SQLAlchemy 2, SQLite locally (a `DATABASE_URL` change
  away from Postgres). Self-hosted magic links, no passwords. Photos are
  resized, re-encoded and stripped of metadata by Pillow. The analysis layer is
  **pandas**: every research question is a function in
  `backend/app/analytics/questions.py`.
- **Seed data** — `seed/` is a deterministic generator (standard library only)
  and `data/` its committed output: 1,000 members, 1,350 internal listings, their
  photos and the four event tables. `backend/scripts/seed.py` loads it. See
  `docs/mock_data_spec.md`.
- **Frontend** — Next.js App Router + TypeScript + Tailwind v4. The design tokens
  in `app/globals.css` map one-for-one onto the Figma variables.

## Who does what

Brian is the only one with the Figma connection, so anything needing an asset
export or a design decision sits on the frontend side with him.

| | Owner | Scope |
|---|---|---|
| **Frontend** | Brian (lead) | Screens, components, design tokens, asset export from Figma. The states in UX_SPEC §7 are the acceptance criteria — a screen is done when its states render. |
| **Backend** | Jae, Vinayak | Schema and enums, the ZIP/distance service, `GET /listings` with live facet counts, auth, photos. `services/badges.py` is small and load-bearing; read it first. |
| **Data & analysis** | Kobe | The `seed/` generator and `data/` corpus, the photo scripts, the `listing_views`, `filter_events` and `enquiries` pipelines, and the questions in `app/analytics/`. |

## Status

Design complete for all six screens. Backend and frontend run end to end
against seeded data: sign-up with country and school pickers, magic-link
sign-in gated to four Columbia domains, the feed with live facet counts, item
detail with the gallery and the two contact shapes, photo upload, posting, owner
actions (sold / reserved / relist / take down), saves, the three collections
behind the avatar menu (my listings, saved items, inbox) with append-on-scroll
paging, profile, sign-out and deactivation. 59 backend tests, including the
disclosure test.

Not built yet: `/search`, `/inbox`, the mobile filter sheet, the lightbox, the
price histogram, drafts, and the remaining interaction states in UX_SPEC §7.
