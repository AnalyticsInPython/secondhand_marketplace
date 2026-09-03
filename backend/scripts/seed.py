"""Load the generated corpus into the database — UX_SPEC.md §9.

    python -m scripts.seed --reset                    # load data/*.csv
    python -m scripts.seed --reset --regenerate       # rebuild the CSVs first
    python -m scripts.seed --reset --users 2000 --listings 3000   # implies --regenerate

This used to generate its own rows. It no longer does, and that is deliberate:
there were two generators claiming the same §9, and they had already drifted.
The ZIP tables disagreed (18 codes here, 47 in the generator), grade and school
were drawn independently here so undergraduates appeared at CBS, and saves were
sampled from users who had never viewed the listing, which made every time-based
analysis over `saves` meaningless.

The corpus now comes from `seed/`, at the repository root, which owns the
distributions, a 16-group validator and the §7 state fixtures. This file is the
loader. See docs/mock_data_spec.md.

Everything about *how* the data looks belongs in `seed/`. Everything about how it
reaches Postgres or SQLite belongs here.
"""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
from datetime import datetime

from sqlalchemy import delete

from app.db import SessionLocal, create_all
from app.models import (
    Enquiry,
    FilterEvent,
    Listing,
    ListingPhoto,
    ListingView,
    Save,
    User,
)

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


def _listing(r: dict) -> Listing:
    return Listing(
        id=r["id"],
        seller_id=_text(r["seller_id"]),
        source=r["source"],
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
        external_url=_text(r["external_url"]),
        posted_at=_dt(r["posted_at"]),
        sold_at=_dt(r["sold_at"]),
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
        viewed_at=_dt(r["viewed_at"]),
    )


def _save(r: dict) -> Save:
    return Save(
        id=r["id"],
        listing_id=r["listing_id"],
        user_id=r["user_id"],
        created_at=_dt(r["created_at"]),
    )


def _enquiry(r: dict) -> Enquiry:
    return Enquiry(
        id=r["id"],
        listing_id=r["listing_id"],
        buyer_id=r["buyer_id"],
        channel=r["channel"],
        created_at=_dt(r["created_at"]),
    )


def _filter_event(r: dict) -> FilterEvent:
    return FilterEvent(
        id=r["id"],
        user_id=_text(r["user_id"]),
        filter_key=r["filter_key"],
        value=_text(r["value"]),
        result_count=_int(r["result_count"]),
        created_at=_dt(r["created_at"]),
    )


# Load order is foreign-key order and is not negotiable.
TABLES = (
    ("users.csv", _user, User),
    ("listings.csv", _listing, Listing),
    ("listing_photos.csv", _photo, ListingPhoto),
    ("listing_views.csv", _view, ListingView),
    ("saves.csv", _save, Save),
    ("enquiries.csv", _enquiry, Enquiry),
    ("filter_events.csv", _filter_event, FilterEvent),
)


def reset(db) -> None:
    """Delete in reverse FK order so nothing is orphaned mid-way."""
    for _name, _build, model in reversed(TABLES):
        db.execute(delete(model))
    db.commit()


def regenerate(users: int | None, listings: int | None) -> None:
    """Shell out to the generator at the repo root.

    A subprocess rather than an import: `seed/` is standard-library only and
    deliberately knows nothing about SQLAlchemy or this virtualenv.
    """
    cmd = [sys.executable, "-m", "seed.generate"]
    if users is not None:
        cmd += ["--users", str(users)]
    if listings is not None:
        cmd += ["--listings", str(listings)]
    print("$ %s" % " ".join(cmd))
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    if result.returncode != 0:
        raise SystemExit(
            "Generation failed. The generator refuses to export when one of its "
            "16 invariant groups fails, so fix that before loading."
        )


def load(do_reset: bool, batch: int = 2000) -> None:
    create_all()
    db = SessionLocal()
    try:
        if do_reset:
            reset(db)

        total = 0
        for name, build, _model in TABLES:
            rows = _read(name)
            for start in range(0, len(rows), batch):
                db.add_all([build(r) for r in rows[start:start + batch]])
                db.flush()
            db.commit()
            print("  %-22s %7d rows" % (name, len(rows)))
            total += len(rows)
        print("  %-22s %7d rows" % ("TOTAL", total))
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true",
                        help="empty the tables before loading")
    parser.add_argument("--regenerate", action="store_true",
                        help="rebuild data/*.csv before loading")
    parser.add_argument("--users", type=int,
                        help="corpus size; implies --regenerate")
    parser.add_argument("--listings", type=int,
                        help="corpus size; implies --regenerate")
    args = parser.parse_args()

    if args.users is not None or args.listings is not None or args.regenerate:
        regenerate(args.users, args.listings)

    print("\nLoading %s" % DATA_DIR)
    load(args.reset)
    print("\nDone. The reference member is @brian_dw — sign in as their address "
          "to see the screens the way the Figma draws them.")


if __name__ == "__main__":
    main()
