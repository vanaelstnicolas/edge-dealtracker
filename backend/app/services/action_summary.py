from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import html

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


def build_owner_summary_email_content(
    store_instance,
    *,
    owner_name: str,
    owner_id: str,
    app_url: str,
) -> tuple[str, str]:
    items = get_owner_todo_items(store_instance, owner_id)
    safe_owner = owner_name.strip() or "Utilisateur"
    cleaned_app_url = app_url.strip()

    if not items:
        text = f"Bonjour {safe_owner},\n\nAucune action active cette semaine."
        if cleaned_app_url:
            text += f"\n\nOuvrir DealTracker: {cleaned_app_url}"

        html_parts = [
            "<div style='font-family:Segoe UI,Arial,sans-serif;line-height:1.5;color:#1f2937;'>",
            f"<h2 style='margin:0 0 8px 0;'>Bonjour {html.escape(safe_owner)},</h2>",
            "<p style='margin:0 0 16px 0;'>Aucune action active cette semaine.</p>",
        ]
        if cleaned_app_url:
            html_parts.append(
                f"<p style='margin:0;'><a href='{html.escape(cleaned_app_url)}' "
                "style='display:inline-block;padding:10px 14px;border-radius:8px;background:#111827;color:#ffffff;text-decoration:none;'>"
                "Ouvrir DealTracker</a></p>"
            )
        html_parts.append("</div>")
        return text, "".join(html_parts)

    text_lines = [
        f"Bonjour {safe_owner},",
        "",
        f"Voici ton resume hebdomadaire ({date.today().isoformat()}) :",
        "",
    ]
    for index, item in enumerate(items, start=1):
        text_lines.append(f"{index}. {item.company}")
        text_lines.append(f"   - Action: {item.action}")
        text_lines.append(f"   - Deadline: {item.deadline}")
    if cleaned_app_url:
        text_lines.extend(["", f"Ouvrir DealTracker: {cleaned_app_url}"])

    html_rows = []
    for item in items:
        html_rows.append(
            "<tr>"
            f"<td style='padding:10px;border-bottom:1px solid #e5e7eb;vertical-align:top;font-weight:600;color:#111827;'>{html.escape(item.company)}</td>"
            f"<td style='padding:10px;border-bottom:1px solid #e5e7eb;vertical-align:top;color:#1f2937;white-space:pre-wrap;'>{html.escape(item.action)}</td>"
            f"<td style='padding:10px;border-bottom:1px solid #e5e7eb;vertical-align:top;color:#1f2937;'>{html.escape(item.deadline)}</td>"
            "</tr>"
        )

    html_parts = [
        "<div style='font-family:Segoe UI,Arial,sans-serif;line-height:1.5;color:#1f2937;'>",
        f"<h2 style='margin:0 0 8px 0;'>Bonjour {html.escape(safe_owner)},</h2>",
        f"<p style='margin:0 0 16px 0;'>Voici ton resume hebdomadaire ({date.today().isoformat()}).</p>",
        "<table style='width:100%;border-collapse:collapse;border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;'>",
        "<thead><tr style='background:#f8fafc;'>"
        "<th style='padding:10px;text-align:left;border-bottom:1px solid #e5e7eb;'>Dossier</th>"
        "<th style='padding:10px;text-align:left;border-bottom:1px solid #e5e7eb;'>Action</th>"
        "<th style='padding:10px;text-align:left;border-bottom:1px solid #e5e7eb;'>Deadline</th>"
        "</tr></thead>",
        "<tbody>",
        *html_rows,
        "</tbody></table>",
    ]
    if cleaned_app_url:
        html_parts.append(
            "<p style='margin:18px 0 0 0;'>"
            f"<a href='{html.escape(cleaned_app_url)}' "
            "style='display:inline-block;padding:10px 14px;border-radius:8px;background:#111827;color:#ffffff;text-decoration:none;'>"
            "Ouvrir DealTracker</a></p>"
        )
    html_parts.append("</div>")

    return "\n".join(text_lines), "".join(html_parts)


def build_owner_summary_whatsapp_messages(
    store_instance,
    *,
    owner_name: str,
    owner_id: str,
    app_url: str,
    max_message_length: int = 1300,
) -> list[str]:
    items = get_owner_todo_items(store_instance, owner_id)
    safe_owner = owner_name.strip() or "Utilisateur"
    cleaned_app_url = app_url.strip()

    if not items:
        body = f"Bonjour {safe_owner}, aucun to-do actif cette semaine."
        if cleaned_app_url:
            body += f"\n\nOuvrir DealTracker: {cleaned_app_url}"
        return [body]

    lines = [f"Bonjour {safe_owner}, voici tes actions actives ({len(items)}):", ""]
    for index, item in enumerate(items, start=1):
        lines.append(f"{index}. {item.company}")
        lines.append(f"   - Action: {item.action}")
        lines.append(f"   - Deadline: {item.deadline}")

    if cleaned_app_url:
        lines.extend(["", f"Ouvrir DealTracker: {cleaned_app_url}"])

    chunks: list[str] = []
    current_lines: list[str] = []
    current_len = 0

    for line in lines:
        addition = len(line) + (1 if current_lines else 0)
        if current_lines and current_len + addition > max_message_length:
            chunks.append("\n".join(current_lines))
            current_lines = [line]
            current_len = len(line)
        else:
            current_lines.append(line)
            current_len += addition

    if current_lines:
        chunks.append("\n".join(current_lines))

    if len(chunks) <= 1:
        return chunks

    numbered_chunks: list[str] = []
    total = len(chunks)
    for idx, chunk in enumerate(chunks, start=1):
        numbered_chunks.append(f"[{idx}/{total}]\n{chunk}")
    return numbered_chunks
