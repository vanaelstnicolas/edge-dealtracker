import base64
import hashlib
import hmac
import json
import logging
from datetime import date
from xml.sax.saxutils import escape

import httpx
from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from app.config import settings
from app.repositories.in_memory import store
from app.schemas.deal import DealCreate, DealStatus, DealUpdate

router = APIRouter()
logger = logging.getLogger(__name__)


class TwilioNluDebugRequest(BaseModel):
    owner_id: str = Field(min_length=2, max_length=120)
    message: str = Field(min_length=1, max_length=4000)


def _extract_openai_output_text(payload: dict) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    for output_item in payload.get("output", []):
        for content_item in output_item.get("content", []):
            text_value = content_item.get("text")
            if isinstance(text_value, str) and text_value.strip():
                return text_value
    return ""


def _nlu_command_from_openai(message: str) -> str | None:
    if not settings.openai_api_key:
        return None

    system_prompt = (
        "Tu extrais des intentions CRM. Retourne uniquement un JSON valide avec la forme: "
        '{"intent":"create|update|close|unknown","company":"","description":"","action":"","deadline":"YYYY-MM-DD","status":"won|lost"}. '
        "Laisse les champs inutiles en chaine vide."
    )
    user_prompt = f"Message utilisateur: {message}"

    try:
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
                        "content": [{"type": "input_text", "text": user_prompt}],
                    },
                ],
            },
            timeout=20.0,
        )
        response.raise_for_status()
        payload = json.loads(_extract_openai_output_text(response.json()))
    except (httpx.HTTPError, json.JSONDecodeError, ValueError, TypeError):
        return None

    intent = str(payload.get("intent", "")).strip().lower()
    company = str(payload.get("company", "")).strip()
    description = str(payload.get("description", "")).strip()
    action = str(payload.get("action", "")).strip()
    deadline = str(payload.get("deadline", "")).strip()
    status_value = str(payload.get("status", "")).strip().lower()

    if intent == "create" and company and description and action and deadline:
        return f"create {company}|{description}|{action}|{deadline}"
    if intent == "update" and company and action:
        return f"update {company}|{action}"
    if intent == "close" and company and status_value in {"won", "lost"}:
        return f"close {company}|{status_value}"
    return None


def _command_kind(command: str) -> str:
    lowered = command.strip().lower()
    if lowered.startswith("create "):
        return "create"
    if lowered.startswith("update "):
        return "update"
    if lowered.startswith("close "):
        return "close"
    return "unknown"


def _is_valid_twilio_signature(request_url: str, params: dict[str, str], signature: str) -> bool:
    if not settings.twilio_auth_token:
        return True
    payload = request_url + "".join(f"{key}{params[key]}" for key in sorted(params))
    digest = hmac.new(settings.twilio_auth_token.encode("utf-8"), payload.encode("utf-8"), hashlib.sha1).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature)


def _twiml_message(message: str) -> Response:
    safe_message = escape(message)
    body = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{safe_message}</Message></Response>'
    return Response(content=body, media_type="application/xml")


def _handle_text_command(owner_id: str, body: str) -> tuple[str, str]:
    command = body.strip()

    if command.lower().startswith("create "):
        payload = command[7:]
        parts = [chunk.strip() for chunk in payload.split("|")]
        if len(parts) != 4:
            return "error", "Format create attendu: create company|description|action|YYYY-MM-DD"
        company, description, action, raw_deadline = parts
        try:
            deadline = date.fromisoformat(raw_deadline)
        except ValueError:
            return "error", "Deadline invalide, utilise YYYY-MM-DD"
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
        return "created", f"Dossier cree pour {company}."

    if command.lower().startswith("update "):
        payload = command[7:]
        parts = [chunk.strip() for chunk in payload.split("|")]
        if len(parts) != 2:
            return "error", "Format update attendu: update company|action"
        company, action = parts
        deal = store.find_active_deal_by_company(owner_id=owner_id, company=company)
        if deal is None:
            return "error", f"Aucun dossier actif trouve pour {company}."
        store.update_deal(deal.id, DealUpdate(action=action))
        return "updated", f"Action mise a jour pour {company}."

    if command.lower().startswith("close "):
        payload = command[6:]
        parts = [chunk.strip() for chunk in payload.split("|")]
        if len(parts) != 2:
            return "error", "Format close attendu: close company|won|lost"
        company, raw_status = parts
        if raw_status not in {"won", "lost"}:
            return "error", "Statut de cloture invalide (won ou lost)."
        deal = store.find_active_deal_by_company(owner_id=owner_id, company=company)
        if deal is None:
            return "error", f"Aucun dossier actif trouve pour {company}."
        store.update_deal(deal.id, DealUpdate(status=DealStatus(raw_status)))
        return "closed", f"Dossier {company} cloture en {raw_status}."

    return "error", "Commande inconnue. Utilise create, update ou close."


@router.post("/twilio")
async def receive_twilio_webhook(request: Request) -> Response:
    form = await request.form()
    data = {key: str(value) for key, value in form.multi_items()}
    signature = request.headers.get("X-Twilio-Signature", "")
    request_url = str(request.url)

    if not _is_valid_twilio_signature(request_url=request_url, params=data, signature=signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Twilio signature")

    from_number = data.get("From", "")
    body = data.get("Body", "")
    media_url = data.get("MediaUrl0")

    phone = from_number.replace("whatsapp:", "")
    user = store.find_user_by_whatsapp(phone)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown WhatsApp sender")

    if media_url:
        return _twiml_message("Audio recu. Transcription IA en cours.")

    if not body.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Empty message")

    nlu_command = _nlu_command_from_openai(body)
    command_body = nlu_command or body
    logger.info(
        "twilio_command_received",
        extra={
            "owner_id": user.id,
            "command_source": "openai_nlu" if nlu_command else "raw_text",
            "command_kind": _command_kind(command_body),
            "parsed_command": command_body,
            "has_media": bool(media_url),
        },
    )
    result, message = _handle_text_command(owner_id=user.id, body=command_body)
    logger.info("twilio_command_result", extra={"owner_id": user.id, "result": result})
    return _twiml_message(message)


@router.post("/twilio/debug/parse")
def debug_parse_twilio_message(payload: TwilioNluDebugRequest) -> dict[str, str]:
    if settings.environment.lower() not in {"dev", "staging"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    nlu_command = _nlu_command_from_openai(payload.message)
    command_body = nlu_command or payload.message
    result, message = _handle_text_command(owner_id=payload.owner_id, body=command_body)
    return {
        "result": result,
        "message": message,
        "owner_id": payload.owner_id,
        "command_source": "openai_nlu" if nlu_command else "raw_text",
        "parsed_command": command_body,
    }
