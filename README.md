# LionsList

A used-goods marketplace for verified Columbia students only. You sign in with
your Columbia address, you see what other students are selling, and you filter
the feed by what you have in common with them — same college, same country,
same neighborhood, same year.

**Team:** Brian (Dongwoo), Jaewon (Jae), Vinayak, Kobe

## Who can sign in

Four domains, agreed by the team:

| Domain | Prefills the college dropdown |
|---|---|
| `columbia.edu` | no — every school issues these |
| `gsb.columbia.edu` | Columbia Business School |
| `cumc.columbia.edu` | no — covers VP&S, Mailman, Nursing and Dental alike |
| `tc.columbia.edu` | Teachers College |

The list lives in `ALLOWED_EMAIL_DOMAINS`, not in code, so a fifth school is an
environment change and a redeploy.

> **Note:** `docs/UX_SPEC.md` §6.1 still specifies a regex admitting
> `@columbia.edu` alone. That document predates this decision and needs the
> same edit.

## Which spec governs

**Unresolved.** Two build specs sit on `main` and they disagree on most of the
data model — external tier, badge experiment, and nearly every enum:

- `LionsListBuildSpec.pdf` (v2.0) — what the code in `api/` currently follows
- `docs/UX_SPEC.md` — newer, merged via PR, and what the root README on `main`
  points at

The team needs to pick one. Until then, treat `api/app/enums.py` as provisional.

[PROPOSAL.md](PROPOSAL.md) is the original course proposal. Both specs have
moved past it; where any of them disagree, the proposal loses.

## Layout

```
web/        Next.js 15 + TypeScript + Tailwind  →  Vercel
api/        FastAPI — every product rule lives here  →  Render
analytics/  Jupyter notebooks, read-only DB role, run on a laptop
```

The browser never talks to Postgres directly.

## Where the build is

| Spec step | | Status |
|---|---|---|
| 01 | Accounts and repo skeleton | folders yes, accounts **not created** |
| 02 | Schema and migrations | **done** — four tables, seven enums |
| 03 | Magic-link sign-in | domain gate done, Supabase call **not wired** |
| 04 | Onboarding and profile | not started |
| 05 | Feed endpoint | not started |
| 06 | Posting, photos, contact | not started |
| 07 | The five screens | not started — **needs Node installed** |
| 08 | Wiring | not started |
| 09 | Events and the notebook | table exists, emission not started |
| 10 | Harden, seed, open | not started |

## Running the API

```bash
cd api
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows;  source .venv/bin/activate elsewhere
pip install -r requirements.txt
cp .env.example .env              # fill in once the Supabase project exists
pytest                            # 21 tests, no database needed
uvicorn app.main:app --reload     # http://127.0.0.1:8000/docs
```

`/health` and the domain gate work with no configuration. Anything that needs
Supabase answers `501` until the project exists.

### Migrations

```bash
alembic upgrade head --sql        # print the SQL, no connection needed
alembic upgrade head              # apply, needs DATABASE_URL
```

`DATABASE_URL` always comes from the environment, never from `alembic.ini`, so
nobody points a migration at the wrong project by editing a file they forgot to
un-edit.

## Accounts still to create

Nobody can do step 03 onward until these exist. All are free at our size except
the domain.

- **Supabase** — two projects, dev and prod
- **Vercel** — for `web/`
- **Render** — for `api/`
- **Resend** — sends the sign-in link
- **A domain**, with SPF and DKIM records set

The spec is blunt about the last one: if you skip SPF and DKIM, the sign-in
emails land in spam and nothing else you build matters.

## Conventions

- Fixed vocabularies live in `api/app/enums.py` and are mirrored by Postgres
  enums. Change one, change both — `api/tests/test_enums_match_migration.py`
  fails if they drift.
- Seller attributes are never copied onto a listing; they are joined at query
  time so a profile edit corrects every badge at once.
- Deleting is a status change, never a row deletion. The `events` table still
  references the row.
- Emit events from the start. Retrofitting instrumentation means throwing away
  the first weeks of data.
