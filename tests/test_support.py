from app.shared import mailer
from tests.helpers import API, buy, make_event, signup


def _open(client, headers, **body):
    payload = {"category": "ticket_delivery", "subject": "I did not get my ticket", "message": "Please help"}
    payload.update(body)
    return client.post(f"{API}/support/cases", headers=headers, json=payload)


def test_uc9_attendee_and_organizer_exchange_messages(client):
    organizer = signup(client, "org@example.com", role="organizer", name="Organizer")
    attendee = signup(client, "att@example.com", name="Attendee")
    event = make_event(client, organizer)
    order = buy(client, attendee, event)
    mailer.outbox.clear()

    # opened from the ticket page: order and event context are filled in automatically
    r = _open(client, attendee, ticket_id=order["tickets"][0]["id"])
    assert r.status_code == 201, r.text
    case = r.json()
    assert case["status"] == "open" and case["kind"] == "attendee" and case["number"].startswith("SC-")
    assert case["context"]["order_number"] == order["number"] and case["context"]["event_title"] == event["title"]
    assert case["context"]["ticket_code"] == order["tickets"][0]["code"]
    assert mailer.outbox[-1].to == "org@example.com"   # the organizer is told about the new request

    # the organizer finds it in the queue of their events and replies
    managed = client.get(f"{API}/support/cases", headers=organizer, params={"scope": "managed"}).json()
    assert [c["id"] for c in managed] == [case["id"]] and managed[0]["can_manage"] is True
    reply = client.post(f"{API}/support/cases/{case['id']}/messages", headers=organizer, json={"body": "Resent, check spam"}).json()
    assert reply["status"] == "in_progress"   # first staff reply moves Open -> In Progress
    assert [m["from_staff"] for m in reply["messages"]] == [False, True]
    assert mailer.outbox[-1].to == "att@example.com"

    # status change by staff, visible to the attendee
    r = client.patch(f"{API}/support/cases/{case['id']}", headers=organizer, json={"status": "resolved"})
    assert r.json()["status"] == "resolved"
    mine = client.get(f"{API}/support/cases", headers=attendee).json()
    assert mine[0]["status"] == "resolved" and mine[0]["can_manage"] is False and mine[0]["message_count"] == 2

    # a new message from the attendee reopens the case
    again = client.post(f"{API}/support/cases/{case['id']}/messages", headers=attendee, json={"body": "Still nothing"}).json()
    assert again["status"] == "in_progress" and len(again["messages"]) == 3

    actions = [h["action"] for h in client.get(f"{API}/organizer/events/{event['id']}/history", headers=organizer,
                                               params={"action": "support"}).json()]
    assert actions.count("support.status_changed") == 3 and "support.opened" in actions


def test_cases_are_hidden_from_unrelated_users(client):
    organizer = signup(client, "org@example.com", role="organizer")
    other_organizer = signup(client, "other@example.com", role="organizer")
    attendee, stranger = signup(client, "att@example.com"), signup(client, "stranger@example.com")
    admin = signup(client, "admin@example.com", role="platform_admin")
    event = make_event(client, organizer)
    case = _open(client, attendee, event_id=event["id"], category="event_information").json()

    for headers in (stranger, other_organizer, admin):   # admins see attendee cases only after escalation
        assert client.get(f"{API}/support/cases/{case['id']}", headers=headers).status_code == 403
        assert client.post(f"{API}/support/cases/{case['id']}/messages", headers=headers, json={"body": "hi"}).status_code == 403
    # the attendee cannot change the status of their own case
    r = client.patch(f"{API}/support/cases/{case['id']}", headers=attendee, json={"status": "resolved"})
    assert r.status_code == 403
    # an attendee cannot open a case about somebody else's order
    order = buy(client, stranger, event)
    assert _open(client, attendee, order_id=order["id"]).status_code == 403

    # after escalation the platform admins can see and answer it
    assert client.patch(f"{API}/support/cases/{case['id']}", headers=organizer, json={"is_escalated": True}).json()["is_escalated"]
    assert client.get(f"{API}/support/cases/{case['id']}", headers=admin).status_code == 200
    assert [c["id"] for c in client.get(f"{API}/support/cases", headers=admin, params={"scope": "platform"}).json()] == [case["id"]]


def test_organizer_writes_to_platform_support(client):
    organizer = signup(client, "org@example.com", role="organizer")
    attendee = signup(client, "att@example.com")
    admin = signup(client, "admin@example.com", role="platform_admin")

    assert _open(client, attendee, kind="organizer", category="account").status_code == 403
    assert _open(client, attendee, category="account").json()["code"] == "context_required"   # attendee cases need a context

    case = _open(client, organizer, kind="organizer", category="activation", subject="Activation question").json()
    assert case["kind"] == "organizer"
    assert mailer.outbox[-1].to == "admin@example.com"

    queue = client.get(f"{API}/support/cases", headers=admin, params={"scope": "platform"}).json()
    assert len(queue) == 1 and queue[0]["can_manage"] is True
    admin_id = client.get(f"{API}/users/me", headers=admin).json()["id"]
    updated = client.patch(f"{API}/support/cases/{case['id']}", headers=admin, json={
        "status": "waiting_for_customer", "assigned_to_id": admin_id}).json()
    assert updated["status"] == "waiting_for_customer" and updated["assigned_to"]["email"] == "admin@example.com"
    assert client.get(f"{API}/support/cases", headers=organizer, params={"scope": "platform"}).status_code == 403

    # in-app notification for the organizer
    notes = client.get(f"{API}/users/me/notifications", headers=organizer).json()
    assert any(n["type"] == "support_status" and not n["is_read"] for n in notes)
    assert client.post(f"{API}/users/me/notifications/read-all", headers=organizer).status_code == 204
    assert all(n["is_read"] for n in client.get(f"{API}/users/me/notifications", headers=organizer).json())
