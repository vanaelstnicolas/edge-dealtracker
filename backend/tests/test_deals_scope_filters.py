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


def _configure_auth(monkeypatch) -> None:
    monkeypatch.setattr(auth.settings, "supabase_url", "https://example.supabase.co")
    monkeypatch.setattr(auth.settings, "supabase_anon_key", "anon-key")
    monkeypatch.setattr(auth.settings, "supabase_service_role_key", "")
    monkeypatch.setattr(
        auth.httpx,
        "get",
        lambda *args, **kwargs: MockAuthResponse(
            200,
            {
                "id": "u-1",
                "email": "user1@example.com",
                "user_metadata": {"full_name": "User One"},
            },
        ),
    )
    monkeypatch.setattr(auth.store, "upsert_user_profile", lambda *args, **kwargs: None)


def _deal(deal_id: str, status: DealStatus) -> DealRead:
    return DealRead(
        id=deal_id,
        company="ACME",
        description="desc",
        action="action",
        deadline=date(2026, 4, 1),
        owner_id="u-1",
        status=status,
        created_at=datetime.now(timezone.utc),
    )


def test_list_deals_scope_archived(monkeypatch) -> None:
    client = TestClient(app)
    _configure_auth(monkeypatch)
    monkeypatch.setattr(
        deals_route.store,
        "list_deals",
        lambda status=None, owner_id=None: [_deal("dl-1", DealStatus.active), _deal("dl-2", DealStatus.won)],
    )

    response = client.get("/api/deals?scope=archived", headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["id"] == "dl-2"


def test_list_deals_scope_active(monkeypatch) -> None:
    client = TestClient(app)
    _configure_auth(monkeypatch)
    monkeypatch.setattr(
        deals_route.store,
        "list_deals",
        lambda status=None, owner_id=None: [_deal("dl-1", DealStatus.active), _deal("dl-2", DealStatus.lost)],
    )

    response = client.get("/api/deals?scope=active", headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["id"] == "dl-1"
