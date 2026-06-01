from datetime import datetime, timedelta, timezone

from scripts.lib.entitlements import has_active_research_unlock


def test_expired_ad_unlock_returns_redacted_state():
    now = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    unlocks = [
        {
            "entitlement_type": "ad_unlocked",
            "status": "active",
            "expires_at": now - timedelta(seconds=1),
            "target_slug": "NVDA",
        }
    ]

    assert has_active_research_unlock(unlocks, "NVDA", now=now) is False


def test_active_subscriber_unlocks_any_research():
    now = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    unlocks = [{"entitlement_type": "subscriber", "status": "active", "expires_at": None, "target_slug": None}]

    assert has_active_research_unlock(unlocks, "NVDA", now=now) is True


def test_ad_unlock_is_symbol_scoped():
    now = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    unlocks = [
        {
            "entitlement_type": "ad_unlocked",
            "status": "active",
            "expires_at": now + timedelta(minutes=30),
            "target_slug": "NVDA",
        }
    ]

    assert has_active_research_unlock(unlocks, "AMD", now=now) is False
