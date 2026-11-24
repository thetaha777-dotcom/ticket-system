#demo data
import sys
from datetime import timedelta

from sqlalchemy import select, update

import app.models  
from app.activation import services as activation
from app.audit.models import AuditLog
from app.auth.schemas import RegisterRequest
from app.auth.services import register
from app.checkin import services as checkin
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine, utcnow
from app.core.security import ticket_qr_payload
from app.events import seating
from app.events import services as events
from app.events.models import Event
from app.events.schemas import EventIn, SeatingConfigIn, SeatingSectionIn
from app.orders import services as orders
from app.orders.models import Order
from app.orders.schemas import OrderCreate, OrderLineIn
from app.promos import services as promos
from app.promos.schemas import CampaignIn
from app.support import services as support
from app.support.schemas import CaseCreate
from app.tickets import services as tickets
from app.tickets.models import CheckInRecord, Ticket
from app.tickets.schemas import TicketTypeIn
from app.users import services as users
from app.users.models import User, UserRole
from app.users.schemas import OrganizerProfileIn, PayoutAccountIn
from app.venues import services as venues
from app.venues.schemas import VenueIn

PASSWORD = "Demo12345"
GUESTS = ["Aigerim Sadykova", "Daniyar Akhmetov", "Madina Omarova", "Timur Zhaksybekov", "Aruzhan Bekova",
          "Nurlan Abenov", "Dana Kassymova", "Yerlan Tulegenov", "Kamila Ismailova", "Arman Serikbayev",
          "Zarina Mukanova", "Sanzhar Ospanov"]


def _user(db, name: str, email: str, role: str = "attendee") -> User:
    user = register(db, RegisterRequest(name=name, email=email, password=PASSWORD, role=role))
    user.is_verified = True
    db.commit()
    return user


def _event(db, organizer: User, venue, title: str, category: str, days: int, hours: int, description: str, **extra) -> Event:
    start = (utcnow() + timedelta(days=days)).replace(hour=14, minute=0, second=0, microsecond=0)   # 19:00 in Almaty
    return events.create_event(db, organizer, EventIn(
        title=title, category=category, venue_id=venue.id, start_at=start, end_at=start + timedelta(hours=hours),
        description=description, **extra))


def _ticket_type(db, event: Event, organizer: User, **data):
    return tickets.create_ticket_type(db, event, organizer, TicketTypeIn(**data))


def _buy(db, buyer: User, event: Event, category, quantity: int = 1, promo: str | None = None, pay: bool = True) -> Order:
    order = orders.create_order(db, buyer, OrderCreate(
        event_id=event.id, items=[OrderLineIn(ticket_category_id=category.id, quantity=quantity)], promo_code=promo))
    if pay and order.status.value == "pending":
        order = orders.pay_order(db, buyer, order.id, "success")
    return order


def _backdate(db, order: Order, days_ago: float) -> None:
    when = utcnow() - timedelta(days=days_ago)
    db.execute(update(Order).where(Order.id == order.id).values(created_at=when, paid_at=when))
    db.commit()


def seed(db) -> None:
    print("Creating users...")
    admin = _user(db, "Platform Admin", "admin@example.com")
    admin.role = UserRole.PLATFORM_ADMIN
    organizer = _user(db, "Olzhas Organizer", "organizer@example.com", "organizer")
    staff = _user(db, "Saule Staff", "staff@example.com")
    staff.role = UserRole.EVENT_ADMIN
    attendee = _user(db, "Alia Attendee", "attendee@example.com")
    guests = [_user(db, name, f"{name.split()[0].lower()}@example.com") for name in GUESTS]
    db.commit()

    users.upsert_profile(db, organizer, OrganizerProfileIn(
        display_name="Steppe Events", contact_email="events@example.org", contact_phone="+7 700 000 00 00",
        description="Concerts, meetups and community events in Almaty.", website="https://example.org"))
    users.verify_identity(db, organizer)
    users.set_payout_account(db, organizer, PayoutAccountIn(
        bank_name="Demo Bank", account_holder="Steppe Events LLP", account_number="KZ00DEMO000000004821"))

    print("Creating venues...")
    hall = venues.create_venue(db, organizer, VenueIn(
        name="Dostyk Concert Hall", city="Almaty", address="12 Demo Avenue",
        description="Demonstration venue with the predefined seat map.", use_predefined_layout=True))
    loft = venues.create_venue(db, organizer, VenueIn(name="Tech Loft", city="Almaty", address="5 Sample Street", capacity=250))
    roof = venues.create_venue(db, organizer, VenueIn(name="Skyline Rooftop", city="Astana", address="88 Example Boulevard", capacity=180))

    print("Creating events...")
    meetup = _event(db, organizer, loft, "Almaty Student Tech Meetup", "Technology", 14, 3,
                    "Talks about mobile development, AI tools and student start-ups. Free entry, registration required.")
    general = _ticket_type(db, meetup, organizer, name="General entry", type="free", quantity=150, order_limit=4)
    _ticket_type(db, meetup, organizer, name="Student (bring your ID)", type="free", quantity=50, order_limit=1)
    events.publish(db, meetup, organizer)
    for index, guest in enumerate(guests[:6]):
        _backdate(db, _buy(db, guest, meetup, general, 1 + index % 2), 6 - index)
    _buy(db, attendee, meetup, general, 2)

    # Paid general-admission event with promo campaigns 
    jazz = _event(db, organizer, roof, "Jazz Evening on the Roof", "Music", 21, 4,
                  "Live quartet, sunset view and a relaxed evening. Doors open 30 minutes before the start.",
                  refund_policy_text="Full refund until the event starts.")
    standard = _ticket_type(db, jazz, organizer, name="Standard", type="paid", price=6000, quantity=120, order_limit=6)
    vip = _ticket_type(db, jazz, organizer, name="VIP table seat", type="paid", price=15000, quantity=20, order_limit=4,
                       description="Reserved table area and a welcome drink.")
    activation.pay_fee(db, jazz, organizer)
    activation.accept_terms(db, jazz, organizer)
    events.publish(db, jazz, organizer)
    promos.create_campaign(db, jazz, organizer, CampaignIn(
        name="Early birds", discount_type="percent", discount_value=20, max_redemptions=50, code="EARLY20"))
    promos.create_campaign(db, jazz, organizer, CampaignIn(
        name="Student flyer", discount_type="fixed", discount_value=1000, code="STUDENT1000", ticket_category_ids=[standard.id]))
    plan = [(0, standard, 2, None, 9), (1, standard, 1, "EARLY20", 8), (2, vip, 2, None, 7), (3, standard, 3, "EARLY20", 6),
            (4, standard, 2, "STUDENT1000", 5), (5, standard, 1, None, 4), (6, vip, 1, "EARLY20", 3), (7, standard, 4, None, 2),
            (8, standard, 2, "STUDENT1000", 1.5), (9, standard, 1, None, 1)]
    for guest_index, category, quantity, promo, days_ago in plan:
        _backdate(db, _buy(db, guests[guest_index], jazz, category, quantity, promo), days_ago)
    refunded = _buy(db, guests[10], jazz, standard, 2)
    orders.refund_order(db, orders.get_order(db, refunded.id), organizer, "Attendee cannot come")
    my_jazz = _buy(db, attendee, jazz, standard, 2, "EARLY20")
    failed = orders.create_order(db, guests[11], OrderCreate(
        event_id=jazz.id, items=[OrderLineIn(ticket_category_id=standard.id, quantity=1)]))
    orders.pay_order(db, guests[11], failed.id, "failure")
    orders.cancel_order(db, orders.get_order(db, failed.id), guests[11])

    # Assigned-seating event 
    gala = _event(db, organizer, hall, "Nauryz Gala Concert", "Music", 35, 3,
                  "Festive concert with assigned seating. Choose your seat on the interactive map.", seating="assigned_seating")
    gala_types = {
        "VIP": _ticket_type(db, gala, organizer, name="VIP", type="paid", price=25000, quantity=1),
        "Standard": _ticket_type(db, gala, organizer, name="Parterre", type="paid", price=12000, quantity=1),
        "Economy": _ticket_type(db, gala, organizer, name="Balcony", type="paid", price=5000, quantity=1),
    }
    layout = venues.get_layout(db, hall.id)
    seating.configure(db, events.get_event(db, gala.id), organizer, SeatingConfigIn(sections=[
        SeatingSectionIn(section_id=s.id, ticket_category_id=gala_types[s.price_category].id) for s in layout.sections]))
    activation.pay_fee(db, gala, organizer)
    activation.accept_terms(db, gala, organizer)
    gala = events.get_event(db, gala.id)
    events.publish(db, gala, organizer)
    seat_map = seating.seat_map(db, gala, None)
    picks = [(0, 0, [3, 4]), (0, 1, [5, 6, 7]), (1, 1, [6, 7]), (1, 2, [1, 2, 3, 4]), (1, 3, [8, 9]), (2, 0, [7, 8, 9]), (1, 0, [10])]
    for index, (section, row, seat_indexes) in enumerate(picks):
        seat_ids = [seat_map.sections[section].rows[row].seats[i].id for i in seat_indexes]
        order = orders.create_order(db, guests[index], OrderCreate(event_id=gala.id, seat_ids=seat_ids))
        _backdate(db, orders.pay_order(db, guests[index], order.id, "success"), 5 - index * 0.6)

    # Draft 
    pitch = _event(db, organizer, loft, "Startup Pitch Night", "Business", 50, 3,
                   "Ten student teams pitch to a jury. This event is still a draft.", visibility="unlisted")
    _ticket_type(db, pitch, organizer, name="Audience", type="free", quantity=100)

    # Completed event 
    ball = _event(db, organizer, loft, "Winter Charity Ball", "Community", 3, 4,
                  "Charity evening: all demonstration proceeds go to a student fund.")
    ball_ticket = _ticket_type(db, ball, organizer, name="Entry", type="paid", price=8000, quantity=80)
    activation.pay_fee(db, ball, organizer)
    activation.accept_terms(db, ball, organizer)
    events.publish(db, ball, organizer)
    ball_orders = [_buy(db, guest, ball, ball_ticket, 1 + index % 2) for index, guest in enumerate(guests[:9])]
    for order in ball_orders[:7]:   # most guests came
        for ticket in orders.get_order(db, order.id).tickets:
            checkin.scan(db, organizer, ball.id, ticket_qr_payload(ticket.id))
    shift = timedelta(days=24)      # move the whole event, its orders and its history into the past
    ball = events.get_event(db, ball.id)
    ball.start_at, ball.end_at, ball.published_at = ball.start_at - shift, ball.end_at - shift, utcnow() - timedelta(days=40)
    for index, order in enumerate(ball_orders):
        when = utcnow() - timedelta(days=36 - index * 1.4)
        db.execute(update(Order).where(Order.id == order.id).values(created_at=when, paid_at=when))
    at_the_door = timedelta(days=21)
    for entry in db.scalars(select(AuditLog).where(AuditLog.event_id == ball.id)):
        entry.created_at -= at_the_door if entry.action.startswith("checkin") else timedelta(days=40)
    for check_in in db.scalars(select(CheckInRecord).where(CheckInRecord.event_id == ball.id)):
        check_in.created_at -= at_the_door
    for ticket in db.scalars(select(Ticket).where(Ticket.event_id == ball.id, Ticket.checked_in_at.is_not(None))):
        ticket.checked_in_at -= at_the_door
    db.commit()

    # Cancelled event 
    cinema = _event(db, organizer, roof, "Outdoor Cinema Night", "Film", 10, 3, "Open-air screening under the stars.")
    cinema_ticket = _ticket_type(db, cinema, organizer, name="Seat", type="free", quantity=60)
    events.publish(db, cinema, organizer)
    _buy(db, guests[0], cinema, cinema_ticket, 2)
    events.cancel(db, events.get_event(db, cinema.id), organizer, "The venue is closed for repairs")

    print("Adding staff, support cases and a report...")
    for event in (meetup, jazz, gala):
        events.assign_staff(db, events.get_event(db, event.id), organizer, staff.email, can_undo=True)
    case = support.create_case(db, attendee, CaseCreate(
        category="ticket_delivery", subject="Can I change the name on my ticket?", order_id=my_jazz.id,
        message="Hello! I bought two tickets, but my friend cannot come. Can another person use the second ticket?"))
    support.add_message(db, case, organizer, "Hello Alia! Yes - the ticket admits whoever shows the QR code. Have a great evening.")
    support.create_case(db, organizer, CaseCreate(
        kind="organizer", category="activation", subject="When are demonstration payouts shown?",
        message="We completed activation for the jazz evening. Where can we see the estimated payout?"))
    events.report_event(db, events.get_event(db, pitch.id), guests[3], "The description looks unfinished (demo report).")
    print("Done.")


def main() -> None:
    settings.email_backend = "memory"   
    if "--reset" in sys.argv:
        print("Dropping all tables...")
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if db.scalar(select(User.id).limit(1)):
            print("The database already has users - nothing to do. Use --reset to start again.")
            return
        seed(db)
    print(f"\nDemo accounts (password {PASSWORD}):")
    for email, role in (("admin@example.com", "Platform Admin"), ("organizer@example.com", "Organizer"),
                        ("staff@example.com", "Event Admin - mobile app"), ("attendee@example.com", "Attendee")):
        print(f"  {email:24} {role}")


if __name__ == "__main__":
    main()