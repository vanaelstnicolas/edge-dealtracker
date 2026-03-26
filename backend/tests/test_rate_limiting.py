from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.api.deps import auth
from app.api.routes import deals as deals_route
from app.api.routes import summary as summary_route
from app.api.routes import twilio as twilio_route
from app.main import app
from app.schemas.user_mapping import UserMapping
from app.services.rate_limit import reset_rate_limits


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


def _workbook_bytes() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Cibles commerciales", "Actions commerciales"])
    sheet.append(["ACME", "Relancer"])
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_summary_send_rate_limited(monkeypatch) -> None:
    reset_rate_limits()
    client = TestClient(app)
    _configure_auth(
        monkeypatch,
        {
            "id": "u-1",
            "email": "u1@example.com",
            "user_metadata": {"full_name": "User One"},
        },
    )
    monkeypatch.setattr(summary_route.settings, "summary_send_rate_limit_per_user", 1)
    monkeypatch.setattr(summary_route.settings, "rate_limit_window_seconds", 60)
    monkeypatch.setattr(
        summary_route.store,
        "list_users",
        lambda: [
            UserMapping(id="u-1", full_name="User One", email="u1@example.com", whatsapp_number="+32400000000")
        ],
    )
    monkeypatch.setattr(summary_route, "build_owner_summary_text", lambda *args, **kwargs: "Resume test")
    monkeypatch.setattr(summary_route, "send_whatsapp_message", lambda **kwargs: "SM1")
    monkeypatch.setattr(summary_route, "send_email_message", lambda **kwargs: None)

    first = client.post("/api/summary/me/send", headers={"Authorization": "Bearer test-token"})
    second = client.post("/api/summary/me/send", headers={"Authorization": "Bearer test-token"})

    assert first.status_code == 200
    assert second.status_code == 429


def test_deals_import_rate_limited(monkeypatch) -> None:
    reset_rate_limits()
    client = TestClient(app)
    _configure_auth(
        monkeypatch,
        {
            "id": "u-1",
            "email": "u1@example.com",
            "user_metadata": {"full_name": "User One"},
        },
    )
    monkeypatch.setattr(deals_route.settings, "deals_import_rate_limit_per_user", 1)
    monkeypatch.setattr(deals_route.settings, "rate_limit_window_seconds", 60)
    monkeypatch.setattr(deals_route.store, "create_deal", lambda payload: payload)

    files = {
        "file": (
            "pipeline.xlsx",
            _workbook_bytes(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }

    first = client.post("/api/deals/import/excel", headers={"Authorization": "Bearer test-token"}, files=files)
    second = client.post("/api/deals/import/excel", headers={"Authorization": "Bearer test-token"}, files=files)

    assert first.status_code == 200
    assert second.status_code == 429


def test_twilio_webhook_rate_limited(monkeypatch) -> None:
    reset_rate_limits()
    client = TestClient(app)
    monkeypatch.setattr(twilio_route.settings, "twilio_rate_limit_per_phone", 1)
    monkeypatch.setattr(twilio_route.settings, "rate_limit_window_seconds", 60)
    monkeypatch.setattr(twilio_route, "_is_valid_twilio_signature", lambda **kwargs: True)
    monkeypatch.setattr(
        twilio_route.store,
        "find_user_by_whatsapp",
        lambda phone: UserMapping(
            id="u-1",
            full_name="User One",
            email="u1@example.com",
            whatsapp_number="+32400000000",
        ),
    )
    monkeypatch.setattr(twilio_route, "_nlu_command_from_openai", lambda _: None)
    monkeypatch.setattr(twilio_route, "_handle_text_command", lambda owner_id, body: ("created", "ok"))
    monkeypatch.setattr(twilio_route, "send_whatsapp_message", lambda to_number, body: "SM1")

    first = client.post(
        "/api/webhooks/twilio",
        data={"From": "whatsapp:+32400000000", "Body": "create ACME|desc|action|2026-04-01"},
    )
    second = client.post(
        "/api/webhooks/twilio",
        data={"From": "whatsapp:+32400000000", "Body": "create ACME|desc|action|2026-04-01"},
    )

    assert first.status_code == 200
    assert second.status_code == 429
