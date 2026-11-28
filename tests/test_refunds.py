from app.shared import mailer
from tests.helpers import API, buy, make_event, paid_event, signup


def test_uc5_organizer_refunds_an_order(client):
    organizer = signup(client, "org@example.com", role="organizer")
    attendee = signup(client, "att@example.com")
    event = paid_event(client, organizer, price=6000)
    order = buy(client, attendee, event, quantity=2)
    assert order["refund_eligible"] is True

    # an attendee cannot refund their own order
    r = client.post(f"{API}/orders/{order['id']}/refund", headers=attendee, json={})
    assert r.status_code == 403

    refunded = client.post(f"{API}/orders/{order['id']}/refund", headers=organizer, json={"reason": "Cannot attend"}).json()
    assert refunded["status"] == "refunded" and refunded["refunds"][0]["amount"] == 12000
    assert refunded["refunds"][0]["is_simulation"] is True
    assert all(t["status"] == "refunded" and t["qr_payload"] is None for t in refunded["tickets"])
    counters = client.get(f"{API}/organizer/events/{event['id']}/ticket-types", headers=organizer).json()[0]
    assert (counters["sold"], counters["refunded"], counters["available"]) == (0, 2, counters["quantity"])   # back on sale
    assert "Refund completed" in mailer.outbox[-1].subject and mailer.outbox[-1].to == "att@example.com"

    counters = client.get(f"{API}/organizer/events/{event['id']}/ticket-types", headers=organizer).json()[0]
    assert (counters["sold"], counters["refunded"], counters["available"]) == (0, 2, 50)   # tickets are back on sale

    sales = client.get(f"{API}/organizer/events/{event['id']}/sales", headers=organizer).json()
    assert (sales["gross_sales"], sales["refunds"], sales["net_revenue"], sales["processing_fees"]) == (12000, 12000, 0, 0)

    # refunding twice is impossible, and the invalid ticket cannot be downloaded
    assert client.post(f"{API}/orders/{order['id']}/refund", headers=organizer, json={}).status_code == 409
    assert client.get(f"{API}/tickets/{order['tickets'][0]['id']}/pdf", headers=attendee).status_code == 409

    actions = [h["action"] for h in client.get(f"{API}/organizer/events/{event['id']}/history", headers=organizer).json()]
    assert "refund.completed" in actions and "payment.succeeded" in actions


def test_refund_policy_none_blocks_refunds(client):
    organizer = signup(client, "org@example.com", role="organizer")
    attendee = signup(client, "att@example.com")
    event = paid_event(client, organizer, refund_policy="none")
    order = buy(client, attendee, event)
    assert order["refund_eligible"] is False
    r = client.post(f"{API}/orders/{order['id']}/refund", headers=organizer, json={})
    assert r.status_code == 409 and r.json()["code"] == "refund_not_allowed"


def test_free_registration_can_be_cancelled_by_attendee_or_organizer(client):
    organizer = signup(client, "org@example.com", role="organizer")
    alice, bob = signup(client, "alice@example.com"), signup(client, "bob@example.com")
    event = make_event(client, organizer)
    first, second = buy(client, alice, event), buy(client, bob, event)

    assert client.post(f"{API}/orders/{first['id']}/cancel", headers=alice, json={}).json()["status"] == "cancelled"
    cancelled = client.post(f"{API}/orders/{second['id']}/cancel", headers=organizer, json={"reason": "Duplicate"}).json()
    assert cancelled["status"] == "cancelled" and cancelled["tickets"][0]["status"] == "cancelled"
    assert client.get(f"{API}/organizer/events/{event['id']}/ticket-types", headers=organizer).json()[0]["sold"] == 0
    # a paid order must be refunded instead
    paid = paid_event(client, organizer, title="Paid one")
    order = buy(client, alice, paid)
    assert client.post(f"{API}/orders/{order['id']}/cancel", headers=alice, json={}).json()["code"] == "use_refund"


def test_cancelling_an_event_refunds_and_notifies_everyone(client):
    organizer = signup(client, "org@example.com", role="organizer")
    alice, bob = signup(client, "alice@example.com"), signup(client, "bob@example.com")
    event = paid_event(client, organizer, price=7000, refund_policy="none")
    paid_order = buy(client, alice, event)
    pending_order = buy(client, bob, event, pay=False)
    mailer.outbox.clear()

    r = client.post(f"{API}/organizer/events/{event['id']}/cancel", headers=organizer, json={"reason": "Artist is ill"})
    assert r.status_code == 200 and r.json()["status"] == "cancelled" and r.json()["event_class"] == "cancelled"

    # refunded even though the policy says "no refunds", because the event itself was cancelled
    assert client.get(f"{API}/orders/{paid_order['id']}", headers=alice).json()["status"] == "refunded"
    assert client.get(f"{API}/orders/{pending_order['id']}", headers=bob).json()["status"] == "cancelled"

    emails = [m for m in mailer.outbox if m.to == "alice@example.com"]
    assert len(emails) == 1 and "has been cancelled" in emails[0].subject
    ics = emails[0].attachments[0][2].decode()
    assert "METHOD:CANCEL" in ics and "STATUS:CANCELLED" in ics

    public = client.get(f"{API}/events/{event['slug']}").json()
    assert public["status"] == "cancelled" and public["is_on_sale"] is False
    assert client.post(f"{API}/organizer/events/{event['id']}/cancel", headers=organizer, json={}).status_code == 409
