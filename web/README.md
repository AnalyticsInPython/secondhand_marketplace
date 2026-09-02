# web — Next.js 15

Not scaffolded yet: **Node is not installed on the build machine.** Install
Node 20+ from [nodejs.org](https://nodejs.org/), then from the repo root:

```bash
npx create-next-app@latest web --ts --tailwind --app --eslint
```

## The five screens (spec step 07)

That is the entire product.

| Screen | Contents |
|---|---|
| Sign in | One email field, one button, one "check your inbox" state |
| Onboarding | Seven fields, four of them dropdowns |
| Feed | Grid of item cards, four filter toggles, a live count, category chips |
| Item detail | Photos, price, condition, description, match badges, one Contact button |
| Post an item | Six fields plus a photo picker, with a preview |

## Rules that are easy to get wrong later

- Filter state goes in the URL (`?college=1&country=1&category=furniture`), so
  pages are shareable and the back button behaves.
- Server-render the feed from the API response.
- Every filter defaults to **off**, and a narrow filter is never remembered
  across sessions. A first view with three results is how you lose a user
  permanently.
- When a filter empties the feed, name the one whose removal brings back the
  most items.
- `/auth/callback` is a Next.js route, not an API endpoint: it trades the magic
  link code for a Supabase session in an httpOnly cookie.
- Attach the Supabase JWT as a Bearer header on every call to the API.
- Use `navigator.sendBeacon` for `POST /v1/events` so navigating away does not
  drop the event.
