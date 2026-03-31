from datetime import date, datetime, timedelta, timezone

from app.schemas.deal import DealRead, DealStatus
from app.services.action_summary import build_owner_summary_whatsapp_messages


class _FakeStore:
    def __init__(self, deals: list[DealRead]) -> None:
        self._deals = deals

    def list_deals(self, status=None, owner_id=None):
        rows = self._deals
        if status is not None:
            rows = [item for item in rows if item.status == status]
        if owner_id is not None:
            rows = [item for item in rows if item.owner_id == owner_id]
        return rows


def test_whatsapp_summary_includes_all_actions() -> None:
    now = datetime.now(timezone.utc)
    deals = [
        DealRead(
            id=f"dl-{i}",
            company=f"Company {i}",
            description="desc",
            action=f"Action {i}",
            deadline=date.today() + timedelta(days=i),
            owner_id="u-1",
            status=DealStatus.active,
            created_at=now,
        )
        for i in range(1, 16)
    ]
    store = _FakeStore(deals)

    messages = build_owner_summary_whatsapp_messages(
        store,
        owner_name="Nicolas",
        owner_id="u-1",
        app_url="https://edge-dealtracker.vercel.app",
        max_message_length=300,
    )

    content = "\n".join(messages)
    assert "Company 15" in content
    assert "+" not in content
    assert len(messages) > 1
