from fastapi.testclient import TestClient

from app.api.routes import twilio
from app.main import app


def test_debug_parse_endpoint_blocked_outside_dev_or_staging(monkeypatch) -> None:
    client = TestClient(app)
    monkeypatch.setattr(twilio.settings, "environment", "prod")

    response = client.post(
        "/api/webhooks/twilio/debug/parse",
        json={"owner_id": "u-1", "message": "create ACME|desc|action|2026-03-21"},
    )

    assert response.status_code == 404


def test_debug_parse_endpoint_available_in_staging(monkeypatch) -> None:
    client = TestClient(app)
    monkeypatch.setattr(twilio.settings, "environment", "staging")

    response = client.post(
        "/api/webhooks/twilio/debug/parse",
        json={"owner_id": "u-1", "message": "commande non reconnue"},
    )

    assert response.status_code == 200
    assert response.json()["command_source"] == "raw_text"
