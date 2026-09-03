"""Load the database into pandas — the entry point for every analysis.

This is a Python course, so the research questions in PROPOSAL.md are answered
here, in pandas, rather than in SQL scattered across the API or in the frontend.
Read the tables once, join in memory, and keep the questions readable.
"""

from __future__ import annotations

import pandas as pd

from ..db import engine


def _read(table: str) -> pd.DataFrame:
    return pd.read_sql_table(table, engine)


def load() -> dict[str, pd.DataFrame]:
    """Every table, as DataFrames, with the joins the questions need.

    Returns a dict rather than a bag of globals so a notebook can do:

        frames = load()
        listings = frames["listings"]
    """
    users = _read("users")
    listings = _read("listings")
    views = _read("listing_views")
    saves = _read("saves")
    enquiries = _read("enquiries")
    filter_events = _read("filter_events")

    # Everything downstream wants the seller's attributes on the listing row.
    seller_cols = users[["id", "nationality", "school", "grade", "zip_code"]].rename(
        columns={
            "id": "seller_id",
            "nationality": "seller_nationality",
            "school": "seller_school",
            "grade": "seller_grade",
            "zip_code": "seller_zip",
        }
    )
    listings = listings.merge(seller_cols, on="seller_id", how="left")

    listings["price_usd"] = listings["price_cents"] / 100
    listings["posted_at"] = pd.to_datetime(listings["posted_at"], utc=True, errors="coerce")
    listings["sold_at"] = pd.to_datetime(listings["sold_at"], utc=True, errors="coerce")
    listings["days_to_sell"] = (listings["sold_at"] - listings["posted_at"]).dt.total_seconds() / 86400

    for frame, col in (
        (views, "viewed_at"),
        (enquiries, "created_at"),
        (saves, "created_at"),
        (filter_events, "created_at"),
    ):
        if not frame.empty:
            frame[col] = pd.to_datetime(frame[col], utc=True, errors="coerce")

    return {
        "users": users,
        "listings": listings,
        "views": views,
        "saves": saves,
        "enquiries": enquiries,
        "filter_events": filter_events,
    }
