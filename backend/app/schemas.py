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

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from .config import settings
from .enums import (
    SELLER_STATUSES,
    Category,
    Condition,
    EnquiryChannel,
    Grade,
    ListingStatus,
    School,
    subcategory_belongs_to,
)
from .services import countries, domains

USERNAME_RE = re.compile(r"^[A-Za-z0-9._]{3,20}$")


def _clean_username(v: str) -> str:
    v = v.strip().lstrip("@")
    if not USERNAME_RE.match(v):
        raise ValueError("3–20 characters, letters, numbers, dots and underscores")
    return v


def _clean_phone(v: str | None) -> str | None:
    """Blank means no number. Otherwise normalise to E.164-ish (+1 for 10 digits)."""
    if v is None or not v.strip():
        return None
    digits = re.sub(r"\D", "", v)
    if len(digits) == 10:
        digits = "1" + digits
    if not 10 <= len(digits) <= 15:
        raise ValueError("Enter a phone number with the area code, e.g. +1 646 555 0142")
    return "+" + digits


def _clean_nationality(v: str) -> str:
    v = v.strip().upper()
    if not countries.is_valid(v):
        raise ValueError("Pick a country from the list")
    return v


# ---------------------------------------------------------------- auth


class SignupIn(BaseModel):
    email: EmailStr
    username: str
    phone: str | None = None  # optional — UX_SPEC.md §5.1
    nationality: str
    school: School
    grade: Grade
    zip_code: str = Field(pattern=r"^\d{5}$")

    @field_validator("email")
    @classmethod
    def columbia_only(cls, v: str) -> str:
        reason = domains.rejection_reason(v)
        if reason:
            raise ValueError(reason)
        return domains.normalize(v)

    @field_validator("username")
    @classmethod
    def valid_username(cls, v: str) -> str:
        return _clean_username(v)

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, v: str | None) -> str | None:
        return _clean_phone(v)

    @field_validator("nationality")
    @classmethod
    def valid_nationality(cls, v: str) -> str:
        return _clean_nationality(v)


class RequestLinkIn(BaseModel):
    email: EmailStr


class LinkSentOut(BaseModel):
    sent: bool
    resend_available_in_seconds: int
    # Dev only: the link we would have emailed, so the team can click through
    # without an inbox. None when EMAIL_DEV_MODE is off.
    dev_link: str | None = None
    # Dev only: why the email itself could not be sent (bad SMTP password, no
    # API key). The link above still works, so a misconfigured mailer never
    # locks the team out of a local build.
    delivery_error: str | None = None


class EmailCheckOut(BaseModel):
    """Live validation for the email field (states A2/A3, B2/B3)."""

    email: str
    allowed: bool
    reason: str | None = None
    suggested_school: School | None = None


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
    display_name: str | None = Field(default=None, max_length=80)
    phone: str | None = None
    phone_contact_enabled: bool | None = None
    nationality: str | None = None
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
        return None if v is None else _clean_username(v)

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, v: str | None) -> str | None:
        return _clean_phone(v)

    @field_validator("nationality")
    @classmethod
    def valid_nationality(cls, v: str | None) -> str | None:
        return None if v is None else _clean_nationality(v)


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


class PhotoOut(BaseModel):
    url: str
    width: int | None = None
    height: int | None = None


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
    neighbourhood: str | None
    distance_mi: float | None
    posted_at: datetime
    status: ListingStatus
    cover_photo_url: str | None
    photo_count: int
    badges: list[str]


class ListingDetail(ListingCard):
    description: str | None
    is_negotiable: bool
    photos: list[PhotoOut]
    photo_urls: list[str]
    view_count: int
    save_count: int
    enquiry_count: int
    sold_at: datetime | None
    seller: SellerPublic | None
    is_saved: bool = False
    is_owner: bool = False


class ListingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=60)
    description: str | None = Field(default=None, max_length=1000)
    category: Category
    subcategory: str | None = None
    condition: Condition
    price_cents: int = Field(ge=0)
    is_free: bool = False
    is_negotiable: bool = False
    zip_code: str = Field(pattern=r"^\d{5}$")
    # At least one photo to publish (UX_SPEC.md §6.5); each must have been
    # uploaded through POST /photos by the same member.
    photo_urls: list[str] = Field(min_length=1, max_length=settings.max_photos_per_listing)

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("Give the listing a title")
        return v

    @model_validator(mode="after")
    def coherent(self) -> ListingCreate:
        if not subcategory_belongs_to(self.subcategory, self.category):
            raise ValueError(f"{self.subcategory!r} is not a {self.category.label()} subcategory")
        if self.is_free:
            self.price_cents = 0
        elif self.price_cents <= 0:
            raise ValueError('Enter a price, or tick "give it away for free". $0 on its own is ambiguous.')
        return self


class ListingUpdate(BaseModel):
    """PATCH /listings/{id}. Owner only. Omitted fields are left alone."""

    title: str | None = Field(default=None, min_length=1, max_length=60)
    description: str | None = Field(default=None, max_length=1000)
    category: Category | None = None
    subcategory: str | None = None
    condition: Condition | None = None
    price_cents: int | None = Field(default=None, ge=0)
    is_free: bool | None = None
    is_negotiable: bool | None = None
    zip_code: str | None = Field(default=None, pattern=r"^\d{5}$")
    photo_urls: list[str] | None = Field(
        default=None, min_length=1, max_length=settings.max_photos_per_listing
    )
    status: ListingStatus | None = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str | None) -> str | None:
        return None if v is None else " ".join(v.split())

    @field_validator("status")
    @classmethod
    def seller_status(cls, v: ListingStatus | None) -> ListingStatus | None:
        if v is not None and v not in SELLER_STATUSES:
            raise ValueError("Status must be active, reserved, sold or delisted")
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


class EnquirerOut(BaseModel):
    """Someone who contacted the seller — the candidate list when marking sold."""

    id: str
    username: str
    display_name: str | None = None
    channel: EnquiryChannel
    enquired_at: datetime


class MarkSoldIn(BaseModel):
    """Optional body for POST /listings/{id}/sold.

    Every field is optional and so is the body itself, so the call that existed
    before this — no body at all — behaves exactly as it did.
    """

    buyer_id: str | None = None
    sold_price_cents: int | None = Field(default=None, ge=0)


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
    subcategories: list[FacetCount]
    conditions: list[FacetCount]
    same_zip: int
    same_nationality: int
    same_school: int
    radius_steps: list[FacetCount]  # 0.5 / 1 / 2.5 / 5 / 10 mi


class EnquiryIn(BaseModel):
    channel: EnquiryChannel


class EnquiryOut(BaseModel):
    """Returned only at the moment the buyer taps Email or Text.

    This is the one and only place a contact detail crosses the wire.
    """

    channel: EnquiryChannel
    address: str | None = None  # email
    phone: str | None = None  # sms


# ---------------------------------------------------------------- reference


class ZipOut(BaseModel):
    zip_code: str
    neighbourhood: str
    borough: str
    miles_away: float
    miles_from_campus: float | None


class CountryOut(BaseModel):
    code: str
    name: str
    pinned: bool
