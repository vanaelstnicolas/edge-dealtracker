from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps.auth import get_current_user
from app.repositories.in_memory import store
from app.schemas.deal import DealCreate, DealRead, DealStatus, DealUpdate

router = APIRouter()


@router.get("", response_model=list[DealRead])
def list_deals(
    current_user: dict[str, Any] = Depends(get_current_user),
    status_value: DealStatus | None = Query(default=None, alias="status"),
    owner_id: str | None = Query(default=None),
) -> list[DealRead]:
    user_id = str(current_user["id"])
    if owner_id is not None and owner_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden owner scope")
    return store.list_deals(status=status_value, owner_id=user_id)


@router.post("", response_model=DealRead, status_code=status.HTTP_201_CREATED)
def create_deal(payload: DealCreate, current_user: dict[str, Any] = Depends(get_current_user)) -> DealRead:
    user_id = str(current_user["id"])
    if payload.owner_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden owner scope")
    return store.create_deal(payload)


@router.patch("/{deal_id}", response_model=DealRead)
def update_deal(deal_id: str, payload: DealUpdate, current_user: dict[str, Any] = Depends(get_current_user)) -> DealRead:
    user_id = str(current_user["id"])
    if all(deal.id != deal_id for deal in store.list_deals(status=None, owner_id=user_id)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")

    updated = store.update_deal(deal_id, payload)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
    return updated
