from tests.helpers import API, activate_paid_sales, buy, future, make_event, paid_event, signup


def test_uc11_event_analytics_add_up(client):
    organizer = signup(client, "org@example.com", role="organizer")
    alice, bob, carol = (signup(client, f"{n}@example.com") for n in ("alice", "bob", "carol"))
    event = make_event(client, organizer, publish=False, tickets=[
        {"name": "Standard", "type": "paid", "price": 5000, "quantity": 40},
        {"name": "Student", "type": "free", "quantity": 10}])
    activate_paid_sales(client, organizer, event["id"])
    client.post(f"{API}/organizer/events/{event['id']}/publish", headers=organizer)
    campaign = client.post(f"{API}/organizer/events/{event['id']}/campaigns", headers=organizer, json={
        "name": "Launch", "discount_type": "percent", "discount_value": 10, "code": "LAUNCH"}).json()

    buy(client, alice, event, quantity=2)                                       # 10 000
    promo_order = buy(client, bob, event, quantity=2, promo_code="LAUNCH")      # 10 000 - 1 000
    refunded = buy(client, carol, event, quantity=1)                            # 5 000, refunded below
    free_order = buy(client, carol, event, quantity=1, type_index=1)
    client.post(f"{API}/orders/{refunded['id']}/refund", headers=organizer, json={})
    client.post(f"{API}/checkin/events/{event['id']}/scan", headers=organizer,
                json={"qr_payload": promo_order["tickets"][0]["qr_payload"]})

    data = client.get(f"{API}/organizer/events/{event['id']}/analytics", headers=organizer).json()
    assert data["capacity"] == {"total": 50, "sold": 5, "remaining": 45, "percent_sold": 10.0}
    assert data["revenue"] == {"gross": 25000, "discounts": 1000, "refunds": 5000, "net": 19000}
    assert len(data["sales_over_time"]) == 1
    assert data["sales_over_time"][0]["tickets"] == 5 and data["sales_over_time"][0]["revenue"] == 19000
    by_type = {row["name"]: row for row in data["by_ticket_type"]}
    assert (by_type["Standard"]["sold"], by_type["Standard"]["revenue"]) == (4, 19000)
    assert (by_type["Student"]["sold"], by_type["Student"]["revenue"]) == (1, 0)
    assert data["campaigns"] == [{"campaign_id": campaign["id"], "name": "Launch", "code": "LAUNCH", "is_active": True,
                                  "redemptions": 1, "tickets": 2, "gross": 10000, "discount": 1000, "net": 9000}]
    assert data["attendance"] == {"registered": 5, "checked_in": 1, "absent": 4, "percent": 20.0}
    assert data["is_simulation"] is True

    # filters: one ticket type, and a date range with no sales
    only_free = client.get(f"{API}/organizer/events/{event['id']}/analytics", headers=organizer,
                           params={"ticket_type_id": event["ticket_types"][1]["id"]}).json()
    assert only_free["capacity"]["total"] == 10 and only_free["revenue"]["gross"] == 0 and len(only_free["by_ticket_type"]) == 1
    empty = client.get(f"{API}/organizer/events/{event['id']}/analytics", headers=organizer,
                       params={"date_from": future(1)}).json()
    assert empty["sales_over_time"] == [] and empty["revenue"]["net"] == 0

    summary = client.get(f"{API}/organizer/summary", headers=organizer).json()
    assert summary == {"events": 1, "upcoming_events": 1, "tickets_sold": 5, "net_revenue": 19000, "checked_in": 1}
    assert free_order["status"] == "completed"


def test_history_timeline_records_and_filters(client):
    organizer = signup(client, "org@example.com", role="organizer", name="Olzhas")
    event = make_event(client, organizer)
    ticket_type = event["ticket_types"][0]
    client.patch(f"{API}/organizer/events/{event['id']}/ticket-types/{ticket_type['id']}", headers=organizer, json={"quantity": 250})
    client.patch(f"{API}/organizer/events/{event['id']}", headers=organizer, json={"capacity": 200})

    history = client.get(f"{API}/organizer/events/{event['id']}/history", headers=organizer).json()
    assert [h["action"] for h in reversed(history)] == [
        "event.created", "ticket_type.created", "event.published", "ticket_type.updated", "event.updated"]
    entry = history[1]
    assert entry["actor_name"] == "Olzhas" and entry["entity_type"] == "ticket_type" and "100 → 250" in entry["description"]
    assert set(entry) >= {"created_at", "actor_id", "action", "entity_id", "description"}

    only_types = client.get(f"{API}/organizer/events/{event['id']}/history", headers=organizer, params={"action": "ticket_type"}).json()
    assert len(only_types) == 2
    assert client.get(f"{API}/organizer/events/{event['id']}/history", headers=organizer, params={"date_from": future(1)}).json() == []
    # there is no way to change or delete history through the API
    assert client.delete(f"{API}/organizer/events/{event['id']}/history", headers=organizer).status_code == 405


def test_admin_suspends_event_and_sales_stop(client):
    """Success criterion: administrators can suspend a suspicious event and stop further sales."""
    organizer = signup(client, "org@example.com", role="organizer")
    attendee = signup(client, "att@example.com")
    admin = signup(client, "admin@example.com", role="platform_admin")
    event = make_event(client, organizer)
    body = {"event_id": event["id"], "items": [{"ticket_category_id": event["ticket_types"][0]["id"], "quantity": 1}]}

    assert client.post(f"{API}/admin/events/{event['id']}/suspend", headers=admin, json={"reason": "Suspected fraud"}).status_code == 200
    r = client.post(f"{API}/orders", headers=attendee, json=body)
    assert r.status_code == 409 and r.json()["code"] == "event_unavailable"
    assert client.get(f"{API}/events").json()["total"] == 0
    assert client.get(f"{API}/admin/events", headers=admin, params={"suspended": True}).json()["items"][0]["suspended_reason"] == "Suspected fraud"

    assert client.post(f"{API}/admin/events/{event['id']}/unsuspend", headers=admin).status_code == 200
    assert client.post(f"{API}/orders", headers=attendee, json=body).status_code == 201


def test_admin_suspends_paid_sales_only(client):
    organizer = signup(client, "org@example.com", role="organizer")
    attendee = signup(client, "att@example.com")
    admin = signup(client, "admin@example.com", role="platform_admin")
    event = paid_event(client, organizer)
    body = {"event_id": event["id"], "items": [{"ticket_category_id": event["ticket_types"][0]["id"], "quantity": 1}]}
    pending = client.post(f"{API}/orders", headers=attendee, json=body).json()

    activation = client.get(f"{API}/admin/activations", headers=admin).json()[0]
    assert activation["status"] == "active" and activation["fee_paid"] is True
    assert client.post(f"{API}/admin/activations/{activation['id']}/suspend", headers=admin, json={"reason": "Policy review"}).status_code == 200

    assert client.post(f"{API}/orders", headers=attendee, json=body).json()["code"] == "paid_sales_inactive"
    # a checkout that was already open cannot be paid either
    assert client.post(f"{API}/orders/{pending['id']}/pay", headers=attendee, json={"outcome": "success"}).json()["code"] == "paid_sales_inactive"

    assert client.post(f"{API}/admin/activations/{activation['id']}/reinstate", headers=admin).status_code == 200
    assert client.post(f"{API}/orders/{pending['id']}/pay", headers=attendee, json={"outcome": "success"}).json()["status"] == "completed"


def test_admin_overview_search_settings_and_exports(client):
    organizer = signup(client, "org@example.com", role="organizer")
    attendee = signup(client, "att@example.com", name="Madina")
    admin = signup(client, "admin@example.com", role="platform_admin")
    event = paid_event(client, organizer, price=4000)
    order = buy(client, attendee, event)
    failing = client.post(f"{API}/orders", headers=attendee, json={
        "event_id": event["id"], "items": [{"ticket_category_id": event["ticket_types"][0]["id"], "quantity": 1}]}).json()
    client.post(f"{API}/orders/{failing['id']}/pay", headers=attendee, json={"outcome": "failure"})

    overview = client.get(f"{API}/admin/overview", headers=admin).json()
    assert overview["users"] == 3 and overview["orders_completed"] == 1 and overview["gross_sales"] == 4000
    assert overview["payment_failures"] == 1 and overview["activations_active"] == 1

    assert client.get(f"{API}/admin/users", headers=admin, params={"q": "madina"}).json()["total"] == 1
    assert client.get(f"{API}/admin/orders", headers=admin, params={"q": order["number"]}).json()["items"][0]["buyer_name"] == "Madina"
    failed = client.get(f"{API}/admin/payments", headers=admin, params={"status": "failed"}).json()
    assert len(failed) == 1 and failed[0]["is_simulation"] is True
    # payments are searchable by reference, order number and payer
    by_order = client.get(f"{API}/admin/payments", headers=admin, params={"q": order["number"]}).json()
    assert by_order and all(p["order_id"] == order["id"] for p in by_order)
    reference = by_order[0]["provider_reference"]
    assert [p["id"] for p in client.get(f"{API}/admin/payments", headers=admin, params={"q": reference}).json()] == [by_order[0]["id"]]
    assert client.get(f"{API}/admin/payments", headers=admin, params={"q": "madina"}).json()
    assert client.get(f"{API}/admin/payments", headers=admin, params={"q": "nobody-by-this-name"}).json() == []

    settings = client.put(f"{API}/admin/settings", headers=admin, json={"activation_fee_kzt": 7500}).json()
    assert settings == {"activation_fee_kzt": 7500, "processing_fee_percent": 3.0, "order_hold_minutes": 10}
    new_event = make_event(client, organizer, publish=False, title="Next", tickets=[
        {"name": "Standard", "type": "paid", "price": 1000, "quantity": 5}])
    assert client.get(f"{API}/organizer/events/{new_event['id']}/activation", headers=organizer).json()["fee_amount"] == 7500

    csv_text = client.get(f"{API}/admin/export/orders.csv", headers=admin)
    assert csv_text.status_code == 200 and order["number"] in csv_text.text and csv_text.text.startswith("number,status")
    assert client.get(f"{API}/admin/export/unknown.csv", headers=admin).status_code == 404
    assert any(a["action"] == "settings.updated" for a in client.get(f"{API}/admin/audit-log", headers=admin).json())
