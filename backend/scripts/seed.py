"""Load the generated corpus into the database — UX_SPEC.md §9.

    python -m scripts.seed --reset                              # load data/*.csv
    python -m scripts.seed --reset --demo-email you@columbia.edu
    python -m scripts.seed --reset --regenerate                 # rebuild the CSVs first
    python -m scripts.seed --reset --limit 200                  # a small database, fast

The corpus comes from `seed/` at the repository root (Kobe), which owns the
distributions, the validator and the §7 state fixtures. This file is the
loader: everything about how the data *looks* belongs in `seed/`, everything
about how it reaches SQLite or Postgres belongs here. See docs/mock_data_spec.md.

One rule is applied on the way in: **only internal listings are loaded**. The
generator still emits an external tier (`source != 'internal'`), but the schema
has no `source` column since 2026-09-02 (docs/DECISIONS.md), so those rows and
every event that references them are skipped and counted.
"""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

from app.db import SessionLocal, create_all, reset_all
from app.enums import Category, Condition, Grade, ListingStatus, School
from app.models import (
    SearchEvent,
    Enquiry,
    FilterEvent,
    Listing,
    ListingPhoto,
    ListingView,
    Save,
    User,
)
from app.services import domains

# repo root: backend/scripts/seed.py -> ../..
REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
DATA_DIR = os.path.join(REPO_ROOT, "data")


def _bool(value: str) -> bool:
    return value.strip().lower() in ("true", "t", "1", "yes")


def _int(value: str) -> int:
    return int(value) if value != "" else 0


def _float(value: str) -> float:
    return float(value) if value != "" else 0.0


def _dt(value: str):
    """ISO-8601 with an offset, as written by seed/export.py."""
    if not value:
        return None
    return datetime.fromisoformat(value)


def _text(value: str):
    """Empty field means NULL — the convention seed/export.py writes."""
    return value if value != "" else None


def _read(name: str) -> list[dict]:
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        raise SystemExit(
            "%s not found.\n"
            "Generate the corpus first:  python3 -m seed.generate\n"
            "or re-run this with --regenerate." % path
        )
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


# --------------------------------------------------------------------------
# Row builders. One per table, mapping CSV columns to the ORM.
# --------------------------------------------------------------------------


def _user(r: dict) -> User:
    return User(
        id=r["id"],
        email=r["email"],
        username=r["username"],
        display_name=_text(r["display_name"]),
        phone=_text(r["phone"]),
        phone_contact_enabled=_bool(r["phone_contact_enabled"]),
        nationality=r["nationality"],
        school=r["school"],
        grade=r["grade"],
        zip_code=r["zip_code"],
        default_radius_mi=_float(r["default_radius_mi"]),
        default_filter_same_zip=_bool(r["default_filter_same_zip"]),
        default_filter_same_nationality=_bool(r["default_filter_same_nationality"]),
        default_filter_same_school=_bool(r["default_filter_same_school"]),
        is_verified=_bool(r["is_verified"]),
        status=r["status"],
        created_at=_dt(r["created_at"]),
        updated_at=_dt(r["updated_at"]),
    )


def _is_internal(r: dict) -> bool:
    return r.get("source", "internal") == "internal" and bool(_text(r["seller_id"]))


def _listing(r: dict) -> Listing:
    return Listing(
        id=r["id"],
        seller_id=r["seller_id"],
        title=r["title"],
        description=_text(r["description"]),
        category=r["category"],
        subcategory=_text(r["subcategory"]),
        condition=r["condition"],
        price_cents=_int(r["price_cents"]),
        is_free=_bool(r["is_free"]),
        is_negotiable=_bool(r["is_negotiable"]),
        zip_code=r["zip_code"],
        status=r["status"],
        view_count=_int(r["view_count"]),
        save_count=_int(r["save_count"]),
        enquiry_count=_int(r["enquiry_count"]),
        posted_at=_dt(r["posted_at"]),
        sold_at=_dt(r["sold_at"]),
        # Added 2026-09-03. Nullable: a sold listing with no buyer went to
        # someone who never enquired, which is a real and measurable case.
        buyer_id=_text(r.get("buyer_id", "")),
        sold_price_cents=(int(r["sold_price_cents"])
                          if r.get("sold_price_cents") else None),
    )


def _photo(r: dict) -> ListingPhoto:
    return ListingPhoto(
        id=r["id"],
        listing_id=r["listing_id"],
        url=r["url"],
        position=_int(r["position"]),
        created_at=_dt(r["created_at"]),
    )


def _view(r: dict) -> ListingView:
    return ListingView(
        id=r["id"],
        listing_id=r["listing_id"],
        viewer_id=_text(r["viewer_id"]),
        surface=r["surface"],
        # The corpus carries the coin flip since 2026-09-03, so the experiment
        # has two arms. Falls back to True for an older CSV without the column,
        # which is what the previous hardcoded value meant.
        badges_shown=_bool(r.get("badges_shown", "true")),
        viewed_at=_dt(r["viewed_at"]),
        session_id=_text(r.get("session_id", "")),
    )


def _save(r: dict) -> Save:
    return Save(
        id=r["id"],
        listing_id=r["listing_id"],
        user_id=r["user_id"],
        created_at=_dt(r["created_at"]),
        session_id=_text(r.get("session_id", "")),
    )


def _enquiry(r: dict) -> Enquiry:
    return Enquiry(
        id=r["id"],
        listing_id=r["listing_id"],
        buyer_id=r["buyer_id"],
        channel=r["channel"],
        created_at=_dt(r["created_at"]),
        session_id=_text(r.get("session_id", "")),
    )


def _filter_event(r: dict) -> FilterEvent:
    return FilterEvent(
        id=r["id"],
        user_id=_text(r["user_id"]),
        filter_key=r["filter_key"],
        value=_text(r["value"]),
        result_count=_int(r["result_count"]),
        created_at=_dt(r["created_at"]),
        session_id=_text(r.get("session_id", "")),
    )


def _search_event(r: dict) -> SearchEvent:
    return SearchEvent(
        id=r["id"],
        user_id=_text(r["user_id"]),
        session_id=_text(r.get("session_id", "")),
        query=r["query"],
        result_count=_int(r["result_count"]),
        clicked_listing_id=_text(r["clicked_listing_id"]),
        created_at=_dt(r["created_at"]),
    )


# Load order is foreign-key order and is not negotiable.
DEPENDENT_TABLES = (
    ("listing_photos.csv", _photo, ListingPhoto),
    ("listing_views.csv", _view, ListingView),
    ("saves.csv", _save, Save),
    ("enquiries.csv", _enquiry, Enquiry),
)


def _insert(db, name: str, rows: list, build, batch: int = 2000) -> None:
    for start in range(0, len(rows), batch):
        db.add_all([build(r) for r in rows[start : start + batch]])
        db.flush()
    db.commit()
    print("  %-22s %7d rows" % (name, len(rows)))


def regenerate(users: int | None, listings: int | None) -> None:
    """Shell out to the generator at the repo root.

    A subprocess rather than an import: `seed/` is standard-library only and
    deliberately knows nothing about SQLAlchemy or this virtualenv.
    """
    # The schema has no external tier, so ask the generator for none. It
    # validates cleanly at --external 0; its own default is Kobe's to change.
    cmd = [sys.executable, "-m", "seed.generate", "--external", "0"]
    if users is not None:
        cmd += ["--users", str(users)]
    if listings is not None:
        cmd += ["--listings", str(listings)]
    print("$ %s" % " ".join(cmd))
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    if result.returncode != 0:
        raise SystemExit(
            "Generation failed. The generator refuses to export when one of its "
            "invariant groups fails, so fix that before loading."
        )


def load(do_reset: bool, *, limit: int | None = None, demo_email: str | None = None) -> dict[str, int]:
    """Load data/*.csv. Returns the row counts, for callers that want to check them."""
    if do_reset:
        reset_all()  # drop and recreate: the schema has moved since the corpus was made
    else:
        create_all()

    counts: dict[str, int] = {}
    db = SessionLocal()
    try:
        users = _read("users.csv")
        _insert(db, "users.csv", users, _user)
        counts["users"] = len(users)

        all_listings = _read("listings.csv")
        listings = [r for r in all_listings if _is_internal(r)]
        skipped = len(all_listings) - len(listings)
        if limit is not None:
            listings = listings[:limit]
        kept = {r["id"] for r in listings}
        _insert(db, "listings.csv", listings, _listing)
        counts["listings"] = len(listings)
        counts["external_skipped"] = skipped
        if skipped:
            print("  %-22s %7d rows skipped — external tier, not in the schema (docs/DECISIONS.md)"
                  % ("", skipped))

        for name, build, _model in DEPENDENT_TABLES:
            rows = [r for r in _read(name) if r["listing_id"] in kept]
            _insert(db, name, rows, build)
            counts[name.split(".")[0]] = len(rows)

        events = _read("filter_events.csv")
        _insert(db, "filter_events.csv", events, _filter_event)
        counts["filter_events"] = len(events)

        # Searches reference a listing only when the searcher clicked one, and
        # that listing may have been skipped with the external tier — so clear
        # the click rather than dropping an otherwise valid search.
        searches = _read("search_events.csv")
        for row in searches:
            if row.get("clicked_listing_id") and row["clicked_listing_id"] not in kept:
                row["clicked_listing_id"] = ""
        _insert(db, "search_events.csv", searches, _search_event)
        counts["search_events"] = len(searches)

        if demo_email:
            _add_demo_account(db, demo_email)
    finally:
        db.close()
    return counts


DEMO_ITEMS = (
    ("IKEA MALM desk 140×65, white", Category.FURNITURE, "desks", Condition.USED_GOOD, 6000),
    ("Sony WH-1000XM4 headphones", Category.ELECTRONICS, None, Condition.LIKE_NEW, 18000),
    ("Corporate Finance (Berk) 5th ed.", Category.TEXTBOOKS, None, Condition.USED_GOOD, 3500),
)


def _add_demo_account(db, email: str) -> None:
    """Your own account, with three fresh listings so My listings is not empty.

    Photos are left off on purpose so the placeholder path stays exercised;
    post something through the app to see a real upload.
    """
    email = domains.normalize(email)
    reason = domains.rejection_reason(email)
    if reason:
        raise SystemExit(reason)
    if db.query(User).filter(User.email == email).first():
        print("  demo account %s already exists" % email)
        return
    now = datetime.now(timezone.utc)
    user = User(
        email=email,
        username=email.split("@")[0].replace(".", "_")[:20],
        phone="+16465550142",
        nationality="IN",
        school=domains.suggested_school(email) or School.SEAS_GRAD,
        grade=Grade.GRADUATE,
        zip_code="10027",
        is_verified=True,
        created_at=now - timedelta(days=30),
    )
    db.add(user)
    db.flush()
    for i, (title, category, sub, condition, price) in enumerate(DEMO_ITEMS):
        db.add(
            Listing(
                seller_id=user.id,
                title=title,
                description="Moving out at the end of the month. Pickup on campus, cash or Venmo.",
                category=category,
                subcategory=sub,
                condition=condition,
                price_cents=price,
                is_negotiable=True,
                zip_code="10027",
                status=ListingStatus.ACTIVE,
                posted_at=now - timedelta(hours=2 + 20 * i),
            )
        )
    db.commit()
    print("  demo account %s (@%s) with %d listings" % (email, user.username, len(DEMO_ITEMS)))


def warn_about_photos() -> None:
    """Say so, loudly, when the photo files the rows point at are not on disk.

    The ~5,800 images are gitignored — they are 200MB and reproducible — so a
    teammate who clones and seeds gets listings whose `url` points at files they
    do not have. The frontend degrades to its gradient placeholder rather than
    breaking, which is worse than an error in one specific way: nothing tells
    you anything is missing. Hence this.
    """
    photos_csv = os.path.join(DATA_DIR, "listing_photos.csv")
    if not os.path.exists(photos_csv):
        return
    with open(photos_csv, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return

    out_dir = os.path.join(REPO_ROOT, "frontend", "public", "photos")
    # Sample rather than stat 5,800 files.
    sample = rows[:: max(len(rows) // 40, 1)][:40]
    present = sum(
        1 for r in sample
        if os.path.exists(os.path.join(out_dir, r["url"].lstrip("/").split("/", 1)[1]))
    )
    if present >= len(sample):
        return

    share = "none" if present == 0 else "only about %d%%" % round(100 * present / len(sample))
    print("\n" + "!" * 74)
    print("  PHOTOS ARE MISSING — %s of the %d listing photos are on disk."
          % (share, len(rows)))
    print()
    print("  The images are not committed: 200MB, and reproducible from the CSV.")
    print("  The app will still run, showing a gradient placeholder on every card,")
    print("  so this will NOT look like an error. Run this once, from the repo root:")
    print()
    print("      python3 scripts/fetch_photos.py       # real photos, ~2 min, no key")
    print("      python3 scripts/make_photos.py        # offline gradients, seconds")
    print()
    print("  See docs/mock_data_spec.md.")
    print("!" * 74)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true",
                        help="drop and recreate every table before loading")
    parser.add_argument("--regenerate", action="store_true",
                        help="rebuild data/*.csv before loading")
    parser.add_argument("--users", type=int, help="corpus size; implies --regenerate")
    parser.add_argument("--listings", type=int, help="corpus size; implies --regenerate")
    parser.add_argument("--limit", type=int, help="load only the first N listings (fast local DB)")
    parser.add_argument("--demo-email", help="also create an account for this Columbia address")
    args = parser.parse_args()

    if args.users is not None or args.listings is not None or args.regenerate:
        regenerate(args.users, args.listings)

    print("\nLoading %s" % DATA_DIR)
    load(args.reset, limit=args.limit, demo_email=args.demo_email)
    warn_about_photos()
    print("\nDone. Sign in with a seeded address (e.g. the reference member @brian_dw"
          "%s) — the link appears on screen in dev mode."
          % (", or your demo account" if args.demo_email else ""))


if __name__ == "__main__":
    main()
