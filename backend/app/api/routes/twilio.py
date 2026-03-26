import base64
import hashlib
import hmac
import json
import logging
import re
import unicodedata
from datetime import date, timedelta
from io import BytesIO
from xml.sax.saxutils import escape

import httpx
from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from app.config import settings
from app.repositories.in_memory import store
from app.schemas.deal import DealCreate, DealStatus, DealUpdate
from app.services.action_summary import build_owner_summary_text
from app.services.notifications import send_whatsapp_message
from app.services.rate_limit import enforce_rate_limit

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
        '{"intent":"create|update|close|summary|unknown","company":"","description":"","action":"","deadline":"YYYY-MM-DD","status":"won|lost"}. '
        "Interprete aussi les messages naturels (ex: opportunite chez X, rencontre le 10/4). "
        "Si date fournie en format jour/mois, convertis-la en YYYY-MM-DD avec l'annee en cours. "
        "Si action manquante pour create, propose une action courte. "
        "Si deadline absente, laisse vide."
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

    if intent == "summary":
        return "summary"

    if intent == "create" and company:
        if not description:
            description = "Opportunite detectee via WhatsApp"
        if not action:
            action = "Planifier prochain contact"
        if not deadline:
            deadline = (date.today() + timedelta(days=7)).isoformat()
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
    if lowered.startswith("summary") or lowered.startswith("resume") or lowered.startswith("todo"):
        return "summary"
    return "unknown"


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def _parse_french_date_to_iso(raw_text: str) -> str | None:
    match = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", raw_text)
    if not match:
        return None

    day = int(match.group(1))
    month = int(match.group(2))
    year_part = match.group(3)
    year = int(year_part) if year_part else date.today().year
    if year < 100:
        year += 2000

    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _heuristic_command_from_natural_text(message: str) -> str | None:
    raw = message.strip()
    if not raw:
        return None

    normalized = _normalize_text(raw)
    if "opportunit" not in normalized and "prospect" not in normalized:
        return None

    company_match = re.search(r"\bchez\s+([^\.,;\n]+)", raw, flags=re.IGNORECASE)
    if not company_match:
        return None

    company_candidate = company_match.group(1)
    company = re.split(r"\b(pour|avec|sur|et|qui|que)\b", company_candidate, flags=re.IGNORECASE)[0].strip(" -")
    if not company:
        return None

    deadline = _parse_french_date_to_iso(raw) or (date.today() + timedelta(days=7)).isoformat()
    if any(keyword in normalized for keyword in ["rencontre", "rdv", "rendez-vous", "meeting"]):
        action = "Preparer la rencontre client"
    else:
        action = "Planifier le prochain contact"

    description = raw[:240]
    return f"create {company}|{description}|{action}|{deadline}"


def _transcribe_audio_from_twilio_media(media_url: str, content_type: str | None = None) -> str | None:
    if not settings.openai_api_key:
        return None

    account_sid = settings.twilio_account_sid.strip()
    auth_token = settings.twilio_auth_token.strip()
    if not account_sid or not auth_token:
        return None

    try:
        media_response = httpx.get(
            media_url,
            auth=(account_sid, auth_token),
            timeout=20.0,
            follow_redirects=True,
        )
        media_response.raise_for_status()
        audio_bytes = media_response.content

        files = {
            "file": (
                "voice-message.ogg",
                BytesIO(audio_bytes),
                content_type or "audio/ogg",
            )
        }
        transcription_response = httpx.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            data={"model": settings.openai_transcribe_model},
            files=files,
            timeout=30.0,
        )
        transcription_response.raise_for_status()
        payload = transcription_response.json()
        text = str(payload.get("text", "")).strip()
        return text or None
    except httpx.HTTPStatusError as exc:
        details = ""
        try:
            body = exc.response.text
            details = f" status={exc.response.status_code} body={body[:300]}"
        except Exception:
            details = ""
        logger.warning("openai_transcription_failed%s", details)
        return None
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        logger.warning("openai_transcription_failed error=%s", exc)
        return None


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
    return Response(content=body, media_type="text/xml", status_code=status.HTTP_200_OK)


def _twiml_empty_response() -> Response:
    return Response(content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>', media_type="text/xml")


def _send_whatsapp_reply(to_number: str, message: str) -> bool:
    try:
        sid = send_whatsapp_message(to_number=to_number, body=message)
        logger.info("twilio_reply_sent sid=%s to=%s", sid, to_number)
        return True
    except Exception as exc:  # pragma: no cover - defensive runtime path
        logger.warning("twilio_reply_send_failed to=%s error=%s", to_number, exc)
        return False


def _handle_text_command(owner_id: str, body: str) -> tuple[str, str]:
    command = body.strip()
    lowered = command.lower()

    if lowered in {"summary", "resume", "résumé", "todo", "to do", "actions"} or lowered.startswith("summary"):
        owner = next((row for row in store.list_users() if row.id == owner_id), None)
        owner_name = owner.full_name if owner else "Utilisateur"
        summary = build_owner_summary_text(store, owner_name=owner_name, owner_id=owner_id)
        return "summary", summary

    if lowered.startswith("create "):
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

    if lowered.startswith("update "):
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

    if lowered.startswith("close "):
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

    return "error", "Commande inconnue. Utilise create, update, close ou summary."


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
    media_content_type = data.get("MediaContentType0")

    phone = from_number.replace("whatsapp:", "")
    enforce_rate_limit(
        bucket="twilio_webhook",
        key=phone or (request.client.host if request.client else "unknown"),
        limit=settings.twilio_rate_limit_per_phone,
        window_seconds=settings.rate_limit_window_seconds,
    )

    user = store.find_user_by_whatsapp(phone)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown WhatsApp sender")

    if media_url:
        transcript = _transcribe_audio_from_twilio_media(media_url=media_url, content_type=media_content_type)
        if not transcript:
            fallback_message = "Audio recu mais transcription indisponible. Envoie aussi le texte si possible."
            if not _send_whatsapp_reply(phone, fallback_message):
                return _twiml_message(fallback_message)
            return _twiml_empty_response()
        body = transcript

    if not body.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Empty message")

    nlu_command = _nlu_command_from_openai(body)
    heuristic_command = None if nlu_command else _heuristic_command_from_natural_text(body)
    command_body = nlu_command or heuristic_command or body
    logger.info(
        "twilio_command_received",
        extra={
            "owner_id": user.id,
            "command_source": "openai_nlu" if nlu_command else "heuristic_nlu" if heuristic_command else "raw_text",
            "command_kind": _command_kind(command_body),
            "parsed_command": command_body,
            "has_media": bool(media_url),
            "transcribed_from_media": bool(media_url and body),
        },
    )
    result, message = _handle_text_command(owner_id=user.id, body=command_body)
    logger.info(
        "twilio_command_result",
        extra={"owner_id": user.id, "result": result, "message_preview": message[:120]},
    )
    if not _send_whatsapp_reply(phone, message):
        return _twiml_message(message)
    return _twiml_empty_response()


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
