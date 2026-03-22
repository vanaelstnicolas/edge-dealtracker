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
    sent_messages: list[str] = []
    monkeypatch.setattr(twilio, "send_whatsapp_message", lambda to_number, body: sent_messages.append(body) or "SM123")

    response = client.post(
        "/api/webhooks/twilio",
        data={
            "From": "whatsapp:+32400000000",
            "Body": "create ACME|desc|action|2026-04-01",
        },
    )

    assert response.status_code == 200
    assert "text/xml" in response.headers.get("content-type", "")
    assert "<Response></Response>" in response.text
    assert sent_messages == ["Dossier cree."]


def test_twilio_webhook_media_returns_twiml_ack(monkeypatch) -> None:
    client = TestClient(app)

    monkeypatch.setattr(twilio, "_is_valid_twilio_signature", lambda **kwargs: True)
    monkeypatch.setattr(twilio, "_transcribe_audio_from_twilio_media", lambda media_url, content_type=None: None)
    sent_messages: list[str] = []
    monkeypatch.setattr(twilio, "send_whatsapp_message", lambda to_number, body: sent_messages.append(body) or "SM124")
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
    assert "<Response></Response>" in response.text
    assert sent_messages
    assert "Audio recu mais transcription indisponible." in sent_messages[0]


def test_twilio_webhook_summary_command(monkeypatch) -> None:
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
    monkeypatch.setattr(twilio, "_nlu_command_from_openai", lambda _: "summary")
    monkeypatch.setattr(twilio, "_handle_text_command", lambda owner_id, body: ("summary", "Resume to-do"))
    sent_messages: list[str] = []
    monkeypatch.setattr(twilio, "send_whatsapp_message", lambda to_number, body: sent_messages.append(body) or "SM125")

    response = client.post(
        "/api/webhooks/twilio",
        data={
            "From": "whatsapp:+32400000000",
            "Body": "resume de mes actions",
        },
    )

    assert response.status_code == 200
    assert "<Response></Response>" in response.text
    assert sent_messages == ["Resume to-do"]


def test_twilio_webhook_heuristic_natural_message(monkeypatch) -> None:
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
    monkeypatch.setattr(twilio, "_nlu_command_from_openai", lambda _: None)

    captured = {"command": ""}

    def fake_handle(owner_id, body):
        captured["command"] = body
        return ("created", "Dossier cree.")

    monkeypatch.setattr(twilio, "_handle_text_command", fake_handle)
    monkeypatch.setattr(twilio, "send_whatsapp_message", lambda to_number, body: "SM126")

    response = client.post(
        "/api/webhooks/twilio",
        data={
            "From": "whatsapp:+32400000000",
            "Body": "J'ai une nouvelle opportunite chez Belfius pour un GTM. Je les rencontre le 10/4",
        },
    )

    assert response.status_code == 200
    assert captured["command"].startswith("create Belfius|")
