"""Item templates, price bands and description fragments.

This is the slow part of the generator and the part that decides whether the feed
reads as a real marketplace or as filler. UX_SPEC §9 fixes the category mix, the
condition skew and four of the eight price ranges; everything else here is ours.

Three rules the templates encode, none of which fall out of independent draws:

* **A title is a category's title.** Each template belongs to exactly one
  category (and, for furniture, one subcategory), so a textbook never gets a
  colour slot and a desk never gets an edition number.
* **Price follows the item, then the condition.** Each template carries its own
  band for a ``used_good`` example -- a used MALM desk is not priced from the same
  distribution as a used Aeron chair -- and the condition multiplier is applied on
  top, then clamped back into the category range from §9.
* **A description cannot contradict its condition.** The opening line is drawn
  from a pool keyed on condition, so a ``new`` item never mentions a scuff. This
  is the coupling that most obviously breaks in generated data.

Slot values are drawn from :data:`SLOTS`; a template may name any slot in it.
"""

from __future__ import annotations

from . import vocabularies as V

# ---------------------------------------------------------------------------
# Mix  (UX_SPEC §9)
# ---------------------------------------------------------------------------

# "furniture ~30%, textbooks ~20%, electronics ~15%, kitchen ~12%,
#  clothing ~10%, rest split"
CATEGORY_WEIGHTS: "dict[str, float]" = {
    "furniture": 30.0,
    "textbooks": 20.0,
    "electronics": 15.0,
    "kitchen_home": 12.0,
    "clothing": 10.0,
    "bikes_transport": 6.0,
    "sports": 4.0,
    "free_stuff": 3.0,
}

# "Condition skews used_good (~45%) and like_new (~30%)". The remaining 25% is
# ours to split, and it is split per category rather than globally: a textbook is
# far more likely to be shrink-wrapped than a sofa is.
CONDITION_WEIGHTS: "dict[str, dict[str, float]]" = {
    #                      new  like_new  used_good  used_fair
    "furniture":       {"new":  3, "like_new": 24, "used_good": 51, "used_fair": 22},
    "textbooks":       {"new": 14, "like_new": 36, "used_good": 41, "used_fair":  9},
    "electronics":     {"new":  9, "like_new": 34, "used_good": 46, "used_fair": 11},
    "kitchen_home":    {"new":  8, "like_new": 30, "used_good": 47, "used_fair": 15},
    "clothing":        {"new":  7, "like_new": 35, "used_good": 44, "used_fair": 14},
    "bikes_transport": {"new":  3, "like_new": 22, "used_good": 51, "used_fair": 24},
    "sports":          {"new":  6, "like_new": 31, "used_good": 47, "used_fair": 16},
    "free_stuff":      {"new":  2, "like_new": 16, "used_good": 50, "used_fair": 32},
}

# §9 gives four of these outright: "Furniture $20-400, textbooks $10-90,
# electronics $30-500, kitchen $10-120". The other four are ours, chosen to sit
# sensibly against them. Prices are clamped into these bands after the condition
# multiplier is applied.
CATEGORY_PRICE_RANGE: "dict[str, tuple[int, int]]" = {
    "furniture": (20, 400),
    "textbooks": (10, 90),
    "electronics": (30, 500),
    "kitchen_home": (10, 120),
    "clothing": (10, 250),
    "bikes_transport": (20, 400),
    "sports": (10, 200),
    "free_stuff": (0, 0),
}

# Applied to a template's used_good band. A "new" item is worth roughly twice a
# well-used one; "used_fair" takes a real haircut.
CONDITION_PRICE_MULTIPLIER: "dict[str, float]" = {
    "new": 1.90,
    "like_new": 1.45,
    "used_good": 1.00,
    "used_fair": 0.70,
}

# free_stuff is free by definition -- it is the category for things with no
# resale value. Everything else has this chance of being given away instead,
# which lands the overall free share near §9's "about 8%".
FREE_GIVEAWAY_RATE = 0.052

# Not in the spec; the Upload screen has the toggle and nothing constrains it.
NEGOTIABLE_RATE = 0.40


# ---------------------------------------------------------------------------
# Slot pools
# ---------------------------------------------------------------------------

SLOTS: "dict[str, tuple[str, ...]]" = {
    "colour": ("white", "black", "grey", "oak", "walnut", "birch", "navy", "beige"),
    "wood": ("white", "oak", "walnut", "birch", "black-brown"),
    "size_cm": ("120×60", "140×65", "160×80", "100×50", "180×80"),
    "ikea_desk": ("MALM", "MICKE", "LINNMON", "BEKANT", "LAGKAPTEN"),
    "ikea_shelf": ("KALLAX", "BILLY", "IVAR", "HYLLIS", "BESTÅ"),
    "ikea_bed": ("MALM", "NEIDEN", "HEMNES", "SLATTUM"),
    "chair_brand": ("Herman Miller Aeron", "Steelcase Leap", "IKEA MARKUS",
                    "Autonomous ErgoChair", "HON Ignition"),
    "chair_size": ("size A", "size B", "size C"),
    "mattress": ("twin XL", "full", "queen"),
    "sofa": ("2-seat", "3-seat", "loveseat", "futon"),
    "subject": ("Corporate Finance", "Managerial Economics", "Organic Chemistry",
                "Linear Algebra", "Microeconomics", "Data Structures",
                "Financial Accounting", "Marketing Strategy", "Statistical Inference",
                "Constitutional Law", "Epidemiology", "Machine Learning"),
    "edition": ("5th", "6th", "7th", "8th", "9th", "12th", "international"),
    "publisher": ("Berk", "Pearson", "McGraw-Hill", "Wiley", "Cengage", "Norton"),
    "laptop": ("MacBook Air M1", "MacBook Pro 13\"", "ThinkPad X1", "Dell XPS 13",
               "Surface Laptop 4"),
    "monitor": ("Dell 24\"", "LG 27\" 4K", "Samsung 32\" curved", "ASUS 24\" 144Hz"),
    "audio": ("Sony WH-1000XM4", "AirPods Pro", "Bose QC35", "Beats Studio3"),
    "ipad": ("iPad Air", "iPad 9th gen", "iPad Pro 11\""),
    "ereader": ("Kindle Paperwhite", "Kobo Clara", "reMarkable 2"),
    "kitchen_small": ("Cuckoo 6-cup rice cooker", "Instant Pot Duo 6qt",
                      "Nespresso Essenza", "Hamilton Beach blender",
                      "Cuisinart toaster oven", "Zojirushi kettle"),
    "cookware": ("10-piece pot and pan set", "cast iron skillet",
                 "non-stick wok", "12-piece dinnerware set"),
    "appliance": ("mini fridge", "microwave", "air purifier", "standing fan",
                  "humidifier", "space heater"),
    "outerwear": ("Canada Goose parka", "Uniqlo down jacket", "Patagonia fleece",
                  "North Face puffer", "wool overcoat"),
    "clothing_size": ("size XS", "size S", "size M", "size L", "size XL"),
    "shoes": ("Nike Air Force 1", "Doc Martens 1460", "New Balance 990",
              "Blundstone 550"),
    "bike": ("Schwinn hybrid", "Trek FX 2", "Citi-style commuter", "Brompton folding",
             "Cannondale Quick 4"),
    "bike_size": ("S frame", "M frame", "L frame"),
    "micro": ("Xiaomi M365 scooter", "Segway Ninebot scooter", "Razor kick scooter"),
    "sports_gear": ("Yoga mat + blocks", "Adjustable dumbbell pair",
                    "Wilson tennis racket", "Spalding basketball",
                    "Rollerblades", "Resistance band set"),
    "free_item": ("Moving boxes", "Desk lamp", "Full-length mirror", "Drying rack",
                  "Houseplant (pothos)", "Shoe rack", "Curtain rod set",
                  "Assorted kitchen utensils", "Textbook bundle"),
    # Plain place names only. The logistics lines supply their own preposition,
    # so a value like "my building lobby" produced "at the my building lobby lobby".
    "reason_place": ("Morningside Heights", "campus", "116th & Broadway",
                     "Amsterdam Ave", "the Columbia gates"),
}


# ---------------------------------------------------------------------------
# Templates
#
# (subcategory, title, used_good price band)
# ---------------------------------------------------------------------------

TEMPLATES: "dict[str, tuple[tuple[str | None, str, tuple[int, int]], ...]]" = {
    "furniture": (
        ("desks", "IKEA {ikea_desk} desk {size_cm}, {wood}", (35, 110)),
        ("desks", "Standing desk, electric, {size_cm}", (90, 260)),
        ("desks", "Small writing desk, {wood}", (30, 90)),
        ("chairs", "{chair_brand}, {chair_size}", (60, 340)),
        ("chairs", "Desk chair, {colour}, adjustable", (25, 90)),
        ("chairs", "Pair of dining chairs, {wood}", (30, 100)),
        ("beds_mattresses", "{mattress} mattress + metal frame", (60, 190)),
        ("beds_mattresses", "IKEA {ikea_bed} bed frame, {mattress}", (50, 160)),
        ("beds_mattresses", "Memory foam mattress topper, {mattress}", (20, 70)),
        ("storage_shelving", "IKEA {ikea_shelf} shelf unit, {wood}", (30, 110)),
        ("storage_shelving", "3-drawer dresser, {colour}", (40, 130)),
        ("storage_shelving", "Rolling clothes rack + hangers", (20, 60)),
        ("sofas_tables", "{sofa} sofa, {colour}", (70, 320)),
        ("sofas_tables", "Coffee table, {wood}", (30, 110)),
        ("sofas_tables", "Folding dining table + 2 chairs", (45, 140)),
    ),
    "textbooks": (
        (None, "{subject} ({publisher}) {edition} ed.", (18, 70)),
        (None, "{subject} {edition} ed. + solutions manual", (25, 85)),
        (None, "{subject} — full course bundle", (30, 88)),
        (None, "{subject} reader, spiral bound", (12, 40)),
        (None, "{subject} ({publisher}), international edition", (14, 55)),
    ),
    "electronics": (
        (None, "{laptop}, 8GB/256GB", (180, 480)),
        (None, "{monitor} monitor + stand", (60, 220)),
        (None, "{audio} headphones", (60, 200)),
        # Split from one "{tablet}" template: a Kindle and an iPad Air cannot
        # share a price band without one of them coming out absurd.
        (None, "{ipad}, wifi", (150, 320)),
        (None, "{ereader}, wifi", (55, 150)),
        (None, "Mechanical keyboard, {colour}", (35, 120)),
        (None, "Logitech mouse + desk mat", (30, 70)),
        (None, "Dyson V8 cordless vacuum, all heads", (110, 300)),
        (None, "Anker power strip + USB-C hub", (30, 60)),
    ),
    "kitchen_home": (
        (None, "{kitchen_small}", (20, 95)),
        (None, "{cookware}", (18, 80)),
        (None, "{appliance}, works fine", (25, 110)),
        (None, "Water filter pitcher + 2 filters", (10, 30)),
        (None, "Set of 4 mugs and 4 glasses", (10, 28)),
    ),
    "clothing": (
        (None, "{outerwear}, {clothing_size}", (60, 240)),
        (None, "{shoes}, US 9", (35, 130)),
        (None, "Winter boots, {clothing_size}, waterproof", (30, 110)),
        (None, "Suit, {clothing_size}, tailored once", (60, 220)),
        (None, "Wool scarf and glove set", (10, 40)),
    ),
    "bikes_transport": (
        (None, "{bike}, {bike_size}", (90, 380)),
        (None, "{micro}", (80, 300)),
        (None, "Bike lock, lights and helmet bundle", (25, 70)),
        (None, "Folding shopping cart", (20, 45)),
        (None, "{bike}, {bike_size}, recently serviced", (110, 390)),
        (None, "Bike rack and floor pump", (20, 55)),
    ),
    "sports": (
        (None, "{sports_gear}", (12, 130)),
        (None, "Weight bench, folding", (40, 160)),
        (None, "Ski jacket and poles, {clothing_size}", (45, 190)),
    ),
    "free_stuff": (
        (None, "{free_item} — free to a good home", (0, 0)),
        (None, "{free_item}, collect this week", (0, 0)),
    ),
}


# ---------------------------------------------------------------------------
# Description fragments
# ---------------------------------------------------------------------------

# Keyed on condition. This is the coupling that keeps a "New" item from
# apologising for a scuff.
_CONDITION_LINES: "dict[str, tuple[str, ...]]" = {
    "new": (
        "Brand new, still sealed — I ordered the wrong size and the return window closed.",
        "Never used. Bought it in September and it has sat in the box since.",
        "Unopened, tags still on. Bought two by mistake.",
    ),
    "like_new": (
        "Used it for about a month and it looks the same as the day I got it.",
        "Barely touched — I moved into a furnished place two weeks later.",
        "Genuinely like new. No marks, everything works exactly as it should.",
    ),
    "used_good": (
        "Solid, no wobble — one small scuff on the back left that you cannot see once it is against a wall.",
        "Used for two semesters and it has held up well. Nothing broken, a bit of normal wear.",
        "Everything works. A couple of light marks from moving, nothing structural.",
        "Good condition overall — some honest wear, but nothing that affects using it.",
    ),
    "used_fair": (
        "Well used and it shows — a few dents and one sticky drawer, but it does its job.",
        "Fair condition, priced to reflect it. Works fine, looks lived in.",
        "Some visible wear and a small chip on one corner. Happy to send more photos.",
    ),
}

_REASON_LINES: "tuple[str, ...]" = (
    "I am graduating in May and everything has to go before I move out.",
    "Moving to a smaller place at the end of the month, so it needs a new home.",
    "Upgraded to a bigger one and have no room for both.",
    "Heading back home after this semester and cannot take it with me.",
    "Finished the course, so I no longer need it.",
    "Bought it for a sublet that ended early.",
)

_LOGISTICS_LINES: "tuple[str, ...]" = (
    "Pickup only, 3rd floor with an elevator — I can help carry it down to the street.",
    "Easy pickup near {reason_place}, evenings and weekends work best.",
    "Cash or Venmo. I can meet near {reason_place} any afternoon.",
    "Happy to hold it for a day if you need to arrange a car.",
    "Collect from {reason_place}; message me and we will find a time.",
)

_EXTRA_LINES: "tuple[str, ...]" = (
    "Original box and instructions included.",
    "I will throw in the matching lamp for free.",
    "Open to a small discount if you take it today.",
    "Can send more photos of any detail you want to see.",
)

# §9 does not constrain this; ~15% empty exercises the no-description layout.
DESCRIPTION_PRESENT_RATE = 0.85
EXTRA_LINE_RATE = 0.35


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def _fill(rng, template: str) -> str:
    """Resolve every ``{slot}`` in a template from :data:`SLOTS`."""
    out = template
    while "{" in out:
        start = out.index("{")
        end = out.index("}", start)
        slot = out[start + 1:end]
        out = out[:start] + rng.choice(SLOTS[slot]) + out[end + 1:]
    return out


def _sentence_case(text: str) -> str:
    """Capitalise the first letter only.

    Templates that open with a slot ("{cookware}", "{outerwear}, {clothing_size}")
    otherwise produce "cast iron skillet" as a title. Brand casing further along
    the string is left alone -- "IKEA MALM" and 'Dell 24"' must survive.
    """
    return text[:1].upper() + text[1:] if text else text


def draw_item(rng, category: str) -> "tuple[str | None, str, tuple[int, int]]":
    """Pick a template for a category and render its title.

    Returns ``(subcategory, title, used_good_price_band)``. The title is retried
    if a slot combination overruns §4.2's 60-character limit, which a couple of
    the longer brand/size pairings can do.
    """
    templates = TEMPLATES[category]
    for _ in range(24):
        subcategory, pattern, band = rng.choice(templates)
        title = _sentence_case(_fill(rng, pattern))
        if len(title) <= V.TITLE_MAX_CHARS:
            return subcategory, title, band
    # Every retry overran: fall back to a truncation on a word boundary rather
    # than emitting an invalid row.
    return subcategory, title[:V.TITLE_MAX_CHARS].rsplit(" ", 1)[0], band


def draw_description(rng, condition: str) -> "str | None":
    """A 2-4 sentence description whose first line agrees with the condition."""
    if rng.random() > DESCRIPTION_PRESENT_RATE:
        return None
    parts = [
        rng.choice(_CONDITION_LINES[condition]),
        rng.choice(_REASON_LINES),
        _fill(rng, rng.choice(_LOGISTICS_LINES)),
    ]
    if rng.random() < EXTRA_LINE_RATE:
        parts.append(rng.choice(_EXTRA_LINES))
    text = " ".join(parts)
    return text[:V.DESCRIPTION_MAX_CHARS]


def _round_price(dollars: float) -> int:
    """Psychological rounding — nobody lists a desk at $63."""
    if dollars < 20:
        return int(round(dollars))
    if dollars < 100:
        return int(round(dollars / 5.0) * 5)
    return int(round(dollars / 10.0) * 10)


def draw_price_cents(rng, category: str, condition: str, band: "tuple[int, int]") -> int:
    """Log-normal within the template's band, adjusted for condition, clamped to §9."""
    low, high = band
    if high <= 0:
        return 0
    # Log-uniform through the band gives a right-skewed spread without needing to
    # fit a variance per template.
    import math

    draw = math.exp(rng.uniform(math.log(low), math.log(high)))
    draw *= CONDITION_PRICE_MULTIPLIER[condition]
    # Clamp back towards the template's own band before the category one. Without
    # this, a "new" multiplier on the top of a band prices a Kindle at $310 --
    # inside §9's electronics range, but not a price anyone would write.
    draw = max(low * 0.55, min(high * 1.20, draw))
    cat_low, cat_high = CATEGORY_PRICE_RANGE[category]
    draw = max(cat_low, min(cat_high, draw))
    return _round_price(draw) * 100


def _check() -> None:
    assert set(CATEGORY_WEIGHTS) == set(V.CATEGORIES), "category weights are incomplete"
    assert set(CONDITION_WEIGHTS) == set(V.CATEGORIES)
    assert set(CATEGORY_PRICE_RANGE) == set(V.CATEGORIES)
    assert set(TEMPLATES) == set(V.CATEGORIES), "every category needs templates"
    assert set(CONDITION_PRICE_MULTIPLIER) == set(V.CONDITIONS)
    assert set(_CONDITION_LINES) == set(V.CONDITIONS)

    for category, weights in CONDITION_WEIGHTS.items():
        assert set(weights) == set(V.CONDITIONS), "%s: condition weights incomplete" % category

    for category, templates in TEMPLATES.items():
        assert templates, "%s has no templates" % category
        low, high = CATEGORY_PRICE_RANGE[category]
        for subcategory, pattern, band in templates:
            assert V.is_valid_subcategory(category, subcategory), (
                "%s: subcategory %r does not belong to it" % (category, subcategory)
            )
            # Two-level categories must always name a subcategory; single-level
            # ones must never do.
            if V.SUBCATEGORIES[category]:
                assert subcategory is not None, "%s template lacks a subcategory" % category
            else:
                assert subcategory is None, "%s is single-level" % category
            assert band[0] <= band[1], "%s: inverted price band" % category
            assert low <= band[0] and band[1] <= high, (
                "%s: band %s escapes the §9 range %s" % (category, band, (low, high))
            )
            # Every slot the template names must exist.
            for slot in _slots_in(pattern):
                assert slot in SLOTS, "%s: unknown slot {%s}" % (category, slot)

    for pattern in _LOGISTICS_LINES:
        for slot in _slots_in(pattern):
            assert slot in SLOTS, "logistics line names unknown slot {%s}" % slot


def _slots_in(pattern: str) -> "list[str]":
    out, rest = [], pattern
    while "{" in rest:
        start = rest.index("{")
        end = rest.index("}", start)
        out.append(rest[start + 1:end])
        rest = rest[end + 1:]
    return out


_check()


if __name__ == "__main__":
    import random

    rng = random.Random(7)
    total_templates = sum(len(t) for t in TEMPLATES.values())
    print("Catalog — %d templates across %d categories\n"
          % (total_templates, len(TEMPLATES)))
    for category in V.CATEGORIES:
        print("%s  (weight %.0f%%, §9 range $%d-%d)"
              % (V.CATEGORY_LABELS[category], CATEGORY_WEIGHTS[category],
                 *CATEGORY_PRICE_RANGE[category]))
        for _ in range(4):
            sub, title, band = draw_item(rng, category)
            cond = rng.choice(V.CONDITIONS)
            cents = draw_price_cents(rng, category, cond, band)
            tag = "/%s" % sub if sub else ""
            print("    %-58s %6s  %-10s%s"
                  % (title, "$%d" % (cents // 100), cond, tag))
        print()
    print("Sample description (used_good):\n  %s"
          % draw_description(rng, "used_good"))
