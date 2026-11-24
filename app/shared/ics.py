from datetime import datetime, timezone
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.core.database import utcnow
from app.events.models import EventStatus


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\r", "").replace("\n", "\\n")


def _fold(line: str) -> str:
    out, current, size = [], "", 0
    for ch in line:
        ch_size = len(ch.encode("utf-8"))
        if size + ch_size > 73:
            out.append(current)
            current, size = " ", 1
        current += ch
        size += ch_size
    out.append(current)
    return "\r\n".join(out)


def _offset(dt: datetime) -> str:
    total = int(dt.utcoffset().total_seconds() // 60)
    sign = "+" if total >= 0 else "-"
    return f"{sign}{abs(total) // 60:02d}{abs(total) % 60:02d}"


def _utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def event_url(event) -> str:
    return f"{settings.frontend_url}/e/{event.slug}"


def _location(venue) -> str:
    return f"{venue.name}, {venue.address}, {venue.city}"


def build_event_ics(event, venue) -> str:
    tz = ZoneInfo(event.timezone)
    start, end = event.start_at.astimezone(tz), event.end_at.astimezone(tz)
    cancelled = event.status == EventStatus.CANCELLED
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//BiletFlow//Event Tickets//EN",
        "CALSCALE:GREGORIAN",
        f"METHOD:{'CANCEL' if cancelled else 'PUBLISH'}",
        "BEGIN:VTIMEZONE",
        f"TZID:{event.timezone}",
        "BEGIN:STANDARD",
        "DTSTART:19700101T000000",
        f"TZOFFSETFROM:{_offset(start)}",
        f"TZOFFSETTO:{_offset(start)}",
        "END:STANDARD",
        "END:VTIMEZONE",
        "BEGIN:VEVENT",
        f"UID:event-{event.id}@biletflow",
        f"SEQUENCE:{event.sequence}",
        f"DTSTAMP:{_utc(utcnow())}",
        f"LAST-MODIFIED:{_utc(event.updated_at)}",
        f"DTSTART;TZID={event.timezone}:{start.strftime('%Y%m%dT%H%M%S')}",
        f"DTEND;TZID={event.timezone}:{end.strftime('%Y%m%dT%H%M%S')}",
        f"SUMMARY:{_escape(event.title)}",
        f"DESCRIPTION:{_escape((event.description or '')[:1500])}",
        f"LOCATION:{_escape(_location(venue))}",
        f"URL:{event_url(event)}",
        f"STATUS:{'CANCELLED' if cancelled else 'CONFIRMED'}",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"


def calendar_links(event, venue) -> dict[str, str]:
    tz = ZoneInfo(event.timezone)
    start, end = event.start_at.astimezone(tz), event.end_at.astimezone(tz)
    details = f"{(event.description or '')[:800]}\n\n{event_url(event)}".strip()
    location = _location(venue)
    google = urlencode({
        "action": "TEMPLATE",
        "text": event.title,
        "dates": f"{start.strftime('%Y%m%dT%H%M%S')}/{end.strftime('%Y%m%dT%H%M%S')}",
        "ctz": event.timezone,
        "details": details,
        "location": location,
    })
    outlook = urlencode({
        "path": "/calendar/action/compose",
        "rru": "addevent",
        "subject": event.title,
        "startdt": start.isoformat(),
        "enddt": end.isoformat(),
        "body": details,
        "location": location,
    })
    yahoo = urlencode({
        "v": "60",
        "title": event.title,
        "st": _utc(event.start_at),
        "et": _utc(event.end_at),
        "desc": details,
        "in_loc": location,
    })
    return {
        "google": f"https://calendar.google.com/calendar/render?{google}",
        "outlook": f"https://outlook.live.com/calendar/0/action/compose?{outlook}",
        "office365": f"https://outlook.office.com/calendar/0/action/compose?{outlook}",
        "yahoo": f"https://calendar.yahoo.com/?{yahoo}",
    }
