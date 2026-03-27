from fastapi.testclient import TestClient

from app.api.deps import auth
from app.api.routes import settings as settings_route
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


def test_settings_update_forbidden_for_other_non_admin_user(monkeypatch) -> None:
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

    response = client.put(
        "/api/settings/users/u-2",
        headers={"Authorization": "Bearer test-token"},
        json={"full_name": "User Two", "whatsapp_number": "+33612345679"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden owner scope"}


def test_settings_list_returns_only_self_for_non_admin_user(monkeypatch) -> None:
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
        settings_route.store,
        "list_users",
        lambda: [
            {"id": "u-1", "full_name": "User One", "email": "user1@example.com", "whatsapp_number": None},
            {"id": "u-2", "full_name": "User Two", "email": "user2@example.com", "whatsapp_number": "+33612345679"},
        ],
    )

    response = client.get("/api/settings/users", headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["id"] == "u-1"


def test_settings_list_returns_all_for_admin_user(monkeypatch) -> None:
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

    monkeypatch.setattr(
        settings_route.store,
        "list_users",
        lambda: [
            {"id": "u-1", "full_name": "User One", "email": "user1@example.com", "whatsapp_number": None},
            {"id": "u-2", "full_name": "User Two", "email": "user2@example.com", "whatsapp_number": "+33612345679"},
        ],
    )

    response = client.get("/api/settings/users", headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 2


def test_settings_update_allowed_for_admin_user(monkeypatch) -> None:
    client = TestClient(app)
    _configure_auth(
        monkeypatch,
        {
            "id": "u-1",
            "email": "admin@example.com",
            "user_metadata": {"full_name": "Admin User"},
            "app_metadata": {"role": "admin"},
        },
    )

    monkeypatch.setattr(
        settings_route.store,
        "update_user_mapping",
        lambda user_id, whatsapp_number, full_name: {
            "id": user_id,
            "full_name": full_name,
            "email": "claire@edge-consulting.fr",
            "whatsapp_number": whatsapp_number,
        },
    )

    response = client.put(
        "/api/settings/users/u-2",
        headers={"Authorization": "Bearer test-token"},
        json={"full_name": "Claire", "whatsapp_number": "+33612345679"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == "u-2"
