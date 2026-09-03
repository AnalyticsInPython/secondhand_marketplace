"""The research questions, one function each.

    python -m app.analytics.questions

Each function takes the frames dict from `frames.load()` and returns a
DataFrame, so a notebook can plot the same object the CLI prints. Nothing here
writes to the database.

The questions follow the internal-only build spec (docs/DECISIONS.md): the
internal-versus-external comparison is gone, and the badge experiment — the one
genuinely causal result — takes its place as Q1.

A warning that matters more than the code: the seed generator produces every
listing and every viewer with the *same* base engagement rates on purpose (see
scripts/seed.py). So on seeded data these functions should find no effect. If
they do, the finding is in the generator, not in the world.
"""

from __future__ import annotations

import math

import pandas as pd

from .frames import load

EMPTY_NOTE = "no data yet"


def _two_proportion_p(x1: int, n1: int, x2: int, n2: int) -> float | None:
    """Two-sided z-test for equal proportions, normal approximation."""
    if n1 == 0 or n2 == 0:
        return None
    p1, p2, p = x1 / n1, x2 / n2, (x1 + x2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return None
    z = (p1 - p2) / se
    return math.erfc(abs(z) / math.sqrt(2))


# ---------------------------------------------------------------------------
# Q1. Do match badges change behaviour?
# ---------------------------------------------------------------------------


def badge_experiment(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Badges shown on a random half of feed impressions; compare contact rate.

    Same items, same prices — only the badge differs, which is what makes this
    causal. `listing_views.badges_shown` carries the treatment flag from day one;
    the coin flip itself is switched on with BADGE_EXPERIMENT_ENABLED.
    """
    views, enquiries = frames["views"], frames["enquiries"]
    impressions = views[views["surface"].isin(["feed", "search"]) & views["viewer_id"].notna()]
    if impressions.empty:
        return pd.DataFrame({"note": [EMPTY_NOTE]})

    contacts = enquiries.rename(columns={"buyer_id": "viewer_id"})[["listing_id", "viewer_id"]].drop_duplicates()
    imp = impressions[["listing_id", "viewer_id", "badges_shown"]].merge(
        contacts, on=["listing_id", "viewer_id"], how="left", indicator=True
    )
    imp["contacted"] = imp.pop("_merge").eq("both")

    out = imp.groupby("badges_shown").agg(impressions=("contacted", "size"), contacts=("contacted", "sum"))
    out["contact_rate"] = (out["contacts"] / out["impressions"]).round(4)
    out.index = out.index.map({True: "badges shown", False: "badges hidden"})

    if len(out) == 2:
        shown, hidden = out.loc["badges shown"], out.loc["badges hidden"]
        p = _two_proportion_p(int(shown["contacts"]), int(shown["impressions"]), int(hidden["contacts"]), int(hidden["impressions"]))
        out.attrs["p_value"] = p
    else:
        out.attrs["p_value"] = None  # the experiment has not been switched on
    return out


# ---------------------------------------------------------------------------
# Q2. How tight can a trust circle be before it stops working?
# ---------------------------------------------------------------------------


def inventory_by_filter_depth(frames: dict[str, pd.DataFrame], sample_users: int = 200) -> pd.DataFrame:
    """Every filter buys trust and costs inventory. This is that curve.

    For a sample of members, count how many active listings survive at each
    filter depth. The median row is the one to quote: it is what a typical
    member actually sees.
    """
    users, listings = frames["users"], frames["listings"]
    active = listings[listings["status"].isin(["active", "reserved"])]
    if users.empty or active.empty:
        return pd.DataFrame({"note": [EMPTY_NOTE]})
    sample = users.sample(min(sample_users, len(users)), random_state=0)

    rows = []
    for user in sample.itertuples():
        zip_ok = active["seller_zip"] == user.zip_code
        nat_ok = active["seller_nationality"] == user.nationality
        school_ok = active["seller_school"] == user.school
        rows.append(
            {
                "no_filters": len(active),
                "same_zip": int(zip_ok.sum()),
                "same_country": int(nat_ok.sum()),
                "same_school": int(school_ok.sum()),
                "zip_and_country": int((zip_ok & nat_ok).sum()),
                "all_three": int((zip_ok & nat_ok & school_ok).sum()),
            }
        )

    depth = pd.DataFrame(rows)
    return depth.describe().loc[["mean", "50%", "min", "max"]].round(1)


# ---------------------------------------------------------------------------
# Q3. Which of the filters is doing the work?
# ---------------------------------------------------------------------------


def filter_usage(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Which filters users keep on, and which they drop when the feed runs thin.

    Reads `filter_events`, which is why every toggle and slider release has to
    be logged at the moment it happens — this cannot be reconstructed later.
    The median result count at the moment a filter is switched *off* is the
    empty-feed threshold: how few items it takes before someone bails.
    """
    events = frames["filter_events"]
    if events.empty:
        return pd.DataFrame({"note": [EMPTY_NOTE]})

    events = events.copy()
    events["turned_off"] = events["value"].isin(["false", "off", "0"])
    out = events.groupby("filter_key").agg(
        events=("id", "count"),
        median_result_count=("result_count", "median"),
        turned_off_share=("turned_off", "mean"),
    )
    off = events[events["turned_off"]].groupby("filter_key")["result_count"].median()
    out["median_count_when_turned_off"] = off
    return out.sort_values("events", ascending=False).round(3)


# ---------------------------------------------------------------------------
# Q4. What does a used dorm couch cost?
# ---------------------------------------------------------------------------


def price_guidance(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Asking price by category and condition — the guidance we can put in the
    posting form, and the size of the like-new premium."""
    listings = frames["listings"]
    priced = listings[listings["price_cents"] > 0]
    if priced.empty:
        return pd.DataFrame({"note": [EMPTY_NOTE]})
    return (
        priced.groupby(["category", "condition"])["price_usd"]
        .agg(["count", "median", "mean"])
        .round(2)
    )


# ---------------------------------------------------------------------------
# Q5. How big is the moving-season effect?
# ---------------------------------------------------------------------------


def seasonality(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Listing volume by month, normalised per active seller.

    One cohort liquidates in May and the next arrives in August. If the academic
    calendar is a real liquidity engine, it shows up here as two spikes and a
    summer trough. Posts per seller keeps platform growth from faking a season.
    """
    listings = frames["listings"]
    dated = listings[listings["posted_at"].notna()]
    if dated.empty:
        return pd.DataFrame({"note": [EMPTY_NOTE]})

    # to_period drops the timezone, so make that explicit rather than warned about.
    month = dated["posted_at"].dt.tz_convert(None).dt.to_period("M")
    by_month = dated.groupby(month).agg(
        listings=("id", "count"),
        sellers=("seller_id", "nunique"),
        median_price=("price_usd", "median"),
        median_days_to_sell=("days_to_sell", "median"),
    )
    by_month["posts_per_seller"] = by_month["listings"] / by_month["sellers"]
    by_month.index = by_month.index.astype(str)
    return by_month.round(1)


# ---------------------------------------------------------------------------
# Q6. Where does the funnel leak, and how fast does anything sell?
# ---------------------------------------------------------------------------


def funnel(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Impressions → detail views → contacts → sold, with conversion between steps."""
    views, enquiries, listings = frames["views"], frames["enquiries"], frames["listings"]
    impressions = int(views["surface"].isin(["feed", "search"]).sum())
    detail = int((views["surface"] == "detail").sum())
    contacts = len(enquiries)
    sold = int((listings["status"] == "sold").sum())
    steps = [("impressions", impressions), ("detail views", detail), ("contacts", contacts), ("sold", sold)]
    out = pd.DataFrame(steps, columns=["step", "count"]).set_index("step")
    out["conversion_from_previous"] = (out["count"] / out["count"].shift(1)).round(4)
    return out


def days_to_sell(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Median days from posting to sold, by category — which categories have
    real demand and which are dead weight in the feed."""
    sold = frames["listings"].dropna(subset=["days_to_sell"])
    if sold.empty:
        return pd.DataFrame({"note": [EMPTY_NOTE]})
    return (
        sold.groupby("category")["days_to_sell"]
        .agg(["count", "median", "mean"])
        .sort_values("median")
        .round(1)
    )


# ---------------------------------------------------------------------------


def main() -> None:
    frames = load()
    pd.set_option("display.width", 120)

    sections = [
        ("Q1 · Do match badges change behaviour? (treated vs control)", badge_experiment),
        ("Q2 · Inventory by filter depth", inventory_by_filter_depth),
        ("Q3 · Which filter is doing the work", filter_usage),
        ("Q4 · Price guidance by category and condition", price_guidance),
        ("Q5 · Moving-season effect", seasonality),
        ("Q6 · Funnel", funnel),
        ("Q6 · Days to sell by category", days_to_sell),
    ]
    for title, fn in sections:
        print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")
        result = fn(frames)
        print(result)
        if result.attrs.get("p_value") is not None:
            print(f"lift p-value: {result.attrs['p_value']:.4f}")
        elif fn is badge_experiment and "note" not in result.columns:
            print("(one arm only — set BADGE_EXPERIMENT_ENABLED=true to start the coin flip)")


if __name__ == "__main__":
    main()
