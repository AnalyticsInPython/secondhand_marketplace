"""ORM models — UX_SPEC.md §4.

Enums are stored as VARCHAR with a check constraint (`native_enum=False`) so the
schema is identical on SQLite and Postgres.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base
from .enums import (
    Category,
    Condition,
    EnquiryChannel,
    Grade,
    ListingStatus,
    School,
    Source,
    UserStatus,
    ViewSurface,
)


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _enum(py_enum, name: str):
    return Enum(py_enum, native_enum=False, values_callable=lambda e: [m.value for m in e], name=name)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)

    # Immutable. This address *is* the membership (UX_SPEC.md §4.1).
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(80))

    # Optional — roughly a third of members are expected to leave it blank.
    # When it is NULL the listing page shows a single full-width Email button
    # rather than a disabled Text button (UX_SPEC.md §5.1).
    phone: Mapped[str | None] = mapped_column(String(32))
    phone_contact_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    nationality: Mapped[str] = mapped_column(String(2), nullable=False)  # ISO-3166 alpha-2
    school: Mapped[School] = mapped_column(_enum(School, "school"), nullable=False)
    grade: Mapped[Grade] = mapped_column(_enum(Grade, "grade"), nullable=False)
    zip_code: Mapped[str] = mapped_column(String(5), nullable=False, index=True)

    default_radius_mi: Mapped[float] = mapped_column(Float, default=2.5)
    default_filter_same_zip: Mapped[bool] = mapped_column(Boolean, default=False)
    default_filter_same_nationality: Mapped[bool] = mapped_column(Boolean, default=False)
    default_filter_same_school: Mapped[bool] = mapped_column(Boolean, default=False)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[UserStatus] = mapped_column(
        _enum(UserStatus, "user_status"), default=UserStatus.ACTIVE
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    listings: Mapped[list[Listing]] = relationship(back_populates="seller")

    @property
    def can_receive_sms(self) -> bool:
        return bool(self.phone) and self.phone_contact_enabled


class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = (
        # External listings must point somewhere; internal ones must not.
        CheckConstraint(
            "(source = 'internal' AND external_url IS NULL AND seller_id IS NOT NULL) "
            "OR (source != 'internal' AND external_url IS NOT NULL)",
            name="ck_listing_source_shape",
        ),
        Index("ix_listings_feed", "status", "source", "category", "zip_code"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    seller_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    source: Mapped[Source] = mapped_column(_enum(Source, "source"), default=Source.INTERNAL)

    title: Mapped[str] = mapped_column(String(60), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[Category] = mapped_column(_enum(Category, "category"), nullable=False)
    subcategory: Mapped[str | None] = mapped_column(String(40))
    condition: Mapped[Condition] = mapped_column(_enum(Condition, "condition"), nullable=False)

    price_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_free: Mapped[bool] = mapped_column(Boolean, default=False)
    is_negotiable: Mapped[bool] = mapped_column(Boolean, default=False)

    # Pickup ZIP. A street address is never collected (UX_SPEC.md §5.2).
    zip_code: Mapped[str] = mapped_column(String(5), nullable=False, index=True)

    status: Mapped[ListingStatus] = mapped_column(
        _enum(ListingStatus, "listing_status"), default=ListingStatus.ACTIVE, index=True
    )

    view_count: Mapped[int] = mapped_column(Integer, default=0)
    save_count: Mapped[int] = mapped_column(Integer, default=0)
    enquiry_count: Mapped[int] = mapped_column(Integer, default=0)

    external_url: Mapped[str | None] = mapped_column(Text)

    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    # The event the whole analysis counts.
    sold_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    seller: Mapped[User | None] = relationship(back_populates="listings")
    photos: Mapped[list[ListingPhoto]] = relationship(
        back_populates="listing", cascade="all, delete-orphan", order_by="ListingPhoto.position"
    )

    @property
    def is_external(self) -> bool:
        return self.source != Source.INTERNAL

    @property
    def cover_photo_url(self) -> str | None:
        return self.photos[0].url if self.photos else None


class ListingPhoto(Base):
    __tablename__ = "listing_photos"
    __table_args__ = (UniqueConstraint("listing_id", "position", name="uq_photo_position"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    listing_id: Mapped[str] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0)  # 0 = cover
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    listing: Mapped[Listing] = relationship(back_populates="photos")


# --------------------------------------------------------------------------
# Auth. No passwords exist anywhere in this product (UX_SPEC.md §6.2).
# --------------------------------------------------------------------------


class LoginToken(Base):
    __tablename__ = "login_tokens"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# --------------------------------------------------------------------------
# Event tables. These are the analysis (UX_SPEC.md §4.4) — write to them
# eagerly, they are cheap and irreplaceable after the fact.
# --------------------------------------------------------------------------


class ListingView(Base):
    __tablename__ = "listing_views"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    listing_id: Mapped[str] = mapped_column(ForeignKey("listings.id"), index=True)
    viewer_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    surface: Mapped[ViewSurface] = mapped_column(_enum(ViewSurface, "view_surface"))
    viewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)


class Save(Base):
    __tablename__ = "saves"
    __table_args__ = (UniqueConstraint("listing_id", "user_id", name="uq_save"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    listing_id: Mapped[str] = mapped_column(ForeignKey("listings.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Enquiry(Base):
    __tablename__ = "enquiries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    listing_id: Mapped[str] = mapped_column(ForeignKey("listings.id"), index=True)
    buyer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    channel: Mapped[EnquiryChannel] = mapped_column(_enum(EnquiryChannel, "enquiry_channel"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)


class FilterEvent(Base):
    """Every toggle and every slider release.

    This is what answers "which of the filters is doing the work" — the question
    we cannot reconstruct later if we forget to log it now.
    """

    __tablename__ = "filter_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    filter_key: Mapped[str] = mapped_column(String(40), index=True)
    value: Mapped[str | None] = mapped_column(String(80))
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
