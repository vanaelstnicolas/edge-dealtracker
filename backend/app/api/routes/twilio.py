import base64
import hashlib
import hmac
from datetime import date

from fastapi import APIRouter, HTTPException, Request, status

from app.config import settings
from app.repositories.in_memory import store
from app.schemas.deal import DealCreate, DealStatus, DealUpdate

router = APIRouter()


def _is_valid_twilio_signature(request_url: str, params: dict[str, str], signature: str) -> bool:
    if not settings.twilio_auth_token:
        return True
    payload = request_url + "".join(f"{key}{params[key]}" for key in sorted(params))
    digest = hmac.new(settings.twilio_auth_token.encode("utf-8"), payload.encode("utf-8"), hashlib.sha1).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature)


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
async def receive_twilio_webhook(request: Request) -> dict[str, str]:
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
        return {
            "result": "received_audio",
            "message": "Audio recu. Transcription IA en cours.",
            "owner_id": user.id,
        }

    if not body.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Empty message")

    result, message = _handle_text_command(owner_id=user.id, body=body)
    return {
        "result": result,
        "message": message,
        "owner_id": user.id,
    }
