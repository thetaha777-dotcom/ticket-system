import io

from PIL import Image
from pypdf import PdfReader

from app.core.security import parse_ticket_qr, ticket_qr_payload
from tests.helpers import API, buy, future, make_event, signup


def test_qr_payload_is_tamper_resistant():
    import uuid
    ticket_id = uuid.uuid4()
    payload = ticket_qr_payload(ticket_id)
    assert parse_ticket_qr(payload) == ticket_id
    assert payload == payload.upper() and set(payload) <= set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.")   # QR alphanumeric mode
    other = ticket_qr_payload(uuid.uuid4())
    # a signature copied from another ticket does not validate
    forged = ".".join([*payload.split(".")[:2], other.split(".")[2]])
    assert parse_ticket_qr(forged) is None
    assert parse_ticket_qr("https://biletflow.kz/e/some-event?c=token") is None


def test_uc7_printable_pdf_and_qr_image(client):
    organizer = signup(client, "org@example.com", role="organizer")
    attendee_email = "att@example.com"
    attendee = signup(client, attendee_email, name="Әлия Нұрланқызы")   # Kazakh letters must print
    event = make_event(client, organizer, title="Наурыз мейрамы — концерт")
    order = buy(client, attendee, event, quantity=2)
    ticket = order["tickets"][0]

    pdf = client.get(f"{API}/tickets/{ticket['id']}/pdf", headers=attendee)
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf" and pdf.content.startswith(b"%PDF")
    assert ticket["code"] in pdf.headers["content-disposition"]
    both = client.get(f"{API}/orders/{order['id']}/tickets.pdf", headers=attendee)
    pages = PdfReader(io.BytesIO(both.content)).pages
    assert len(pages) == 2   # one page per ticket

    # what is printed: event, date and time, venue, ticket type, attendee, ticket code - and nothing about payment
    printed = PdfReader(io.BytesIO(pdf.content)).pages[0].extract_text()
    for expected in ("Наурыз мейрамы — концерт", "Dostyk Hall", "Dostyk Ave 1", "Әлия Нұрланқызы", "Free entry",
                     ticket["code"], order["number"], "Asia/Almaty"):
        assert expected in printed, expected
    wording = printed.replace(ticket["code"], "").replace(order["number"], "").lower()   # the codes are random letters
    assert "card" not in wording and "payment" not in wording and attendee_email not in printed

    png = client.get(f"{API}/tickets/{ticket['id']}/qr.png", headers=attendee)
    image = Image.open(io.BytesIO(png.content))
    assert image.format == "PNG" and image.width >= 300
    assert client.get(f"{API}/tickets/{ticket['id']}/pdf").status_code == 401


def test_uc6_calendar_export(client):
    organizer = signup(client, "org@example.com", role="organizer")
    event = make_event(client, organizer, title="Meetup, Almaty; spring", timezone="Asia/Almaty")

    ics = client.get(f"{API}/events/{event['slug']}/calendar.ics")
    assert ics.status_code == 200 and ics.headers["content-type"].startswith("text/calendar")
    text = ics.text.replace("\r\n ", "")   # undo line folding
    assert f"UID:event-{event['id']}@biletflow" in text and "SEQUENCE:0" in text
    assert "DTSTART;TZID=Asia/Almaty:" in text and "TZOFFSETTO:+0500" in text
    assert "SUMMARY:Meetup\\, Almaty\\; spring" in text
    assert "LOCATION:Dostyk Hall\\, Dostyk Ave 1\\, Almaty" in text and f"URL:http://localhost:5173/e/{event['slug']}" in text
    assert all(len(line.encode()) <= 75 for line in ics.text.split("\r\n"))

    links = client.get(f"{API}/events/{event['slug']}/calendar-links").json()
    assert links["google"].startswith("https://calendar.google.com/calendar/render?") and "ctz=Asia%2FAlmaty" in links["google"]
    assert set(links) == {"ics", "google", "outlook", "office365", "yahoo"}

    # moving the event keeps the UID and raises the sequence, so calendars replace the old entry
    client.patch(f"{API}/organizer/events/{event['id']}", headers=organizer, json={"start_at": future(40), "end_at": future(40, 2)})
    updated = client.get(f"{API}/events/{event['slug']}/calendar.ics").text
    assert f"UID:event-{event['id']}@biletflow" in updated and "SEQUENCE:1" in updated


def test_event_update_notifies_ticket_holders(client):
    from app.shared import mailer
    organizer = signup(client, "org@example.com", role="organizer")
    attendee = signup(client, "att@example.com")
    event = make_event(client, organizer)
    buy(client, attendee, event)
    mailer.outbox.clear()
    client.patch(f"{API}/organizer/events/{event['id']}", headers=organizer, json={"start_at": future(45), "end_at": future(45, 2)})
    assert [m.to for m in mailer.outbox] == ["att@example.com"] and "has been updated" in mailer.outbox[0].subject
    # a description edit is not worth an email
    mailer.outbox.clear()
    client.patch(f"{API}/organizer/events/{event['id']}", headers=organizer, json={"description": "New text"})
    assert mailer.outbox == []


def test_image_upload(client):
    organizer = signup(client, "org@example.com", role="organizer")
    buffer = io.BytesIO()
    Image.new("RGB", (40, 30), "teal").save(buffer, format="PNG")
    r = client.post(f"{API}/uploads/images", headers=organizer, files={"file": ("cover.png", buffer.getvalue(), "image/png")})
    assert r.status_code == 200 and r.json()["url"].endswith(".png")
    assert client.get(r.json()["url"].replace("http://localhost:8000", "")).status_code == 200
    r = client.post(f"{API}/uploads/images", headers=organizer, files={"file": ("evil.png", b"<script>", "image/png")})
    assert r.status_code == 400 and r.json()["code"] == "invalid_image"
