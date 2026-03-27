from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.schemas.deal import DashboardKPIs, DealCreate, DealRead, DealStatus, DealUpdate
from app.schemas.user_mapping import UserMapping


class SupabaseStore:
    def __init__(self, supabase_url: str, supabase_key: str) -> None:
        base_url = f"{supabase_url.rstrip('/')}/rest/v1"
        self._client = httpx.Client(
            base_url=base_url,
            headers={
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": "application/json",
            },
            timeout=15.0,
        )

    def _get(self, path: str, params: dict[str, str] | None = None) -> list[dict]:
        response = self._client.get(path, params=params)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return data
        return [data]

    def list_deals(self, status: DealStatus | None, owner_id: str | None) -> list[DealRead]:
        params: dict[str, str] = {
            "select": "id,company,description,action,deadline,owner_id,status,created_at,closed_at",
            "order": "deadline.asc",
        }
        if status is not None:
            params["status"] = f"eq.{status.value}"
        if owner_id is not None:
            params["owner_id"] = f"eq.{owner_id}"
        rows = self._get("/deals", params=params)
        return [DealRead.model_validate(row) for row in rows]

    def create_deal(self, payload: DealCreate) -> DealRead:
        response = self._client.post(
            "/deals",
            params={"select": "id,company,description,action,deadline,owner_id,status,created_at,closed_at"},
            headers={"Prefer": "return=representation"},
            json=payload.model_dump(mode="json"),
        )
        response.raise_for_status()
        rows = response.json()
        return DealRead.model_validate(rows[0])

    def update_deal(self, deal_id: str, payload: DealUpdate) -> DealRead | None:
        updates = payload.model_dump(exclude_none=True, mode="json")
        if not updates:
            rows = self._get(
                "/deals",
                params={
                    "id": f"eq.{deal_id}",
                    "select": "id,company,description,action,deadline,owner_id,status,created_at,closed_at",
                    "limit": "1",
                },
            )
            if not rows:
                return None
            return DealRead.model_validate(rows[0])

        if updates.get("status") in {DealStatus.won.value, DealStatus.lost.value}:
            updates.setdefault("closed_at", datetime.now(timezone.utc).isoformat())

        response = self._client.patch(
            "/deals",
            params={
                "id": f"eq.{deal_id}",
                "select": "id,company,description,action,deadline,owner_id,status,created_at,closed_at",
            },
            headers={"Prefer": "return=representation"},
            json=updates,
        )
        response.raise_for_status()
        rows = response.json()
        if not rows:
            return None
        return DealRead.model_validate(rows[0])

    def delete_deal(self, deal_id: str) -> bool:
        response = self._client.delete(
            "/deals",
            params={"id": f"eq.{deal_id}"},
            headers={"Prefer": "return=representation"},
        )
        response.raise_for_status()
        rows = response.json()
        return bool(rows)

    def dashboard_kpis(self, owner_id: str | None = None) -> DashboardKPIs:
        params = {"select": "status"}
        if owner_id is not None:
            params["owner_id"] = f"eq.{owner_id}"

        rows = self._get("/deals", params=params)
        active = sum(1 for row in rows if row["status"] == DealStatus.active.value)
        won = sum(1 for row in rows if row["status"] == DealStatus.won.value)
        lost = sum(1 for row in rows if row["status"] == DealStatus.lost.value)
        conversion = won / (won + lost) if (won + lost) > 0 else 0.0
        return DashboardKPIs(active=active, won=won, lost=lost, conversion=conversion)

    def list_users(self) -> list[UserMapping]:
        rows = self._get(
            "/users",
            params={"select": "id,full_name,email,whatsapp_number", "order": "created_at.asc"},
        )
        return [UserMapping.model_validate(row) for row in rows]

    def upsert_user_profile(self, user_id: str, email: str, full_name: str) -> UserMapping:
        existing_rows = self._get(
            "/users",
            params={
                "id": f"eq.{user_id}",
                "select": "id,full_name,email,whatsapp_number",
                "limit": "1",
            },
        )
        effective_full_name = full_name
        if existing_rows:
            existing_name = str(existing_rows[0].get("full_name") or "").strip()
            if existing_name:
                effective_full_name = existing_name

        response = self._client.post(
            "/users",
            params={"on_conflict": "id", "select": "id,full_name,email,whatsapp_number"},
            headers={"Prefer": "resolution=merge-duplicates,return=representation"},
            json={"id": user_id, "email": email, "full_name": effective_full_name},
        )
        response.raise_for_status()
        rows = response.json()
        return UserMapping.model_validate(rows[0])

    def update_user_mapping(self, user_id: str, whatsapp_number: str, full_name: str) -> UserMapping | None:
        response = self._client.patch(
            "/users",
            params={"id": f"eq.{user_id}", "select": "id,full_name,email,whatsapp_number"},
            headers={"Prefer": "return=representation"},
            json={"whatsapp_number": whatsapp_number, "full_name": full_name},
        )
        response.raise_for_status()
        rows = response.json()
        if not rows:
            return None
        return UserMapping.model_validate(rows[0])

    def find_user_by_whatsapp(self, phone: str) -> UserMapping | None:
        rows = self._get(
            "/users",
            params={
                "select": "id,full_name,email,whatsapp_number",
                "whatsapp_number": f"eq.{phone}",
                "limit": "1",
            },
        )
        if not rows:
            return None
        return UserMapping.model_validate(rows[0])

    def find_active_deal_by_company(self, owner_id: str, company: str) -> DealRead | None:
        rows = self._get(
            "/deals",
            params={
                "select": "id,company,description,action,deadline,owner_id,status,created_at,closed_at",
                "owner_id": f"eq.{owner_id}",
                "status": f"eq.{DealStatus.active.value}",
            },
        )
        company_normalized = company.strip().lower()
        for row in rows:
            if str(row.get("company", "")).strip().lower() == company_normalized:
                return DealRead.model_validate(row)
        return None
