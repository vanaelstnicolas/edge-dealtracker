from __future__ import annotations

import hmac
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.api.deps.auth import get_current_user
from app.repositories.in_memory import store
from app.services.action_summary import build_owner_summary_text, get_owner_todo_items
from app.services.notifications import (
    email_provider_status,
    report_summary_delivery_failure,
    send_email_message,
    send_whatsapp_message,
)
from app.services.rate_limit import enforce_rate_limit
from app.jobs.weekly_summary import send_weekly_summaries_job
from app.config import settings

router = APIRouter()


def _is_admin(current_user: dict[str, Any]) -> bool:
    app_metadata = current_user.get("app_metadata")
    if not isinstance(app_metadata, dict):
        return False

    role = app_metadata.get("role")
    if isinstance(role, str) and role.lower() == "admin":
        return True

    roles = app_metadata.get("roles")
    if isinstance(roles, list):
        return any(isinstance(item, str) and item.lower() == "admin" for item in roles)

    return False


def _owner_identity(current_user: dict[str, Any]) -> tuple[str, str, str]:
    owner_id = str(current_user["id"])
    owner_name = str(current_user.get("email") or "Utilisateur")
    owner_email = str(current_user.get("email") or "").strip()

    for row in store.list_users():
        if row.id == owner_id:
            owner_name = row.full_name
            owner_email = row.email
            break

    return owner_id, owner_name, owner_email


@router.get("/me")
def get_my_summary(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    owner_id, owner_name, _owner_email = _owner_identity(current_user)
    items = get_owner_todo_items(store, owner_id)
    return {
        "owner_id": owner_id,
        "owner_name": owner_name,
        "summary": build_owner_summary_text(store, owner_name=owner_name, owner_id=owner_id),
        "items": [item.__dict__ for item in items],
    }


@router.post("/me/send")
def send_my_summary(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    owner_id, owner_name, owner_email = _owner_identity(current_user)
    enforce_rate_limit(
        bucket="summary_send",
        key=owner_id,
        limit=settings.summary_send_rate_limit_per_user,
        window_seconds=settings.rate_limit_window_seconds,
    )
    summary_text = build_owner_summary_text(store, owner_name=owner_name, owner_id=owner_id)

    whatsapp_status = "skipped"
    email_status = "skipped"

    target = next((row for row in store.list_users() if row.id == owner_id), None)
    if target and target.whatsapp_number:
        try:
            send_whatsapp_message(to_number=target.whatsapp_number, body=summary_text)
            whatsapp_status = "sent"
        except Exception as exc:  # pragma: no cover - defensive
            report_summary_delivery_failure(
                operation="manual_send",
                channel="whatsapp",
                owner_id=owner_id,
                owner_name=owner_name,
                owner_email=owner_email,
                error=exc,
            )
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"WhatsApp send failed: {exc}") from exc

    if owner_email:
        try:
            send_email_message(
                to_email=owner_email,
                subject="DealTracker - Resume hebdomadaire des actions",
                body=summary_text,
            )
            email_status = "sent"
        except Exception:
            report_summary_delivery_failure(
                operation="manual_send",
                channel="email",
                owner_id=owner_id,
                owner_name=owner_name,
                owner_email=owner_email,
                error="email_send_failed_or_not_configured",
            )
            email_status = "not_configured"

    return {
        "owner_id": owner_id,
        "whatsapp": whatsapp_status,
        "email": email_status,
        "summary": summary_text,
    }


@router.post("/weekly/trigger")
def trigger_weekly_summary_now(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    if not _is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")

    send_weekly_summaries_job()
    return {"result": "ok", "message": "Weekly summaries triggered"}


@router.post("/weekly/trigger/cron")
def trigger_weekly_summary_from_cron(x_cron_token: str | None = Header(default=None, alias="X-Cron-Token")) -> dict[str, Any]:
    expected_token = settings.weekly_summary_cron_token.strip()
    if not expected_token:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Cron trigger is not configured")

    if not x_cron_token or not hmac.compare_digest(x_cron_token, expected_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid cron token")

    send_weekly_summaries_job()
    return {"result": "ok", "message": "Weekly summaries triggered"}


@router.get("/weekly/status")
def weekly_summary_status(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    if not _is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")

    return {
        "scheduler_enabled": settings.weekly_summary_scheduler_enabled,
        "timezone": settings.weekly_summary_timezone,
        "day_of_week": settings.weekly_summary_day_of_week,
        "hour": settings.weekly_summary_hour,
        "minute": settings.weekly_summary_minute,
        "summary_alert_webhook_configured": bool(settings.summary_alert_webhook_url.strip()),
        "summary_alert_timeout_seconds": settings.summary_alert_timeout_seconds,
        **email_provider_status(),
    }
