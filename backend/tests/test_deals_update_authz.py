from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from app.api.deps import auth
from app.api.routes import deals as deals_route
from app.main import app
from app.schemas.deal import DealRead, DealStatus


class MockAuthResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload


def _configure_auth(monkeypatch, payload: dict) -> None:
    monkeypatch.setattr(auth.settings, "supabase_url", "https://example.supabase.co")
    monkeypatch.setattr(auth.settings, "supabase_anon_key", "anon-key")
    monkeypatch.setattr(auth.settings, "supabase_service_role_key", "")
    monkeypatch.setattr(auth.httpx, "get", lambda *args, **kwargs: MockAuthResponse(200, payload))
    monkeypatch.setattr(auth.store, "upsert_user_profile", lambda *args, **kwargs: None)


def _deal(owner_id: str) -> DealRead:
    return DealRead(
        id="dl-1",
        company="Nova Industrie",
        description="desc",
        action="act",
        deadline=date(2026, 3, 21),
        owner_id=owner_id,
        status=DealStatus.active,
        created_at=datetime.now(timezone.utc),
    )


def test_non_admin_cannot_reassign_owner(monkeypatch) -> None:
    client = TestClient(app)
    _configure_auth(
        monkeypatch,
        {
            "id": "u-1",
            "email": "user1@example.com",
            "user_metadata": {"full_name": "User One"},
            "app_metadata": {"role": "user"},
        },
    )

    monkeypatch.setattr(deals_route.store, "list_deals", lambda status=None, owner_id=None: [_deal("u-1")])

    response = client.patch(
        "/api/deals/dl-1",
        headers={"Authorization": "Bearer test-token"},
        json={"owner_id": "u-2"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden owner scope"}


def test_admin_can_reassign_owner(monkeypatch) -> None:
    client = TestClient(app)
    _configure_auth(
        monkeypatch,
        {
            "id": "u-admin",
            "email": "admin@example.com",
            "user_metadata": {"full_name": "Admin User"},
            "app_metadata": {"roles": ["admin"]},
        },
    )

    monkeypatch.setattr(deals_route.store, "list_deals", lambda status=None, owner_id=None: [_deal("u-1")])
    monkeypatch.setattr(
        deals_route.store,
        "update_deal",
        lambda deal_id, payload: _deal(payload.owner_id or "u-1"),
    )

    response = client.patch(
        "/api/deals/dl-1",
        headers={"Authorization": "Bearer test-token"},
        json={"owner_id": "u-2"},
    )

    assert response.status_code == 200
    assert response.json()["owner_id"] == "u-2"
