from datetime import date

from app.repositories.in_memory import InMemoryStore
from app.schemas.deal import DealCreate, DealStatus


def test_dashboard_kpis_scoped_by_owner() -> None:
    store = InMemoryStore()
    store.create_deal(
        DealCreate(
            owner_id="u-2",
            company="ACME",
            description="desc",
            action="act",
            deadline=date(2026, 3, 21),
            status=DealStatus.won,
        )
    )

    scoped = store.dashboard_kpis(owner_id="u-1")
    other = store.dashboard_kpis(owner_id="u-2")

    assert scoped.active == 1
    assert scoped.won == 0
    assert scoped.lost == 0
    assert other.active == 0
    assert other.won == 1
    assert other.lost == 0


def test_upsert_user_profile_creates_user_when_missing() -> None:
    store = InMemoryStore()

    created = store.upsert_user_profile(
        user_id="00000000-0000-0000-0000-000000000010",
        email="new-user@example.com",
        full_name="New User",
    )

    assert created.id == "00000000-0000-0000-0000-000000000010"
    assert created.email == "new-user@example.com"
    assert created.full_name == "New User"
    assert created.whatsapp_number is None


def test_upsert_user_profile_keeps_whatsapp_number() -> None:
    store = InMemoryStore()

    updated = store.upsert_user_profile(
        user_id="u-1",
        email="nicolas.updated@example.com",
        full_name="Nicolas Updated",
    )

    assert updated.id == "u-1"
    assert updated.email == "nicolas.updated@example.com"
    assert updated.full_name == "Nicolas Ferrand"
    assert updated.whatsapp_number == "+33612345678"
