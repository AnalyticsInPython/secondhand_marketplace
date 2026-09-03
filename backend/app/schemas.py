"""Request and response shapes — UX_SPEC.md §8.

Two rules worth holding on to:

1.  The client never receives a seller's raw attributes. It receives
    `badges: []`, already computed for the viewer (see services/badges.py).
2.  The client never computes distance. It receives `distance_mi`, already
    measured from the viewer's ZIP.

Both exist so that a careless frontend cannot leak what the disclosure rule is
meant to withhold.
"""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from . import emails
from .config import settings
from .enums import (
    Category,
    Condition,
    EnquiryChannel,
    Grade,
    ListingStatus,
    School,
    Source,
    SortOrder,
)

USERNAME_RE = re.compile(r"^[A-Za-z0-9._]{3,20}$")


# ---------------------------------------------------------------- auth


class SignupIn(BaseModel):
    email: EmailStr
    username: str
    phone: str | None = None  # optional — UX_SPEC.md §5.1
    nationality: str = Field(min_length=2, max_length=2)
    school: School
    grade: Grade
    zip_code: str = Field(pattern=r"^\d{5}$")

    @field_validator("email")
    @classmethod
    def columbia_only(cls, v: str) -> str:
        if not emails.is_allowed(v):
            raise ValueError(emails.rejection_message())
        return v.lower()

    @field_validator("username")
    @classmethod
    def valid_username(cls, v: str) -> str:
        v = v.lstrip("@")
        if not USERNAME_RE.match(v):
            raise ValueError("3–20 characters, letters, numbers, dots and underscores")
        return v


class RequestLinkIn(BaseModel):
    email: EmailStr


class LinkSentOut(BaseModel):
    sent: bool
    resend_available_in_seconds: int
    # Dev only: the link we would have emailed, so the team can click through
    # without an SMTP server. None when EMAIL_DEV_MODE is off.
    dev_link: str | None = None


# ---------------------------------------------------------------- users


class MeOut(BaseModel):
    """The full own-profile payload. Only ever returned for the signed-in user."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    username: str
    display_name: str | None
    phone: str | None
    phone_contact_enabled: bool
    nationality: str
    school: School
    grade: Grade
    zip_code: str
    default_radius_mi: float
    default_filter_same_zip: bool
    default_filter_same_nationality: bool
    default_filter_same_school: bool
    is_verified: bool
    created_at: datetime


class ProfileUpdate(BaseModel):
    """Everything on the Profile & account screen except the email, which is
    immutable — changing it would mean a different account."""

    username: str | None = None
    display_name: str | None = None
    phone: str | None = None
    phone_contact_enabled: bool | None = None
    nationality: str | None = Field(default=None, min_length=2, max_length=2)
    school: School | None = None
    grade: Grade | None = None
    zip_code: str | None = Field(default=None, pattern=r"^\d{5}$")
    default_radius_mi: float | None = Field(
        default=None, ge=settings.min_radius_mi, le=settings.max_radius_mi
    )
    default_filter_same_zip: bool | None = None
    default_filter_same_nationality: bool | None = None
    default_filter_same_school: bool | None = None

    @field_validator("username")
    @classmethod
    def valid_username(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.lstrip("@")
        if not USERNAME_RE.match(v):
            raise ValueError("3–20 characters, letters, numbers, dots and underscores")
        return v


class UsernameAvailability(BaseModel):
    username: str
    available: bool
    suggestions: list[str] = []


# ---------------------------------------------------------------- listings


class SellerPublic(BaseModel):
    """Safe for any viewer. Note the absences — see services/badges.py."""

    username: str
    display_name: str | None
    is_verified: bool
    member_since: str
    badges: list[str]
    can_receive_sms: bool


class ListingCard(BaseModel):
    """One card in the feed."""

    id: str
    title: str
    price_cents: int
    is_free: bool
    condition: Condition
    category: Category
    subcategory: str | None
    zip_code: str
    distance_mi: float | None
    posted_at: datetime
    status: ListingStatus
    cover_photo_url: str | None
    badges: list[str]
    is_external: bool
    source: Source
    source_label: str


class ListingDetail(ListingCard):
    description: str | None
    is_negotiable: bool
    photo_urls: list[str]
    view_count: int
    save_count: int
    enquiry_count: int
    external_url: str | None
    seller: SellerPublic | None
    is_saved: bool = False
    is_owner: bool = False


class ListingCreate(BaseModel):
    title: str = Field(max_length=60)
    description: str | None = Field(default=None, max_length=1000)
    category: Category
    subcategory: str | None = None
    condition: Condition
    price_cents: int = Field(ge=0)
    is_free: bool = False
    is_negotiable: bool = False
    zip_code: str = Field(pattern=r"^\d{5}$")
    photo_urls: list[str] = []

    @field_validator("photo_urls")
    @classmethod
    def photo_limit(cls, v: list[str]) -> list[str]:
        if len(v) > settings.max_photos_per_listing:
            raise ValueError(f"At most {settings.max_photos_per_listing} photos")
        return v


class ListingPage(BaseModel):
    items: list[ListingCard]
    total: int
    next_cursor: str | None = None


class EnquiryRow(BaseModel):
    """One row of the inbox (UX_SPEC.md §6.6, avatar menu).

    There is no in-app chat, so an "inbox" is a record of contacts made rather
    than a thread list: which listing, which channel, when. The listing travels
    as a full card so the row renders with the same badges and distance as it
    would in the feed.
    """

    id: str
    channel: EnquiryChannel
    created_at: datetime
    listing: ListingCard
    seller_username: str | None = None


class FacetCount(BaseModel):
    key: str
    label: str
    count: int


class FacetCounts(BaseModel):
    """Every number the filter sidebar shows.

    Each count is "what you would get if you applied this one filter, with all
    the other active filters still on". They move as filters change; that live
    honesty is the point, so do not cache these into static values.
    """

    total: int
    categories: list[FacetCount]
    conditions: list[FacetCount]
    same_zip: int
    same_nationality: int
    same_school: int
    radius_steps: list[FacetCount]  # 0.5 / 1 / 2.5 / 5 / 10 mi


class EnquiryIn(BaseModel):
    channel: str  # "email" | "sms"


class EnquiryOut(BaseModel):
    """Returned only at the moment the buyer taps Email or Text.

    This is the one and only place a contact detail crosses the wire.
    """

    channel: str
    address: str | None = None  # email
    phone: str | None = None  # sms


class ZipOut(BaseModel):
    zip_code: str
    neighbourhood: str
    borough: str
    miles_away: float
    miles_from_campus: float | None


class ListingQuery(BaseModel):
    """Mirrors the query string of GET /listings."""

    q: str | None = None
    category: list[Category] = []
    subcategory: list[str] = []
    condition: list[Condition] = []
    price_min_cents: int | None = None
    price_max_cents: int | None = None
    radius_mi: float | None = None
    same_zip: bool = False
    same_nationality: bool = False
    same_school: bool = False
    source: list[Source] = []
    sort: SortOrder = SortOrder.NEWEST
    limit: int = 24
    offset: int = 0
