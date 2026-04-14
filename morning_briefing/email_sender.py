"""
SMTP email delivery via Gmail.

Sends the morning briefing body (plain text) with an optional MP3 attachment.

Requires:
  GMAIL_ADDRESS       - sender Gmail address
  GMAIL_APP_PASSWORD  - 16-char App Password (not your main Google password)
                        Generate at: https://myaccount.google.com/apppasswords
"""

import logging
import os
import smtplib
from email.mime.audio import MIMEAudio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

_SMTP_HOST = "smtp.gmail.com"
_SMTP_PORT = 465  # SSL


def send_briefing_email(
    recipient: str,
    subject: str,
    body: str,
    mp3_path: str | None,
    date_str: str,
) -> None:
    """
    Send email with body and optional MP3 attachment.

    Raises smtplib.SMTPException on delivery failure — callers should handle
    and decide whether to retry or log.
    """
    sender = os.environ.get("GMAIL_ADDRESS", "").strip()
    password = os.environ.get("GMAIL_APP_PASSWORD", "").strip()

    if not sender:
        raise EnvironmentError("GMAIL_ADDRESS is not set")
    if not password:
        raise EnvironmentError("GMAIL_APP_PASSWORD is not set")

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient

    msg.attach(MIMEText(body, "plain", "utf-8"))

    if mp3_path:
        _attach_mp3(msg, mp3_path, date_str)

    with smtplib.SMTP_SSL(_SMTP_HOST, _SMTP_PORT) as server:
        server.login(sender, password)
        server.send_message(msg)

    logger.info("Email delivered to %s (subject: %s)", recipient, subject)


def _attach_mp3(msg: MIMEMultipart, mp3_path: str, date_str: str) -> None:
    if not os.path.exists(mp3_path):
        logger.warning("MP3 path does not exist, skipping attachment: %s", mp3_path)
        return

    try:
        with open(mp3_path, "rb") as fh:
            data = fh.read()

        audio_part = MIMEAudio(data, _subtype="mpeg")
        audio_part.add_header(
            "Content-Disposition",
            "attachment",
            filename=f"morning_briefing_{date_str}.mp3",
        )
        msg.attach(audio_part)
        logger.info("Attached MP3: %.1f KB", len(data) / 1024)
    except OSError as exc:
        logger.error("Failed to attach MP3 (%s): %s", mp3_path, exc)
