# Columbia Market

A secondhand marketplace for verified Columbia members — `columbia.edu`,
`gsb.columbia.edu`, `cumc.columbia.edu` and `tc.columbia.edu`. Karrot (당근마켓)'s
proximity feed, but the trust signal is ZIP-code distance plus three affiliation
attributes instead of GPS.

ENGI 4503 · Analytics in Python — Brian (Dongwoo), Jaewon (Jae), Vinayak, Kobe

## Where to start

| Document | Read it for |
|---|---|
| **[docs/UX_SPEC.md](docs/UX_SPEC.md)** | **The build spec.** Data model, enums, derived logic, all six screens, every interaction state, an API sketch, and fake-data guidance. Read this before writing code. |
| [PROPOSAL.md](PROPOSAL.md) | The research proposal — the problem, the questions the data should answer. The design has moved past it in three places; §2 of the UX spec lists them. |
| [docs/screens/](docs/screens/) | 19 exported PNGs — six screens × desktop/mobile, the user-flow map, the design foundations, and the interaction states. |
| **[docs/mock_data_spec.md](docs/mock_data_spec.md)** | **The seed data.** Column-by-column reference, how to load it, the constraints your schema should enforce, and the logic the API must compute rather than read. Read this before writing the backend. |
| [data/](data/) | The generated corpus — 1,000 members, 1,500 listings, photos and the four event tables. Regenerate with `python3 -m seed.generate`. |
| [backend/README.md](backend/README.md) | Running the API, the analysis, and the three things that are easy to break. |
| [frontend/README.md](frontend/README.md) | Running the app and the conventions the components follow. |

The Figma file is the visual source of truth, but only one team member has the
connection, so the exports and the spec are written to stand on their own.

## Run it

```bash
# API — http://localhost:8000
cd backend
python3 -m venv .venv && source .venv/bin/activate    # Python 3.12 or 3.13
pip install -r requirements.txt && cp .env.example .env
python -m scripts.seed --users 1000 --listings 1500 --reset
uvicorn app.main:app --reload

# App — http://localhost:3000
cd frontend && npm install && npm run dev
```

There is no password anywhere. In dev the sign-in link is returned in the API
response and printed to the console rather than emailed.

```bash
cd backend && python -m app.analytics.questions   # the five research questions
```

## Stack

- **Backend** — FastAPI + SQLAlchemy, SQLite locally (a `DATABASE_URL` change away
  from Postgres/Neon). The analysis layer is **pandas**: every research question
  in `PROPOSAL.md` is a function in `app/analytics/questions.py`.
- **Frontend** — Next.js App Router + TypeScript + Tailwind v4. The design tokens
  in `app/globals.css` map one-for-one onto the Figma variables.

## Who does what

Brian is the only one with the Figma connection, so anything needing an asset
export or a design decision sits on the frontend side with him.

| | Owner | Scope |
|---|---|---|
| **Frontend** | Brian (lead) | Screens, components, design tokens, asset export from Figma, the photo uploader. The states in UX_SPEC §7 are the acceptance criteria — a screen is done when its states render. |
| **Backend** | Jae, Vinayak | Schema and enums, the ZIP/distance service, `GET /listings` with live facet counts, auth. `services/badges.py` is small and load-bearing; read it first. |
| **Data & analysis** | Kobe | The seed generator, the `filter_events` and `enquiries` pipelines, and the five questions in `app/analytics/`. |

Suggested build order for the frontend: sign in → feed → detail → sign up →
sell → profile. The feed is where most of the product's ideas live, so getting
its filters and live counts right unblocks everything else.

## Status

Design complete for all six screens. Backend and frontend skeletons run
end to end against seeded data: feed, filters with live counts, listing detail
with the two contact shapes, sign-up, magic-link sign-in, posting, and profile.

Not built yet: photo upload, `/search`, `/inbox`, the mobile filter sheet, and
most of the interaction states catalogued in UX_SPEC §7.
