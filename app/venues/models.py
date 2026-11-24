import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, created_at_col, uuid_pk


class Venue(Base):
    __tablename__ = "venues"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    capacity: Mapped[int | None] = mapped_column(Integer)
    has_seat_map: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = created_at_col()

    sections: Mapped[list["VenueSection"]] = relationship(
        back_populates="venue", order_by="VenueSection.sort_order", cascade="all, delete-orphan"
    )

class VenueSection(Base):
    
    __tablename__ = "venue_sections"

    id: Mapped[uuid.UUID] = uuid_pk()
    venue_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("venues.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    price_category: Mapped[str] = mapped_column(String(50), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    venue: Mapped[Venue] = relationship(back_populates="sections")
    rows: Mapped[list["SeatRow"]] = relationship(
        back_populates="section", order_by="SeatRow.sort_order", cascade="all, delete-orphan"
    )

class SeatRow(Base):
    __tablename__ = "venue_rows"

    id: Mapped[uuid.UUID] = uuid_pk()
    section_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("venue_sections.id"), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(10), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    section: Mapped[VenueSection] = relationship(back_populates="rows")
    seats: Mapped[list["Seat"]] = relationship(back_populates="row", order_by="Seat.number", cascade="all, delete-orphan")

class Seat(Base):

    __tablename__ = "seats"

    id: Mapped[uuid.UUID] = uuid_pk()
    venue_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("venues.id"), nullable=False, index=True)
    section_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("venue_sections.id"), nullable=False)
    row_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("venue_rows.id"), nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    is_accessible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    row: Mapped[SeatRow] = relationship(back_populates="seats")
    section: Mapped[VenueSection] = relationship()

#deprecated 

# class VenuesEvents(Base):
#     __tablename__ = "venues_events"
#     venue_id: Mapped[UUID] = mapped_column(ForeignKey("venues.id"), nullable=False, primary_key=True)
#     event_id: Mapped[UUID] = mapped_column(ForeignKey("events.id"), nullable=False, primary_key=True)
#     fill_line: Mapped[str] = mapped_column(String(10000), nullable=False)