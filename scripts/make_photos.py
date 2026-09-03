#!/usr/bin/env python3
"""Render the placeholder photos referenced by ``listing_photos.url``.

The images are *not* committed — there are ~5,800 of them and they carry no
information. This script rebuilds them from the CSV, deterministically, so two
people running it get the same pictures.

    python3 scripts/make_photos.py --out frontend/public/photos

Each photo is a 135° gradient in one of the ``01 · Foundations`` tints — the same
angle and palette as the ``.photo-placeholder`` rule in ``frontend/app/globals.css``,
so a missing file degrades to something that looks deliberate rather than broken.
The colour comes from a hash of the listing id, so a listing's gallery is a
coherent set and the same listing always gets the same colour; later positions
step through the palette so a five-photo gallery reads as five shots rather than
five copies.

A simple line drawing of the category sits in the middle — a book, a desk, a
bicycle. Deliberately *not* text: the feed card already draws the category as an
overline and the title underneath it, so baking either into the image renders it
twice, overlapping. These are honest placeholders, not fake photographs of things
that do not exist.

Pillow is required for the WebP files the URLs name. Without it the script writes
SVGs beside them and says so.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import sys

# The pastel card fills from docs/screens/91-foundations.png, as (from, to).
# Matched to the --ph-from / --ph-to custom properties in globals.css.
GRADIENTS = (
    ((0xDC, 0xE9, 0xF5), (0x9F, 0xC2, 0xE0)),   # brand blue — the CSS default
    ((0xEE, 0xDF, 0xC4), (0xD8, 0xBE, 0x92)),   # sand
    ((0xDD, 0xE0, 0xEC), (0xB9, 0xBF, 0xD4)),   # slate
    ((0xD6, 0xE8, 0xDA), (0xA6, 0xC9, 0xB0)),   # sage
    ((0xF4, 0xDD, 0xDD), (0xDE, 0xB0, 0xB0)),   # blush
    ((0xE4, 0xDC, 0xEF), (0xC0, 0xB0, 0xDC)),   # lilac
    ((0xE6, 0xE6, 0xE6), (0xBB, 0xBB, 0xBB)),   # neutral
)

WIDTH, HEIGHT = 800, 600
QUALITY = 78

# Glyph ink: color/text/primary at low alpha, so the drawing reads as a watermark
# on every one of the seven tints rather than fighting the lighter ones.
GLYPH_INK = (0x11, 0x19, 0x27, 64)
STROKE = 7
GLYPH_BOX = 300  # the square the drawing is fitted into, centred on the canvas


def _palette_for(listing_id: str, position: int):
    digest = hashlib.sha256(listing_id.encode()).digest()
    return GRADIENTS[(digest[0] + position) % len(GRADIENTS)]


def _gradient(top, bottom):
    """A 135° linear gradient, the same angle globals.css uses.

    Computed on a small grid and resampled — smooth to the eye, and roughly two
    orders of magnitude faster than per-pixel work at full size.
    """
    from PIL import Image

    small_w, small_h = 96, 72
    base = Image.new("RGB", (small_w, small_h))
    pixels = base.load()
    for y in range(small_h):
        for x in range(small_w):
            t = (x / (small_w - 1) + y / (small_h - 1)) / 2.0
            pixels[x, y] = tuple(
                int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)
            )
    return base.resize((WIDTH, HEIGHT), Image.LANCZOS)


# --------------------------------------------------------------------------
# Category glyphs
#
# Each takes a drawing context and a square (x, y, size) and draws inside it.
# Primitives on purpose: no font dependency, no asset files, and it renders
# identically on every machine.
# --------------------------------------------------------------------------


def _book(d, x, y, s):
    d.line([(x + s * 0.5, y + s * 0.18), (x + s * 0.5, y + s * 0.86)], GLYPH_INK, STROKE)
    for side in (-1, 1):
        cx = x + s * 0.5
        outer = cx + side * s * 0.42
        d.line([(cx, y + s * 0.18), (outer, y + s * 0.28)], GLYPH_INK, STROKE)
        d.line([(outer, y + s * 0.28), (outer, y + s * 0.80)], GLYPH_INK, STROKE)
        d.line([(cx, y + s * 0.86), (outer, y + s * 0.80)], GLYPH_INK, STROKE)


def _desk(d, x, y, s):
    d.line([(x + s * 0.06, y + s * 0.36), (x + s * 0.94, y + s * 0.36)], GLYPH_INK, STROKE)
    d.line([(x + s * 0.16, y + s * 0.36), (x + s * 0.16, y + s * 0.84)], GLYPH_INK, STROKE)
    d.line([(x + s * 0.84, y + s * 0.36), (x + s * 0.84, y + s * 0.84)], GLYPH_INK, STROKE)
    d.rectangle([x + s * 0.28, y + s * 0.44, x + s * 0.62, y + s * 0.60],
                outline=GLYPH_INK, width=STROKE - 2)


def _laptop(d, x, y, s):
    d.rectangle([x + s * 0.16, y + s * 0.22, x + s * 0.84, y + s * 0.64],
                outline=GLYPH_INK, width=STROKE)
    d.line([(x + s * 0.04, y + s * 0.78), (x + s * 0.96, y + s * 0.78)], GLYPH_INK, STROKE)
    d.line([(x + s * 0.16, y + s * 0.64), (x + s * 0.04, y + s * 0.78)], GLYPH_INK, STROKE)
    d.line([(x + s * 0.84, y + s * 0.64), (x + s * 0.96, y + s * 0.78)], GLYPH_INK, STROKE)


def _mug(d, x, y, s):
    d.rectangle([x + s * 0.20, y + s * 0.34, x + s * 0.64, y + s * 0.82],
                outline=GLYPH_INK, width=STROKE)
    d.arc([x + s * 0.58, y + s * 0.44, x + s * 0.88, y + s * 0.68], -90, 90,
          GLYPH_INK, STROKE)
    for i in range(2):
        sx = x + s * (0.32 + i * 0.18)
        d.line([(sx, y + s * 0.24), (sx, y + s * 0.10)], GLYPH_INK, STROKE - 2)


def _shirt(d, x, y, s):
    d.polygon([
        (x + s * 0.32, y + s * 0.22), (x + s * 0.44, y + s * 0.16),
        (x + s * 0.56, y + s * 0.16), (x + s * 0.68, y + s * 0.22),
        (x + s * 0.90, y + s * 0.38), (x + s * 0.78, y + s * 0.50),
        (x + s * 0.72, y + s * 0.44), (x + s * 0.72, y + s * 0.84),
        (x + s * 0.28, y + s * 0.84), (x + s * 0.28, y + s * 0.44),
        (x + s * 0.22, y + s * 0.50), (x + s * 0.10, y + s * 0.38),
    ], outline=GLYPH_INK, width=STROKE)


def _bike(d, x, y, s):
    r = s * 0.20
    for cx in (x + s * 0.24, x + s * 0.76):
        d.ellipse([cx - r, y + s * 0.54 - r, cx + r, y + s * 0.54 + r],
                  outline=GLYPH_INK, width=STROKE)
    d.line([(x + s * 0.24, y + s * 0.54), (x + s * 0.44, y + s * 0.30)], GLYPH_INK, STROKE)
    d.line([(x + s * 0.44, y + s * 0.30), (x + s * 0.64, y + s * 0.30)], GLYPH_INK, STROKE)
    d.line([(x + s * 0.64, y + s * 0.30), (x + s * 0.76, y + s * 0.54)], GLYPH_INK, STROKE)
    d.line([(x + s * 0.44, y + s * 0.30), (x + s * 0.52, y + s * 0.54)], GLYPH_INK, STROKE)
    d.line([(x + s * 0.52, y + s * 0.54), (x + s * 0.76, y + s * 0.54)], GLYPH_INK, STROKE)


def _dumbbell(d, x, y, s):
    d.line([(x + s * 0.22, y + s * 0.50), (x + s * 0.78, y + s * 0.50)], GLYPH_INK, STROKE)
    for cx in (x + s * 0.18, x + s * 0.82):
        d.line([(cx, y + s * 0.30), (cx, y + s * 0.70)], GLYPH_INK, STROKE + 5)
    for cx in (x + s * 0.06, x + s * 0.94):
        d.line([(cx, y + s * 0.38), (cx, y + s * 0.62)], GLYPH_INK, STROKE)


def _gift(d, x, y, s):
    d.rectangle([x + s * 0.12, y + s * 0.40, x + s * 0.88, y + s * 0.86],
                outline=GLYPH_INK, width=STROKE)
    d.line([(x + s * 0.50, y + s * 0.40), (x + s * 0.50, y + s * 0.86)], GLYPH_INK, STROKE)
    d.line([(x + s * 0.12, y + s * 0.54), (x + s * 0.88, y + s * 0.54)], GLYPH_INK, STROKE)
    d.arc([x + s * 0.22, y + s * 0.18, x + s * 0.52, y + s * 0.44], 0, 180,
          GLYPH_INK, STROKE)
    d.arc([x + s * 0.48, y + s * 0.18, x + s * 0.78, y + s * 0.44], 0, 180,
          GLYPH_INK, STROKE)


GLYPHS = {
    "furniture": _desk,
    "textbooks": _book,
    "electronics": _laptop,
    "kitchen_home": _mug,
    "clothing": _shirt,
    "bikes_transport": _bike,
    "sports": _dumbbell,
    "free_stuff": _gift,
}


def _glyph_layer(category):
    """The category drawing, once, as a transparent layer to composite onto a base."""
    from PIL import Image, ImageDraw

    layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    x = (WIDTH - GLYPH_BOX) / 2
    y = (HEIGHT - GLYPH_BOX) / 2
    GLYPHS.get(category, _gift)(draw, x, y, GLYPH_BOX)
    return layer


def _write_svg(path, top, bottom, label):
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d">'
        '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0%%" stop-color="rgb(%d,%d,%d)"/>'
        '<stop offset="100%%" stop-color="rgb(%d,%d,%d)"/>'
        '</linearGradient></defs>'
        '<rect width="100%%" height="100%%" fill="url(#g)"/>'
        '<text x="30" y="%d" font-family="Helvetica,Arial,sans-serif" '
        'font-size="21" letter-spacing="2" fill="rgba(42,58,82,0.62)">%s</text>'
        '</svg>'
    ) % (WIDTH, HEIGHT, top[0], top[1], top[2], bottom[0], bottom[1], bottom[2],
         HEIGHT - 40, label.upper())
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(svg)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--photos-csv", default="data/listing_photos.csv")
    parser.add_argument("--listings-csv", default="data/listings.csv")
    parser.add_argument("--out", default="frontend/public/photos")
    parser.add_argument("--limit", type=int, default=0,
                        help="only render the first N (useful for a quick look)")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    try:
        from PIL import Image
        have_pillow = True
    except ImportError:
        have_pillow = False

    listings = {}
    with open(args.listings_csv, encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            listings[row["id"]] = (row["category"], row["title"])

    with open(args.photos_csv, encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if args.limit:
        rows = rows[: args.limit]

    if have_pillow:
        # One base per palette entry and one layer per category, both reused
        # across every photo that wants them: 7 gradients and 8 glyphs drawn
        # once each, rather than 5,849 drawings.
        bases = [_gradient(top, bottom) for top, bottom in GRADIENTS]
        layers = {c: _glyph_layer(c) for c in GLYPHS}

    written = 0
    for row in rows:
        listing_id = row["listing_id"]
        position = int(row["position"])
        top, bottom = _palette_for(listing_id, position)
        category, _title = listings.get(listing_id, ("free_stuff", ""))
        label = category.replace("_", " ")

        # url is "/photos/<listing_id>/<position>.webp" — root-relative so it
        # resolves the same on /listings/<id> as on /. Strip the leading slash
        # and the "photos" segment so --out decides where the tree lands.
        relative = row["url"].lstrip("/").split("/", 1)[1]
        target = os.path.join(args.out, relative)
        os.makedirs(os.path.dirname(target), exist_ok=True)

        if have_pillow:
            image = bases[GRADIENTS.index((top, bottom))].convert("RGBA")
            image = Image.alpha_composite(image, layers[category])
            image.convert("RGB").save(target, "WEBP", quality=QUALITY)
        else:
            _write_svg(os.path.splitext(target)[0] + ".svg", top, bottom, label)
        written += 1
        if written % 1000 == 0:
            print("  %d / %d" % (written, len(rows)))

    print("wrote %d placeholder%s to %s/"
          % (written, "" if have_pillow else " SVGs (Pillow not installed)", args.out))
    if not have_pillow:
        print("  install Pillow for the .webp files the URLs name:  pip install Pillow")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
