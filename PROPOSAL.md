# Marketplace

A marketplace where you choose who you trade with — filtered by the things you
already have in common.

## The Problem

Columbia students buy and sell constantly: furniture at move-out, appliances,
textbooks, winter coats. Today that happens in group chats, where a listing
scrolls away within an hour and can never be searched, or on Facebook
Marketplace, where you are meeting a stranger with no accountability and
haggling in norms you may not share. Neither gives you a way to find the people
you would actually be comfortable trading with.

## Who It's For

Columbia students, verified by a `@columbia.edu` email address. Nobody without
one can sign in during the pilot. Our sharpest use case is MBA students, who
arrive and leave on a fixed two-year cycle, furnish an apartment from scratch,
and liquidate it on the way out.

**The demand is already proven.** The Korean Columbia Association group chat has
roughly 1,000 members, and the overwhelming majority of its traffic is people
buying and selling from each other — a marketplace that exists today with no
infrastructure, running entirely on messages that scroll away within the hour.

That community is not our market. It is our proof that the need is real, and our
route to a populated launch. We plan to recruit KCA members as our first sellers
and have them post the items they are already trying to sell in the chat, so the
platform opens with genuine listings from verified Columbia students instead of
an empty page. Once that flywheel is turning, the same mechanism extends to every
other circle a Columbia student belongs to.

## How We Solve It

A marketplace where every user declares four attributes — **location,
nationality, school, industry** — and every listing carries the same four from
its seller. Buyers turn those attributes on as filters, so the same pool of
listings becomes a different marketplace depending on who you are and what you
care about.

The bet: trust in a used-goods trade comes from accountability, not from star
ratings. When a seller shares your school and your country, a bad transaction
has social consequences and you both already know how the exchange is supposed
to go. Karrot (당근마켓) built Korea's largest marketplace on GPS-verified
neighborhoods; we are testing whether affiliation does the same job in the US.

## Key Features

1. **Affiliation profile** — four attributes set once at signup. School is
   verified by email domain; the rest are self-declared.
2. **Filtered browse** — toggle any of the four filters on or off. The listing
   count updates live, so the trade-off between trust and selection is never
   hidden.
3. **Match badges** — every internal listing shows what you have in common with
   the seller (`SAME AREA · SAME COUNTRY · SAME SCHOOL`).
4. **Two-tier feed** — internal listings from verified Columbia users sit
   alongside external listings aggregated from other marketplaces. External
   items are clearly labeled and link out to their source.
5. **Audience selection on posting** — the seller chooses which circle sees a
   listing, with the reach count shown for each option. Offer it to your closest
   community first; widen it if nobody bites.
6. **Overlap-only disclosure** — you reveal an attribute to another user only
   where you already share it. Someone with nothing in common sees nothing
   about you.

## What Data It Could Use

### External — scraped listings (aggregated tier)

So the platform is populated from day one rather than launching empty, we will
collect roughly 50 listings each from three existing marketplaces:

- **Facebook Marketplace** — local NYC listings, the closest comparison to what
  we are building.
- **Karrot (당근마켓 US)** — the model we are adapting; useful for category
  structure and pricing norms.
- **eBay** — collected through the official eBay Browse API, which returns
  structured listing and completed-sale data directly.

From each listing we take title, category, asking price, condition, location,
source, and source URL. These appear in the feed marked as external, carry no
affiliation badges, and **redirect to the original marketplace when clicked** —
we aggregate and point, we do not host the transaction.

### Internal — user-generated (the real product)

- **Listings** — title, category, asking price, condition, photos, pickup
  location, posted date, sold date.
- **User profiles** — location, nationality, school, industry.
- **Interaction events** — listing views, filter toggles, click-throughs,
  messages started, items marked sold.

To seed the internal tier we start where the trade already happens: the Korean
Columbia Association community, whose group chat gives us real listings, real
prices and real categories on day one. From there the same mechanism extends to
any circle a Columbia student belongs to.

## What Questions It Would Answer

**Does shared affiliation actually change behavior?**

Our two-tier feed gives us a clean natural experiment. Internal listings carry
affiliation badges; external ones do not. Same feed, same categories, same price
ranges. Comparing engagement and click-through between the two directly tests
whether "sense of belonging" is a real transaction driver or just a nice story —
and it is the single most important thing we could learn.

**How tight can a trust circle be before it stops working?**

Every filter a user adds buys trust and costs inventory. We can measure exactly
where that curve breaks: how many listings the median member sees at each filter
depth, and the minimum community size for a circle to stay useful. If a circle
of 1,000 produces enough inventory, the model works at surprisingly small scale —
and that finding generalizes to every other affiliation group, on this campus
and beyond it.

**Which of the four filters is doing the work?**

Which filters do users keep on, and which do they drop first when their feed runs
thin? We expect location and nationality to dominate and industry to go nearly
unused — but if school turns out to be the binding one, that changes which
communities we would launch next.

**Is there an in-group discount?**

How do asking prices inside a community compare to external listings for the
same category and condition? We expect in-community prices to run lower, because
people discount for their own. Quantifying that gap, and finding which categories
show it most, would be a genuinely novel result.

**How big is the moving-season effect?**

Listing volume should spike as one cohort liquidates in May and the next arrives
in August. Measuring the size and shape of that mismatch tells us whether the
academic calendar is a real liquidity engine or just an intuition.

## Scope for This Week

In scope: profiles, filtered browse, the two-tier feed, listing detail, posting
with audience selection, the scraped seed catalog, and the analysis above.

Out of scope: payments, shipping, in-app messaging beyond a contact button,
real identity verification, ratings, and a mobile app.

Also excluded on purpose: **housing and sublets.** Filtering rental listings by
nationality raises US fair-housing issues that filtering goods does not.
