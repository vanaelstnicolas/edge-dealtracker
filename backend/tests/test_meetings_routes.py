from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from app.api.deps import auth
from app.api.routes import meetings as meetings_route
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
                "app_metadata": {"role": "user"},
            },
        ),
    )
    monkeypatch.setattr(auth.store, "upsert_user_profile", lambda *args, **kwargs: None)


def _active_deal(company: str) -> DealRead:
    return DealRead(
        id="dl-1",
        company=company,
        description="desc",
        action="act",
        deadline=date(2026, 4, 10),
        owner_id="u-1",
        status=DealStatus.active,
        created_at=datetime.now(timezone.utc),
    )


def test_extract_meeting_actions_returns_ai_output(monkeypatch) -> None:
    client = TestClient(app)
    _configure_auth(monkeypatch)
    monkeypatch.setattr(
        meetings_route,
        "_extract_actions_with_openai",
        lambda content: [
            meetings_route.MeetingAction(
                operation="create",
                company="ACME",
                description="Nouveau besoin",
                action="Envoyer proposition",
                deadline="2026-04-20",
                status="",
                reason="Detecte dans le compte rendu",
                confidence=0.92,
            )
        ],
    )

    response = client.post(
        "/api/meetings/extract",
        headers={"Authorization": "Bearer test-token"},
        json={"content": "Compte rendu de reunion client ACME..."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["actions"]) == 1
    assert payload["actions"][0]["operation"] == "create"


def test_extract_meeting_actions_from_text_file(monkeypatch) -> None:
    client = TestClient(app)
    _configure_auth(monkeypatch)
    monkeypatch.setattr(
        meetings_route,
        "_extract_actions_with_openai",
        lambda content: [
            meetings_route.MeetingAction(
                operation="update",
                company="ACME",
                description="",
                action="Relancer",
                deadline="",
                status="",
                reason="Action explicite detectee",
                confidence=0.81,
            )
        ],
    )

    response = client.post(
        "/api/meetings/extract/file",
        headers={"Authorization": "Bearer test-token"},
        files={"file": ("meeting.txt", b"Compte rendu: relancer ACME vendredi", "text/plain")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["actions"][0]["operation"] == "update"


def test_extract_meeting_actions_from_pdf_file(monkeypatch) -> None:
    client = TestClient(app)
    _configure_auth(monkeypatch)
    monkeypatch.setattr(meetings_route, "_extract_text_from_pdf_bytes", lambda payload: "Compte rendu PDF ACME")
    monkeypatch.setattr(
        meetings_route,
        "_extract_actions_with_openai",
        lambda content: [
            meetings_route.MeetingAction(
                operation="create",
                company="Nova",
                description="Besoin detecte",
                action="Envoyer proposition",
                deadline="",
                status="",
                reason="PDF",
                confidence=0.9,
            )
        ],
    )

    response = client.post(
        "/api/meetings/extract/file",
        headers={"Authorization": "Bearer test-token"},
        files={"file": ("meeting.pdf", b"%PDF-1.4", "application/pdf")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["actions"][0]["operation"] == "create"


def test_apply_meeting_actions_handles_create_update_close(monkeypatch) -> None:
    client = TestClient(app)
    _configure_auth(monkeypatch)

    created_payloads: list = []
    updated_payloads: list = []

    monkeypatch.setattr(meetings_route.store, "create_deal", lambda payload: created_payloads.append(payload))
    monkeypatch.setattr(
        meetings_route.store,
        "find_active_deal_by_company",
        lambda owner_id, company: _active_deal(company) if company in {"ACME", "Contoso"} else None,
    )
    monkeypatch.setattr(
        meetings_route.store,
        "update_deal",
        lambda deal_id, payload: updated_payloads.append((deal_id, payload)),
    )

    response = client.post(
        "/api/meetings/apply",
        headers={"Authorization": "Bearer test-token"},
        json={
            "actions": [
                {"operation": "create", "company": "Nova", "description": "desc", "action": "next", "deadline": "2026-04-21"},
                {"operation": "update", "company": "ACME", "action": "Recontacter"},
                {"operation": "close", "company": "Contoso", "status": "won"},
                {"operation": "ignore", "company": ""},
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["created"] == 1
    assert payload["updated"] == 1
    assert payload["closed"] == 1
    assert payload["ignored"] == 1
    assert payload["failed"] == 0
    assert len(created_payloads) == 1
    assert len(updated_payloads) == 2


def test_apply_meeting_actions_dry_run(monkeypatch) -> None:
    client = TestClient(app)
    _configure_auth(monkeypatch)

    monkeypatch.setattr(meetings_route.store, "create_deal", lambda payload: (_ for _ in ()).throw(RuntimeError("should not run")))
    monkeypatch.setattr(
        meetings_route.store,
        "find_active_deal_by_company",
        lambda owner_id, company: _active_deal(company),
    )
    monkeypatch.setattr(meetings_route.store, "update_deal", lambda deal_id, payload: (_ for _ in ()).throw(RuntimeError("should not run")))

    response = client.post(
        "/api/meetings/apply",
        headers={"Authorization": "Bearer test-token"},
        json={
            "dry_run": True,
            "actions": [
                {"operation": "create", "company": "Nova", "description": "desc", "action": "next"},
                {"operation": "update", "company": "ACME", "action": "Recontacter"},
                {"operation": "close", "company": "Contoso", "status": "lost"},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["created"] == 1
    assert payload["updated"] == 1
    assert payload["closed"] == 1
