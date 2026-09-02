"""Enumerations from UX_SPEC.md §4.5.

The *values* are contractual — the frontend copy and the seed data both depend
on them. `label()` is the display string used in the UI; keep the two in sync.
"""

from enum import StrEnum


class Category(StrEnum):
    FURNITURE = "furniture"
    TEXTBOOKS = "textbooks"
    ELECTRONICS = "electronics"
    KITCHEN_HOME = "kitchen_home"
    CLOTHING = "clothing"
    BIKES_TRANSPORT = "bikes_transport"
    SPORTS = "sports"
    FREE_STUFF = "free_stuff"

    def label(self) -> str:
        return CATEGORY_LABELS[self]


CATEGORY_LABELS = {
    Category.FURNITURE: "Furniture",
    Category.TEXTBOOKS: "Textbooks",
    Category.ELECTRONICS: "Electronics",
    Category.KITCHEN_HOME: "Kitchen & home",
    Category.CLOTHING: "Clothing",
    Category.BIKES_TRANSPORT: "Bikes & transport",
    Category.SPORTS: "Sports",
    Category.FREE_STUFF: "Free stuff",
}

# Only furniture is two-level for now (UX_SPEC.md §4.5).
SUBCATEGORIES: dict[Category, list[str]] = {
    Category.FURNITURE: [
        "desks",
        "chairs",
        "beds_mattresses",
        "storage_shelving",
        "sofas_tables",
    ],
}

SUBCATEGORY_LABELS = {
    "desks": "Desks",
    "chairs": "Chairs",
    "beds_mattresses": "Beds & mattresses",
    "storage_shelving": "Storage & shelving",
    "sofas_tables": "Sofas & tables",
}


class Condition(StrEnum):
    NEW = "new"
    LIKE_NEW = "like_new"
    USED_GOOD = "used_good"
    USED_FAIR = "used_fair"

    def label(self) -> str:
        return CONDITION_LABELS[self]


CONDITION_LABELS = {
    Condition.NEW: "New",
    Condition.LIKE_NEW: "Like new",
    Condition.USED_GOOD: "Used — good",
    Condition.USED_FAIR: "Used — fair",
}


class Grade(StrEnum):
    UNDERGRADUATE = "undergraduate"
    GRADUATE = "graduate"
    FACULTY_STAFF = "faculty_staff"

    def label(self) -> str:
        return {
            Grade.UNDERGRADUATE: "Undergraduate",
            Grade.GRADUATE: "Graduate",
            Grade.FACULTY_STAFF: "Faculty / Staff",
        }[self]


class ListingStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    RESERVED = "reserved"
    SOLD = "sold"


class Source(StrEnum):
    INTERNAL = "internal"
    EBAY = "ebay"
    FACEBOOK = "facebook"
    KARROT = "karrot"

    def label(self) -> str:
        return {
            Source.INTERNAL: "Columbia Market",
            Source.EBAY: "eBay",
            Source.FACEBOOK: "Facebook Marketplace",
            Source.KARROT: "Karrot",
        }[self]


class School(StrEnum):
    COLUMBIA_COLLEGE = "columbia_college"
    SEAS_UNDERGRAD = "seas_undergrad"
    GENERAL_STUDIES = "general_studies"
    CBS = "cbs"
    LAW = "law"
    SIPA = "sipa"
    SEAS_GRAD = "seas_grad"
    TEACHERS_COLLEGE = "teachers_college"
    JOURNALISM = "journalism"
    PUBLIC_HEALTH = "public_health"
    GSAS = "gsas"
    ARTS = "arts"
    GSAPP = "gsapp"
    VPS = "vps"

    def label(self) -> str:
        return SCHOOL_LABELS[self]


SCHOOL_LABELS = {
    School.COLUMBIA_COLLEGE: "Columbia College",
    School.SEAS_UNDERGRAD: "Engineering — SEAS",
    School.GENERAL_STUDIES: "General Studies",
    School.CBS: "Business — CBS",
    School.LAW: "Law",
    School.SIPA: "SIPA",
    School.SEAS_GRAD: "Engineering — SEAS",
    School.TEACHERS_COLLEGE: "Teachers College",
    School.JOURNALISM: "Journalism",
    School.PUBLIC_HEALTH: "Public Health",
    School.GSAS: "GSAS",
    School.ARTS: "Arts",
    School.GSAPP: "Architecture — GSAPP",
    School.VPS: "Medicine — VP&S",
}

UNDERGRADUATE_SCHOOLS = [
    School.COLUMBIA_COLLEGE,
    School.SEAS_UNDERGRAD,
    School.GENERAL_STUDIES,
]
GRADUATE_SCHOOLS = [s for s in School if s not in UNDERGRADUATE_SCHOOLS]


class EnquiryChannel(StrEnum):
    EMAIL = "email"
    SMS = "sms"


class ViewSurface(StrEnum):
    FEED = "feed"
    SEARCH = "search"
    DETAIL = "detail"


class UserStatus(StrEnum):
    ACTIVE = "active"
    DEACTIVATED = "deactivated"


class SortOrder(StrEnum):
    NEWEST = "newest"
    CLOSEST = "closest"
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    MOST_SAVED = "most_saved"
