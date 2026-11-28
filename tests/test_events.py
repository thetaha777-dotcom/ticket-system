from tests.helpers import API, buy, future, make_event, make_venue, signup


def test_uc1_organizer_creates_and_publishes_a_free_event(client):
    """UC1: details -> free ticket type -> preview -> publish -> attendees can register without payment."""
    organizer = signup(client, "org@example.com", role="organizer")
    event = make_event(client, organizer, publish=False)
    assert event["status"] == "draft"

    # the draft is invisible to the public, but the organizer can preview it
    assert client.get(f"{API}/events/{event['slug']}").status_code == 404
    assert client.get(f"{API}/events/{event['slug']}", headers=organizer).json()["can_manage"] is True
    assert client.get(f"{API}/events").json()["total"] == 0

    assert client.post(f"{API}/organizer/events/{event['id']}/publish", headers=organizer).json()["status"] == "published"
    listing = client.get(f"{API}/events").json()
    assert listing["total"] == 1 and listing["items"][0]["price_from"] == 0

    attendee = signup(client, "att@example.com")
    order = buy(client, attendee, event)
    assert order["status"] == "completed" and order["total"] == 0 and len(order["tickets"]) == 1


def test_publishing_needs_a_verified_email_and_a_ticket_type(client):
    unverified = signup(client, "org@example.com", role="organizer", verified=False)
    event = make_event(client, unverified, publish=False)
    r = client.post(f"{API}/organizer/events/{event['id']}/publish", headers=unverified)
    assert r.status_code == 400 and r.json()["code"] == "email_not_verified"

    verified = signup(client, "org2@example.com", role="organizer")
    empty = make_event(client, verified, publish=False, tickets=[])
    r = client.post(f"{API}/organizer/events/{empty['id']}/publish", headers=verified)
    assert r.status_code == 400 and r.json()["code"] == "no_ticket_types"


def test_event_dates_are_validated(client):
    organizer = signup(client, "org@example.com", role="organizer")
    venue = make_venue(client, organizer)
    r = client.post(f"{API}/organizer/events", headers=organizer, json={
        "title": "Backwards", "category": "Music", "venue_id": venue["id"], "start_at": future(10), "end_at": future(9)})
    assert r.status_code == 422


def test_visibility_public_unlisted_private(client):
    organizer = signup(client, "org@example.com", role="organizer")
    unlisted = make_event(client, organizer, title="Unlisted", visibility="unlisted")
    private = make_event(client, organizer, title="Private", visibility="private")

    assert client.get(f"{API}/events").json()["total"] == 0                      # neither is listed
    assert client.get(f"{API}/events/{unlisted['slug']}").status_code == 200      # link is enough
    r = client.get(f"{API}/events/{private['slug']}")
    assert r.status_code == 403 and r.json()["code"] == "event_private"
    r = client.get(f"{API}/events/{private['slug']}", params={"access_key": private["access_key"]})
    assert r.status_code == 200


def test_search_filters(client):
    organizer = signup(client, "org@example.com", role="organizer")
    make_event(client, organizer, title="Jazz Evening", category="Music")
    make_event(client, organizer, title="Startup Meetup", category="Business")
    assert client.get(f"{API}/events", params={"q": "jazz"}).json()["total"] == 1
    assert client.get(f"{API}/events", params={"category": "Business"}).json()["items"][0]["title"] == "Startup Meetup"
    assert client.get(f"{API}/events/filters").json() == {"categories": ["Business", "Music"], "cities": ["Almaty"]}


def test_only_the_owner_manages_an_event(client):
    owner = signup(client, "owner@example.com", role="organizer")
    other = signup(client, "other@example.com", role="organizer")
    event = make_event(client, owner)
    for call in (
        client.get(f"{API}/organizer/events/{event['id']}", headers=other),
        client.patch(f"{API}/organizer/events/{event['id']}", headers=other, json={"title": "Hijacked"}),
        client.get(f"{API}/organizer/events/{event['id']}/orders", headers=other),
        client.get(f"{API}/organizer/events/{event['id']}/analytics", headers=other),
        client.get(f"{API}/organizer/events/{event['id']}/history", headers=other),
    ):
        assert call.status_code == 403 and call.json()["code"] == "not_event_manager"


def test_unpublish_pauses_registration(client):
    organizer = signup(client, "org@example.com", role="organizer")
    attendee = signup(client, "att@example.com")
    event = make_event(client, organizer)
    assert client.post(f"{API}/organizer/events/{event['id']}/unpublish", headers=organizer).json()["status"] == "unpublished"
    r = client.post(f"{API}/orders", headers=attendee, json={
        "event_id": event["id"], "items": [{"ticket_category_id": event["ticket_types"][0]["id"], "quantity": 1}]})
    assert r.status_code == 409 and r.json()["code"] == "event_unavailable"


def test_ticket_type_rules(client):
    organizer = signup(client, "org@example.com", role="organizer")
    event = make_event(client, organizer)
    base = f"{API}/organizer/events/{event['id']}/ticket-types"
    # a paid type must have a price
    assert client.post(base, headers=organizer, json={"name": "VIP", "type": "paid", "price": 0, "quantity": 5}).status_code == 422

    attendee = signup(client, "att@example.com")
    buy(client, attendee, event, quantity=3)
    ticket_type = event["ticket_types"][0]
    # quantity cannot drop below what is already sold; a type with orders cannot be deleted, only hidden
    r = client.patch(f"{base}/{ticket_type['id']}", headers=organizer, json={"quantity": 2})
    assert r.status_code == 409 and r.json()["code"] == "quantity_below_sold"
    assert client.delete(f"{base}/{ticket_type['id']}", headers=organizer).json()["code"] == "ticket_type_in_use"
    assert client.patch(f"{base}/{ticket_type['id']}", headers=organizer, json={"hidden": True}).json()["hidden"] is True
    assert client.get(f"{API}/events/{event['slug']}").json()["ticket_types"] == []

    counters = client.get(base, headers=organizer).json()[0]
    assert (counters["sold"], counters["available"], counters["reserved"]) == (3, 97, 0)


def test_uc12_duplicate_copies_configuration_but_no_transactions(client):
    organizer = signup(client, "org@example.com", role="organizer")
    attendee = signup(client, "att@example.com")
    event = make_event(client, organizer)
    buy(client, attendee, event, quantity=2)

    r = client.post(f"{API}/organizer/events/{event['id']}/duplicate", headers=organizer)
    assert r.status_code == 201
    copy = r.json()
    assert copy["status"] == "draft" and copy["duplicated_from_id"] == event["id"] and copy["title"].endswith("(copy)")
    assert copy["ticket_types"][0]["name"] == "Free entry" and copy["ticket_types"][0]["sold"] == 0
    assert client.get(f"{API}/organizer/events/{copy['id']}/orders", headers=organizer).json()["total"] == 0
    # the original keeps its records
    assert client.get(f"{API}/organizer/events/{event['id']}/orders", headers=organizer).json()["total"] == 1


def test_dashboard_groups(client):
    organizer = signup(client, "org@example.com", role="organizer")
    make_event(client, organizer, title="Draft one", publish=False)
    upcoming = make_event(client, organizer, title="Upcoming one")
    cancelled = make_event(client, organizer, title="Cancelled one")
    client.post(f"{API}/organizer/events/{cancelled['id']}/cancel", headers=organizer, json={"reason": "Venue closed"})

    def titles(group):
        return [e["title"] for e in client.get(f"{API}/organizer/events", headers=organizer, params={"group": group}).json()]

    assert titles("draft") == ["Draft one"]
    assert titles("upcoming") == [upcoming["title"]]
    assert titles("cancelled") == ["Cancelled one"]
    assert titles("completed") == []


def test_report_event_reaches_admin(client):
    organizer = signup(client, "org@example.com", role="organizer")
    attendee = signup(client, "att@example.com")
    admin = signup(client, "admin@example.com", role="platform_admin")
    event = make_event(client, organizer)
    assert client.post(f"{API}/events/{event['slug']}/report", headers=attendee, json={"reason": "Looks like a scam"}).status_code == 201
    reports = client.get(f"{API}/admin/reports", headers=admin, params={"status": "open"}).json()
    assert len(reports) == 1 and reports[0]["event_title"] == event["title"]
