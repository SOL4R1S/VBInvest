from fastapi.testclient import TestClient

from scripts import api


class FakeLocalModeDB:
    def record_payment_webhook(self, event_id: str, provider: str, event_type: str, payload: dict, signature_valid: bool):
        raise AssertionError("local mode must not process hosted payment webhooks")

    def grant_ad_unlock(self, auth_user_id: str, symbol: str, ad_event_id: str):
        raise AssertionError("local mode must not grant ad unlocks")

    def grant_subscription_entitlement(self, auth_user_id: str, provider: str, provider_subject_id: str):
        raise AssertionError("local mode must not grant subscription entitlements")


def client_with_db(monkeypatch, fake_db: FakeLocalModeDB):
    monkeypatch.setattr(api, "db", lambda: fake_db)
    return TestClient(api.app)


def test_mock_payment_webhook_is_disabled_in_local_mode(monkeypatch):
    client = client_with_db(monkeypatch, FakeLocalModeDB())

    response = client.post(
        "/api/webhooks/mock-payment",
        json={"event_id": "evt-1", "auth_user_id": "user-a", "symbol": "NVDA", "event_type": "ad_unlocked"},
    )

    assert response.status_code == 410
    assert response.json()["detail"] == "hosted monetization is disabled in local mode"


def test_mock_payment_webhook_does_not_require_secret_in_local_mode(monkeypatch):
    client = client_with_db(monkeypatch, FakeLocalModeDB())
    monkeypatch.delenv("VBINVEST_MOCK_PAYMENT_WEBHOOK_SECRET", raising=False)

    response = client.post("/api/webhooks/mock-payment", content=b"not-json")

    assert response.status_code == 410
    assert "secret" not in response.text.lower()
