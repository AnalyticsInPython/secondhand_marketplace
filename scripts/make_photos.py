#!/usr/bin/env python3
"""Regenerate the placeholder photos referenced by ``listing_photos.url``.

The images are *not* committed -- there are ~5,800 of them and they carry no
information. This script rebuilds them from the CSV, deterministically, so two
people running it get the same pictures.

    python3 scripts/make_photos.py                 # into ./photos
    python3 scripts/make_photos.py --out web/public/photos

Each photo is a soft vertical gradient in one of the ``01 · Foundations`` brand
tints, chosen from a hash of the listing id so a listing's photos are a coherent
set and the same listing always gets the same colour. The category name is drawn
in the corner the way the mockup's placeholder cards do.

Pillow is used when available (it produces the WebP the URLs name). Without it,
the script writes SVGs alongside and prints how to point at them instead -- the
generator does not depend on this running at all.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import sys

# The pastel card fills from docs/screens/91-foundations.png, as (top, bottom).
GRADIENTS = (
    ((0xC7, 0xD9, 0xF0), (0xA8, 0xC2, 0xE4)),   # brand blue
    ((0xE8, 0xD6, 0xB8), (0xD8, 0xBE, 0x92)),   # sand
    ((0xD5, 0xD8, 0xE6), (0xB9, 0xBF, 0xD4)),   # slate
    ((0xC9, 0xE0, 0xCE), (0xA6, 0xC9, 0xB0)),   # sage
    ((0xEE, 0xD2, 0xD2), (0xDE, 0xB0, 0xB0)),   # blush
    ((0xDC, 0xD2, 0xEA), (0xC0, 0xB0, 0xDC)),   # lilac
    ((0xDD, 0xDD, 0xDD), (0xBB, 0xBB, 0xBB)),   # neutral
)

WIDTH, HEIGHT = 800, 600


def _palette_for(listing_id: str, position: int):
    digest = hashlib.sha256(listing_id.encode()).digest()
    base = digest[0] % len(GRADIENTS)
    # Later photos of the same listing shift one step, so a gallery looks like a
    # set of shots rather than seven copies of one image.
    return GRADIENTS[(base + position) % len(GRADIENTS)]


def _write_svg(path, top, bottom, label):
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d">'
        '<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0%%" stop-color="rgb(%d,%d,%d)"/>'
        '<stop offset="100%%" stop-color="rgb(%d,%d,%d)"/>'
        '</linearGradient></defs>'
        '<rect width="100%%" height="100%%" fill="url(#g)"/>'
        '<text x="28" y="%d" font-family="Helvetica,Arial,sans-serif" '
        'font-size="20" letter-spacing="2" fill="rgba(20,32,52,0.55)">%s</text>'
        '</svg>'
    ) % (WIDTH, HEIGHT, top[0], top[1], top[2], bottom[0], bottom[1], bottom[2],
         HEIGHT - 28, label.upper())
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(svg)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--photos-csv", default="data/listing_photos.csv")
    parser.add_argument("--listings-csv", default="data/listings.csv")
    parser.add_argument("--out", default="photos")
    parser.add_argument("--limit", type=int, default=0,
                        help="only render the first N (useful for a quick look)")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    try:
        from PIL import Image, ImageDraw  # noqa: F401
        have_pillow = True
    except ImportError:
        have_pillow = False

    categories = {}
    with open(args.listings_csv, encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            categories[row["id"]] = row["category"]

    with open(args.photos_csv, encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if args.limit:
        rows = rows[: args.limit]

    written = 0
    for row in rows:
        listing_id = row["listing_id"]
        position = int(row["position"])
        top, bottom = _palette_for(listing_id, position)
        label = categories.get(listing_id, "item").replace("_", " ")

        # url is "photos/<listing_id>/<position>.webp"; strip the leading dir so
        # --out decides where the tree actually lands.
        relative = row["url"].split("/", 1)[1]
        target = os.path.join(args.out, relative)
        os.makedirs(os.path.dirname(target), exist_ok=True)

        if have_pillow:
            from PIL import Image, ImageDraw

            image = Image.new("RGB", (WIDTH, HEIGHT), top)
            draw = ImageDraw.Draw(image)
            for y in range(HEIGHT):
                t = y / float(HEIGHT - 1)
                draw.line(
                    [(0, y), (WIDTH, y)],
                    fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)),
                )
            draw.text((28, HEIGHT - 44), label.upper(), fill=(60, 76, 100))
            image.save(target, "WEBP", quality=80)
        else:
            _write_svg(os.path.splitext(target)[0] + ".svg", top, bottom, label)
        written += 1

    print("wrote %d placeholder%s to %s/"
          % (written, "" if have_pillow else " SVGs (Pillow not installed)", args.out))
    if not have_pillow:
        print("  install Pillow for the .webp files the URLs name:  pip install Pillow")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
