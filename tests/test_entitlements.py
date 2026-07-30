"""Tests for scripts.lib.entitlements — unlock checks and webhook signatures."""

from datetime import UTC, datetime, timedelta

import pytest

from scripts.lib.entitlements import (
    WebhookSignatureError,
    has_active_research_unlock,
    sign_webhook_payload,
    verify_webhook_signature,
)

NOW = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)


def _unlock(entitlement_type="subscriber", status="active", target_slug=None, expires_at=None):
    return {
        "entitlement_type": entitlement_type,
        "status": status,
        "target_slug": target_slug,
        "expires_at": expires_at,
    }


# ---------------------------------------------------------------------------
# has_active_research_unlock
# ---------------------------------------------------------------------------


def test_unlock_active_subscriber():
    unlocks = [_unlock()]
    assert has_active_research_unlock(unlocks, "NVDA", now=NOW) is True


def test_unlock_expired():
    unlocks = [_unlock(expires_at=NOW - timedelta(days=1))]
    assert has_active_research_unlock(unlocks, "NVDA", now=NOW) is False


def test_unlock_wrong_symbol():
    unlocks = [_unlock(target_slug="AAPL")]
    assert has_active_research_unlock(unlocks, "NVDA", now=NOW) is False


def test_unlock_null_slug_matches_any():
    unlocks = [_unlock(target_slug=None)]
    assert has_active_research_unlock(unlocks, "NVDA", now=NOW) is True


def test_unlock_inactive_status():
    unlocks = [_unlock(status="canceled")]
    assert has_active_research_unlock(unlocks, "NVDA", now=NOW) is False


def test_unlock_wrong_type():
    unlocks = [_unlock(entitlement_type="basic")]
    assert has_active_research_unlock(unlocks, "NVDA", now=NOW) is False


def test_unlock_ad_unlocked():
    unlocks = [_unlock(entitlement_type="ad_unlocked")]
    assert has_active_research_unlock(unlocks, "NVDA", now=NOW) is True


def test_unlock_empty_list():
    assert has_active_research_unlock([], "NVDA", now=NOW) is False


# ---------------------------------------------------------------------------
# webhook signatures
# ---------------------------------------------------------------------------


def test_sign_and_verify():
    body = b'{"event": "payment.completed"}'
    secret = "test-secret"
    signature = sign_webhook_payload(body, secret)
    assert signature.startswith("sha256=")
    verify_webhook_signature(body, signature, secret)  # should not raise


def test_verify_wrong_signature():
    body = b'{"event": "payment.completed"}'
    with pytest.raises(WebhookSignatureError, match="invalid"):
        verify_webhook_signature(body, "sha256=wrong", "secret")


def test_verify_missing_signature():
    with pytest.raises(WebhookSignatureError, match="missing"):
        verify_webhook_signature(b"body", None, "secret")


def test_verify_missing_secret():
    with pytest.raises(WebhookSignatureError, match="not configured"):
        verify_webhook_signature(b"body", "sha256=abc", None)
