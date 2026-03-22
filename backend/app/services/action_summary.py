from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.schemas.deal import DealStatus


@dataclass
class ActionSummaryItem:
    company: str
    action: str
    deadline: str
    status: str


def get_owner_todo_items(store_instance, owner_id: str) -> list[ActionSummaryItem]:
    deals = store_instance.list_deals(status=DealStatus.active, owner_id=owner_id)
    return [
        ActionSummaryItem(
            company=deal.company,
            action=deal.action,
            deadline=deal.deadline.isoformat(),
            status=deal.status.value,
        )
        for deal in deals
    ]


def build_owner_summary_text(store_instance, owner_name: str, owner_id: str) -> str:
    items = get_owner_todo_items(store_instance, owner_id)
    if not items:
        return f"Bonjour {owner_name}, aucun to-do actif cette semaine."

    today = date.today().isoformat()
    lines = [f"Bonjour {owner_name}, resume to-do ({today}) :"]
    for item in items[:10]:
        short_action = item.action if len(item.action) <= 110 else f"{item.action[:107]}..."
        lines.append(f"- {item.company}: {short_action} (deadline {item.deadline})")
    if len(items) > 10:
        lines.append(f"... +{len(items) - 10} action(s)")
    return "\n".join(lines)
