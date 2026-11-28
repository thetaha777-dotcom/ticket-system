from urllib.parse import parse_qs, urlparse

from tests.helpers import API, buy, future, make_event, paid_event, signup


def _campaign(client, organizer, event, **overrides) -> dict:
    body = {"name": "Student week", "discount_type": "percent", "discount_value": 20}
    body.update(overrides)
    r = client.post(f"{API}/organizer/events/{event['id']}/campaigns", headers=organizer, json=body)
    assert r.status_code == 201, r.text
    return r.json()


def _body(event, quantity=1, code=None, type_index=0):
    return {"event_id": event["id"], "promo_code": code,
            "items": [{"ticket_category_id": event["ticket_types"][type_index]["id"], "quantity": quantity}]}


def test_uc10_campaign_qr_link_applies_the_discount_and_attributes_the_order(client):
    organizer = signup(client, "org@example.com", role="organizer")
    attendee = signup(client, "att@example.com")
    event = paid_event(client, organizer, price=5000)
    campaign = _campaign(client, organizer, event)

    # the QR link holds only an opaque token: no code, no amount, no percentage
    link = urlparse(campaign["link"])
    assert link.path == f"/e/{event['slug']}" and list(parse_qs(link.query)) == ["c"]
    token = parse_qs(link.query)["c"][0]
    assert campaign["code"] not in campaign["link"] and len(token) >= 20
    # ... and the token is random, not derived from the discount: an identical campaign gets a different one
    twin = _campaign(client, organizer, event, code="TWIN20")
    assert parse_qs(urlparse(twin["link"]).query)["c"][0] != token

    # opening the link resolves the token on the server and returns the code to pre-apply
    preview = client.get(f"{API}/promo/resolve", params={"token": token}).json()
    assert preview["code"] == campaign["code"] and preview["event_slug"] == event["slug"]

    quote = client.post(f"{API}/orders/quote", json=_body(event, 2, preview["code"])).json()
    assert (quote["subtotal"], quote["discount_total"], quote["total"]) == (10000, 2000, 8000)
    assert quote["promo"]["code"] == campaign["code"]

    order = buy(client, attendee, event, quantity=2, promo_code=preview["code"])
    assert order["total"] == 8000 and order["discount_total"] == 2000 and order["promo_code"] == campaign["code"]

    campaigns = {c["id"]: c for c in client.get(f"{API}/organizer/events/{event['id']}/campaigns", headers=organizer).json()}
    assert campaigns[campaign["id"]]["stats"] == {"redemptions": 1, "orders": 1, "tickets_sold": 2, "gross_revenue": 10000,
                                                  "discount_amount": 2000, "net_revenue": 8000, "link_visits": 1}
    assert campaigns[twin["id"]]["stats"]["redemptions"] == 0   # the sale is attributed to the right campaign only


def test_fixed_discount_never_exceeds_the_ticket_price(client):
    organizer = signup(client, "org@example.com", role="organizer")
    event = paid_event(client, organizer, price=3000)
    campaign = _campaign(client, organizer, event, discount_type="fixed", discount_value=5000)
    quote = client.post(f"{API}/orders/quote", json=_body(event, 2, campaign["code"])).json()
    assert quote["discount_total"] == 6000 and quote["total"] == 0


def test_redemption_limit_is_enforced_and_released_on_cancel(client):
    organizer = signup(client, "org@example.com", role="organizer")
    alice, bob = signup(client, "alice@example.com"), signup(client, "bob@example.com")
    event = paid_event(client, organizer)
    campaign = _campaign(client, organizer, event, max_redemptions=1, code="ONLYONE")
    assert campaign["code"] == "ONLYONE"

    pending = client.post(f"{API}/orders", headers=alice, json=_body(event, 1, "onlyone")).json()   # case-insensitive
    assert pending["discount_total"] == 1000
    r = client.post(f"{API}/orders", headers=bob, json=_body(event, 1, "ONLYONE"))
    assert r.status_code == 400 and r.json()["code"] == "promo_exhausted"

    # Alice abandons her checkout, so the redemption is free again
    assert client.post(f"{API}/orders/{pending['id']}/cancel", headers=alice, json={}).json()["status"] == "cancelled"
    order = buy(client, bob, event, promo_code="ONLYONE")
    assert order["discount_total"] == 1000
    r = client.post(f"{API}/orders", headers=alice, json=_body(event, 1, "ONLYONE"))
    assert r.json()["code"] == "promo_exhausted"


def test_invalid_codes_are_rejected_with_clear_reasons(client):
    organizer = signup(client, "org@example.com", role="organizer")
    attendee = signup(client, "att@example.com")
    event = make_event(client, organizer, publish=False, tickets=[
        {"name": "Standard", "type": "paid", "price": 4000, "quantity": 20},
        {"name": "VIP", "type": "paid", "price": 9000, "quantity": 20}])
    from tests.helpers import activate_paid_sales
    activate_paid_sales(client, organizer, event["id"])
    client.post(f"{API}/organizer/events/{event['id']}/publish", headers=organizer)

    def code_of(response):
        return response.json()["code"]

    assert code_of(client.post(f"{API}/orders", headers=attendee, json=_body(event, 1, "NOPE"))) == "promo_not_found"

    expired = _campaign(client, organizer, event, code="OLD", starts_at=future(-10), ends_at=future(-1))
    assert code_of(client.post(f"{API}/orders", headers=attendee, json=_body(event, 1, expired["code"]))) == "promo_expired"
    assert code_of(client.post(f"{API}/promo/check", json={"event_id": event["id"], "code": "OLD"})) == "promo_expired"

    vip_only = _campaign(client, organizer, event, code="VIPONLY", ticket_category_ids=[event["ticket_types"][1]["id"]])
    assert code_of(client.post(f"{API}/orders", headers=attendee, json=_body(event, 1, vip_only["code"], type_index=0))) == "promo_not_applicable"
    assert client.post(f"{API}/orders/quote", json=_body(event, 1, "VIPONLY", type_index=1)).json()["discount_total"] == 1800

    disabled = _campaign(client, organizer, event, code="OFF")
    r = client.patch(f"{API}/organizer/events/{event['id']}/campaigns/{disabled['id']}", headers=organizer, json={"is_active": False})
    assert r.json()["is_active"] is False
    assert code_of(client.post(f"{API}/orders", headers=attendee, json=_body(event, 1, "OFF"))) == "promo_disabled"

    # a code of another event does not work here
    other = paid_event(client, organizer, title="Other event")
    assert code_of(client.post(f"{API}/orders", headers=attendee, json=_body(other, 1, "VIPONLY"))) == "promo_not_found"


def test_campaign_qr_image_and_duplicate_code(client):
    organizer = signup(client, "org@example.com", role="organizer")
    event = paid_event(client, organizer)
    campaign = _campaign(client, organizer, event, code="SPRING")
    r = client.get(f"{API}/organizer/events/{event['id']}/campaigns/{campaign['id']}/qr.png", headers=organizer)
    assert r.status_code == 200 and r.content.startswith(b"\x89PNG")
    r = client.post(f"{API}/organizer/events/{event['id']}/campaigns", headers=organizer, json={
        "name": "Again", "discount_type": "percent", "discount_value": 10, "code": "spring"})
    assert r.status_code == 409 and r.json()["code"] == "promo_code_taken"
    r = client.post(f"{API}/organizer/events/{event['id']}/campaigns", headers=organizer, json={
        "name": "Too much", "discount_type": "percent", "discount_value": 150})
    assert r.status_code == 422
