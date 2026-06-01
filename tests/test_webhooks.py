import json
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from scripts import api
from scripts.lib.auth import create_test_token
from scripts.lib.entitlements import sign_webhook_payload


TEST_WEBHOOK_SECRET = "test-webhook-secret"


class FakeBillingDB:
    def __init__(self):
        self.entitlements = {}
        self.webhook_events = {}
        self.research = {
            "NVDA": {
                "target_slug": "NVDA",
                "opinion": "매수",
                "thesis": "Full source-cited thesis",
                "bull": "Bull case",
                "base": "Base case",
                "bear": "Bear case",
                "sources": [{"title": "Source", "url": "https://example.com"}],
            }
        }

    def fetch_profile_by_auth_user(self, auth_user_id: str):
        return {"profile_id": 1, "auth_user_id": auth_user_id, "slug": auth_user_id}

    def fetch_latest_research_for_asset(self, symbol: str):
        return self.research.get(symbol)

    def user_has_research_entitlement(self, auth_user_id: str, symbol: str):
        now = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
        return any(
            item["auth_user_id"] == auth_user_id
            and item["target_slug"] == symbol
            and item["expires_at"] > now
            for item in self.entitlements.values()
        )

    def grant_ad_unlock(self, auth_user_id: str, symbol: str, ad_event_id: str):
        expires_at = datetime(2026, 6, 1, 12, 30, tzinfo=timezone.utc)
        self.entitlements.setdefault(
            ad_event_id,
            {
                "auth_user_id": auth_user_id,
                "target_slug": symbol,
                "entitlement_state": "ad_unlocked",
                "expires_at": expires_at,
            },
        )
        return self.entitlements[ad_event_id]

    def grant_subscription_entitlement(self, auth_user_id: str, provider: str, provider_subject_id: str):
        self.entitlements.setdefault(
            f"{provider}:{provider_subject_id}",
            {
                "auth_user_id": auth_user_id,
                "target_slug": "NVDA",
                "entitlement_state": "subscriber",
                "expires_at": datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc),
            },
        )
        return self.entitlements[f"{provider}:{provider_subject_id}"]

    def record_payment_webhook(self, event_id: str, provider: str, event_type: str, payload: dict, signature_valid: bool):
        if event_id in self.webhook_events:
            return {"status": "ignored", "duplicate": True}
        self.webhook_events[event_id] = {
            "event_id": event_id,
            "provider": provider,
            "event_type": event_type,
            "payload": payload,
            "signature_valid": signature_valid,
        }
        return {"status": "processed", "duplicate": False}


def client_with_db(monkeypatch, fake_db):
    monkeypatch.setattr(api, "db", lambda: fake_db)
    return TestClient(api.app)


def test_ad_unlock_grants_temporary_access(monkeypatch):
    fake_db = FakeBillingDB()
    client = client_with_db(monkeypatch, fake_db)
    token = create_test_token("user-a")

    unlock = client.post(
        "/api/research/NVDA/ad-unlock",
        headers={"Authorization": f"Bearer {token}"},
        json={"ad_event_id": "test-ad-1"},
    )
    research = client.get("/api/research/NVDA/latest", headers={"Authorization": f"Bearer {token}"})

    assert unlock.status_code == 200
    assert unlock.json()["entitlement_state"] == "ad_unlocked"
    assert research.status_code == 200
    assert research.json()["locked"] is False
    assert research.json()["thesis"] == "Full source-cited thesis"


def test_ad_unlock_rejects_empty_event_id(monkeypatch):
    fake_db = FakeBillingDB()
    client = client_with_db(monkeypatch, fake_db)
    token = create_test_token("user-a")

    response = client.post(
        "/api/research/NVDA/ad-unlock",
        headers={"Authorization": f"Bearer {token}"},
        json={"ad_event_id": ""},
    )

    assert response.status_code == 422
    assert fake_db.entitlements == {}


def test_same_webhook_event_is_idempotent(monkeypatch):
    fake_db = FakeBillingDB()
    client = client_with_db(monkeypatch, fake_db)
    monkeypatch.setenv("VBINVEST_MOCK_PAYMENT_WEBHOOK_SECRET", TEST_WEBHOOK_SECRET)
    payload = {"event_id": "evt-1", "auth_user_id": "user-a", "symbol": "NVDA", "event_type": "ad_unlocked"}
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    signature = sign_webhook_payload(body, TEST_WEBHOOK_SECRET)

    first = client.post("/api/webhooks/mock-payment", content=body, headers={"x-webhook-signature": signature})
    second = client.post("/api/webhooks/mock-payment", content=body, headers={"x-webhook-signature": signature})

    assert first.status_code == 200
    assert first.json()["status"] == "processed"
    assert second.status_code == 200
    assert second.json()["status"] == "ignored"
    assert len(fake_db.entitlements) == 1
    assert len(fake_db.webhook_events) == 1


def test_subscription_activated_webhook_unlocks_research(monkeypatch):
    fake_db = FakeBillingDB()
    client = client_with_db(monkeypatch, fake_db)
    monkeypatch.setenv("VBINVEST_MOCK_PAYMENT_WEBHOOK_SECRET", TEST_WEBHOOK_SECRET)
    payload = {"event_id": "evt-sub-1", "auth_user_id": "user-sub", "symbol": "NVDA", "event_type": "subscription.activated"}
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    signature = sign_webhook_payload(body, TEST_WEBHOOK_SECRET)
    token = create_test_token("user-sub")

    webhook = client.post("/api/webhooks/mock-payment", content=body, headers={"x-webhook-signature": signature})
    research = client.get("/api/research/NVDA/latest", headers={"Authorization": f"Bearer {token}"})

    assert webhook.status_code == 200
    assert webhook.json()["status"] == "processed"
    assert len(fake_db.entitlements) == 1
    assert research.status_code == 200
    assert research.json()["locked"] is False
    assert research.json()["thesis"] == "Full source-cited thesis"


def test_invalid_webhook_signature_records_no_entitlement(monkeypatch):
    fake_db = FakeBillingDB()
    client = client_with_db(monkeypatch, fake_db)
    monkeypatch.setenv("VBINVEST_MOCK_PAYMENT_WEBHOOK_SECRET", TEST_WEBHOOK_SECRET)
    payload = {"event_id": "evt-bad", "auth_user_id": "user-a", "symbol": "NVDA", "event_type": "ad_unlocked"}

    response = client.post(
        "/api/webhooks/mock-payment",
        json=payload,
        headers={"x-webhook-signature": "sha256=invalid"},
    )

    assert response.status_code == 401
    assert fake_db.entitlements == {}
    assert fake_db.webhook_events == {}


def test_missing_webhook_secret_fails_closed(monkeypatch):
    fake_db = FakeBillingDB()
    client = client_with_db(monkeypatch, fake_db)
    monkeypatch.delenv("VBINVEST_MOCK_PAYMENT_WEBHOOK_SECRET", raising=False)
    payload = {"event_id": "evt-missing-secret", "auth_user_id": "user-a", "symbol": "NVDA", "event_type": "ad_unlocked"}
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    signature = sign_webhook_payload(body, TEST_WEBHOOK_SECRET)

    response = client.post(
        "/api/webhooks/mock-payment",
        content=body,
        headers={"x-webhook-signature": signature},
    )

    assert response.status_code == 401
    assert "secret" not in response.text.lower()
    assert fake_db.entitlements == {}
    assert fake_db.webhook_events == {}


def test_expired_ad_unlock_keeps_research_redacted(monkeypatch):
    fake_db = FakeBillingDB()
    fake_db.entitlements["expired"] = {
        "auth_user_id": "user-free",
        "target_slug": "NVDA",
        "entitlement_state": "ad_unlocked",
        "expires_at": datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc) - timedelta(seconds=1),
    }
    client = client_with_db(monkeypatch, fake_db)
    token = create_test_token("user-free")

    response = client.get("/api/research/NVDA/latest", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["locked"] is True
    assert "Full source-cited thesis" not in response.text
