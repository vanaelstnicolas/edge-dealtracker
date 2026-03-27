from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps.auth import get_current_user
from app.config import settings
from app.repositories.in_memory import store
from app.schemas.user_mapping import UserMapping, UserMappingUpdate

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


def _row_id(row: UserMapping | dict[str, Any]) -> str:
    if isinstance(row, dict):
        return str(row.get("id", ""))
    return row.id


def _row_whatsapp(row: UserMapping | dict[str, Any]) -> str | None:
    if isinstance(row, dict):
        value = row.get("whatsapp_number")
        return str(value) if isinstance(value, str) else None
    return row.whatsapp_number


def _as_user_mapping(row: UserMapping | dict[str, Any]) -> UserMapping:
    if isinstance(row, UserMapping):
        return row
    return UserMapping.model_validate(row)


@router.get("/users", response_model=list[UserMapping])
def list_user_mappings(current_user: dict[str, Any] = Depends(get_current_user)) -> list[UserMapping]:
    rows = [_as_user_mapping(row) for row in store.list_users()]
    if _is_admin(current_user):
        return rows

    current_user_id = str(current_user["id"])
    return [row for row in rows if _row_id(row) == current_user_id]


@router.put("/users/{user_id}", response_model=UserMapping)
def update_user_mapping(
    user_id: str,
    payload: UserMappingUpdate,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> UserMapping:
    current_user_id = str(current_user["id"])
    if user_id != current_user_id and not _is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden owner scope")

    updated = store.update_user_mapping(
        user_id=user_id,
        whatsapp_number=payload.whatsapp_number,
        full_name=payload.full_name,
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return updated


@router.post("/users/{user_id}/whatsapp/test")
def send_whatsapp_test_message(
    user_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    current_user_id = str(current_user["id"])
    if user_id != current_user_id and not _is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden owner scope")

    rows: list[UserMapping | dict[str, Any]] = list(store.list_users())
    target = next((row for row in rows if _row_id(row) == user_id), None)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    whatsapp_number = _row_whatsapp(target)
    if not isinstance(whatsapp_number, str) or not whatsapp_number.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No WhatsApp number configured")

    account_sid = settings.twilio_account_sid.strip()
    auth_token = settings.twilio_auth_token.strip()
    from_number = settings.twilio_whatsapp_number.strip()
    if not account_sid or not auth_token or not from_number:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Twilio is not configured")

    normalized_from = from_number if from_number.startswith("whatsapp:") else f"whatsapp:{from_number}"
    normalized_to = (
        whatsapp_number if whatsapp_number.startswith("whatsapp:") else f"whatsapp:{whatsapp_number}"
    )

    try:
        response = httpx.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
            auth=(account_sid, auth_token),
            data={
                "From": normalized_from,
                "To": normalized_to,
                "Body": "DealTracker test: integration WhatsApp operationnelle.",
            },
            timeout=15.0,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        message = "Twilio send failed"
        try:
            twilio_payload = exc.response.json()
            twilio_message = str(twilio_payload.get("message", "")).strip()
            twilio_code = str(twilio_payload.get("code", "")).strip()
            if twilio_code and twilio_message:
                message = f"Twilio send failed ({twilio_code}): {twilio_message}"
            elif twilio_message:
                message = f"Twilio send failed: {twilio_message}"
        except ValueError:
            pass
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=message) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Twilio send failed") from exc

    payload = response.json()
    return {
        "result": "sent",
        "message_sid": str(payload.get("sid", "")),
    }
