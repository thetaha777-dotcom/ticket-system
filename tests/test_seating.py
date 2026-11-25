import io
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader
from sqlalchemy import update

from app.core.database import SessionLocal, engine, utcnow
from app.events.models import EventSeat, SeatStatus
from app.main import app as fastapi_app
from app.orders.models import Order
from tests.helpers import API, activate_paid_sales, make_event, signup


def seated_event(client, organizer) -> tuple[dict, dict]:
    event = make_event(client, organizer, publish=False, seat_map=True, seating="assigned_seating", tickets=[
        {"name": "VIP", "type": "paid", "price": 20000, "quantity": 1},
        {"name": "Standard", "type": "paid", "price": 8000, "quantity": 1},
        {"name": "Economy", "type": "free", "quantity": 1},
    ])
    types = {t["name"]: t["id"] for t in event["ticket_types"]}
    layout = client.get(f"{API}/venues/{event['venue']['id']}/layout").json()
    by_category = {"VIP": types["VIP"], "Standard": types["Standard"], "Economy": types["Economy"]}
    blocked = layout["sections"][1]["rows"][0]["seats"][5]["id"]   # one Parterre seat is blocked
    r = client.put(f"{API}/organizer/events/{event['id']}/seating", headers=organizer, json={
        "sections": [{"section_id": s["id"], "ticket_category_id": by_category[s["price_category"]]} for s in layout["sections"]],
        "unavailable_seat_ids": [blocked]})
    assert r.status_code == 200, r.text
    activate_paid_sales(client, organizer, event["id"])
    assert client.post(f"{API}/organizer/events/{event['id']}/publish", headers=organizer).status_code == 200
    return event, client.get(f"{API}/events/{event['slug']}/seats").json()


def _seat(seat_map, section, row=0, index=0):
    return seat_map["sections"][section]["rows"][row]["seats"][index]


def test_seat_map_shows_layout_prices_and_statuses(client):
    organizer = signup(client, "org@example.com", role="organizer")
    event, seat_map = seated_event(client, organizer)
    assert [(s["name"], s["price"]) for s in seat_map["sections"]] == [("VIP", 20000), ("Parterre", 8000), ("Balcony", 0)]
    assert _seat(seat_map, 1, 0, 5)["status"] == "unavailable"
    assert _seat(seat_map, 1, 0, 0)["is_accessible"] is True and _seat(seat_map, 1, 1, 0)["is_accessible"] is False
    # ticket-type quantities follow the number of seats on sale
    quantities = {t["name"]: t["quantity"] for t in client.get(
        f"{API}/organizer/events/{event['id']}/ticket-types", headers=organizer).json()}
    assert quantities == {"VIP": 20, "Standard": 83, "Economy": 48}


def test_publishing_assigned_seating_requires_a_configured_seat_map(client):
    organizer = signup(client, "org@example.com", role="organizer")
    event = make_event(client, organizer, publish=False, seat_map=True, seating="assigned_seating")
    r = client.post(f"{API}/organizer/events/{event['id']}/publish", headers=organizer)
    assert r.status_code == 400 and r.json()["code"] == "seating_not_configured"


def test_uc8_seat_is_held_then_sold_and_stored_on_the_ticket(client):
    organizer = signup(client, "org@example.com", role="organizer")
    alice, bob = signup(client, "alice@example.com"), signup(client, "bob@example.com")
    event, seat_map = seated_event(client, organizer)
    seat = _seat(seat_map, 0, 1, 3)   # VIP, row "2", seat 4

    # the price is shown before anything is reserved
    quote = client.post(f"{API}/orders/quote", json={"event_id": event["id"], "seat_ids": [seat["id"]]}).json()
    assert quote["total"] == 20000 and (quote["lines"][0]["seat_row"], quote["lines"][0]["seat_number"]) == ("2", 4)
    assert _seat(client.get(f"{API}/events/{event['slug']}/seats").json(), 0, 1, 3)["status"] == "available"

    order = client.post(f"{API}/orders", headers=alice, json={"event_id": event["id"], "seat_ids": [seat["id"]]}).json()
    assert order["status"] == "pending" and order["total"] == 20000
    assert (order["items"][0]["seat_section"], order["items"][0]["seat_row"], order["items"][0]["seat_number"]) == ("VIP", "2", 4)

    held = _seat(client.get(f"{API}/events/{event['slug']}/seats", headers=alice).json(), 0, 1, 3)
    assert held["status"] == "held" and held["held_by_me"] is True
    assert _seat(client.get(f"{API}/events/{event['slug']}/seats", headers=bob).json(), 0, 1, 3)["held_by_me"] is False

    # Bob cannot take a seat that Alice is holding
    r = client.post(f"{API}/orders", headers=bob, json={"event_id": event["id"], "seat_ids": [seat["id"]]})
    assert r.status_code == 409 and r.json()["code"] == "seat_unavailable"

    paid = client.post(f"{API}/orders/{order['id']}/pay", headers=alice, json={"outcome": "success"}).json()
    ticket = paid["tickets"][0]
    assert (ticket["seat_section"], ticket["seat_row"], ticket["seat_number"]) == ("VIP", "2", 4)
    pdf = client.get(f"{API}/tickets/{ticket['id']}/pdf", headers=alice)
    assert "VIP · Row 2 · Seat 4" in PdfReader(io.BytesIO(pdf.content)).pages[0].extract_text()   # printed on the ticket
    assert _seat(client.get(f"{API}/events/{event['slug']}/seats").json(), 0, 1, 3)["status"] == "sold"
    r = client.post(f"{API}/orders", headers=bob, json={"event_id": event["id"], "seat_ids": [seat["id"]]})
    assert r.status_code == 409


def test_expired_hold_releases_the_seat(client):
    organizer = signup(client, "org@example.com", role="organizer")
    alice, bob = signup(client, "alice@example.com"), signup(client, "bob@example.com")
    event, seat_map = seated_event(client, organizer)
    seat = _seat(seat_map, 1, 2, 2)   # a paid Parterre seat (a free seat would be completed at once)
    order = client.post(f"{API}/orders", headers=alice, json={"event_id": event["id"], "seat_ids": [seat["id"]]}).json()

    with SessionLocal() as db:   # the hold time passes without payment
        db.execute(update(Order).where(Order.number == order["number"]).values(expires_at=utcnow() - timedelta(minutes=1)))
        db.execute(update(EventSeat).where(EventSeat.status == SeatStatus.HELD).values(held_until=utcnow() - timedelta(minutes=1)))
        db.commit()

    assert _seat(client.get(f"{API}/events/{event['slug']}/seats").json(), 1, 2, 2)["status"] == "available"
    r = client.post(f"{API}/orders", headers=bob, json={"event_id": event["id"], "seat_ids": [seat["id"]]})
    assert r.status_code == 201
    # Alice is too late
    r = client.post(f"{API}/orders/{order['id']}/pay", headers=alice, json={"outcome": "success"})
    assert r.status_code == 409


def test_seat_map_is_locked_after_sales(client):
    organizer = signup(client, "org@example.com", role="organizer")
    alice = signup(client, "alice@example.com")
    event, seat_map = seated_event(client, organizer)
    client.post(f"{API}/orders", headers=alice, json={"event_id": event["id"], "seat_ids": [_seat(seat_map, 2)["id"]]})
    r = client.put(f"{API}/organizer/events/{event['id']}/seating", headers=organizer, json={"sections": []})
    assert r.status_code == 409 and r.json()["code"] == "has_sales"


@pytest.mark.skipif(engine.dialect.name == "sqlite", reason="real concurrency needs PostgreSQL (set TEST_DATABASE_URL)")
def test_concurrent_checkouts_never_double_sell_a_seat(client):
    organizer = signup(client, "org@example.com", role="organizer")
    event, seat_map = seated_event(client, organizer)
    seat_id = _seat(seat_map, 1, 3, 6)["id"]
    buyers = [signup(client, f"buyer{i}@example.com") for i in range(10)]

    def attempt(headers):
        with TestClient(fastapi_app) as own_client:
            return own_client.post(f"{API}/orders", headers=headers, json={"event_id": event["id"], "seat_ids": [seat_id]}).status_code

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(attempt, buyers))
    assert results.count(201) == 1 and results.count(409) == 9, results


@pytest.mark.skipif(engine.dialect.name == "sqlite", reason="real concurrency needs PostgreSQL (set TEST_DATABASE_URL)")
def test_concurrent_checkouts_never_oversell_general_admission(client):
    
    organizer = signup(client, "org@example.com", role="organizer")
    event = make_event(client, organizer, tickets=[{"name": "Few", "type": "free", "quantity": 5}])
    body = {"event_id": event["id"], "items": [{"ticket_category_id": event["ticket_types"][0]["id"], "quantity": 1}]}
    buyers = [signup(client, f"buyer{i}@example.com") for i in range(12)]

    def attempt(headers):
        with TestClient(fastapi_app) as own_client:
            return own_client.post(f"{API}/orders", headers=headers, json=body).status_code

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(attempt, buyers))
    assert results.count(201) == 5 and results.count(409) == 7, results
    sold = client.get(f"{API}/organizer/events/{event['id']}/ticket-types", headers=organizer).json()[0]["sold"]
    assert sold == 5
