from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.repositories.in_memory import store

security = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


def _extract_profile_data(payload: dict[str, Any]) -> tuple[str, str]:
    email = str(payload.get("email") or "").strip().lower()

    full_name = ""
    metadata = payload.get("user_metadata")
    if isinstance(metadata, dict):
        for key in ("full_name", "name", "display_name"):
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                full_name = value.strip()
                break

    if not full_name:
        full_name = str(payload.get("phone") or "").strip()
    if not full_name and email:
        full_name = email.split("@", maxsplit=1)[0]
    return email, full_name


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    supabase_url = settings.supabase_url.strip()
    supabase_key = (settings.supabase_anon_key or settings.supabase_service_role_key).strip()
    if not supabase_url or not supabase_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Auth provider is not configured")

    token = credentials.credentials
    try:
        response = httpx.get(
            f"{supabase_url.rstrip('/')}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": supabase_key,
            },
            timeout=10.0,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Auth provider unavailable") from exc

    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    payload = response.json()
    if not isinstance(payload, dict) or "id" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user payload")

    email, full_name = _extract_profile_data(payload)
    if email and full_name:
        try:
            store.upsert_user_profile(user_id=str(payload["id"]), email=email, full_name=full_name)
        except Exception as exc:
            logger.exception("failed_to_upsert_user_profile")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="User profile sync failed",
            ) from exc

    return payload
