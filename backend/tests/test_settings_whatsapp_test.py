from fastapi.testclient import TestClient

from app.api.deps import auth
from app.api.routes import settings as settings_route
from app.main import app
from app.schemas.user_mapping import UserMapping


class MockAuthResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload


class MockTwilioResponse:
    def __init__(self, sid: str):
        self._sid = sid

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"sid": self._sid}


def _configure_auth(monkeypatch, payload: dict) -> None:
    monkeypatch.setattr(auth.settings, "supabase_url", "https://example.supabase.co")
    monkeypatch.setattr(auth.settings, "supabase_anon_key", "anon-key")
    monkeypatch.setattr(auth.settings, "supabase_service_role_key", "")
    monkeypatch.setattr(auth.httpx, "get", lambda *args, **kwargs: MockAuthResponse(200, payload))
    monkeypatch.setattr(auth.store, "upsert_user_profile", lambda *args, **kwargs: None)


def test_whatsapp_test_send_for_self(monkeypatch) -> None:
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
            UserMapping(
                id="u-1",
                full_name="User One",
                email="user1@example.com",
                whatsapp_number="+33612345678",
            )
        ],
    )
    monkeypatch.setattr(settings_route.settings, "twilio_account_sid", "AC123")
    monkeypatch.setattr(settings_route.settings, "twilio_auth_token", "token")
    monkeypatch.setattr(settings_route.settings, "twilio_whatsapp_number", "+14155238886")
    monkeypatch.setattr(settings_route.httpx, "post", lambda *args, **kwargs: MockTwilioResponse("SM123"))

    response = client.post("/api/settings/users/u-1/whatsapp/test", headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 200
    assert response.json() == {"result": "sent", "message_sid": "SM123"}


def test_whatsapp_test_send_forbidden_for_other_user(monkeypatch) -> None:
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

    response = client.post("/api/settings/users/u-2/whatsapp/test", headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden owner scope"}
