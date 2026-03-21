from fastapi.testclient import TestClient

from app.api.deps import auth
from app.api.routes import deals, settings
from app.main import app


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


def test_business_smoke_login_deals_settings(monkeypatch) -> None:
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

    monkeypatch.setattr(
        deals.store,
        "list_deals",
        lambda status=None, owner_id=None: [
            {
                "id": "dl-1",
                "company": "Nova Industrie",
                "description": "Relance finale",
                "action": "Envoyer proposition",
                "deadline": "2026-03-31",
                "owner_id": owner_id or "u-1",
                "status": "active",
                "created_at": "2026-03-20T10:00:00Z",
                "closed_at": None,
            }
        ],
    )

    monkeypatch.setattr(
        settings.store,
        "list_users",
        lambda: [
            {"id": "u-1", "full_name": "User One", "email": "user1@example.com", "whatsapp_number": None},
            {"id": "u-2", "full_name": "User Two", "email": "user2@example.com", "whatsapp_number": "+33611112222"},
        ],
    )

    monkeypatch.setattr(
        settings.store,
        "update_user_mapping",
        lambda user_id, whatsapp_number: {
            "id": user_id,
            "full_name": "User One",
            "email": "user1@example.com",
            "whatsapp_number": whatsapp_number,
        },
    )

    login_gate = client.get("/api/deals")
    assert login_gate.status_code == 401

    deals_response = client.get("/api/deals", headers={"Authorization": "Bearer test-token"})
    assert deals_response.status_code == 200
    assert len(deals_response.json()) == 1
    assert deals_response.json()[0]["owner_id"] == "u-1"

    settings_list = client.get("/api/settings/users", headers={"Authorization": "Bearer test-token"})
    assert settings_list.status_code == 200
    assert len(settings_list.json()) == 1
    assert settings_list.json()[0]["id"] == "u-1"

    settings_update = client.put(
        "/api/settings/users/u-1",
        headers={"Authorization": "Bearer test-token"},
        json={"whatsapp_number": "+33699990000"},
    )
    assert settings_update.status_code == 200
    assert settings_update.json()["whatsapp_number"] == "+33699990000"
