from __future__ import annotations

from app.repositories.in_memory import store
from app.services.action_summary import build_owner_summary_text
from app.services.notifications import report_summary_delivery_failure, send_email_message, send_whatsapp_message


def send_weekly_summaries_job() -> None:
    users = store.list_users()
    for user in users:
        summary_text = build_owner_summary_text(store, owner_name=user.full_name, owner_id=user.id)

        if user.whatsapp_number:
            try:
                send_whatsapp_message(to_number=user.whatsapp_number, body=summary_text)
            except Exception as exc:
                report_summary_delivery_failure(
                    operation="weekly_scheduler",
                    channel="whatsapp",
                    owner_id=user.id,
                    owner_name=user.full_name,
                    owner_email=user.email,
                    error=exc,
                )

        if user.email:
            try:
                send_email_message(
                    to_email=user.email,
                    subject="DealTracker - Resume hebdomadaire des actions",
                    body=summary_text,
                )
            except Exception as exc:
                report_summary_delivery_failure(
                    operation="weekly_scheduler",
                    channel="email",
                    owner_id=user.id,
                    owner_name=user.full_name,
                    owner_email=user.email,
                    error=exc,
                )
