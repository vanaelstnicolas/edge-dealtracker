import httpx
import pytest

from app.repositories.supabase import SupabaseStore


class MockResponse:
    def __init__(self, payload: list[dict] | None = None, error: Exception | None = None):
        self._payload = payload or []
        self._error = error

    def raise_for_status(self) -> None:
        if self._error is not None:
            raise self._error

    def json(self) -> list[dict]:
        return self._payload


def test_upsert_user_profile_returns_merged_user(monkeypatch) -> None:
    store = SupabaseStore("https://example.supabase.co", "service-role-key")

    def fake_post(*args, **kwargs):
        assert kwargs["params"]["on_conflict"] == "id"
        assert kwargs["headers"]["Prefer"] == "resolution=merge-duplicates,return=representation"
        return MockResponse(
            payload=[
                {
                    "id": "00000000-0000-0000-0000-000000000012",
                    "email": "merge@example.com",
                    "full_name": "Merge User",
                    "whatsapp_number": None,
                }
            ]
        )

    monkeypatch.setattr(store._client, "post", fake_post)

    user = store.upsert_user_profile(
        user_id="00000000-0000-0000-0000-000000000012",
        email="merge@example.com",
        full_name="Merge User",
    )

    assert user.id == "00000000-0000-0000-0000-000000000012"
    assert user.email == "merge@example.com"
    assert user.full_name == "Merge User"
    assert user.whatsapp_number is None


def test_upsert_user_profile_raises_on_email_conflict(monkeypatch) -> None:
    store = SupabaseStore("https://example.supabase.co", "service-role-key")

    request = httpx.Request("POST", "https://example.supabase.co/rest/v1/users")
    response = httpx.Response(
        status_code=409,
        request=request,
        json={
            "code": "23505",
            "details": "Key (email)=(existing@example.com) already exists.",
            "message": "duplicate key value violates unique constraint \"users_email_key\"",
        },
    )
    conflict_error = httpx.HTTPStatusError("conflict", request=request, response=response)

    monkeypatch.setattr(store._client, "post", lambda *args, **kwargs: MockResponse(error=conflict_error))

    with pytest.raises(httpx.HTTPStatusError):
        store.upsert_user_profile(
            user_id="00000000-0000-0000-0000-000000000013",
            email="existing@example.com",
            full_name="Existing User",
        )
