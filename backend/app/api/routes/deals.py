from fastapi import APIRouter, HTTPException, Query, status

from app.repositories.in_memory import store
from app.schemas.deal import DealCreate, DealRead, DealStatus, DealUpdate

router = APIRouter()


@router.get("", response_model=list[DealRead])
def list_deals(
    status_value: DealStatus | None = Query(default=None, alias="status"),
    owner_id: str | None = Query(default=None),
) -> list[DealRead]:
    return store.list_deals(status=status_value, owner_id=owner_id)


@router.post("", response_model=DealRead, status_code=status.HTTP_201_CREATED)
def create_deal(payload: DealCreate) -> DealRead:
    return store.create_deal(payload)


@router.patch("/{deal_id}", response_model=DealRead)
def update_deal(deal_id: str, payload: DealUpdate) -> DealRead:
    updated = store.update_deal(deal_id, payload)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")
    return updated
