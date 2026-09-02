"""SQLAlchemy 2 models for the four tables in build spec section 2.

Two rules from the spec are load-bearing and easy to break later:

  * Seller attributes are never copied onto a listing. They are joined at query
    time, so editing a profile immediately corrects every badge on every item
    that person has posted.
  * Deleting is a status change, never a row deletion. The events table still
    references the row.
"""

from __future__ import annotations

import datetime
import uuid

from sqlalchemy import (
    CheckConstraint, DateTime, Enum, ForeignKey, Integer, SmallInteger, String,
    Text, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app import enums


def _pg_enum(python_enum, name):
    """Bind a Python enum to the Postgres type of the same name.

    values_callable stores the lowercase *values* ('cbs'), not the member
    names ('CBS'), which is what the spec's CREATE TYPE declares.
    """
    return Enum(
        python_enum,
        name=name,
        values_callable=lambda e: [m.value for m in e],
        create_type=False,
    )


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    # Mirrors auth.users(id) in Supabase. The foreign key to the auth schema is
    # added in the migration -- SQLAlchemy does not manage that schema.
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    user_name: Mapped[str] = mapped_column(Text, nullable=False)
    phone_number: Mapped[str | None] = mapped_column(Text)

    # The four matching fields. All four are required, and all four are fixed
    # vocabularies -- see app/enums.py for why.
    nationality: Mapped[str] = mapped_column(String(2), nullable=False)  # ISO 3166-1
    college: Mapped[enums.College] = mapped_column(
        _pg_enum(enums.College, "college"), nullable=False
    )
    grade: Mapped[enums.Grade] = mapped_column(
        _pg_enum(enums.Grade, "grade"), nullable=False
    )
    location: Mapped[enums.Location] = mapped_column(
        _pg_enum(enums.Location, "location"), nullable=False
    )

    deleted_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    listings: Mapped[list[Listing]] = relationship(back_populates="seller")


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[enums.Category] = mapped_column(
        _pg_enum(enums.Category, "category"), nullable=False
    )
    # Cents, so no floating point ever touches a price. 0 is allowed --
    # free giveaways are real.
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    condition: Mapped[enums.ItemCondition] = mapped_column(
        _pg_enum(enums.ItemCondition, "item_condition"), nullable=False
    )
    status: Mapped[enums.ListingStatus] = mapped_column(
        _pg_enum(enums.ListingStatus, "listing_status"),
        nullable=False,
        server_default=enums.ListingStatus.ACTIVE.value,
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    sold_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))

    seller: Mapped[User] = relationship(back_populates="listings")
    photos: Mapped[list[Photo]] = relationship(
        back_populates="listing", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("price_cents >= 0", name="ck_listings_price_nonneg"),
    )


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), nullable=False
    )
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="0"
    )

    listing: Mapped[Listing] = relationship(back_populates="photos")


class Event(Base):
    """Append-only. Never updated, never deleted.

    The spec is emphatic that this table exists from the first migration:
    retrofitting instrumentation means throwing away the first weeks of data.
    """

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[enums.EventType] = mapped_column(
        _pg_enum(enums.EventType, "event_type"), nullable=False
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    listing_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listings.id")
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
