from app.jobs import weekly_summary
from app.schemas.user_mapping import UserMapping


def test_weekly_job_reports_channel_failures(monkeypatch) -> None:
    monkeypatch.setattr(
        weekly_summary.store,
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
        weekly_summary,
        "build_owner_summary_text",
        lambda store, owner_name, owner_id: "Resume test",
    )

    def _whatsapp_failure(**kwargs):
        raise RuntimeError("twilio down")

    def _email_failure(**kwargs):
        raise RuntimeError("graph down")

    alerts: list[dict] = []
    monkeypatch.setattr(weekly_summary, "send_whatsapp_message", _whatsapp_failure)
    monkeypatch.setattr(weekly_summary, "send_email_message", _email_failure)
    monkeypatch.setattr(weekly_summary, "report_summary_delivery_failure", lambda **kwargs: alerts.append(kwargs))

    weekly_summary.send_weekly_summaries_job()

    assert len(alerts) == 2
    channels = {item["channel"] for item in alerts}
    assert channels == {"whatsapp", "email"}
    for item in alerts:
        assert item["operation"] == "weekly_scheduler"
        assert item["owner_id"] == "u-1"
