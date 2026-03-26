from contextlib import asynccontextmanager
import importlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from zoneinfo import ZoneInfo

from app.api.router import api_router
from app.config import settings
from app.jobs.weekly_summary import send_weekly_summaries_job


@asynccontextmanager
async def lifespan(_app: FastAPI):
    scheduler = None
    if settings.weekly_summary_scheduler_enabled:
        try:
            background = importlib.import_module("apscheduler.schedulers.background")
            BackgroundScheduler = background.BackgroundScheduler
            active_scheduler = BackgroundScheduler(timezone=ZoneInfo(settings.weekly_summary_timezone))
            active_scheduler.add_job(
                send_weekly_summaries_job,
                trigger="cron",
                day_of_week=settings.weekly_summary_day_of_week,
                hour=settings.weekly_summary_hour,
                minute=settings.weekly_summary_minute,
                id="weekly-owner-summary",
                replace_existing=True,
            )
            active_scheduler.start()
            scheduler = active_scheduler
        except ModuleNotFoundError:
            scheduler = None

    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)

app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)
