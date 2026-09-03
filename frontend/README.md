# Frontend — Columbia Market

Next.js (App Router) + TypeScript + Tailwind v4. The design lives in
[`../docs/UX_SPEC.md`](../docs/UX_SPEC.md) and `../docs/screens/`; decisions
that changed it are in [`../docs/DECISIONS.md`](../docs/DECISIONS.md).

## Run it

```bash
cd frontend
npm install
npm run dev            # http://localhost:3000
```

The backend must be running on `http://localhost:8000` (see
`../backend/README.md`), seeded, or the feed will be empty. `../dev.sh` starts
both.

```bash
NEXT_PUBLIC_API_BASE=http://localhost:8000   # override if it runs elsewhere
```

## Layout

```
app/
  page.tsx                    feed / search        (UX_SPEC §6.3)
  listings/[id]/page.tsx      item detail          (§6.4) — gallery, save, contact, owner actions
  sell/page.tsx               post a listing       (§6.5) — photo uploader, live preview
  signup/page.tsx             sign up              (§6.1) — country and school pickers
  signin/page.tsx             request a link       (§6.2)
  signin/verify/page.tsx      what the link does   (states B8–B10)
  settings/profile/page.tsx   profile & account    (§6.6) — my listings, saved, sign out
  globals.css                 the design tokens
components/
  ui.tsx                      Button, Input, Select, Field, Chip, Toggle, Checkbox,
                              Segmented, MatchBadge, icons
  ItemCard.tsx                feed card (desktop) and row (mobile)
  TopNav.tsx                  desktop nav + mobile tab bar
  DistanceSlider.tsx          the radius filter
  Logo.tsx                    crown mark + wordmark
lib/
  types.ts                    mirrors backend/app/schemas.py
  api.ts                      the only place that talks to the API
  domains.ts                  the four sign-in domains (mirrors ALLOWED_EMAIL_DOMAINS)
  format.ts                   price, distance, relative time, placeholders
```

## Conventions

- **No raw hex.** Colours are tokens in `globals.css`; use `bg-deep`, `text-ink2`
  and so on. The token names map one-for-one onto the Figma variables.
- **Never derive a badge on the client.** Render `listing.badges` as given. The
  client is deliberately not sent the seller's attributes to compare
  (UX_SPEC §5.3) — if you find yourself needing them, the bug is in the API.
- **Never compute distance on the client** either. `distance_mi` arrives already
  measured from the viewer's ZIP.
- **No browsing without an account.** Every page that shows listings calls
  `api.me()` first and sends a signed-out visitor to `/signin`.
- **Fixed pickers for the matching attributes.** Nationality and school come
  from `/reference/countries` and `/reference/enums`, never a text box.
- **Log filter interactions.** `api.logFilter(...)` on every toggle and slider
  release. One of the research questions is answered entirely from that table
  and it cannot be reconstructed after the fact.
- **Phone is optional.** Anywhere you render contact actions, handle
  `seller.can_receive_sms === false` as a full-width Email button — not a
  disabled Text button. See `ContactBlock` in `app/listings/[id]/page.tsx`.
- **Photos go through the API.** `api.uploadPhoto(file)` returns the URL to put
  in `photo_urls`; the browser never writes to storage.

## Not built yet

- `/search` and `/inbox` (the mobile tab bar links to them), the mobile filter
  sheet (C10), the lightbox (D2), the price histogram (C8), drafts.
- The remaining interaction states in UX_SPEC §7 — those are the acceptance
  criteria for finishing each screen.
