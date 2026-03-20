from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps.auth import get_current_user
from app.repositories.in_memory import store
from app.schemas.deal import DashboardKPIs

router = APIRouter()


@router.get("/kpis", response_model=DashboardKPIs)
def get_kpis(_current_user: dict[str, Any] = Depends(get_current_user)) -> DashboardKPIs:
    return store.dashboard_kpis()
