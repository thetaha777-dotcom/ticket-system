import html
import uuid

from sqlalchemy import event, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.notifications.models import Notification
from app.shared import mailer
from app.users.models import User


def _render_html(title: str, body: str, link: str | None) -> str:
    paragraphs = "".join(f"<p style='margin:0 0 12px'>{html.escape(p)}</p>" for p in body.split("\n") if p.strip())
    button = ""
    if link:
        button = (
            f"<p style='margin:20px 0'><a href='{html.escape(link)}' style='background:#0f766e;color:#fff;"
            f"padding:10px 18px;border-radius:6px;text-decoration:none'>Open in BiletFlow</a></p>"
        )
    return (
        "<div style='font-family:Arial,sans-serif;max-width:560px;margin:auto;color:#1f2937'>"
        f"<h2 style='color:#0f766e'>{html.escape(title)}</h2>{paragraphs}{button}"
        "<hr style='border:none;border-top:1px solid #e5e7eb'>"
        "<p style='font-size:12px;color:#6b7280'>BiletFlow academic demo. Payments shown here are simulations, "
        "not real financial transactions.</p></div>"
    )


def notify(
    db: Session,
    user: User,
    type_: str,
    title: str,
    body: str,
    *,
    link: str | None = None,
    attachments: list[tuple[str, str, bytes]] | None = None,
    email: bool = True,
    in_app: bool = True,
) -> None:
    if in_app:
        db.add(Notification(user_id=user.id, type=type_, title=title, body=body, link=link, emailed=email))
    if email:
        full_link = f"{settings.frontend_url}{link}" if link and link.startswith("/") else link
        text = body + (f"\n\n{full_link}" if full_link else "")
        message = mailer.Email(
            to=user.email, subject=title, text=text, html=_render_html(title, body, full_link), attachments=attachments or []
        )
        db.info.setdefault("email_queue", []).append(message)


def list_for_user(db: Session, user: User, limit: int = 50) -> list[Notification]:
    query = select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(limit)
    return list(db.scalars(query))


def mark_read(db: Session, user: User, notification_id: uuid.UUID | None = None) -> None:
    stmt = update(Notification).where(Notification.user_id == user.id).values(is_read=True)
    if notification_id:
        stmt = stmt.where(Notification.id == notification_id)
    db.execute(stmt)
    db.commit()


@event.listens_for(Session, "after_commit")
def _send_queued_emails(session: Session) -> None:
    for message in session.info.pop("email_queue", []):
        mailer.send_email(message)


@event.listens_for(Session, "after_rollback")
def _drop_queued_emails(session: Session) -> None:
    session.info.pop("email_queue", None)
