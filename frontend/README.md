# Frontend — Columbia Market

Next.js (App Router) + TypeScript + Tailwind v4. The design lives in
[`../docs/UX_SPEC.md`](../docs/UX_SPEC.md) and `../docs/screens/`.

## Run it

```bash
cd frontend
npm install
npm run dev            # http://localhost:3000
```

The backend must be running on `http://localhost:8000` (see `../backend/README.md`),
seeded, or the feed will be empty.

```bash
NEXT_PUBLIC_API_BASE=http://localhost:8000   # override if it runs elsewhere
```

## Layout

```
app/
  page.tsx                    feed / search        (UX_SPEC §6.3)
  listings/[id]/page.tsx      item detail          (§6.4)
  sell/page.tsx               post a listing       (§6.5)
  signup/page.tsx             sign up              (§6.1)
  signin/page.tsx             request a link       (§6.2)
  signin/verify/page.tsx      what the link does   (states B8–B10)
  settings/profile/page.tsx   profile & account    (§6.6)
  globals.css                 the design tokens
components/
  ui.tsx                      Button, Input, Field, Chip, Toggle, Checkbox,
                              Segmented, MatchBadge, icons
  ItemCard.tsx                feed card (desktop) and row (mobile)
  TopNav.tsx                  desktop nav + mobile tab bar
  DistanceSlider.tsx          the radius filter
  Logo.tsx                    crown mark + wordmark
lib/
  types.ts                    mirrors backend/app/schemas.py
  api.ts                      the only place that talks to the API
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
- **Log filter interactions.** `api.logFilter(...)` on every toggle and slider
  release. One of the research questions is answered entirely from that table
  and it cannot be reconstructed after the fact.
- **Phone is optional.** Anywhere you render contact actions, handle
  `seller.can_receive_sms === false` as a full-width Email button — not a
  disabled Text button. See `ContactBlock` in `app/listings/[id]/page.tsx`.

## Not built yet

- Photo upload (needs the storage decision and the Figma asset export)
- `/search`, `/inbox`, the mobile filter sheet, the lightbox
- The interaction states in UX_SPEC §7 beyond the ones the pages already show —
  those are the acceptance criteria for finishing each screen.
