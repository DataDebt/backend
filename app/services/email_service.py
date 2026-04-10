from datetime import UTC, datetime
import json
import logging
from pathlib import Path
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings


def build_email_verification_html(username: str, confirm_url: str) -> str:
    return f"<h1>Welcome, {username}</h1><p>Confirm your email: <a href='{confirm_url}'>{confirm_url}</a></p>"


def build_password_reset_html(username: str, reset_url: str) -> str:
    return f"<h1>Password reset</h1><p>{username}, reset your password: <a href='{reset_url}'>{reset_url}</a></p>"


def build_email_verification_text(username: str, confirm_url: str) -> str:
    return f"Welcome, {username}. Confirm your email: {confirm_url}"


def build_password_reset_text(username: str, reset_url: str) -> str:
    return f"Hi {username}, reset your password: {reset_url}"


def capture_email(to_email: str, subject: str, html: str, metadata: dict):
    emails_dir = Path("emails")
    emails_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
    stem = f"{timestamp}_{to_email.replace('@', '_at_')}"
    (emails_dir / f"{stem}.json").write_text(json.dumps({"to": to_email, "subject": subject, **metadata}, indent=2))
    (emails_dir / f"{stem}.html").write_text(html)


def send_email(to_email: str, subject: str, html: str, text: str, metadata: dict | None = None):
    metadata = metadata or {}
    if settings.smtp_host and settings.smtp_user and settings.smtp_pass:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from
        msg["To"] = to_email
        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.ehlo()
            if settings.smtp_tls:
                server.starttls()
            server.login(settings.smtp_user, settings.smtp_pass)
            server.sendmail(settings.smtp_from, to_email, msg.as_string())
    elif settings.capture_emails_to_files:
        capture_email(to_email, subject, html, metadata)
    else:
        logging.getLogger(__name__).warning(
            "Email to %s not delivered: SMTP not configured and capture_emails_to_files is False",
            to_email,
        )
