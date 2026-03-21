from fastapi.testclient import TestClient

from app.api.deps import auth
from app.main import app


class MockAuthResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload


def test_deals_requires_bearer_token() -> None:
    client = TestClient(app)

    response = client.get("/api/deals")

    assert response.status_code == 401
    assert response.json() == {"detail": "Missing bearer token"}


def test_deals_with_valid_token_syncs_user_profile(monkeypatch) -> None:
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
                "id": "00000000-0000-0000-0000-000000000001",
                "email": "alice@example.com",
                "user_metadata": {"full_name": "Alice Martin"},
            },
        ),
    )

    captured: dict[str, str] = {}

    def fake_upsert_user_profile(user_id: str, email: str, full_name: str) -> None:
        captured["user_id"] = user_id
        captured["email"] = email
        captured["full_name"] = full_name

    monkeypatch.setattr(auth.store, "upsert_user_profile", fake_upsert_user_profile)

    response = client.get("/api/deals", headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 200
    assert captured == {
        "user_id": "00000000-0000-0000-0000-000000000001",
        "email": "alice@example.com",
        "full_name": "Alice Martin",
    }
