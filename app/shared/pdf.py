import io
from pathlib import Path

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.core.security import ticket_qr_payload
from app.shared.utils import format_local

FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
pdfmetrics.registerFont(TTFont("BF", str(FONT_DIR / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("BF-Bold", str(FONT_DIR / "DejaVuSans-Bold.ttf")))

PAGE_W, PAGE_H = A4
MARGIN = 20 * mm
QR_SIZE = 80 * mm


def _draw_qr(c: canvas.Canvas, payload: str, x: float, y: float, size: float) -> None:
    widget = QrCodeWidget(payload, barLevel="Q")
    x0, y0, x1, y1 = widget.getBounds()
    drawing = Drawing(size, size, transform=[size / (x1 - x0), 0, 0, size / (y1 - y0), 0, 0])
    drawing.add(widget)
    renderPDF.draw(drawing, c, x, y)


def _field(c: canvas.Canvas, label: str, value: str, x: float, y: float, width: float) -> float:
    c.setFont("BF", 8)
    c.setFillGray(0.35)
    c.drawString(x, y, label.upper())
    c.setFillGray(0)
    c.setFont("BF-Bold", 12)
    for line in simpleSplit(value, "BF-Bold", 12, width)[:3]:
        y -= 15
        c.drawString(x, y, line)
    return y - 16


def _draw_ticket(c: canvas.Canvas, ticket) -> None:
    event, venue, order = ticket.event, ticket.event.venue, ticket.order
    width = PAGE_W - 2 * MARGIN
    y = PAGE_H - MARGIN

    c.setFont("BF-Bold", 16)
    c.drawString(MARGIN, y - 12, "BiletFlow")
    c.setFont("BF", 9)
    c.drawRightString(PAGE_W - MARGIN, y - 10, "ADMISSION TICKET · БИЛЕТ")
    y -= 24
    c.setLineWidth(1.5)
    c.line(MARGIN, y, PAGE_W - MARGIN, y)

    y -= 14
    c.setFont("BF-Bold", 22)
    for line in simpleSplit(event.title, "BF-Bold", 22, width)[:3]:
        y -= 26
        c.drawString(MARGIN, y, line)
    y -= 28

    col = (width - 10 * mm) / 2
    left_y = _field(c, "Date and time", format_local(event.start_at, event.timezone), MARGIN, y, col)
    left_y = _field(c, "Venue", f"{venue.name}", MARGIN, left_y, col)
    left_y = _field(c, "Address", f"{venue.address}, {venue.city}", MARGIN, left_y, col)

    right_x = MARGIN + col + 10 * mm
    right_y = _field(c, "Attendee", ticket.attendee_name, right_x, y, col)
    right_y = _field(c, "Ticket type", ticket.category.name, right_x, right_y, col)
    if ticket.seat_row:
        seat = f"{ticket.seat_section} · Row {ticket.seat_row} · Seat {ticket.seat_number}"
        right_y = _field(c, "Section / row / seat", seat, right_x, right_y, col)

    y = min(left_y, right_y) - 6
    c.setLineWidth(0.5)
    c.setDash(3, 3)
    c.line(MARGIN, y, PAGE_W - MARGIN, y)
    c.setDash()

    qr_x = (PAGE_W - QR_SIZE) / 2
    qr_y = y - 12 * mm - QR_SIZE
    _draw_qr(c, ticket_qr_payload(ticket.id), qr_x, qr_y, QR_SIZE)

    c.setFont("BF-Bold", 16)
    c.drawCentredString(PAGE_W / 2, qr_y - 9 * mm, ticket.code)
    c.setFont("BF", 9)
    c.setFillGray(0.35)
    c.drawCentredString(PAGE_W / 2, qr_y - 15 * mm, f"Ticket ID · Order {order.number}")

    notes = [
        "Show this QR code at the entrance. It admits one person, once.",
        "The printed copy and the copy in your account are the same ticket.",
    ]
    ny = MARGIN + 14
    c.setFont("BF", 8.5)
    for note in notes:
        c.drawCentredString(PAGE_W / 2, ny, note)
        ny -= 12
    c.setFillGray(0)


def render_tickets_pdf(tickets: list) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle("BiletFlow tickets")
    c.setAuthor("BiletFlow")
    for ticket in tickets:
        _draw_ticket(c, ticket)
        c.showPage()
    c.save()
    return buf.getvalue()
