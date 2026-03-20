from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps.auth import get_current_user
from app.repositories.in_memory import store
from app.schemas.user_mapping import UserMapping, UserMappingUpdate

router = APIRouter()


@router.get("/users", response_model=list[UserMapping])
def list_user_mappings(_current_user: dict[str, Any] = Depends(get_current_user)) -> list[UserMapping]:
    return store.list_users()


@router.put("/users/{user_id}", response_model=UserMapping)
def update_user_mapping(
    user_id: str,
    payload: UserMappingUpdate,
    _current_user: dict[str, Any] = Depends(get_current_user),
) -> UserMapping:
    updated = store.update_user_mapping(user_id=user_id, whatsapp_number=payload.whatsapp_number)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return updated
