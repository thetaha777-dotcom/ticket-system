from tests.helpers import API, buy, make_event, paid_event, signup


def _scan(client, headers, event, payload, **extra):
    r = client.post(f"{API}/checkin/events/{event['id']}/scan", headers=headers, json={"qr_payload": payload, **extra})
    assert r.status_code == 200, r.text
    return r.json()


def _staffed_event(client, paid=False):
    organizer = signup(client, "org@example.com", role="organizer")
    staff = signup(client, "door@example.com", name="Door Staff")
    event = paid_event(client, organizer) if paid else make_event(client, organizer)
    r = client.post(f"{API}/organizer/events/{event['id']}/staff", headers=organizer, json={"email": "door@example.com"})
    assert r.status_code == 201, r.text
    return organizer, staff, event


def test_uc4_scan_checks_in_once_and_undo_reverses_it(client):
    organizer, staff, event = _staffed_event(client)
    attendee = signup(client, "att@example.com", name="Aruzhan")
    ticket = buy(client, attendee, event, quantity=2)["tickets"][0]

    # the staff member sees only the assigned event
    events = client.get(f"{API}/checkin/events", headers=staff).json()
    assert [e["id"] for e in events] == [event["id"]] and events[0]["stats"] == {"registered": 2, "checked_in": 0, "remaining": 2}

    # verify-only does not consume the ticket
    assert _scan(client, staff, event, ticket["qr_payload"], check_in=False)["result"] == "valid"

    first = _scan(client, staff, event, ticket["qr_payload"])
    assert first["result"] == "valid" and first["ticket"]["attendee_name"] == "Aruzhan"
    assert first["stats"] == {"registered": 2, "checked_in": 1, "remaining": 1}
    counters = client.get(f"{API}/organizer/events/{event['id']}/ticket-types", headers=organizer).json()[0]
    assert (counters["sold"], counters["checked_in"]) == (2, 1)

    second = _scan(client, staff, event, ticket["qr_payload"])
    assert second["result"] == "already_used" and second["stats"]["checked_in"] == 1

    undone = client.post(f"{API}/checkin/events/{event['id']}/tickets/{ticket['id']}/undo", headers=staff).json()
    assert undone["ticket"]["status"] == "valid" and undone["stats"]["checked_in"] == 0
    assert _scan(client, staff, event, ticket["qr_payload"])["result"] == "valid"   # usable again after the reversal

    actions = [r["action"] for r in client.get(f"{API}/checkin/events/{event['id']}/recent", headers=staff).json()]
    assert actions == ["check_in", "undo", "check_in"]
    assert client.get(f"{API}/organizer/events/{event['id']}/ticket-types", headers=organizer).json()[0]["checked_in"] == 1


def test_forged_and_foreign_codes_are_rejected(client):
    organizer, staff, event = _staffed_event(client)
    attendee = signup(client, "att@example.com")
    payload = buy(client, attendee, event)["tickets"][0]["qr_payload"]

    tampered = payload[:-1] + ("A" if payload[-1] != "A" else "B")
    assert _scan(client, staff, event, tampered)["result"] == "invalid"
    assert _scan(client, staff, event, "hello world")["result"] == "invalid"
    assert _scan(client, staff, event, "BFT1.00000000000000000000000000000000.AAAAAAAAAAAAAAAAAAAAAAAA")["result"] == "invalid"

    other_event = make_event(client, organizer, title="Another event")
    assert _scan(client, organizer, other_event, payload)["result"] == "wrong_event"
    assert _scan(client, staff, event, payload)["result"] == "valid"   # the real one still works


def test_campaign_qr_is_never_accepted_as_a_ticket(client):
    """Success criterion: the scanner rejects Campaign QR codes while accepting ticket QR codes."""
    organizer, staff, event = _staffed_event(client, paid=True)
    campaign = client.post(f"{API}/organizer/events/{event['id']}/campaigns", headers=organizer, json={
        "name": "Promo", "discount_type": "percent", "discount_value": 10}).json()
    result = _scan(client, staff, event, campaign["link"])
    assert result["result"] == "campaign_qr" and result["ticket"] is None and result["stats"]["checked_in"] == 0
    assert _scan(client, staff, event, campaign["code"])["result"] == "invalid"


def test_cancelled_and_refunded_tickets_are_refused(client):
    organizer, staff, event = _staffed_event(client, paid=True)
    attendee = signup(client, "att@example.com")
    refunded_order = buy(client, attendee, event)
    client.post(f"{API}/orders/{refunded_order['id']}/refund", headers=organizer, json={"reason": "Requested"})
    assert _scan(client, staff, event, refunded_order["tickets"][0]["qr_payload"])["result"] == "refunded"

    free_event = make_event(client, organizer, title="Free one")
    cancelled_order = buy(client, attendee, free_event)
    client.post(f"{API}/orders/{cancelled_order['id']}/cancel", headers=attendee, json={})
    assert _scan(client, organizer, free_event, cancelled_order["tickets"][0]["qr_payload"])["result"] == "cancelled"


def test_only_assigned_staff_can_scan_and_undo_needs_permission(client):
    organizer, staff, event = _staffed_event(client)
    attendee = signup(client, "att@example.com")
    ticket = buy(client, attendee, event)["tickets"][0]

    outsider = signup(client, "outsider@example.com")
    r = client.post(f"{API}/checkin/events/{event['id']}/scan", headers=outsider, json={"qr_payload": ticket["qr_payload"]})
    assert r.status_code == 403 and r.json()["code"] == "not_event_staff"
    assert client.get(f"{API}/checkin/events", headers=outsider).json() == []

    limited = signup(client, "limited@example.com")
    client.post(f"{API}/organizer/events/{event['id']}/staff", headers=organizer, json={"email": "limited@example.com", "can_undo": False})
    assert _scan(client, limited, event, ticket["qr_payload"])["result"] == "valid"
    r = client.post(f"{API}/checkin/events/{event['id']}/tickets/{ticket['id']}/undo", headers=limited)
    assert r.status_code == 403 and r.json()["code"] == "undo_not_allowed"

    # removing the assignment removes access
    assignments = client.get(f"{API}/organizer/events/{event['id']}/staff", headers=organizer).json()
    limited_id = next(a["id"] for a in assignments if a["user"]["email"] == "limited@example.com")
    assert client.delete(f"{API}/organizer/events/{event['id']}/staff/{limited_id}", headers=organizer).status_code == 204
    assert client.get(f"{API}/checkin/events/{event['id']}/stats", headers=limited).status_code == 403


def test_manual_search_and_check_in(client):
    organizer, staff, event = _staffed_event(client)
    signup(client, "aruzhan@example.com", name="Aruzhan Bekova")
    signup(client, "timur@example.com", name="Timur Sadykov")
    from tests.helpers import login
    buy(client, login(client, "aruzhan@example.com"), event)
    order = buy(client, login(client, "timur@example.com"), event)

    found = client.get(f"{API}/checkin/events/{event['id']}/attendees", headers=staff, params={"q": "sadyk"}).json()
    assert [t["attendee_name"] for t in found] == ["Timur Sadykov"]
    assert len(client.get(f"{API}/checkin/events/{event['id']}/attendees", headers=staff, params={"q": order["number"]}).json()) == 1

    r = client.post(f"{API}/checkin/events/{event['id']}/tickets/{found[0]['id']}/check-in", headers=staff)
    assert r.status_code == 200 and r.json()["ticket"]["status"] == "checked_in"
    r = client.post(f"{API}/checkin/events/{event['id']}/tickets/{found[0]['id']}/check-in", headers=staff)
    assert r.status_code == 409 and r.json()["code"] == "ticket_checked_in"
