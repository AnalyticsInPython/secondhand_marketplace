"""Aggregates for the dashboard — the analysis component, in Python.

Every figure the /insights page draws is computed here with pandas and handed to
the client as plain numbers. The frontend draws; it does not analyse. That split
is deliberate: the coursework asks for the data analysis to be Python, and it
also keeps one definition of "a sale" or "a session" rather than one per chart.

Aggregation is done with SQL `GROUP BY` feeding small DataFrames, not by loading
64,000 view rows into memory on every request. `app/analytics/frames.py` remains
the place for exploratory work in a notebook, where loading everything is the
point.

Read `docs/data_visualization_spec.md` §6 before presenting any of this: several
of the effects visible here were planted in the seed data and are listed there.
"""

from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session as DbSession

from ..db import engine, get_db
from ..models import User
from ..security import current_user
from ..services import geo

router = APIRouter(prefix="/insights", tags=["insights"])


def _frame(sql: str, params: dict | None = None) -> pd.DataFrame:
    return pd.read_sql(sql, engine, params=params or {})


# ---------------------------------------------------------------- top line

# How much history each granularity shows. A day view of two years is 730 points
# nobody can read; a month view of 90 days is three bars.
WINDOW = {"day": 90, "week": 52 * 7, "month": 24 * 31}
RULE = {"day": "D", "week": "W", "month": "MS"}


def _events_frame(sql: str, column: str) -> pd.DataFrame:
    df = _frame(sql)
    if df.empty:
        return pd.DataFrame(columns=[column]).set_index(pd.DatetimeIndex([], name="at"))
    df["at"] = pd.to_datetime(df["at"])
    return df.set_index("at")


def _topline(period: str) -> dict:
    """Listed, sold and the rest, bucketed by day, week or month.

    Each metric is counted at its own event time — a listing counts towards the
    bucket it was *posted* in, a sale towards the bucket it was *sold* in. They
    are deliberately not forced onto one timeline: an item listed in May and
    sold in June belongs to both, and pretending otherwise would understate one.
    """
    rule = RULE[period]

    listed = _events_frame(
        "select posted_at as at, seller_id, price_cents from listings", "seller_id")
    sold = _events_frame(
        "select sold_at as at, sold_price_cents, price_cents, buyer_id from listings "
        "where sold_at is not null", "sold_price_cents")
    joined = _events_frame("select created_at as at, id from users", "id")
    views = _events_frame("select viewed_at as at, viewer_id from listing_views", "viewer_id")
    saves = _events_frame("select created_at as at, id from saves", "id")
    contacts = _events_frame("select created_at as at, id from enquiries", "id")
    searches = _events_frame("select created_at as at, id from search_events", "id")

    frames = {}
    if not listed.empty:
        frames["listed"] = listed.resample(rule).size()
        frames["sellers"] = listed.resample(rule)["seller_id"].nunique()
    if not sold.empty:
        frames["sold"] = sold.resample(rule).size()
        # Gross merchandise value: what actually changed hands. Falls back to the
        # asking price where a sale predates sold_price_cents being recorded.
        gmv = sold["sold_price_cents"].fillna(sold["price_cents"])
        frames["gmv_cents"] = gmv.resample(rule).sum()
        frames["buyers"] = sold.resample(rule)["buyer_id"].nunique()
    if not joined.empty:
        frames["new_members"] = joined.resample(rule).size()
    if not views.empty:
        frames["views"] = views.resample(rule).size()
        frames["active_members"] = views.resample(rule)["viewer_id"].nunique()
    if not saves.empty:
        frames["saves"] = saves.resample(rule).size()
    if not contacts.empty:
        frames["contacts"] = contacts.resample(rule).size()
    if not searches.empty:
        frames["searches"] = searches.resample(rule).size()

    table = pd.DataFrame(frames).fillna(0)
    if table.empty:
        return {"period": period, "buckets": [], "current": {}, "previous": {}, "change": {}}

    cutoff = table.index.max() - pd.Timedelta(days=WINDOW[period])
    table = table[table.index >= cutoff]

    # Derived rates, computed on the bucket rather than averaged from averages.
    table["sell_through"] = (
        table.get("sold", 0) / table.get("listed", pd.Series(0, index=table.index)).replace(0, pd.NA)
    ).fillna(0) * 100
    table["contact_rate"] = (
        table.get("contacts", 0) / table.get("views", pd.Series(0, index=table.index)).replace(0, pd.NA)
    ).fillna(0) * 100

    buckets = []
    for index, row in table.iterrows():
        bucket = {"start": index.strftime("%Y-%m-%d")}
        for key in table.columns:
            value = row[key]
            bucket[key] = round(float(value), 2) if key in ("sell_through", "contact_rate") else int(value)
        buckets.append(bucket)

    # The last complete bucket against the one before it. The bucket in progress
    # is excluded from the comparison — half a week always looks like a collapse.
    complete = buckets[:-1] if len(buckets) > 1 else buckets
    current = complete[-1] if complete else {}
    previous = complete[-2] if len(complete) > 1 else {}
    change = {}
    for key, value in current.items():
        if key == "start" or key not in previous:
            continue
        before = previous[key]
        change[key] = None if not before else round(100.0 * (value - before) / before, 1)

    return {
        "period": period,
        "buckets": buckets,
        "current": current,
        "previous": previous,
        "change": change,
    }


# ---------------------------------------------------------------- sections


def _overview() -> dict:
    """The headline counts, one row."""
    df = _frame("""
        select
          (select count(*) from users)                                    as members,
          (select count(*) from listings)                                 as listings,
          (select count(*) from listings where status = 'sold')           as sold,
          (select count(*) from listings where status = 'active')         as active,
          (select count(*) from listing_views)                            as views,
          (select count(*) from saves)                                    as saves,
          (select count(*) from enquiries)                                as enquiries,
          (select count(distinct session_id) from listing_views
             where session_id is not null)                                as sessions,
          (select count(*) from search_events)                            as searches
    """)
    row = df.iloc[0]
    return {k: int(row[k]) for k in df.columns}


def _activity() -> list[dict]:
    """Listings posted and sold per week — the seasonality chart.

    Posts per *active seller* is the honest version: raw volume rises simply
    because the platform grew, so dividing by the number of people posting that
    week is what separates a real season from growth.
    """
    posted = _frame("""
        select date(posted_at) as day, count(*) as posted,
               count(distinct seller_id) as sellers
          from listings group by date(posted_at)
    """)
    sold = _frame("""
        select date(sold_at) as day, count(*) as sold
          from listings where sold_at is not null group by date(sold_at)
    """)
    if posted.empty:
        return []

    posted["day"] = pd.to_datetime(posted["day"])
    sold["day"] = pd.to_datetime(sold["day"]) if not sold.empty else pd.Series(dtype="datetime64[ns]")

    weekly = (
        posted.set_index("day")
        .resample("W")
        .agg(posted=("posted", "sum"), sellers=("sellers", "sum"))
    )
    if not sold.empty:
        weekly["sold"] = sold.set_index("day").resample("W")["sold"].sum()
    weekly["sold"] = weekly.get("sold", 0)
    weekly = weekly.fillna(0)
    weekly["per_seller"] = (
        weekly["posted"] / weekly["sellers"].replace(0, pd.NA)
    ).fillna(0).round(2)

    return [
        {
            "week": index.strftime("%Y-%m-%d"),
            "posted": int(row["posted"]),
            "sold": int(row["sold"]),
            "per_seller": float(row["per_seller"]),
        }
        for index, row in weekly.iterrows()
    ]


def _funnel() -> list[dict]:
    """Impression → save → enquiry → sale, as counts and as a rate."""
    counts = _overview()
    stages = [
        ("Views", counts["views"]),
        ("Saves", counts["saves"]),
        ("Enquiries", counts["enquiries"]),
        ("Sales", counts["sold"]),
    ]
    top = stages[0][1] or 1
    out = []
    previous = None
    for label, value in stages:
        out.append({
            "stage": label,
            "count": value,
            "share_of_views": round(100.0 * value / top, 2),
            # What fraction of the previous stage survives — where the leak is.
            "conversion": None if previous is None else round(100.0 * value / previous, 2)
            if previous else 0.0,
        })
        previous = value
    return out


def _sales_by_distance() -> list[dict]:
    """How far a sold item travelled, buyer ZIP to listing ZIP.

    Only possible since buyers were recorded. Sales with no identified buyer are
    reported separately rather than dropped — the unattributed share is itself a
    number worth seeing.
    """
    df = _frame("""
        select l.zip_code as listing_zip, u.zip_code as buyer_zip
          from listings l join users u on u.id = l.buyer_id
         where l.status = 'sold'
    """)
    unattributed = _frame("""
        select count(*) as n from listings
         where status = 'sold' and buyer_id is null
    """).iloc[0]["n"]

    bands = [(0.5, "Same ZIP (0–0.5 mi)"), (1.0, "0.5–1 mi"), (2.5, "1–2.5 mi"),
             (5.0, "2.5–5 mi"), (10.0, "5–10 mi"), (float("inf"), "Over 10 mi")]
    tally = {label: 0 for _, label in bands}

    for _, row in df.iterrows():
        miles = geo.distance_mi(row["buyer_zip"], row["listing_zip"])
        if miles is None:
            continue
        for limit, label in bands:
            if miles <= limit:
                tally[label] += 1
                break

    out = [{"band": label, "sales": tally[label]} for _, label in bands]
    out.append({"band": "Buyer not identified", "sales": int(unattributed)})
    return out


def _searches() -> dict:
    """What people typed, and what came back empty."""
    top = _frame("""
        select query, count(*) as searches,
               sum(case when result_count = 0 then 1 else 0 end) as empty,
               sum(case when clicked_listing_id is not null then 1 else 0 end) as clicks
          from search_events group by query order by searches desc limit 12
    """)
    totals = _frame("""
        select count(*) as total,
               sum(case when result_count = 0 then 1 else 0 end) as empty
          from search_events
    """).iloc[0]

    empty_top = _frame("""
        select query, count(*) as searches
          from search_events where result_count = 0
         group by query order by searches desc limit 8
    """)

    return {
        "empty_top": [
            {"query": r["query"], "searches": int(r["searches"])}
            for _, r in empty_top.iterrows()
        ],
        "total": int(totals["total"]),
        "empty": int(totals["empty"] or 0),
        "empty_share": round(100.0 * (totals["empty"] or 0) / (totals["total"] or 1), 1),
        "top": [
            {
                "query": r["query"],
                "searches": int(r["searches"]),
                "empty": int(r["empty"] or 0),
                "clicks": int(r["clicks"] or 0),
            }
            for _, r in top.iterrows()
        ],
    }


def _categories() -> list[dict]:
    """Listings, median price and sell-through by category."""
    df = _frame("""
        select category,
               count(*) as listings,
               sum(case when status = 'sold' then 1 else 0 end) as sold,
               avg(price_cents) as mean_cents
          from listings group by category order by listings desc
    """)
    prices = _frame("select category, price_cents from listings where price_cents > 0")
    medians = prices.groupby("category")["price_cents"].median().to_dict()

    return [
        {
            "category": r["category"],
            "listings": int(r["listings"]),
            "sold": int(r["sold"]),
            "sell_through": round(100.0 * r["sold"] / r["listings"], 1) if r["listings"] else 0.0,
            "median_price": round(float(medians.get(r["category"], 0)) / 100, 2),
        }
        for _, r in df.iterrows()
    ]


# How few results counts as a feed that has stopped being useful. UX_SPEC §7
# calls a first view with three results "how you lose a user permanently"; ten
# is a generous reading of the same idea.
USABLE_THRESHOLD = 10
TRUST_SAMPLE = 300


def _trust_curve() -> dict:
    """Every filter buys trust and costs inventory — this is that curve.

    For a sample of members, count how many live listings survive at each depth
    of trust filtering. Two readings come out of it:

    * the **median** member's feed size at each depth — what a typical person
      actually sees, which the mean would flatter because a few people in 10027
      see far more than everyone else;
    * the share of members whose feed drops below USABLE_THRESHOLD, which is the
      proposal's real question: not "does filtering cost inventory" (obviously)
      but "how tight can a circle get before it stops working".

    Computed vectorised over a small frame rather than by running the feed query
    per member per combination — 1,350 live listings against 300 members is a
    few hundred boolean operations, where the query version is 2,400 round trips.
    """
    listings = _frame("""
        select l.zip_code as listing_zip,
               u.zip_code as seller_zip,
               u.nationality as seller_nationality,
               u.school as seller_school
          from listings l join users u on u.id = l.seller_id
         where l.status in ('active', 'reserved')
    """)
    members = _frame("select zip_code, nationality, school from users")
    if listings.empty or members.empty:
        return {"steps": [], "sample": 0, "total": 0, "threshold": USABLE_THRESHOLD}

    sample = members.sample(min(TRUST_SAMPLE, len(members)), random_state=0)
    total = len(listings)

    combos = [
        ("Everything", ()),
        ("Same ZIP", ("zip",)),
        ("Same country", ("nat",)),
        ("Same school", ("school",)),
        ("ZIP + country", ("zip", "nat")),
        ("ZIP + school", ("zip", "school")),
        ("Country + school", ("nat", "school")),
        ("All three", ("zip", "nat", "school")),
    ]

    counts: dict[str, list[int]] = {label: [] for label, _ in combos}
    for member in sample.itertuples():
        masks = {
            "zip": listings["seller_zip"] == member.zip_code,
            "nat": listings["seller_nationality"] == member.nationality,
            "school": listings["seller_school"] == member.school,
        }
        for label, keys in combos:
            if not keys:
                counts[label].append(total)
                continue
            mask = masks[keys[0]]
            for key in keys[1:]:
                mask = mask & masks[key]
            counts[label].append(int(mask.sum()))

    steps = []
    for label, keys in combos:
        series = pd.Series(counts[label])
        steps.append({
            "label": label,
            "depth": len(keys),
            "median": int(series.median()),
            "p25": int(series.quantile(0.25)),
            "p75": int(series.quantile(0.75)),
            "share_of_all": round(100.0 * series.median() / total, 1) if total else 0.0,
            # The number that answers the question.
            "below_threshold": round(100.0 * (series < USABLE_THRESHOLD).mean(), 1),
        })

    return {
        "steps": steps,
        "sample": len(sample),
        "total": total,
        "threshold": USABLE_THRESHOLD,
    }


def _overlap_contact_rate() -> dict:
    """Contact rate by how much the viewer and the seller have in common.

    0 to 3 shared attributes, counted per impression. This is the thesis in one
    chart: if sharing a school or a country makes people readier to deal, the
    line goes up.
    """
    df = _frame("""
        select
          (case when vu.zip_code    = su.zip_code    then 1 else 0 end) +
          (case when vu.nationality = su.nationality then 1 else 0 end) +
          (case when vu.school      = su.school      then 1 else 0 end) as shared,
          count(*) as impressions,
          sum(case when e.id is not null then 1 else 0 end) as contacts
        from listing_views v
        join users vu on vu.id = v.viewer_id
        join listings l on l.id = v.listing_id
        join users su on su.id = l.seller_id
        left join enquiries e
          on e.listing_id = v.listing_id and e.buyer_id = v.viewer_id
       group by shared order by shared
    """)
    rows = []
    for _, r in df.iterrows():
        impressions = int(r["impressions"]) or 1
        rows.append({
            "shared": int(r["shared"]),
            "impressions": int(r["impressions"]),
            "contacts": int(r["contacts"] or 0),
            "rate": round(100.0 * (r["contacts"] or 0) / impressions, 3),
        })
    return {"levels": rows}


def _price_by_condition() -> list[dict]:
    """What things go for, by condition. The unused premium made visible."""
    df = _frame("""
        select condition, price_cents from listings
         where price_cents > 0
    """)
    if df.empty:
        return []
    order = ["new", "like_new", "used_good", "used_fair"]
    out = []
    for condition in order:
        prices = df[df["condition"] == condition]["price_cents"] / 100
        if prices.empty:
            continue
        out.append({
            "condition": condition,
            "listings": int(prices.count()),
            "p25": round(float(prices.quantile(0.25)), 2),
            "median": round(float(prices.median()), 2),
            "p75": round(float(prices.quantile(0.75)), 2),
        })
    return out


def _inventory_age() -> dict:
    """How old the live inventory is.

    A marketplace with a long tail of months-old listings looks fuller than it
    is: those items are being scrolled past, not considered.
    """
    df = _frame("""
        select posted_at from listings where status in ('active', 'reserved')
    """)
    if df.empty:
        return {"buckets": [], "total": 0, "stale_share": 0.0}

    age = (pd.Timestamp.utcnow().tz_localize(None) -
           pd.to_datetime(df["posted_at"]).dt.tz_localize(None)).dt.days
    bands = [(7, "Under a week"), (30, "1–4 weeks"), (90, "1–3 months"),
             (10**6, "Over 3 months")]
    buckets, seen = [], 0
    for limit, label in bands:
        count = int(((age <= limit) & (age > seen)).sum()) if seen else int((age <= limit).sum())
        seen = limit
        buckets.append({"band": label, "listings": count})
    stale = int((age > 90).sum())
    return {
        "buckets": buckets,
        "total": int(len(age)),
        "stale_share": round(100.0 * stale / len(age), 1),
    }


def _days_to_sell() -> list[dict]:
    """Median days from posting to sale, by category.

    Right-censored on purpose: items that have not sold are excluded, so this is
    "how long the ones that sold took", not "how long things take". The
    sell-through column alongside is what stops that being read the wrong way.
    """
    df = _frame("""
        select category, posted_at, sold_at,
               (case when status = 'sold' then 1 else 0 end) as sold
          from listings
    """)
    if df.empty:
        return []
    df["posted_at"] = pd.to_datetime(df["posted_at"])
    df["sold_at"] = pd.to_datetime(df["sold_at"])
    df["days"] = (df["sold_at"] - df["posted_at"]).dt.total_seconds() / 86400

    out = []
    for category, group in df.groupby("category"):
        sold = group[group["sold"] == 1]["days"].dropna()
        out.append({
            "category": category,
            "listings": int(len(group)),
            "sold": int(len(sold)),
            "sell_through": round(100.0 * len(sold) / len(group), 1) if len(group) else 0.0,
            "median_days": round(float(sold.median()), 1) if not sold.empty else None,
        })
    return sorted(out, key=lambda r: -r["listings"])


def _buyer_vs_viewer() -> dict:
    """Did the person who bought share more with the seller than the people who
    merely looked?

    This is the sharpest test of the product's thesis available in the data, and
    it is deliberately not "do buyers share a lot with sellers" — that number is
    inflated by proximity alone, because people near a seller see more of their
    listings in the first place.

    Instead it compares, *within the same listing*, the buyer against everyone
    else who viewed it. The choice set is held constant, so exposure cancels out
    and what remains is whether shared attributes predicted who actually went
    through with it.
    """
    df = _frame("""
        select l.id as listing_id,
               v.viewer_id,
               (case when v.viewer_id = l.buyer_id then 1 else 0 end) as is_buyer,
               (case when vu.zip_code    = su.zip_code    then 1 else 0 end) +
               (case when vu.nationality = su.nationality then 1 else 0 end) +
               (case when vu.school      = su.school      then 1 else 0 end) as shared
          from listings l
          join listing_views v on v.listing_id = l.id
          join users vu on vu.id = v.viewer_id
          join users su on su.id = l.seller_id
         where l.status = 'sold' and l.buyer_id is not null
    """)
    if df.empty:
        return {"listings": 0, "buyer_mean": 0.0, "viewer_mean": 0.0, "lift": None, "by_attribute": []}

    # One row per (listing, viewer): a viewer who looked twice should not vote twice.
    df = df.groupby(["listing_id", "viewer_id"], as_index=False).max()

    buyers = df[df["is_buyer"] == 1]
    others = df[df["is_buyer"] == 0]
    if buyers.empty or others.empty:
        return {"listings": 0, "buyer_mean": 0.0, "viewer_mean": 0.0, "lift": None, "by_attribute": []}

    buyer_mean = float(buyers["shared"].mean())
    viewer_mean = float(others["shared"].mean())

    # And the same comparison one attribute at a time, so it is clear which of
    # the three is carrying the effect rather than reading one blended number.
    per_attribute = []
    for column, label in (("zip", "Same ZIP"), ("nat", "Same country"), ("school", "Same school")):
        col = _frame("""
            select (case when v.viewer_id = l.buyer_id then 1 else 0 end) as is_buyer,
                   (case when vu.%s = su.%s then 1 else 0 end) as match
              from listings l
              join listing_views v on v.listing_id = l.id
              join users vu on vu.id = v.viewer_id
              join users su on su.id = l.seller_id
             where l.status = 'sold' and l.buyer_id is not null
        """ % ({"zip": "zip_code", "nat": "nationality", "school": "school"}[column],
               {"zip": "zip_code", "nat": "nationality", "school": "school"}[column]))
        if col.empty:
            continue
        b = col[col["is_buyer"] == 1]["match"].mean()
        o = col[col["is_buyer"] == 0]["match"].mean()
        per_attribute.append({
            "attribute": label,
            "buyers": round(100.0 * float(b), 1),
            "viewers": round(100.0 * float(o), 1),
        })

    return {
        "listings": int(buyers["listing_id"].nunique()),
        "buyer_mean": round(buyer_mean, 3),
        "viewer_mean": round(viewer_mean, 3),
        "lift": round(100.0 * (buyer_mean / viewer_mean - 1), 1) if viewer_mean else None,
        "by_attribute": per_attribute,
    }


def _badges() -> dict:
    """The experiment: contact rate with badges shown against hidden.

    NOTE: the lift in the seeded corpus is planted — see
    docs/data_visualization_spec.md §6. The chart demonstrates the measurement,
    it does not evidence a real effect.
    """
    df = _frame("""
        select v.badges_shown as shown,
               count(*) as impressions,
               sum(case when e.id is not null then 1 else 0 end) as contacts
          from listing_views v
          left join enquiries e
            on e.listing_id = v.listing_id and e.buyer_id = v.viewer_id
         group by v.badges_shown
    """)
    out = []
    for _, r in df.iterrows():
        impressions = int(r["impressions"]) or 1
        out.append({
            "arm": "Badges shown" if r["shown"] else "Badges hidden",
            "impressions": int(r["impressions"]),
            "contacts": int(r["contacts"] or 0),
            "rate": round(100.0 * (r["contacts"] or 0) / impressions, 3),
        })
    return {"arms": out, "planted": True}


# ---------------------------------------------------------------- route


@router.get("/topline")
def topline(
    period: str = Query(default="week", pattern="^(day|week|month)$"),
    user: User = Depends(current_user),
):
    """Headline counts bucketed by day, week or month.

    Separate from /insights because it is the one section that changes with a
    control, and re-fetching six other panels to redraw one chart is waste.
    """
    return _topline(period)


@router.get("")
def insights(user: User = Depends(current_user), db: DbSession = Depends(get_db)):
    """Everything the dashboard draws, in one response.

    One call rather than six: the payload is a few kilobytes and a single
    round-trip keeps the page from flashing in six places as it loads.
    """
    return {
        "overview": _overview(),
        "activity": _activity(),
        "funnel": _funnel(),
        "sales_by_distance": _sales_by_distance(),
        "searches": _searches(),
        "categories": _categories(),
        "price_by_condition": _price_by_condition(),
        "inventory_age": _inventory_age(),
        "days_to_sell": _days_to_sell(),
        "trust_curve": _trust_curve(),
        "overlap": _overlap_contact_rate(),
        "buyer_vs_viewer": _buyer_vs_viewer(),
        "badges": _badges(),
    }
