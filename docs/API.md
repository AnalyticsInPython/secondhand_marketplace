# API

Base URL `http://localhost:8000`. Interactive docs at `/docs`. Auth is an
HttpOnly session cookie (`cm_session`); send `credentials: "include"`. Errors
are `{"detail": "..."}` (or Pydantic's list for validation failures).

## Auth

| Method | Path | Auth | Does |
|---|---|---|---|
| GET | `/auth/email-check?email=` | — | `{allowed, reason, suggested_school}` for live validation. Says nothing about whether an account exists. |
| GET | `/auth/username-available?username=` | — | `{available, suggestions[]}` |
| POST | `/auth/signup` | — | `{email, username, phone?, nationality, school, grade, zip_code}` → 201, sends the link. 409 on a taken email or username, 422 outside the domain allowlist or the NYC ZIP table. |
| POST | `/auth/request-link` | — | `{email}` → 202 `{sent, resend_available_in_seconds, dev_link?}`. Identical answer for unknown addresses. `sent:false` while the 60 s resend lock holds. |
| POST | `/auth/verify?token=` | — | Opens the link. Sets the cookie, returns the profile. 400 with `detail` = `expired` / `already_used` / `unknown`. |
| POST | `/auth/signout` | ● | Drops the session. |
| GET | `/auth/me` | ● | Own profile (alias of `GET /me`). |

## Profile

| Method | Path | Does |
|---|---|---|
| GET | `/me` | Own profile — the only payload that ever contains your email and phone. |
| PATCH | `/me` | Any of `username, display_name, phone, phone_contact_enabled, nationality, school, grade, zip_code, default_radius_mi, default_filter_same_*`. Blank phone clears it. |
| POST | `/me/deactivate` | Reversible by signing in again. |
| GET | `/me/listings?limit=&offset=` | Everything you posted, every status, newest first. A `ListingPage`. |
| GET | `/me/saves?limit=&offset=` | Listings you saved, newest save first. Sold and reserved stay. A `ListingPage`. |
| GET | `/me/enquiries` | The inbox: `[{id, channel, created_at, listing, seller_username}]`. A record of contacts made, not a thread list. |

## Listings

All of these require a session — there is no browsing without an account.

| Method | Path | Does |
|---|---|---|
| GET | `/listings` | The feed. Query: `q, category[], subcategory[], condition[], price_min_cents, price_max_cents, radius_mi, same_zip, same_nationality, same_school, sort, limit, offset`. Sort defaults to `newest`, or `closest` when `q` is present. Returns `{items[], total, next_cursor}`. |
| GET | `/listings/facets` | Same query string; returns every sidebar number: `{total, categories[], subcategories[], conditions[], same_zip, same_nationality, same_school, radius_steps[]}`. Each count is "if you applied this one filter, with everything else still on". |
| POST | `/listings` | `{title, description?, category, subcategory?, condition, price_cents, is_free, is_negotiable, zip_code, photo_urls[1..10]}` → 201 detail. Photos must be your own uploads. |
| GET | `/listings/{id}` | Detail. Logs a `detail` view unless you own it. 404 for delisted listings you do not own; sold pages stay reachable. |
| PATCH | `/listings/{id}` | Owner only. Any create field plus `status` ∈ `active, reserved, sold, delisted`. `sold` sets `sold_at`; `active` clears it. |
| POST | `/listings/{id}/sold` | Shorthand for `PATCH {status: "sold"}`. |
| POST / DELETE | `/listings/{id}/save` | Save / unsave. |
| POST | `/listings/{id}/enquiry` | `{channel: "email" \| "sms"}` → `{channel, address?, phone?}`. **The only place a contact detail appears.** 409 when sold, own listing, or no number on file; 429 past 30 an hour. |
| POST | `/listings/events/filter?filter_key=&result_count=&value=` | Log a toggle or slider release. Fire and forget. |

### A card

```json
{
  "id": "…", "title": "IKEA MALM desk 140×65, white",
  "price_cents": 6000, "is_free": false,
  "condition": "used_good", "category": "furniture", "subcategory": "desks",
  "zip_code": "10027", "neighbourhood": "Morningside Heights",
  "distance_mi": 0.0, "posted_at": "2026-09-02T21:14:00Z", "status": "active",
  "cover_photo_url": "http://localhost:8000/media/….webp", "photo_count": 3,
  "badges": ["SAME ZIP", "SAME COUNTRY"]
}
```

A detail adds `description, is_negotiable, photos[], photo_urls[], view_count,
save_count, enquiry_count, sold_at, seller, is_saved, is_owner`, where `seller`
is exactly `{username, display_name, is_verified, member_since, badges,
can_receive_sms}`.

## Photos

| Method | Path | Does |
|---|---|---|
| POST | `/photos` | multipart `file` (JPG/PNG/WebP ≤ 10 MB) → 201 `{url, width, height}`. Resized to 1600 px, WebP, metadata stripped. Put the `url` in `photo_urls`. |
| GET | `/media/{name}.webp` | The processed file. Seeded listings instead point at `/photos/<listing>/<n>.webp`, served by the Next.js app from `frontend/public/photos`. |

## Reference

| Method | Path | Does |
|---|---|---|
| GET | `/zips?q=` | ZIP autocomplete: prefix, neighbourhood or borough; ordered by distance from your ZIP (or campus). |
| GET | `/reference/enums` | Every picker: categories with subcategories, conditions, grades, schools (grouped), statuses, radius presets, photo limits, the allowed email domains. |
| GET | `/reference/countries` | ISO-3166 list, the four most common at Columbia pinned first. |
| GET | `/health` | `{status, version}` |
