"""The five research questions from PROPOSAL.md, one function each.

    python -m app.analytics.questions

Each function takes the frames dict from `frames.load()` and returns a
DataFrame, so a notebook can plot the same object the CLI prints. Nothing here
writes to the database.

A warning that matters more than the code: the seed generator produces both
tiers with the *same* base engagement rates on purpose (see scripts/seed.py).
So on seeded data these functions should find no effect. If they do, the finding
is in the generator, not in the world.
"""

from __future__ import annotations

import pandas as pd

from .frames import load


# ---------------------------------------------------------------------------
# Q1. Does shared affiliation actually change behaviour?
# ---------------------------------------------------------------------------


def internal_vs_external(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """The two-tier feed as a natural experiment.

    Internal listings carry match badges; external ones cannot. Same feed, same
    categories, same price ranges — so a difference in the view → save → enquiry
    funnel is the cleanest read we have on whether belonging drives a trade.
    """
    listings, views, saves, enquiries = (
        frames["listings"],
        frames["views"],
        frames["saves"],
        frames["enquiries"],
    )

    per_listing = (
        listings[["id", "is_internal", "category", "price_usd"]]
        .rename(columns={"id": "listing_id"})
        .merge(views.groupby("listing_id").size().rename("views"), on="listing_id", how="left")
        .merge(saves.groupby("listing_id").size().rename("saves"), on="listing_id", how="left")
        .merge(enquiries.groupby("listing_id").size().rename("enquiries"), on="listing_id", how="left")
        .fillna({"views": 0, "saves": 0, "enquiries": 0})
    )

    out = per_listing.groupby("is_internal").agg(
        listings=("listing_id", "count"),
        views=("views", "sum"),
        saves=("saves", "sum"),
        enquiries=("enquiries", "sum"),
        median_price=("price_usd", "median"),
    )
    out["save_rate"] = (out["saves"] / out["views"]).round(4)
    out["enquiry_rate"] = (out["enquiries"] / out["views"]).round(4)
    out.index = out.index.map({True: "internal", False: "external"})
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
    sample = users.sample(min(sample_users, len(users)), random_state=0)

    rows = []
    for user in sample.itertuples():
        internal = active[active["is_internal"]]
        rows.append(
            {
                "user_id": user.id,
                "no_filters": len(active),
                "internal_only": len(internal),
                "same_zip": len(internal[internal["seller_zip"] == user.zip_code]),
                "same_country": len(internal[internal["seller_nationality"] == user.nationality]),
                "same_school": len(internal[internal["seller_school"] == user.school]),
                "zip_and_country": len(
                    internal[
                        (internal["seller_zip"] == user.zip_code)
                        & (internal["seller_nationality"] == user.nationality)
                    ]
                ),
                "all_three": len(
                    internal[
                        (internal["seller_zip"] == user.zip_code)
                        & (internal["seller_nationality"] == user.nationality)
                        & (internal["seller_school"] == user.school)
                    ]
                ),
            }
        )

    depth = pd.DataFrame(rows).drop(columns=["user_id"])
    return depth.describe().loc[["mean", "50%", "min", "max"]].round(1)


# ---------------------------------------------------------------------------
# Q3. Which of the filters is doing the work?
# ---------------------------------------------------------------------------


def filter_usage(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Which filters users keep on, and which they drop when the feed runs thin.

    Reads `filter_events`, which is why every toggle and slider release has to
    be logged at the moment it happens — this cannot be reconstructed later.
    """
    events = frames["filter_events"]
    if events.empty:
        return pd.DataFrame(columns=["events", "median_result_count", "turned_off_share"])

    events = events.copy()
    events["turned_off"] = events["value"].isin(["false", "off", "0"])
    out = events.groupby("filter_key").agg(
        events=("id", "count"),
        median_result_count=("result_count", "median"),
        turned_off_share=("turned_off", "mean"),
    )
    return out.sort_values("events", ascending=False).round(3)


# ---------------------------------------------------------------------------
# Q4. Is there an in-group discount?
# ---------------------------------------------------------------------------


def in_group_discount(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Asking price inside the community versus the aggregated tier.

    Compared per category and condition, because a cheap textbook and a cheap
    sofa are not the same claim. A negative `discount_pct` means internal
    listings ask less than comparable external ones.
    """
    listings = frames["listings"]
    priced = listings[listings["price_cents"] > 0]

    pivot = (
        priced.groupby(["category", "condition", "is_internal"])["price_usd"]
        .median()
        .unstack("is_internal")
        .rename(columns={True: "internal_median", False: "external_median"})
        .dropna()
    )
    if pivot.empty:
        return pivot
    pivot["discount_pct"] = (
        (pivot["internal_median"] - pivot["external_median"]) / pivot["external_median"] * 100
    ).round(1)
    return pivot.sort_values("discount_pct")


# ---------------------------------------------------------------------------
# Q5. How big is the moving-season effect?
# ---------------------------------------------------------------------------


def seasonality(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Listing volume by month.

    One cohort liquidates in May and the next arrives in August. If the academic
    calendar is a real liquidity engine, it shows up here as two spikes and a
    summer trough — and the gap between them is the mismatch worth quantifying.
    """
    listings = frames["listings"]
    internal = listings[listings["is_internal"] & listings["posted_at"].notna()]
    if internal.empty:
        return pd.DataFrame(columns=["listings", "median_price", "median_days_to_sell"])

    # to_period drops the timezone, so make that explicit rather than warned about.
    month = internal["posted_at"].dt.tz_convert(None).dt.to_period("M")
    by_month = internal.groupby(month).agg(
        listings=("id", "count"),
        median_price=("price_usd", "median"),
        median_days_to_sell=("days_to_sell", "median"),
    )
    by_month.index = by_month.index.astype(str)
    return by_month.round(1)


# ---------------------------------------------------------------------------


def main() -> None:
    frames = load()
    pd.set_option("display.width", 120)

    sections = [
        ("Q1 · Internal vs external engagement", internal_vs_external),
        ("Q2 · Inventory by filter depth", inventory_by_filter_depth),
        ("Q3 · Which filter is doing the work", filter_usage),
        ("Q4 · In-group discount", in_group_discount),
        ("Q5 · Moving-season effect", seasonality),
    ]
    for title, fn in sections:
        print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")
        print(fn(frames))


if __name__ == "__main__":
    main()
