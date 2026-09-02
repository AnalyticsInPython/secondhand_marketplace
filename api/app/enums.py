"""The fixed vocabularies from the build spec, section 2.

Every one of these mirrors a Postgres ENUM of the same name. They are fixed on
purpose: the four matching fields are compared with `=` in the feed query, so a
free-text value anywhere here silently degrades every filter in the product.

Changing a vocabulary means one migration line and a change here. Keep the two
in step.
"""

import enum


class College(str, enum.Enum):
    CC = "cc"
    SEAS = "seas"
    GS = "gs"
    CBS = "cbs"
    SIPA = "sipa"
    TC = "tc"
    LAW = "law"
    GSAS = "gsas"
    JOURNALISM = "journalism"
    MAILMAN = "mailman"
    SPS = "sps"
    GSAPP = "gsapp"
    OTHER = "other"


class Grade(str, enum.Enum):
    FRESHMAN = "freshman"
    SOPHOMORE = "sophomore"
    JUNIOR = "junior"
    SENIOR = "senior"
    MASTERS = "masters"
    PHD = "phd"
    ALUMNI = "alumni"


class Location(str, enum.Enum):
    MORNINGSIDE = "morningside"
    MANHATTANVILLE = "manhattanville"
    UWS = "uws"
    UES = "ues"
    HARLEM = "harlem"
    WASHINGTON_HEIGHTS = "washington_heights"
    DOWNTOWN = "downtown"
    BROOKLYN = "brooklyn"
    QUEENS = "queens"
    OTHER = "other"


class Category(str, enum.Enum):
    FURNITURE = "furniture"
    APPLIANCES = "appliances"
    ELECTRONICS = "electronics"
    TEXTBOOKS = "textbooks"
    CLOTHING = "clothing"
    KITCHEN = "kitchen"
    DECOR = "decor"
    SPORTS = "sports"
    TICKETS = "tickets"
    OTHER = "other"


class ItemCondition(str, enum.Enum):
    USED = "used"
    UNUSED = "unused"


class ListingStatus(str, enum.Enum):
    ACTIVE = "active"
    SOLD = "sold"
    DELISTED = "delisted"


class EventType(str, enum.Enum):
    SESSION_START = "session_start"
    FEED_VIEW = "feed_view"
    FILTER_TOGGLE = "filter_toggle"
    LISTING_VIEW = "listing_view"
    CONTACT_CLICK = "contact_click"
    LISTING_POSTED = "listing_posted"
    LISTING_EDITED = "listing_edited"
    LISTING_SOLD = "listing_sold"


# Which college an email subdomain proves. Used to prefill the dropdown at
# onboarding, where it is unambiguous; the student can still change it.
#
# Two of the four allowed domains prove nothing on their own and are absent
# here on purpose:
#   columbia.edu       every school issues these
#   cumc.columbia.edu  covers VP&S, Mailman, Nursing and Dental alike
# Those members pick their school themselves.
SUBDOMAIN_TO_COLLEGE = {
    "gsb.columbia.edu": College.CBS,
    "tc.columbia.edu": College.TC,
}
