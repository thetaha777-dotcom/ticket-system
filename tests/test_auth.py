import re

from app.shared import mailer
from tests.helpers import API, PASSWORD, login, signup


def _token_from_last_email() -> str:
    return re.search(r"token=([\w\-.]+)", mailer.outbox[-1].text).group(1)


def test_register_sends_verification_email_and_link_verifies(client):
    r = client.post(f"{API}/auth/register", json={"name": "Aigerim", "email": "Aigerim@Example.com", "password": PASSWORD})
    assert r.status_code == 201
    assert r.json()["email"] == "aigerim@example.com" and r.json()["is_verified"] is False
    assert "Confirm your BiletFlow email" in mailer.outbox[-1].subject

    r = client.post(f"{API}/auth/verify-email", json={"token": _token_from_last_email()})
    assert r.status_code == 200 and r.json()["is_verified"] is True


def test_duplicate_email_and_weak_password_are_rejected(client):
    signup(client, "a@example.com")
    r = client.post(f"{API}/auth/register", json={"name": "A", "email": "A@example.com", "password": PASSWORD})
    assert r.status_code == 409 and r.json()["code"] == "email_taken"
    r = client.post(f"{API}/auth/register", json={"name": "B", "email": "b@example.com", "password": "short"})
    assert r.status_code == 422 and r.json()["code"] == "validation_error"


def test_login_and_me(client):
    headers = signup(client, "user@example.com")
    assert client.get(f"{API}/auth/me", headers=headers).json()["email"] == "user@example.com"
    assert client.get(f"{API}/auth/me").status_code == 401
    r = client.post(f"{API}/auth/login", json={"email": "user@example.com", "password": "wrong-password"})
    assert r.status_code == 401 and r.json()["code"] == "invalid_credentials"


def test_password_reset_link_works_once(client):
    signup(client, "reset@example.com")
    assert client.post(f"{API}/auth/forgot-password", json={"email": "reset@example.com"}).status_code == 200
    token = _token_from_last_email()
    assert client.post(f"{API}/auth/reset-password", json={"token": token, "new_password": "NewPassword456"}).status_code == 200
    login(client, "reset@example.com", "NewPassword456")
    # the same link cannot be used a second time
    r = client.post(f"{API}/auth/reset-password", json={"token": token, "new_password": "Another789000"})
    assert r.status_code == 400 and r.json()["code"] == "invalid_token"


def test_forgot_password_does_not_reveal_unknown_emails(client):
    r = client.post(f"{API}/auth/forgot-password", json={"email": "nobody@example.com"})
    assert r.status_code == 200 and not mailer.outbox


def test_a_login_token_cannot_be_used_as_a_verification_token(client):
    headers = signup(client, "x@example.com", verified=False)
    access_token = headers["Authorization"].split()[1]
    assert client.post(f"{API}/auth/verify-email", json={"token": access_token}).status_code == 400


def test_role_based_permissions(client):
    attendee = signup(client, "att@example.com")
    organizer = signup(client, "org@example.com", role="organizer")
    admin = signup(client, "admin@example.com", role="platform_admin")
    assert client.get(f"{API}/organizer/events", headers=attendee).status_code == 403
    assert client.get(f"{API}/organizer/events", headers=organizer).status_code == 200
    assert client.get(f"{API}/admin/overview", headers=organizer).status_code == 403
    assert client.get(f"{API}/admin/overview", headers=admin).status_code == 200


def test_creating_an_organizer_profile_upgrades_an_attendee(client):
    headers = signup(client, "new-org@example.com")
    r = client.put(f"{API}/users/me/organizer-profile", headers=headers, json={
        "display_name": "KBTU Student Club", "contact_email": "club@example.com", "contact_phone": "+7 700 000 00 00"})
    assert r.status_code == 200 and r.json()["verification_status"] == "not_started"
    assert client.get(f"{API}/users/me", headers=headers).json()["role"] == "organizer"


def test_suspended_user_is_locked_out(client):
    admin = signup(client, "admin@example.com", role="platform_admin")
    headers = signup(client, "bad@example.com")
    user_id = client.get(f"{API}/users/me", headers=headers).json()["id"]
    assert client.patch(f"{API}/admin/users/{user_id}", headers=admin, json={"is_active": False}).status_code == 200
    assert client.get(f"{API}/users/me", headers=headers).status_code == 401
    r = client.post(f"{API}/auth/login", json={"email": "bad@example.com", "password": PASSWORD})
    assert r.status_code == 403 and r.json()["code"] == "account_suspended"
