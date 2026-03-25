from fastapi.testclient import TestClient

from app.api.deps import auth
from app.api.routes import summary as summary_route
from app.main import app
from app.schemas.deal import DealRead, DealStatus
from app.schemas.user_mapping import UserMapping
from datetime import date, datetime, timezone


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


def test_get_my_summary_returns_only_owner_items(monkeypatch) -> None:
    client = TestClient(app)
    _configure_auth(
        monkeypatch,
        {
            "id": "u-1",
            "email": "nicolas.vanaelst@edge-consulting.biz",
            "user_metadata": {"full_name": "Nicolas"},
        },
    )

    monkeypatch.setattr(
        summary_route.store,
        "list_users",
        lambda: [
            UserMapping(
                id="u-1",
                full_name="Nicolas",
                email="nicolas.vanaelst@edge-consulting.biz",
                whatsapp_number="+32479591226",
            )
        ],
    )
    monkeypatch.setattr(
        summary_route.store,
        "list_deals",
        lambda status=None, owner_id=None: [
            DealRead(
                id="dl-1",
                company="Belfius",
                description="desc",
                action="Relancer",
                deadline=date(2026, 4, 10),
                owner_id=owner_id or "u-1",
                status=DealStatus.active,
                created_at=datetime.now(timezone.utc),
            )
        ],
    )

    response = client.get("/api/summary/me", headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["owner_id"] == "u-1"
    assert "resume" in payload["summary"].lower()


def test_send_my_summary_calls_channels(monkeypatch) -> None:
    client = TestClient(app)
    _configure_auth(
        monkeypatch,
        {
            "id": "u-1",
            "email": "nicolas.vanaelst@edge-consulting.biz",
            "user_metadata": {"full_name": "Nicolas"},
        },
    )

    monkeypatch.setattr(
        summary_route.store,
        "list_users",
        lambda: [
            UserMapping(
                id="u-1",
                full_name="Nicolas",
                email="nicolas.vanaelst@edge-consulting.biz",
                whatsapp_number="+32479591226",
            )
        ],
    )
    monkeypatch.setattr(
        summary_route.store,
        "list_deals",
        lambda status=None, owner_id=None: [
            DealRead(
                id="dl-1",
                company="Belfius",
                description="desc",
                action="Relancer",
                deadline=date(2026, 4, 10),
                owner_id=owner_id or "u-1",
                status=DealStatus.active,
                created_at=datetime.now(timezone.utc),
            )
        ],
    )

    monkeypatch.setattr(summary_route, "send_whatsapp_message", lambda **kwargs: "SM123")
    monkeypatch.setattr(summary_route, "send_email_message", lambda **kwargs: None)

    response = client.post("/api/summary/me/send", headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["whatsapp"] == "sent"
    assert payload["email"] == "sent"


def test_weekly_trigger_requires_admin(monkeypatch) -> None:
    client = TestClient(app)
    _configure_auth(
        monkeypatch,
        {
            "id": "u-1",
            "email": "user@example.com",
            "user_metadata": {"full_name": "User"},
            "app_metadata": {"role": "user"},
        },
    )

    response = client.post("/api/summary/weekly/trigger", headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 403


def test_weekly_trigger_admin_ok(monkeypatch) -> None:
    client = TestClient(app)
    _configure_auth(
        monkeypatch,
        {
            "id": "u-admin",
            "email": "admin@example.com",
            "user_metadata": {"full_name": "Admin"},
            "app_metadata": {"role": "admin"},
        },
    )
    called = {"ok": False}
    monkeypatch.setattr(summary_route, "send_weekly_summaries_job", lambda: called.__setitem__("ok", True))

    response = client.post("/api/summary/weekly/trigger", headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 200
    assert called["ok"] is True


def test_weekly_status_admin_exposes_smtp_config(monkeypatch) -> None:
    client = TestClient(app)
    _configure_auth(
        monkeypatch,
        {
            "id": "u-admin",
            "email": "admin@example.com",
            "user_metadata": {"full_name": "Admin"},
            "app_metadata": {"role": "admin"},
        },
    )

    monkeypatch.setattr(summary_route.settings, "weekly_summary_scheduler_enabled", True)
    monkeypatch.setattr(summary_route.settings, "weekly_summary_timezone", "Europe/Brussels")
    monkeypatch.setattr(summary_route.settings, "weekly_summary_day_of_week", "mon")
    monkeypatch.setattr(summary_route.settings, "weekly_summary_hour", 9)
    monkeypatch.setattr(summary_route.settings, "email_provider", "auto")
    monkeypatch.setattr(summary_route.settings, "graph_tenant_id", "")
    monkeypatch.setattr(summary_route.settings, "graph_client_id", "")
    monkeypatch.setattr(summary_route.settings, "graph_client_secret", "")
    monkeypatch.setattr(summary_route.settings, "graph_sender_user", "")
    monkeypatch.setattr(summary_route.settings, "smtp_host", "smtp.office365.com")
    monkeypatch.setattr(summary_route.settings, "smtp_from_email", "noreply@example.com")
    monkeypatch.setattr(summary_route.settings, "smtp_username", "noreply@example.com")
    monkeypatch.setattr(summary_route.settings, "smtp_password", "topsecret")
    monkeypatch.setattr(summary_route.settings, "smtp_starttls_enabled", True)
    monkeypatch.setattr(summary_route.settings, "smtp_ssl_enabled", False)

    response = client.get("/api/summary/weekly/status", headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["email_provider_requested"] == "auto"
    assert payload["email_provider_effective"] == "smtp"
    assert payload["smtp_configured"] is True
    assert payload["smtp_auth_configured"] is True
    assert payload["smtp_mode"] == "starttls"
    assert payload["smtp_host"] == "smtp.office365.com"


def test_weekly_status_prefers_graph_when_configured(monkeypatch) -> None:
    client = TestClient(app)
    _configure_auth(
        monkeypatch,
        {
            "id": "u-admin",
            "email": "admin@example.com",
            "user_metadata": {"full_name": "Admin"},
            "app_metadata": {"role": "admin"},
        },
    )

    monkeypatch.setattr(summary_route.settings, "email_provider", "graph")
    monkeypatch.setattr(summary_route.settings, "graph_tenant_id", "tenant-id")
    monkeypatch.setattr(summary_route.settings, "graph_client_id", "client-id")
    monkeypatch.setattr(summary_route.settings, "graph_client_secret", "client-secret")
    monkeypatch.setattr(summary_route.settings, "graph_sender_user", "noreply@example.com")

    response = client.get("/api/summary/weekly/status", headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["email_provider_requested"] == "graph"
    assert payload["email_provider_effective"] == "graph"
    assert payload["graph_configured"] is True
    assert payload["graph_sender_user"] == "noreply@example.com"
