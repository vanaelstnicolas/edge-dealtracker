from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DealStatus(str, Enum):
    active = "active"
    won = "won"
    lost = "lost"


class DealBase(BaseModel):
    company: str = Field(min_length=2, max_length=140)
    description: str = Field(min_length=2, max_length=2000)
    action: str = Field(min_length=2, max_length=240)
    deadline: date
    owner_id: str = Field(min_length=2, max_length=120)
    status: DealStatus = DealStatus.active


class DealCreate(DealBase):
    pass


class DealUpdate(BaseModel):
    company: Optional[str] = Field(default=None, min_length=2, max_length=140)
    description: Optional[str] = Field(default=None, min_length=2, max_length=2000)
    action: Optional[str] = Field(default=None, min_length=2, max_length=240)
    deadline: Optional[date] = None
    status: Optional[DealStatus] = None
    owner_id: Optional[str] = Field(default=None, min_length=2, max_length=120)


class DealRead(DealBase):
    id: str
    created_at: datetime
    closed_at: Optional[datetime] = None


class DashboardKPIs(BaseModel):
    active: int
    won: int
    lost: int
    conversion: float
