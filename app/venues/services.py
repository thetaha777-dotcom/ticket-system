import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.shared.exceptions import NotFound
from app.users.models import User
from app.venues.models import Seat, SeatRow, Venue, VenueSection
from app.venues.schemas import VenueIn

# name, price category, row labels, seats per row, accessible seats as (row, seat number)
PREDEFINED_LAYOUT = [
    ("VIP", "VIP", ["1", "2"], 10, set()),
    ("Parterre", "Standard", ["3", "4", "5", "6", "7", "8"], 14, {("3", 1), ("3", 2), ("3", 13), ("3", 14)}),
    ("Balcony", "Economy", ["9", "10", "11"], 16, {("9", 1), ("9", 16)}), 
]
#makes sense

def attach_predefined_layout(db: Session, venue: Venue) -> int:
    total = 0
    for s_index, (name, category, rows, per_row, accessible) in enumerate(PREDEFINED_LAYOUT):
        section = VenueSection(venue_id=venue.id, name=name, price_category=category, sort_order=s_index)
        db.add(section)
        db.flush()
        for r_index, label in enumerate(rows):
            row = SeatRow(section_id=section.id, label=label, sort_order=r_index)
            db.add(row)
            db.flush()
            for number in range(1, per_row + 1):
                db.add(Seat(venue_id=venue.id, section_id=section.id, row_id=row.id, number=number,
                            is_accessible=(label, number) in accessible))
                total += 1
    venue.has_seat_map = True
    venue.capacity = total
    return total


def create_venue(db: Session, user: User | None, data: VenueIn) -> Venue:
    venue = Venue(
        name=data.name, description=data.description, city=data.city, address=data.address,
        capacity=data.capacity, created_by_id=user.id if user else None,
    )
    db.add(venue)
    db.flush()
    if data.use_predefined_layout:
        attach_predefined_layout(db, venue)
    db.commit()
    return venue


def list_venues(db: Session, q: str | None = None) -> list[Venue]:
    query = select(Venue).order_by(Venue.name)
    if q:
        like = f"%{q.lower()}%"
        query = query.where(or_(Venue.name.ilike(like), Venue.city.ilike(like)))
    return list(db.scalars(query))


def get_venue(db: Session, venue_id: uuid.UUID) -> Venue:
    venue = db.get(Venue, venue_id)
    if venue is None:
        raise NotFound("Venue not found", "venue_not_found")
    return venue


def get_layout(db: Session, venue_id: uuid.UUID) -> Venue:
    venue = db.scalar(
        select(Venue).where(Venue.id == venue_id)
        .options(selectinload(Venue.sections).selectinload(VenueSection.rows).selectinload(SeatRow.seats))
    )
    if venue is None:
        raise NotFound("Venue not found", "venue_not_found")
    return venue
