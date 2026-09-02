# Columbia Market

A secondhand marketplace for verified `@columbia.edu` members. Karrot (당근마켓)'s
proximity feed, but the trust signal is ZIP-code distance plus three affiliation
attributes instead of GPS.

ENGI 4503 · Analytics in Python — Brian (Dongwoo), Jaewon (Jae), Vinayak, Kobe

## Where to start

| Document | Read it for |
|---|---|
| **[docs/UX_SPEC.md](docs/UX_SPEC.md)** | **The build spec.** Data model, enums, derived logic, all six screens, every interaction state, an API sketch, and fake-data guidance. Read this before writing code. |
| [PROPOSAL.md](PROPOSAL.md) | The research proposal — the problem, the questions the data should answer. Note that the design has moved past it in three places; §2 of the UX spec lists them. |
| [docs/screens/](docs/screens/) | 19 exported PNGs — six screens × desktop/mobile, the user-flow map, the design foundations, and the interaction states. |

The Figma file is the visual source of truth but only one team member has the
connection, so the exports and the spec are written to stand on their own.

## Status

Design complete for Sign Up, Sign In, Feed/Search, Item Detail, Upload Item and
Profile & Account. No application code yet.
