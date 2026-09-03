#!/usr/bin/env python3
"""Fetch real photos that match what each listing actually is.

    python3 scripts/fetch_photos.py                      # Openverse, no key needed
    python3 scripts/fetch_photos.py --fraction 0.1       # a sample, to judge quality
    python3 scripts/fetch_photos.py --source pexels      # needs PEXELS_API_KEY

Default source is Openverse, which aggregates openly-licensed photos from Flickr,
Wikimedia and others and needs no account or key. Pexels gives better-looking
photos but wants a free API key; Wikimedia Commons is the fallback when Openverse
returns nothing, and skews to product-catalogue shots.

Why this works without 1,500 searches: the corpus is generated from ~75 item
templates, and each template carries its own search query (see
``seed/catalog.py``). ``seed.generate`` writes the per-listing query to
``data/photo_queries.csv``, so a listing titled "IKEA MALM desk 140x65, white"
asks for "white wooden desk" and one titled "Cuckoo 6-cup rice cooker" asks for
"rice cooker". Roughly 75 searches cover the whole catalogue.

Two pools, kept apart on purpose:

``data/photo_pool/<query>/<n>.jpg``
    Downloaded originals, one directory per query. Cached, so re-running does not
    re-download, and so switching which listing gets which photo costs nothing.

``frontend/public/photos/<listing_id>/<position>.webp``
    What the app serves, resized and re-encoded. Assignment is by a hash of the
    listing id, so it is deterministic and a listing keeps the same photo across
    runs.

Anything a search cannot fill falls back to ``scripts/make_photos.py``'s glyph,
so the app never shows a broken image. Credits are written to
``data/PHOTO_CREDITS.csv``: the Pexels licence does not require attribution, but
recording where a file came from is cheap and makes the licence auditable.

The API key is read from ``backend/.env`` (``PEXELS_API_KEY=...``) or the
environment. It is never printed and never written anywhere else.
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), os.pardir))
POOL_DIR = os.path.join(REPO_ROOT, "data", "photo_pool")
CREDITS_CSV = os.path.join(REPO_ROOT, "data", "PHOTO_CREDITS.csv")

PEXELS_API = "https://api.pexels.com/v1/search"
OPENVERSE_API = "https://api.openverse.org/v1/images/"
WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"
UA = "columbia-market-seed/1.0 (ENGI 4503 coursework)"
OUT_W, OUT_H = 760, 570
QUALITY = 72


def _api_key() -> str:
    key = os.environ.get("PEXELS_API_KEY")
    if key:
        return key.strip()
    env_path = os.path.join(REPO_ROOT, "backend", ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line.startswith("PEXELS_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit(
        "No Pexels API key found.\n"
        "Add one line to backend/.env:\n"
        "    PEXELS_API_KEY=your_key_here\n"
        "or export PEXELS_API_KEY in your shell. Get a free key at\n"
        "https://www.pexels.com/api/ — it is not printed or stored anywhere else."
    )


def _slug(query: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")


def _get_json(url: str, headers=None, timeout=30):
    req = urllib.request.Request(url, headers=dict(headers or {}, **{"User-Agent": UA}))
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read())


def _search_openverse(query: str, count: int) -> "list[dict]":
    """Openverse. No key. Restricted to the permissive licences so the corpus
    stays redistributable — cc0, by and by-sa, deliberately excluding nd."""
    url = OPENVERSE_API + "?" + urllib.parse.urlencode({
        "q": query,
        "page_size": count,
        "license": "cc0,by,by-sa",
        "mature": "false",
    })
    try:
        payload = _get_json(url)
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            print("    (Openverse rate limit — falling back to Wikimedia)")
            return _search_wikimedia(query, count)
        raise
    out = []
    for r in payload.get("results", []):
        if r.get("url"):
            out.append({
                "src": r["url"],
                "photographer": r.get("creator") or "",
                "page": r.get("foreign_landing_url") or "",
                "licence": "%s %s" % (r.get("license", ""), r.get("license_version", "")),
            })
    return out


def _search_wikimedia(query: str, count: int) -> "list[dict]":
    """Wikimedia Commons. No key. Product-catalogue-ish but reliable."""
    url = WIKIMEDIA_API + "?" + urllib.parse.urlencode({
        "action": "query", "generator": "search",
        "gsrsearch": "filetype:bitmap " + query,
        "gsrnamespace": "6", "gsrlimit": count,
        "prop": "imageinfo", "iiprop": "url|extmetadata",
        "iiurlwidth": "1000", "format": "json",
    })
    payload = _get_json(url)
    out = []
    for page in (payload.get("query") or {}).get("pages", {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        src = info.get("thumburl") or info.get("url")
        if src:
            out.append({
                "src": src,
                "photographer": "",
                "page": info.get("descriptionurl") or "",
                "licence": "see Commons file page",
            })
    return out


def _search_pexels(key: str, query: str, count: int) -> "list[dict]":
    """One Pexels search. Landscape orientation suits a 4:3 card."""
    url = PEXELS_API + "?" + urllib.parse.urlencode({
        "query": query,
        "per_page": count,
        "orientation": "landscape",
    })
    try:
        payload = _get_json(url, {"Authorization": key})
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise SystemExit(
                "Pexels rate limit reached (200 requests/hour on the free tier).\n"
                "The pool already downloaded is cached, so re-running later "
                "resumes rather than starting over."
            )
        if exc.code == 401:
            raise SystemExit("Pexels rejected the API key (401). Check backend/.env.")
        raise
    out = []
    for photo in payload.get("photos", []):
        src = photo.get("src", {}).get("large") or photo.get("src", {}).get("original")
        if src:
            out.append({
                "src": src,
                "photographer": photo.get("photographer", ""),
                "page": photo.get("url", ""),
                "licence": "Pexels License",
            })
    return out


def search(source: str, key: str, query: str, count: int) -> "list[dict]":
    if source == "openverse":
        return _search_openverse(query, count)
    if source == "wikimedia":
        return _search_wikimedia(query, count)
    return _search_pexels(key, query, count)


def _download(url: str, path: str) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "columbia-market-seed"})
        with urllib.request.urlopen(req, timeout=60) as response:
            data = response.read()
    except Exception:
        return False
    with open(path, "wb") as handle:
        handle.write(data)
    return True


def build_pool(source: str, key: str, queries: "list[str]", per_query: int, credits: list) -> "dict[str, list[str]]":
    """Download up to ``per_query`` photos for each query. Cached between runs."""
    pool: "dict[str, list[str]]" = {}
    for i, query in enumerate(sorted(queries), 1):
        directory = os.path.join(POOL_DIR, _slug(query))
        os.makedirs(directory, exist_ok=True)
        existing = sorted(f for f in os.listdir(directory) if f.endswith(".jpg"))

        if len(existing) >= per_query:
            pool[query] = [os.path.join(directory, f) for f in existing[:per_query]]
            print("  [%2d/%d] %-32s cached (%d)" % (i, len(queries), query, len(existing)))
            continue

        photos = search(source, key, query, per_query)
        # Top up rather than only falling back on zero. Under the cc0/by/by-sa
        # licence filter some ordinary objects return one or two results, and a
        # single photo shared by 31 office-chair listings is worse than a mixed
        # pool: the grid reads as one item posted 31 times.
        if source == "openverse" and len(photos) < per_query:
            seen = {p["src"] for p in photos}
            for extra in _search_wikimedia(query, per_query - len(photos)):
                if extra["src"] not in seen:
                    photos.append(extra)
        saved = [os.path.join(directory, f) for f in existing]
        for n, photo in enumerate(photos):
            target = os.path.join(directory, "%02d.jpg" % n)
            if os.path.exists(target):
                continue
            if _download(photo["src"], target):
                saved.append(target)
                credits.append({
                    "query": query,
                    "file": os.path.relpath(target, REPO_ROOT),
                    "photographer": photo.get("photographer", ""),
                    "source_url": photo.get("page", ""),
                    "licence": photo.get("licence", ""),
                })
        pool[query] = sorted(set(saved))
        print("  [%2d/%d] %-32s %d photo(s)" % (i, len(queries), query, len(pool[query])))
    return pool


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="openverse",
                        choices=("openverse", "wikimedia", "pexels"),
                        help="openverse and wikimedia need no key")
    parser.add_argument("--fraction", type=float, default=1.0,
                        help="share of listings to render, 0-1. Use 0.1 for a sample.")
    parser.add_argument("--per-query", type=int, default=8,
                        help="photos to pool per search term")
    parser.add_argument("--out", default="frontend/public/photos")
    parser.add_argument("--photos-csv", default="data/listing_photos.csv")
    parser.add_argument("--queries-csv", default="data/photo_queries.csv")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    try:
        from PIL import Image
    except ImportError:
        raise SystemExit("Pillow is required: pip install Pillow")

    key = _api_key() if args.source == "pexels" else ""

    queries_by_listing = {}
    with open(args.queries_csv, encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            queries_by_listing[row["listing_id"]] = row["photo_query"]

    with open(args.photos_csv, encoding="utf-8") as handle:
        photo_rows = list(csv.DictReader(handle))

    # Take a deterministic slice of LISTINGS, not of photo rows, so a sampled
    # listing keeps its whole gallery rather than photo 3 of 5.
    listing_ids = sorted({r["listing_id"] for r in photo_rows})
    if args.fraction < 1.0:
        keep = set()
        for listing_id in listing_ids:
            h = int(hashlib.sha256(listing_id.encode()).hexdigest()[:8], 16)
            if (h % 1000) < args.fraction * 1000:
                keep.add(listing_id)
        photo_rows = [r for r in photo_rows if r["listing_id"] in keep]
        listing_ids = sorted(keep)

    wanted = sorted({queries_by_listing.get(i, "") for i in listing_ids} - {""})
    print("listings: %d   photo rows: %d   distinct queries: %d"
          % (len(listing_ids), len(photo_rows), len(wanted)))
    print("\nBuilding pool in data/photo_pool/ from %s (cached between runs)" % args.source)

    credits: list = []
    pool = build_pool(args.source, key, wanted, args.per_query, credits)

    if credits:
        write_header = not os.path.exists(CREDITS_CSV)
        with open(CREDITS_CSV, "a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=["query", "file", "photographer", "source_url", "licence"])
            if write_header:
                writer.writeheader()
            writer.writerows(credits)

    print("\nRendering into %s/" % args.out)
    rendered, fell_back = 0, 0
    by_listing = collections.defaultdict(list)
    for row in photo_rows:
        by_listing[row["listing_id"]].append(row)

    for listing_id, rows in by_listing.items():
        query = queries_by_listing.get(listing_id, "")
        candidates = pool.get(query, [])
        for row in sorted(rows, key=lambda r: int(r["position"])):
            position = int(row["position"])
            relative = row["url"].lstrip("/").split("/", 1)[1]
            target = os.path.join(args.out, relative)
            os.makedirs(os.path.dirname(target), exist_ok=True)

            if not candidates:
                fell_back += 1
                continue

            # Deterministic pick: the same listing and position always land on
            # the same source photo, and a gallery shows different ones.
            h = int(hashlib.sha256(("%s:%d" % (listing_id, position)).encode())
                    .hexdigest()[:8], 16)
            source = candidates[(h + position) % len(candidates)]

            with Image.open(source) as image:
                image = image.convert("RGB")
                # Cover-crop to 4:3 so nothing is letterboxed in the card.
                target_ratio = OUT_W / OUT_H
                w, h_px = image.size
                if w / h_px > target_ratio:
                    new_w = int(h_px * target_ratio)
                    box = ((w - new_w) // 2, 0, (w + new_w) // 2, h_px)
                else:
                    new_h = int(w / target_ratio)
                    box = (0, (h_px - new_h) // 2, w, (h_px + new_h) // 2)
                image.crop(box).resize((OUT_W, OUT_H), Image.LANCZOS).save(
                    target, "WEBP", quality=QUALITY)
            rendered += 1

    print("\nrendered %d photo(s)" % rendered)
    if fell_back:
        print("%d had no search results — run scripts/make_photos.py to fill those "
              "with the category glyph" % fell_back)
    if credits:
        print("credits appended to data/PHOTO_CREDITS.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
