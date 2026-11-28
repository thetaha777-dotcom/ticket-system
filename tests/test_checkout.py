from datetime import timedelta

from sqlalchemy import update

from app.core.database import SessionLocal, utcnow
from app.orders.models import Order
from app.orders.services import expire_stale_orders
from app.shared import mailer
from tests.helpers import API, activate_paid_sales, buy, future, make_event, paid_event, signup


def _counters(client, organizer, event) -> dict:
    return client.get(f"{API}/organizer/events/{event['id']}/ticket-types", headers=organizer).json()[0]


def _order_body(event, quantity=1):
    return {"event_id": event["id"], "items": [{"ticket_category_id": event["ticket_types"][0]["id"], "quantity": quantity}]}


def test_free_registration_issues_tickets_and_email(client):
    organizer = signup(client, "org@example.com", role="organizer")
    attendee = signup(client, "att@example.com", name="Dana K")
    event = make_event(client, organizer)

    order = buy(client, attendee, event, quantity=2, attendees=[{"name": "Dana K"}, {"name": "Guest One", "email": "guest@example.com"}])
    assert order["status"] == "completed" and order["total"] == 0 and order["payments"] == []
    assert [t["attendee_name"] for t in order["tickets"]] != [] and {t["attendee_name"] for t in order["tickets"]} == {"Dana K", "Guest One"}
    assert all(t["status"] == "valid" and t["qr_payload"].startswith("BFT1.") for t in order["tickets"])
    assert len({t["code"] for t in order["tickets"]}) == 2

    email = mailer.outbox[-1]
    assert email.to == "att@example.com" and "Your tickets" in email.subject
    assert [a[0].rsplit(".", 1)[1] for a in email.attachments] == ["pdf", "ics"]
    assert email.attachments[0][2].startswith(b"%PDF")

    assert _counters(client, organizer, event)["sold"] == 2
    attendees = client.get(f"{API}/organizer/events/{event['id']}/attendees", headers=organizer).json()
    assert len(attendees) == 2   # the organizer sees the registration in the attendee list
    assert len(client.get(f"{API}/tickets", headers=attendee).json()) == 2


def test_inventory_cannot_be_oversold(client):
    organizer = signup(client, "org@example.com", role="organizer")
    attendee = signup(client, "att@example.com")
    event = make_event(client, organizer, tickets=[{"name": "Limited", "type": "free", "quantity": 3, "order_limit": 2}])

    r = client.post(f"{API}/orders", headers=attendee, json=_order_body(event, 3))
    assert r.status_code == 400 and r.json()["code"] == "order_limit_exceeded"
    buy(client, attendee, event, quantity=2)
    r = client.post(f"{API}/orders", headers=attendee, json=_order_body(event, 2))
    assert r.status_code == 409 and r.json()["code"] == "sold_out"
    buy(client, attendee, event, quantity=1)
    public = client.get(f"{API}/events/{event['slug']}").json()["ticket_types"][0]
    assert public["available"] == 0 and public["unavailable_reason"] == "sold_out"


def test_event_capacity_limits_all_ticket_types_together(client):
    organizer = signup(client, "org@example.com", role="organizer")
    attendee = signup(client, "att@example.com")
    event = make_event(client, organizer, capacity=3, tickets=[
        {"name": "A", "type": "free", "quantity": 10}, {"name": "B", "type": "free", "quantity": 10}])
    buy(client, attendee, event, quantity=2, type_index=0)
    r = client.post(f"{API}/orders", headers=attendee, json={
        "event_id": event["id"], "items": [{"ticket_category_id": event["ticket_types"][1]["id"], "quantity": 2}]})
    assert r.status_code == 409 and r.json()["code"] == "event_full"


def test_paid_tickets_cannot_be_bought_before_activation(client):
    organizer = signup(client, "org@example.com", role="organizer")
    attendee = signup(client, "att@example.com")
    event = make_event(client, organizer, tickets=[{"name": "Standard", "type": "paid", "price": 4000, "quantity": 10}])

    public = client.get(f"{API}/events/{event['slug']}").json()
    assert public["paid_sales_active"] is False and public["ticket_types"][0]["unavailable_reason"] == "paid_sales_inactive"
    r = client.post(f"{API}/orders", headers=attendee, json=_order_body(event))
    assert r.status_code == 409 and r.json()["code"] == "paid_sales_inactive"


def test_uc2_activation_checklist(client):
    organizer = signup(client, "org@example.com", role="organizer")
    event = make_event(client, organizer, publish=False, tickets=[{"name": "Standard", "type": "paid", "price": 4000, "quantity": 10}])
    base = f"{API}/organizer/events/{event['id']}/activation"

    checklist = client.get(base, headers=organizer).json()
    assert checklist["is_active"] is False and checklist["fee_amount"] == 5000 and checklist["is_simulation"] is True
    assert {s["key"]: s["done"] for s in checklist["steps"]} == {
        "paid_ticket_type": True, "identity_verified": False, "payout_account": False, "fee_paid": False, "terms_accepted": False}

    # a declined fee payment is recorded but does not tick the step
    r = client.post(f"{base}/pay-fee", headers=organizer, json={"outcome": "failure"})
    assert r.status_code == 400 and r.json()["code"] == "payment_failed"

    done = activate_paid_sales(client, organizer, event["id"])
    assert done["is_active"] is True and all(s["done"] for s in done["steps"])
    notes = client.get(f"{API}/users/me/notifications", headers=organizer).json()
    assert [n["type"] for n in notes].count("payout_status") == 2   # payout account connected, paid sales active
    # the fee cannot be paid twice, and activation belongs to this event only
    assert client.post(f"{base}/pay-fee", headers=organizer, json={"outcome": "success"}).json()["code"] == "fee_already_paid"
    other = make_event(client, organizer, publish=False, tickets=[{"name": "Standard", "type": "paid", "price": 1000, "quantity": 5}])
    assert client.get(f"{API}/organizer/events/{other['id']}/activation", headers=organizer).json()["is_active"] is False


def test_uc3_paid_checkout_with_simulated_payment(client):
    organizer = signup(client, "org@example.com", role="organizer")
    attendee = signup(client, "att@example.com")
    event = paid_event(client, organizer, price=5000)

    r = client.post(f"{API}/orders/quote", json=_order_body(event, 2))
    assert r.json()["total"] == 10000

    order = client.post(f"{API}/orders", headers=attendee, json=_order_body(event, 2)).json()
    assert order["status"] == "pending" and order["total"] == 10000 and order["tickets"] == [] and order["expires_at"]
    assert _counters(client, organizer, event)["reserved"] == 2   # inventory is held during checkout

    # a failed payment creates no tickets and keeps the reservation
    failed = client.post(f"{API}/orders/{order['id']}/pay", headers=attendee, json={"outcome": "failure"}).json()
    assert failed["status"] == "pending" and failed["tickets"] == [] and failed["payments"][0]["status"] == "failed"
    assert "Payment failed" in mailer.outbox[-1].subject

    paid = client.post(f"{API}/orders/{order['id']}/pay", headers=attendee, json={"outcome": "success"}).json()
    assert paid["status"] == "completed" and len(paid["tickets"]) == 2
    assert paid["payments"][-1]["status"] == "succeeded" and paid["payments"][-1]["is_simulation"] is True
    counters = _counters(client, organizer, event)
    assert (counters["reserved"], counters["sold"]) == (0, 2)

    # paying twice is impossible
    r = client.post(f"{API}/orders/{order['id']}/pay", headers=attendee, json={"outcome": "success"})
    assert r.status_code == 409 and r.json()["code"] == "order_not_pending"

    sales = client.get(f"{API}/organizer/events/{event['id']}/sales", headers=organizer).json()
    assert sales["gross_sales"] == 10000 and sales["processing_fees"] == 300 and sales["estimated_payout"] == 9700


def test_abandoned_checkout_expires_and_releases_inventory(client):
    organizer = signup(client, "org@example.com", role="organizer")
    attendee = signup(client, "att@example.com")
    event = paid_event(client, organizer, quantity=2)
    order = client.post(f"{API}/orders", headers=attendee, json=_order_body(event, 2)).json()
    assert client.post(f"{API}/orders", headers=attendee, json=_order_body(event, 1)).json()["code"] == "sold_out"

    with SessionLocal() as db:   # pretend the hold time has passed
        db.execute(update(Order).values(expires_at=utcnow() - timedelta(minutes=1)))
        db.commit()
        assert expire_stale_orders(db) == 1

    assert _counters(client, organizer, event)["reserved"] == 0
    r = client.post(f"{API}/orders/{order['id']}/pay", headers=attendee, json={"outcome": "success"})
    assert r.status_code == 409   # the expired order can no longer be paid
    assert client.get(f"{API}/orders/{order['id']}", headers=attendee).json()["tickets"] == []
    buy(client, attendee, event, quantity=2)   # the tickets are on sale again


def test_sales_windows(client):
    organizer = signup(client, "org@example.com", role="organizer")
    attendee = signup(client, "att@example.com")
    event = make_event(client, organizer, registration_open_at=future(1), tickets=[
        {"name": "Early", "type": "free", "quantity": 10}])
    r = client.post(f"{API}/orders", headers=attendee, json=_order_body(event))
    assert r.status_code == 409 and r.json()["code"] == "registration_not_open"

    event2 = make_event(client, organizer, title="Second", tickets=[
        {"name": "Later", "type": "free", "quantity": 10, "sale_start": future(2)}])
    r = client.post(f"{API}/orders", headers=attendee, json=_order_body(event2))
    assert r.status_code == 409 and r.json()["code"] == "sales_not_started"


def test_orders_are_private(client):
    organizer = signup(client, "org@example.com", role="organizer")
    buyer = signup(client, "buyer@example.com")
    stranger = signup(client, "stranger@example.com")
    event = make_event(client, organizer)
    order = buy(client, buyer, event)
    assert client.get(f"{API}/orders/{order['id']}", headers=stranger).status_code == 403
    assert client.get(f"{API}/tickets/{order['tickets'][0]['id']}", headers=stranger).status_code == 403
    assert client.get(f"{API}/orders/{order['id']}", headers=organizer).status_code == 200   # organizer of the event may
    assert client.get(f"{API}/orders", headers=stranger).json() == []
