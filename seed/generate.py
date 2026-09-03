"""CLI entry point: generate, inject, validate, export, report.

    python -m seed.generate                       # defaults from UX_SPEC §9
    python -m seed.generate --users 2000 --listings 3000
    python -m seed.generate --seed 42 --out data/

Deterministic: the same ``--seed`` with the same counts produces byte-identical
files, so a bug someone finds on Tuesday still exists on Thursday.

Order matters and is not arbitrary:

  users -> listings + photos -> edge cases -> events -> validate -> export

Edge cases run *before* events because they change listing statuses and seller
attributes, and events must be generated against the final corpus. Counters are
backfilled inside the events step for the same reason.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import random
import sys

from . import catalog as C
from . import edge_cases, events, export, listings as L, users as U, validate
from . import vocabularies as V
from . import zips as Z
from .feed import Feed, FilterState

# §9: "~1,000 members and ~1,500 listings", of which ~150 are external.
DEFAULT_USERS = 1000
DEFAULT_LISTINGS = 1500
DEFAULT_EXTERNAL = 150
DEFAULT_SEED = 20260902

# Fixed so "now" does not drift between runs. Override with --now.
DEFAULT_NOW = "2026-09-02T18:00:00"


def _parse_args(argv):
    p = argparse.ArgumentParser(prog="seed.generate", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--users", type=int, default=DEFAULT_USERS)
    p.add_argument("--listings", type=int, default=DEFAULT_LISTINGS,
                   help="total listings, internal + external")
    p.add_argument("--external", type=int, default=DEFAULT_EXTERNAL,
                   help="how many of --listings come from the aggregated tier")
    p.add_argument("--now", default=DEFAULT_NOW,
                   help="ISO timestamp treated as the present")
    p.add_argument("--out", default="data",
                   help="output directory for the CSVs and seed.sql")
    p.add_argument("--no-export", action="store_true",
                   help="generate and validate without writing files")
    return p.parse_args(argv)


def _pct(part, whole):
    return 100.0 * part / whole if whole else 0.0


def build(seed, n_users, n_listings, n_external, now):
    """Run the pipeline and return everything, unwritten."""
    rng = random.Random(seed)
    n_internal = max(n_listings - n_external, 0)

    people = U.generate_users(rng, n_users, now)
    rows, photos = L.generate_listings(rng, people, n_internal, n_external, now)
    manifest, notes = edge_cases.install(rng, people, rows, photos, now)
    views, saves, enquiries, filter_events = events.generate_events(
        rng, people, rows, photos, now)

    return {
        "users": people,
        "listings": rows,
        "photos": photos,
        "views": views,
        "saves": saves,
        "enquiries": enquiries,
        "filter_events": filter_events,
        "manifest": manifest,
        "notes": notes,
    }


def _report(bundle, now):
    people = bundle["users"]
    rows = bundle["listings"]
    internal = [l for l in rows if l["source"] == "internal"]

    print("\n" + "=" * 72)
    print("CORPUS")
    print("=" * 72)
    print("  users              %6d" % len(people))
    print("  listings           %6d   (%d internal, %d external)"
          % (len(rows), len(internal), len(rows) - len(internal)))
    print("  photos             %6d   (%.1f per listing)"
          % (len(bundle["photos"]), len(bundle["photos"]) / max(len(rows), 1)))
    print("  listing_views      %6d" % len(bundle["views"]))
    print("  saves              %6d" % len(bundle["saves"]))
    print("  enquiries          %6d" % len(bundle["enquiries"]))
    print("  filter_events      %6d" % len(bundle["filter_events"]))

    v, s, e = len(bundle["views"]), len(bundle["saves"]), len(bundle["enquiries"])
    if e:
        print("\n  funnel             %.0f : %.1f : 1   (§9 asks for 100 : 8 : 1)"
              % (100.0 * v / v, 100.0 * s / v))

    print("\n" + "-" * 72)
    print("USERS vs UX_SPEC §9")
    print("-" * 72)
    for grade in V.GRADES:
        n = sum(1 for u in people if u["grade"] == grade)
        print("  %-16s %5.1f%%   (§9: %.0f%%)"
              % (grade, _pct(n, len(people)), U.GRADE_WEIGHTS[grade]))
    print()
    for code, target in (("US", 35), ("CN", 18), ("KR", 10), ("IN", 8)):
        n = sum(1 for u in people if u["nationality"] == code)
        print("  nationality %-4s %5.1f%%   (§9: %d%%)" % (code, _pct(n, len(people)), target))
    print()
    for zip_code, target in (("10027", 40), ("10025", 15), ("10031", 10)):
        n = sum(1 for u in people if u["zip_code"] == zip_code)
        print("  ZIP %-11s %5.1f%%   (§9: %d%%)" % (zip_code, _pct(n, len(people)), target))
    no_phone = sum(1 for u in people if u["phone"] is None)
    print("\n  phone NULL      %5.1f%%   (§9: ~30%%)" % _pct(no_phone, len(people)))

    print("\n" + "-" * 72)
    print("LISTINGS vs UX_SPEC §9")
    print("-" * 72)
    targets = C.CATEGORY_WEIGHTS
    for category in V.CATEGORIES:
        n = sum(1 for l in rows if l["category"] == category)
        print("  %-17s %5.1f%%   (§9: %.0f%%)"
              % (category, _pct(n, len(rows)), targets[category]))
    print()
    for condition, target in (("used_good", 45), ("like_new", 30),
                              ("new", None), ("used_fair", None)):
        n = sum(1 for l in rows if l["condition"] == condition)
        note = "(§9: %d%%)" % target if target else ""
        print("  %-17s %5.1f%%   %s" % (condition, _pct(n, len(rows)), note))
    print()
    free = sum(1 for l in rows if l["is_free"])
    print("  free              %5.1f%%   (§9: ~8%%)" % _pct(free, len(rows)))
    sold = [l for l in internal if l["status"] == "sold"]
    print("  sold (internal)   %5.1f%%   (§9: ~35%%)" % _pct(len(sold), len(internal)))
    if sold:
        days = sorted((l["sold_at"] - l["posted_at"]).total_seconds() / 86400
                      for l in sold)
        print("  median days to sell %5.1f   (§9: ~6)" % days[len(days) // 2])
    for status in V.LISTING_STATUSES:
        n = sum(1 for l in rows if l["status"] == status)
        print("    %-15s %5.1f%%" % (status, _pct(n, len(rows))))

    print("\n  price by category (median of listed, free excluded)")
    for category in V.CATEGORIES:
        prices = sorted(l["price_cents"] // 100 for l in rows
                        if l["category"] == category and l["price_cents"] > 0)
        if prices:
            low, high = C.CATEGORY_PRICE_RANGE[category]
            print("    %-17s $%-5d  (band $%d-%d, n=%d)"
                  % (category, prices[len(prices) // 2], low, high, len(prices)))

    print("\n  seasonality — listings per month posted")
    per_month: "dict[str, int]" = {}
    for l in rows:
        key = l["posted_at"].strftime("%Y-%m")
        per_month[key] = per_month.get(key, 0) + 1
    recent = sorted(per_month.items())[-14:]
    peak = max(n for _, n in recent) if recent else 1
    for month, n in recent:
        bar = "#" * int(38 * n / peak)
        marker = "  <- move season" if month.endswith(("-05", "-08")) else ""
        print("    %s %4d %s%s" % (month, n, bar, marker))


def _reference_report(bundle, now):
    """What the reference member actually sees. The demo-readiness check."""
    people = bundle["users"]
    rows = bundle["listings"]
    reference = next(u for u in people
                     if u["id"] == bundle["manifest"]["reference_member"])
    feed = Feed(rows, people)

    print("\n" + "-" * 72)
    print("REFERENCE MEMBER — @%s  (%s · %s · %s · %s)"
          % (reference["username"], reference["zip_code"],
             reference["nationality"], reference["school"], reference["grade"]))
    print("-" * 72)

    base = FilterState()
    print("  all visible listings        %5d" % feed.count(reference, base))
    print("  within 2.5 mi               %5d"
          % feed.count(reference, FilterState(radius_mi=2.5)))

    trust = feed.facet_counts(reference, FilterState(radius_mi=2.5), "trust")
    for key, value in trust.items():
        print("  + %-25s %5d" % (key, value))

    print("\n  category facets at 2.5 mi (§5.4 conditional counts)")
    for key, value in feed.facet_counts(
            reference, FilterState(radius_mi=2.5), "category").items():
        print("    %-17s %5d" % (key, value))

    print("\n  distance slider (§7 state C6)")
    for key, value in feed.facet_counts(reference, FilterState(), "radius").items():
        print("    %-6s mi %11d" % (key, value))

    print("\n  §7 state coverage")
    for tag, row_id in sorted(bundle["manifest"].items()):
        print("    %-26s %s" % (tag, row_id))
    for tag, ok, detail in edge_cases.audit(feed, reference, now):
        print("    %-26s %s   %s" % (tag, "OK " if ok else "FAIL", detail))
    for note in bundle["notes"]:
        print("    note: %s" % note)


def main(argv=None):
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    now = dt.datetime.fromisoformat(args.now)

    print("Columbia Market seed generator")
    print("  seed=%d  users=%d  listings=%d (external %d)  now=%s"
          % (args.seed, args.users, args.listings, args.external, now.isoformat()))

    bundle = build(args.seed, args.users, args.listings, args.external, now)
    _report(bundle, now)
    _reference_report(bundle, now)

    print("\n" + "-" * 72)
    print("VALIDATION")
    print("-" * 72)
    failures = validate.validate(
        bundle["users"], bundle["listings"], bundle["photos"], bundle["views"],
        bundle["saves"], bundle["enquiries"], bundle["filter_events"], now)
    if failures:
        for failure in failures:
            print("  FAIL  %s" % failure)
        print("\n  %d invariant(s) failed — not exporting." % len(failures))
        return 1
    print("  all 16 invariant groups pass")

    if args.no_export:
        print("\n--no-export: nothing written")
        return 0

    zip_rows = [
        {
            "zip_code": z.zip_code,
            "neighbourhood": z.neighbourhood,
            "borough": z.borough,
            "lat": z.lat,
            "lon": z.lon,
            "miles_from_campus": z.miles_from_campus,
        }
        for z in sorted(Z.ZIPS.values(), key=lambda z: z.zip_code)
    ]
    written = export.export_all(
        args.out, bundle["users"], bundle["listings"], bundle["photos"],
        bundle["views"], bundle["saves"], bundle["enquiries"],
        bundle["filter_events"], zip_rows)

    print("\n" + "-" * 72)
    print("WRITTEN to %s/" % args.out)
    print("-" * 72)
    for name in sorted(written):
        path = os.path.join(args.out, name)
        size = os.path.getsize(path)
        print("  %-22s %8d rows   %7.1f KB"
              % (name, written[name], size / 1024.0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
