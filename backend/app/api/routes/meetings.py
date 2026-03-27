from __future__ import annotations

from io import BytesIO
from datetime import date, timedelta
import json
from typing import Any, Literal

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - optional import guard
    PdfReader = None

from app.api.deps.auth import get_current_user
from app.config import settings
from app.repositories.in_memory import store
from app.schemas.deal import DealCreate, DealStatus, DealUpdate

router = APIRouter()
MAX_MEETING_FILE_BYTES = 5 * 1024 * 1024


class MeetingExtractRequest(BaseModel):
    content: str = Field(min_length=20, max_length=60000)


class MeetingAction(BaseModel):
    operation: Literal["create", "update", "close", "ignore"]
    company: str = Field(default="", max_length=140)
    description: str = Field(default="", max_length=2000)
    action: str = Field(default="", max_length=240)
    deadline: str = Field(default="")
    status: Literal["", "won", "lost"] = ""
    reason: str = Field(default="", max_length=400)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class MeetingExtractResponse(BaseModel):
    actions: list[MeetingAction]


class MeetingApplyRequest(BaseModel):
    actions: list[MeetingAction]
    dry_run: bool = False


def _extract_openai_output_text(payload: dict[str, Any]) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    for output_item in payload.get("output", []):
        for content_item in output_item.get("content", []):
            text_value = content_item.get("text")
            if isinstance(text_value, str) and text_value.strip():
                return text_value
    return ""


def _extract_actions_with_openai(content: str) -> list[MeetingAction]:
    if not settings.openai_api_key.strip():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI extraction is not configured")

    system_prompt = (
        "Tu lis un compte rendu de reunion commerciale. "
        "Retourne uniquement un JSON valide de la forme: "
        '{"actions":[{"operation":"create|update|close|ignore","company":"","description":"","action":"",'
        '"deadline":"YYYY-MM-DD","status":"won|lost|","reason":"","confidence":0.0}]}. '
        "Regles: operation=create pour nouveau dossier, update pour dossier existant, "
        "close pour cloturer un dossier (status won ou lost), ignore sinon. "
        "Si date absente, laisse deadline vide. Pas de texte hors JSON."
    )

    response = httpx.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.openai_nlu_model,
            "temperature": 0,
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_prompt}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": content}],
                },
            ],
        },
        timeout=30.0,
    )
    response.raise_for_status()

    try:
        parsed = json.loads(_extract_openai_output_text(response.json()))
        rows = parsed.get("actions", [])
        if not isinstance(rows, list):
            return []
        return [MeetingAction.model_validate(row) for row in rows]
    except (json.JSONDecodeError, ValueError, TypeError):
        return []


def _parse_deadline(raw_deadline: str) -> date:
    cleaned = raw_deadline.strip()
    if not cleaned:
        return date.today() + timedelta(days=7)
    try:
        return date.fromisoformat(cleaned)
    except ValueError:
        return date.today() + timedelta(days=7)


def _extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    if PdfReader is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PDF extraction is unavailable")

    try:
        reader = PdfReader(BytesIO(pdf_bytes))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid PDF file") from exc

    chunks: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            chunks.append(text)
    return "\n".join(chunks).strip()


def _extract_text_from_upload_bytes(*, file_name: str, content_type: str | None, payload: bytes) -> str:
    name = file_name.lower().strip()
    content_type_value = (content_type or "").lower().strip()

    if name.endswith(".pdf") or content_type_value == "application/pdf":
        return _extract_text_from_pdf_bytes(payload)

    if name.endswith(".txt") or name.endswith(".md") or name.endswith(".csv") or content_type_value.startswith("text/"):
        return payload.decode("utf-8", errors="ignore").strip()

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported file format. Use .pdf, .txt, .md or .csv",
    )


@router.post("/extract", response_model=MeetingExtractResponse)
def extract_meeting_actions(payload: MeetingExtractRequest, current_user: dict[str, Any] = Depends(get_current_user)) -> MeetingExtractResponse:
    del current_user
    actions = _extract_actions_with_openai(payload.content)
    return MeetingExtractResponse(actions=actions)


@router.post("/extract/file", response_model=MeetingExtractResponse)
async def extract_meeting_actions_from_file(
    current_user: dict[str, Any] = Depends(get_current_user),
    file: UploadFile = File(...),
) -> MeetingExtractResponse:
    del current_user

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")
    if len(payload) > MAX_MEETING_FILE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Uploaded file is too large")

    text = _extract_text_from_upload_bytes(file_name=file.filename or "", content_type=file.content_type, payload=payload)
    if len(text.strip()) < 20:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not enough readable text found in file")

    actions = _extract_actions_with_openai(text[:60000])
    return MeetingExtractResponse(actions=actions)


@router.post("/apply")
def apply_meeting_actions(payload: MeetingApplyRequest, current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    owner_id = str(current_user["id"])

    created = 0
    updated = 0
    closed = 0
    ignored = 0
    failed = 0
    details: list[dict[str, str]] = []

    for item in payload.actions:
        if item.operation == "ignore":
            ignored += 1
            continue

        company = item.company.strip()
        if not company:
            failed += 1
            details.append({"operation": item.operation, "company": "", "result": "missing_company"})
            continue

        if item.operation == "create":
            if payload.dry_run:
                created += 1
                details.append({"operation": "create", "company": company, "result": "dry_run"})
                continue

            description = item.description.strip() or "Ajout depuis compte rendu de reunion"
            action = item.action.strip() or "Planifier la prochaine action"
            deadline = _parse_deadline(item.deadline)
            store.create_deal(
                DealCreate(
                    owner_id=owner_id,
                    company=company,
                    description=description,
                    action=action,
                    deadline=deadline,
                    status=DealStatus.active,
                )
            )
            created += 1
            details.append({"operation": "create", "company": company, "result": "created"})
            continue

        deal = store.find_active_deal_by_company(owner_id=owner_id, company=company)
        if deal is None:
            failed += 1
            details.append({"operation": item.operation, "company": company, "result": "active_deal_not_found"})
            continue

        if item.operation == "update":
            if payload.dry_run:
                updated += 1
                details.append({"operation": "update", "company": company, "result": "dry_run"})
                continue

            update_payload = DealUpdate(
                description=item.description.strip() or None,
                action=item.action.strip() or None,
                deadline=_parse_deadline(item.deadline) if item.deadline.strip() else None,
            )
            store.update_deal(deal.id, update_payload)
            updated += 1
            details.append({"operation": "update", "company": company, "result": "updated"})
            continue

        if item.operation == "close":
            if item.status not in {"won", "lost"}:
                failed += 1
                details.append({"operation": "close", "company": company, "result": "missing_status"})
                continue

            if payload.dry_run:
                closed += 1
                details.append({"operation": "close", "company": company, "result": "dry_run"})
                continue

            store.update_deal(deal.id, DealUpdate(status=DealStatus(item.status)))
            closed += 1
            details.append({"operation": "close", "company": company, "result": "closed"})
            continue

    return {
        "created": created,
        "updated": updated,
        "closed": closed,
        "ignored": ignored,
        "failed": failed,
        "details": details,
    }
