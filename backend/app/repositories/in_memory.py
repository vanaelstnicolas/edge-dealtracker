from datetime import date, datetime, timezone
from typing import Iterable
from uuid import uuid4

from app.config import settings
from app.repositories.supabase import SupabaseStore
from app.schemas.deal import DashboardKPIs, DealCreate, DealRead, DealStatus, DealUpdate
from app.schemas.user_mapping import UserMapping


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InMemoryStore:
    def __init__(self) -> None:
        self.deals: dict[str, DealRead] = {}
        self.users: dict[str, UserMapping] = {}
        self._seed()

    def _seed(self) -> None:
        self.users["u-1"] = UserMapping(
            id="u-1",
            full_name="Nicolas Ferrand",
            email="nicolas@edge-consulting.fr",
            whatsapp_number="+33612345678",
        )
        self.users["u-2"] = UserMapping(
            id="u-2",
            full_name="Claire Dubois",
            email="claire@edge-consulting.fr",
            whatsapp_number="+33622334455",
        )

        deal = DealRead(
            id="dl-1",
            company="Nova Industrie",
            description="Renouvellement audit organisationnel",
            action="Envoyer proposition finale",
            deadline=date.today(),
            owner_id="u-1",
            status=DealStatus.active,
            created_at=_utc_now(),
        )
        self.deals[deal.id] = deal

    def list_deals(self, status: DealStatus | None, owner_id: str | None) -> list[DealRead]:
        rows: Iterable[DealRead] = self.deals.values()
        if status is not None:
            rows = [deal for deal in rows if deal.status == status]
        if owner_id is not None:
            rows = [deal for deal in rows if deal.owner_id == owner_id]
        return sorted(rows, key=lambda deal: deal.deadline)

    def create_deal(self, payload: DealCreate) -> DealRead:
        record = DealRead(
            id=str(uuid4()),
            created_at=_utc_now(),
            closed_at=_utc_now() if payload.status in {DealStatus.won, DealStatus.lost} else None,
            **payload.model_dump(),
        )
        self.deals[record.id] = record
        return record

    def update_deal(self, deal_id: str, payload: DealUpdate) -> DealRead | None:
        current = self.deals.get(deal_id)
        if current is None:
            return None
        updates = payload.model_dump(exclude_none=True)
        updated = current.model_copy(update=updates)
        if updated.status in {DealStatus.won, DealStatus.lost} and updated.closed_at is None:
            updated = updated.model_copy(update={"closed_at": _utc_now()})
        self.deals[deal_id] = updated
        return updated

    def delete_deal(self, deal_id: str) -> bool:
        if deal_id not in self.deals:
            return False
        del self.deals[deal_id]
        return True

    def dashboard_kpis(self, owner_id: str | None = None) -> DashboardKPIs:
        rows: Iterable[DealRead] = self.deals.values()
        if owner_id is not None:
            rows = [deal for deal in rows if deal.owner_id == owner_id]

        active = sum(1 for deal in rows if deal.status == DealStatus.active)
        won = sum(1 for deal in rows if deal.status == DealStatus.won)
        lost = sum(1 for deal in rows if deal.status == DealStatus.lost)
        conversion = won / (won + lost) if (won + lost) > 0 else 0.0
        return DashboardKPIs(active=active, won=won, lost=lost, conversion=conversion)

    def list_users(self) -> list[UserMapping]:
        return list(self.users.values())

    def upsert_user_profile(self, user_id: str, email: str, full_name: str) -> UserMapping:
        existing = self.users.get(user_id)
        updated = UserMapping(
            id=user_id,
            email=email,
            full_name=full_name,
            whatsapp_number=existing.whatsapp_number if existing else None,
        )
        self.users[user_id] = updated
        return updated

    def update_user_mapping(self, user_id: str, whatsapp_number: str) -> UserMapping | None:
        user = self.users.get(user_id)
        if user is None:
            return None
        updated = user.model_copy(update={"whatsapp_number": whatsapp_number})
        self.users[user_id] = updated
        return updated

    def find_user_by_whatsapp(self, phone: str) -> UserMapping | None:
        for user in self.users.values():
            if user.whatsapp_number is not None and user.whatsapp_number == phone:
                return user
        return None

    def find_active_deal_by_company(self, owner_id: str, company: str) -> DealRead | None:
        company_normalized = company.strip().lower()
        for deal in self.deals.values():
            if (
                deal.owner_id == owner_id
                and deal.status == DealStatus.active
                and deal.company.strip().lower() == company_normalized
            ):
                return deal
        return None


if settings.supabase_url and (settings.supabase_service_role_key or settings.supabase_anon_key):
    store = SupabaseStore(
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_service_role_key or settings.supabase_anon_key,
    )
else:
    store = InMemoryStore()
