from fastapi.testclient import TestClient

from app.api.deps import auth
from app.api.routes import dashboard
from app.main import app


class MockAuthResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload


def test_dashboard_kpis_are_scoped_to_authenticated_user(monkeypatch) -> None:
    client = TestClient(app)

    monkeypatch.setattr(auth.settings, "supabase_url", "https://example.supabase.co")
    monkeypatch.setattr(auth.settings, "supabase_anon_key", "anon-key")
    monkeypatch.setattr(auth.settings, "supabase_service_role_key", "")

    monkeypatch.setattr(
        auth.httpx,
        "get",
        lambda *args, **kwargs: MockAuthResponse(
            200,
            {
                "id": "00000000-0000-0000-0000-0000000000ab",
                "email": "kpi-user@example.com",
                "user_metadata": {"full_name": "KPI User"},
            },
        ),
    )

    monkeypatch.setattr(auth.store, "upsert_user_profile", lambda *args, **kwargs: None)

    captured: dict[str, str] = {}

    def fake_dashboard_kpis(owner_id: str):
        captured["owner_id"] = owner_id
        return {"active": 3, "won": 2, "lost": 1, "conversion": 2 / 3}

    monkeypatch.setattr(dashboard.store, "dashboard_kpis", fake_dashboard_kpis)

    response = client.get("/api/dashboard/kpis", headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 200
    assert captured["owner_id"] == "00000000-0000-0000-0000-0000000000ab"
    assert response.json()["active"] == 3
