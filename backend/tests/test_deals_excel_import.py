from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.api.deps import auth
from app.api.routes import deals
from app.main import app


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


def _build_workbook_bytes() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Priorite", "Cibles commerciales", "Avancement", "Actions commerciales", "Commentaires"])
    sheet.append(["x", "Asfalys", "Contact etabli", "Envoyer proposition", ""])
    sheet.append(["", "B12", "Reponse negative definitive", "Offre abandonnee", "cloture"])

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_import_deals_excel_creates_owner_scoped_deals(monkeypatch) -> None:
    client = TestClient(app)
    _configure_auth(monkeypatch)

    captured: list[dict[str, str]] = []

    def fake_create_deal(payload):
        data = payload.model_dump()
        captured.append(data)
        return payload.model_copy(update={"id": f"dl-{len(captured)}", "created_at": "2026-01-01T00:00:00Z"})

    monkeypatch.setattr(deals.store, "create_deal", fake_create_deal)

    files = {
        "file": (
            "pipeline.xlsx",
            _build_workbook_bytes(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }

    response = client.post("/api/deals/import/excel", headers={"Authorization": "Bearer test-token"}, files=files)

    assert response.status_code == 200
    assert response.json()["imported"] == 2
    assert response.json()["skipped"] == 0
    assert len(captured) == 2
    assert all(item["owner_id"] == "u-1" for item in captured)
    assert captured[0]["status"] == "active"
    assert captured[1]["status"] == "lost"


def test_import_deals_excel_rejects_non_xlsx(monkeypatch) -> None:
    client = TestClient(app)
    _configure_auth(monkeypatch)

    files = {"file": ("pipeline.csv", b"company;action", "text/csv")}

    response = client.post("/api/deals/import/excel", headers={"Authorization": "Bearer test-token"}, files=files)

    assert response.status_code == 400
    assert response.json() == {"detail": "Only .xlsx files are supported"}
