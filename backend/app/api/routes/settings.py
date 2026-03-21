from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps.auth import get_current_user
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


@router.get("/users", response_model=list[UserMapping])
def list_user_mappings(current_user: dict[str, Any] = Depends(get_current_user)) -> list[UserMapping]:
    rows = store.list_users()
    if _is_admin(current_user):
        return rows

    current_user_id = str(current_user["id"])
    return [
        row
        for row in rows
        if (row.id if hasattr(row, "id") else str(row.get("id", ""))) == current_user_id
    ]


@router.put("/users/{user_id}", response_model=UserMapping)
def update_user_mapping(
    user_id: str,
    payload: UserMappingUpdate,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> UserMapping:
    current_user_id = str(current_user["id"])
    if user_id != current_user_id and not _is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden owner scope")

    updated = store.update_user_mapping(user_id=user_id, whatsapp_number=payload.whatsapp_number)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return updated
