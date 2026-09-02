# analytics

One notebook, a read-only database role, pandas for shaping and statsmodels for
the confidence intervals. Everything comes from the `events` table plus
`listings` and `users` — no third-party analytics vendor.

Not started. Blocked on the Supabase project, since it needs a read-only role
and a `DATABASE_URL` to point at.

## The eight questions (spec section 4)

1. **Do match badges change behavior?** Badges shown on a random half of feed
   impressions; two-proportion test on contact rate. The one genuinely causal
   result — same items, same prices, only the badge differs.
2. **How tight can a circle get before it stops working?** Median result count
   per filter combination against the chance of a contact within 7 days.
3. **Which filter do people actually use?** Toggle frequency and retention per
   filter, divided by the inventory each yields.
4. **Where do people give up?** Median `result_count` at the moment a filter is
   switched back off — the empty-feed threshold.
5. **What does a used dorm couch cost?** Price distributions by category and
   condition, and the used/unused premium.
6. **How fast does anything sell?** Days between `created_at` and `sold_at`.
7. **Is there a moving season?** Weekly posts and sales per *active seller*, so
   platform growth does not fake a spike.
8. **Where does the funnel leak?** Impressions → detail views → contacts.

## Before the first real user signs in

Write down what counts as a "successful contact" and what circle depth means.
Choosing those after seeing the numbers is the fastest way to turn a real
finding into an unpublishable one.

The badge coin-flip is assigned server-side per impression in `GET /v1/feed`
and recorded in the `feed_view` event, so question 1 has data from day one.
