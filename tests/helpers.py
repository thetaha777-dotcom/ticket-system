from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import create_token
from app.users.models import User, UserRole

API = "/api/v1"
PASSWORD = "Password123"


def future(days: float = 30, hours: float = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days, hours=hours)).isoformat()


def signup(client, email: str, role: str = "attendee", verified: bool = True, name: str | None = None) -> dict:
    api_role = role if role in ("attendee", "organizer") else "attendee"
    response = client.post(f"{API}/auth/register", json={
        "name": name or email.split("@")[0].title(), "email": email, "password": PASSWORD, "role": api_role})
    assert response.status_code == 201, response.text
    user_id = response.json()["id"]
    if verified:
        token = create_token(user_id, "verify_email", 60)
        assert client.post(f"{API}/auth/verify-email", json={"token": token}).status_code == 200
    if role == "platform_admin":
        with SessionLocal() as db:
            db.scalar(select(User).where(User.email == email)).role = UserRole.PLATFORM_ADMIN
            db.commit()
    return login(client, email)


def login(client, email: str, password: str = PASSWORD) -> dict:
    response = client.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def make_venue(client, headers, seat_map: bool = False) -> dict:
    response = client.post(f"{API}/venues", headers=headers, json={
        "name": "Dostyk Hall", "city": "Almaty", "address": "Dostyk Ave 1", "use_predefined_layout": seat_map})
    assert response.status_code == 201, response.text
    return response.json()


def make_event(client, headers, *, tickets: list[dict] | None = None, publish: bool = True, seat_map: bool = False,
               **overrides) -> dict:
    venue = make_venue(client, headers, seat_map=seat_map)
    body = {"title": "Test Concert", "category": "Music", "venue_id": venue["id"], "start_at": future(30),
            "end_at": future(30, 3), "description": "A night of music"}
    body.update(overrides)
    response = client.post(f"{API}/organizer/events", headers=headers, json=body)
    assert response.status_code == 201, response.text
    event = response.json()
    for ticket in tickets if tickets is not None else [{"name": "Free entry", "type": "free", "quantity": 100}]:
        r = client.post(f"{API}/organizer/events/{event['id']}/ticket-types", headers=headers, json=ticket)
        assert r.status_code == 201, r.text
    if publish:
        r = client.post(f"{API}/organizer/events/{event['id']}/publish", headers=headers)
        assert r.status_code == 200, r.text
    return client.get(f"{API}/organizer/events/{event['id']}", headers=headers).json()


def activate_paid_sales(client, headers, event_id: str) -> dict:
    client.put(f"{API}/users/me/organizer-profile", headers=headers, json={
        "display_name": "Test Org", "contact_email": "org@example.com"})
    assert client.post(f"{API}/users/me/organizer-profile/verify-identity", headers=headers).status_code == 200
    assert client.put(f"{API}/users/me/payout-account", headers=headers, json={
        "bank_name": "Demo Bank", "account_holder": "Test Org", "account_number": "KZ00DEMO0000001234"}).status_code == 200
    base = f"{API}/organizer/events/{event_id}/activation"
    assert client.post(f"{base}/pay-fee", headers=headers, json={"outcome": "success"}).status_code == 200
    response = client.post(f"{base}/accept-terms", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def paid_event(client, headers, price: int = 5000, quantity: int = 50, **overrides) -> dict:
    event = make_event(client, headers, publish=False, tickets=[
        {"name": "Standard", "type": "paid", "price": price, "quantity": quantity}], **overrides)
    activation = activate_paid_sales(client, headers, event["id"])
    assert activation["is_active"], activation
    assert client.post(f"{API}/organizer/events/{event['id']}/publish", headers=headers).status_code == 200
    return client.get(f"{API}/organizer/events/{event['id']}", headers=headers).json()


def buy(client, headers, event: dict, quantity: int = 1, type_index: int = 0, pay: bool = True, **extra) -> dict:
    body = {"event_id": event["id"], "items": [{"ticket_category_id": event["ticket_types"][type_index]["id"], "quantity": quantity}]}
    body.update(extra)
    response = client.post(f"{API}/orders", headers=headers, json=body)
    assert response.status_code == 201, response.text
    order = response.json()
    if pay and order["status"] == "pending":
        response = client.post(f"{API}/orders/{order['id']}/pay", headers=headers, json={"outcome": "success"})
        assert response.status_code == 200, response.text
        order = response.json()
    return order
