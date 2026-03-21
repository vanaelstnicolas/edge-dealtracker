from fastapi.testclient import TestClient

from app.api.routes import twilio
from app.main import app
from app.schemas.user_mapping import UserMapping


def test_twilio_webhook_replies_with_twiml_message(monkeypatch) -> None:
    client = TestClient(app)

    monkeypatch.setattr(twilio, "_is_valid_twilio_signature", lambda **kwargs: True)
    monkeypatch.setattr(twilio, "_nlu_command_from_openai", lambda _: None)
    monkeypatch.setattr(
        twilio.store,
        "find_user_by_whatsapp",
        lambda phone: UserMapping(
            id="u-1",
            full_name="User One",
            email="user1@example.com",
            whatsapp_number="+32400000000",
        ),
    )
    monkeypatch.setattr(twilio, "_handle_text_command", lambda owner_id, body: ("created", "Dossier cree."))

    response = client.post(
        "/api/webhooks/twilio",
        data={
            "From": "whatsapp:+32400000000",
            "Body": "create ACME|desc|action|2026-04-01",
        },
    )

    assert response.status_code == 200
    assert "application/xml" in response.headers.get("content-type", "")
    assert "<Message>Dossier cree.</Message>" in response.text


def test_twilio_webhook_media_returns_twiml_ack(monkeypatch) -> None:
    client = TestClient(app)

    monkeypatch.setattr(twilio, "_is_valid_twilio_signature", lambda **kwargs: True)
    monkeypatch.setattr(
        twilio.store,
        "find_user_by_whatsapp",
        lambda phone: UserMapping(
            id="u-1",
            full_name="User One",
            email="user1@example.com",
            whatsapp_number="+32400000000",
        ),
    )

    response = client.post(
        "/api/webhooks/twilio",
        data={
            "From": "whatsapp:+32400000000",
            "Body": "",
            "MediaUrl0": "https://example.com/audio.ogg",
        },
    )

    assert response.status_code == 200
    assert "<Message>Audio recu. Transcription IA en cours.</Message>" in response.text
