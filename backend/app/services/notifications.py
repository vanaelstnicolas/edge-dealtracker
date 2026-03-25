from __future__ import annotations

import smtplib
import time
from email.message import EmailMessage
from urllib.parse import quote

import httpx

from app.config import settings

MAX_WHATSAPP_BODY_LENGTH = 1500
GRAPH_SCOPE = "https://graph.microsoft.com/.default"

_GRAPH_TOKEN_CACHE: dict[str, float | str] = {
    "access_token": "",
    "expires_at": 0.0,
}


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


def _normalized_email_provider() -> str:
    provider = settings.email_provider.strip().lower()
    if provider in {"auto", "graph", "smtp"}:
        return provider
    return "auto"


def _smtp_status() -> tuple[bool, bool]:
    host = settings.smtp_host.strip()
    from_email = settings.smtp_from_email.strip()
    username = settings.smtp_username.strip()
    password = settings.smtp_password
    smtp_auth_configured = bool(username and password)
    smtp_configured = bool(host and from_email and (smtp_auth_configured or not username))
    return smtp_configured, smtp_auth_configured


def _graph_status() -> tuple[bool, bool, bool]:
    tenant_id = settings.graph_tenant_id.strip()
    client_id = settings.graph_client_id.strip()
    client_secret = settings.graph_client_secret
    sender_user = settings.graph_sender_user.strip()
    graph_configured = bool(tenant_id and client_id and client_secret and sender_user)
    return graph_configured, bool(tenant_id), bool(client_id and client_secret)


def email_provider_status() -> dict[str, str | bool]:
    provider = _normalized_email_provider()
    smtp_configured, smtp_auth_configured = _smtp_status()
    graph_configured, graph_tenant_configured, graph_app_configured = _graph_status()
    fallback_enabled = settings.graph_fallback_to_smtp

    effective_provider = "none"
    if provider == "graph":
        if graph_configured:
            effective_provider = "graph"
        elif fallback_enabled and smtp_configured:
            effective_provider = "smtp_fallback"
    elif provider == "smtp":
        if smtp_configured:
            effective_provider = "smtp"
    else:
        if graph_configured:
            effective_provider = "graph"
        elif smtp_configured:
            effective_provider = "smtp"

    return {
        "email_provider_requested": provider,
        "email_provider_effective": effective_provider,
        "graph_configured": graph_configured,
        "graph_tenant_configured": graph_tenant_configured,
        "graph_app_configured": graph_app_configured,
        "graph_sender_user": settings.graph_sender_user.strip(),
        "graph_fallback_to_smtp": fallback_enabled,
        "smtp_configured": smtp_configured,
        "smtp_auth_configured": smtp_auth_configured,
        "smtp_mode": "ssl" if settings.smtp_ssl_enabled else "starttls" if settings.smtp_starttls_enabled else "plain",
        "smtp_host": settings.smtp_host.strip(),
        "smtp_from_email": settings.smtp_from_email.strip(),
    }


def _graph_access_token() -> str:
    cached_token = str(_GRAPH_TOKEN_CACHE.get("access_token", ""))
    cached_expiry = float(_GRAPH_TOKEN_CACHE.get("expires_at", 0.0))
    if cached_token and time.time() < cached_expiry:
        return cached_token

    tenant_id = settings.graph_tenant_id.strip()
    client_id = settings.graph_client_id.strip()
    client_secret = settings.graph_client_secret
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

    response = httpx.post(
        token_url,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": GRAPH_SCOPE,
        },
        timeout=max(1, settings.graph_timeout_seconds),
    )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError("Microsoft Graph token request failed") from exc

    payload = response.json()
    token = str(payload.get("access_token", "")).strip()
    if not token:
        raise RuntimeError("Microsoft Graph token response missing access_token")
    expires_in = int(payload.get("expires_in", 3600))
    _GRAPH_TOKEN_CACHE["access_token"] = token
    _GRAPH_TOKEN_CACHE["expires_at"] = time.time() + max(60, expires_in - 60)
    return token


def _send_email_via_graph(*, to_email: str, subject: str, body: str) -> None:
    sender_user = settings.graph_sender_user.strip()
    if not sender_user:
        raise RuntimeError("Microsoft Graph sender user is not configured")

    def _call(access_token: str) -> httpx.Response:
        endpoint = f"https://graph.microsoft.com/v1.0/users/{quote(sender_user, safe='@._-')}/sendMail"
        return httpx.post(
            endpoint,
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json={
                "message": {
                    "subject": subject,
                    "body": {"contentType": "Text", "content": body},
                    "toRecipients": [{"emailAddress": {"address": to_email}}],
                },
                "saveToSentItems": True,
            },
            timeout=max(1, settings.graph_timeout_seconds),
        )

    token = _graph_access_token()
    response = _call(token)
    if response.status_code == 401:
        _GRAPH_TOKEN_CACHE["access_token"] = ""
        _GRAPH_TOKEN_CACHE["expires_at"] = 0.0
        response = _call(_graph_access_token())

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError("Microsoft Graph sendMail failed") from exc


def _send_email_via_smtp(*, to_email: str, subject: str, body: str) -> None:
    host = settings.smtp_host.strip()
    from_email = settings.smtp_from_email.strip()
    if not host or not from_email:
        raise RuntimeError("SMTP is not configured")

    username = settings.smtp_username.strip()
    password = settings.smtp_password
    if username and not password:
        raise RuntimeError("SMTP password is missing")

    msg = EmailMessage()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    timeout = max(1, settings.smtp_timeout_seconds)
    if settings.smtp_ssl_enabled:
        with smtplib.SMTP_SSL(host, settings.smtp_port, timeout=timeout) as smtp:
            if username and password:
                smtp.login(username, password)
            smtp.send_message(msg)
        return

    with smtplib.SMTP(host, settings.smtp_port, timeout=timeout) as smtp:
        if settings.smtp_starttls_enabled:
            smtp.starttls()
        if username and password:
            smtp.login(username, password)
        smtp.send_message(msg)


def send_email_message(*, to_email: str, subject: str, body: str) -> None:
    status = email_provider_status()
    effective_provider = str(status["email_provider_effective"])

    if effective_provider == "graph":
        try:
            _send_email_via_graph(to_email=to_email, subject=subject, body=body)
            return
        except Exception as exc:
            if settings.graph_fallback_to_smtp and bool(status["smtp_configured"]):
                _send_email_via_smtp(to_email=to_email, subject=subject, body=body)
                return
            raise RuntimeError(f"Graph email send failed: {exc}") from exc

    if effective_provider in {"smtp", "smtp_fallback"}:
        _send_email_via_smtp(to_email=to_email, subject=subject, body=body)
        return

    raise RuntimeError("No email provider configured (Graph or SMTP)")
