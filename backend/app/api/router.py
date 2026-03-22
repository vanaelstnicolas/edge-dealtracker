from fastapi import APIRouter

from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.deals import router as deals_router
from app.api.routes.health import router as health_router
from app.api.routes.settings import router as settings_router
from app.api.routes.summary import router as summary_router
from app.api.routes.twilio import router as twilio_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(deals_router, prefix="/deals", tags=["deals"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(settings_router, prefix="/settings", tags=["settings"])
api_router.include_router(summary_router, prefix="/summary", tags=["summary"])
api_router.include_router(twilio_router, prefix="/webhooks", tags=["webhooks"])
