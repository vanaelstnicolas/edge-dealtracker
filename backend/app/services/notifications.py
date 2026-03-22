from __future__ import annotations

import smtplib
from email.message import EmailMessage

import httpx

from app.config import settings

MAX_WHATSAPP_BODY_LENGTH = 1500


def send_whatsapp_message(*, to_number: str, body: str) -> str:
    account_sid = settings.twilio_account_sid.strip()
    auth_token = settings.twilio_auth_token.strip()
    from_number = settings.twilio_whatsapp_number.strip()
    if not account_sid or not auth_token or not from_number:
        raise RuntimeError("Twilio is not configured")

    normalized_from = from_number if from_number.startswith("whatsapp:") else f"whatsapp:{from_number}"
    normalized_to = to_number if to_number.startswith("whatsapp:") else f"whatsapp:{to_number}"

    normalized_body = body.strip()
    if len(normalized_body) > MAX_WHATSAPP_BODY_LENGTH:
        normalized_body = f"{normalized_body[: MAX_WHATSAPP_BODY_LENGTH - 3]}..."

    response = httpx.post(
        f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
        auth=(account_sid, auth_token),
        data={
            "From": normalized_from,
            "To": normalized_to,
            "Body": normalized_body,
        },
        timeout=20.0,
    )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        details = ""
        try:
            payload = exc.response.json()
            code = str(payload.get("code", "")).strip()
            message = str(payload.get("message", "")).strip()
            if code and message:
                details = f" ({code}) {message}"
            elif message:
                details = f" {message}"
        except ValueError:
            pass
        raise RuntimeError(f"Twilio send failed{details}") from exc
    payload = response.json()
    return str(payload.get("sid", ""))


def send_email_message(*, to_email: str, subject: str, body: str) -> None:
    host = settings.smtp_host.strip()
    from_email = settings.smtp_from_email.strip()
    if not host or not from_email:
        raise RuntimeError("SMTP is not configured")

    msg = EmailMessage()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(host, settings.smtp_port, timeout=20) as smtp:
        smtp.starttls()
        username = settings.smtp_username.strip()
        password = settings.smtp_password
        if username and password:
            smtp.login(username, password)
        smtp.send_message(msg)
