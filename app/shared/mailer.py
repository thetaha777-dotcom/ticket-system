import logging
import smtplib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from email.message import EmailMessage as MimeMessage

from app.core.config import settings

log = logging.getLogger("biletflow.mail")


@dataclass
class Email:
    to: str
    subject: str
    text: str
    html: str | None = None
    attachments: list[tuple[str, str, bytes]] = field(default_factory=list)   # (filename, mime type, content)


outbox: list[Email] = []
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="mail")


def _send_smtp(msg: Email) -> None:
    mime = MimeMessage()
    mime["From"] = settings.email_from
    mime["To"] = msg.to
    mime["Subject"] = msg.subject
    mime.set_content(msg.text)
    if msg.html:
        mime.add_alternative(msg.html, subtype="html")
    for filename, mime_type, content in msg.attachments:
        maintype, _, subtype = mime_type.partition("/")
        mime.add_attachment(content, maintype=maintype, subtype=subtype or "octet-stream", filename=filename)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_tls:
                smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(mime)
    except Exception as exc:
        log.warning("Could not send email to %s (%s): %s", msg.to, msg.subject, exc)


def send_email(msg: Email) -> None:
    backend = settings.email_backend
    if backend == "memory":
        outbox.append(msg)
    elif backend == "smtp":
        _executor.submit(_send_smtp, msg)
    else:
        names = ", ".join(a[0] for a in msg.attachments) or "-"
        log.info("EMAIL to=%s subject=%r attachments=%s\n%s", msg.to, msg.subject, names, msg.text)
