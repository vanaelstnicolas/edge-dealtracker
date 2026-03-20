from fastapi import APIRouter

from app.repositories.in_memory import store
from app.schemas.deal import DashboardKPIs

router = APIRouter()


@router.get("/kpis", response_model=DashboardKPIs)
def get_kpis() -> DashboardKPIs:
    return store.dashboard_kpis()
