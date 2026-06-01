from fastapi.testclient import TestClient

from scripts import api
from scripts.lib.auth import create_test_token


class FakeAuthDB:
    def __init__(self):
        self.created = []
        self.entitlements = {}
        self.webhook_events = {}
        self.holdings = {
            "holding-a": {
                "holding_id": "holding-a",
                "owner_auth_user_id": "user-a",
                "symbol": "NVDA",
                "quantity": 2,
                "average_cost": 100.0,
            }
        }
        self.watchlists = {
            "wl-a": {
                "watchlist_id": "wl-a",
                "owner_auth_user_id": "user-a",
                "name": "AI Memory",
                "symbols": ["NVDA", "005930.KS"],
            }
        }
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
        self.generated = []

    def fetch_profile_by_auth_user(self, auth_user_id: str):
        return {"profile_id": 1, "auth_user_id": auth_user_id, "slug": auth_user_id, "email": f"{auth_user_id}@example.com"}

    def list_user_watchlists(self, auth_user_id: str):
        return [item for item in self.watchlists.values() if item["owner_auth_user_id"] == auth_user_id]

    def create_user_watchlist(self, auth_user_id: str, name: str, symbols: list[str]):
        watchlist = {
            "watchlist_id": f"wl-{len(self.watchlists) + 1}",
            "owner_auth_user_id": auth_user_id,
            "name": name,
            "symbols": symbols,
        }
        self.watchlists[watchlist["watchlist_id"]] = watchlist
        self.created.append(watchlist)
        return watchlist

    def get_user_watchlist(self, auth_user_id: str, watchlist_id: str):
        watchlist = self.watchlists.get(watchlist_id)
        if not watchlist or watchlist["owner_auth_user_id"] != auth_user_id:
            return None
        return watchlist

    def add_user_watchlist_asset(self, auth_user_id: str, watchlist_id: str, symbol: str):
        watchlist = self.get_user_watchlist(auth_user_id, watchlist_id)
        if watchlist is None:
            return None
        if symbol not in ["NVDA", "005930.KS", "000660.KS"]:
            raise LookupError("asset not found")
        if symbol not in watchlist["symbols"]:
            watchlist["symbols"].append(symbol)
        return watchlist

    def remove_user_watchlist_asset(self, auth_user_id: str, watchlist_id: str, symbol: str):
        watchlist = self.get_user_watchlist(auth_user_id, watchlist_id)
        if watchlist is None:
            return None
        watchlist["symbols"] = [item for item in watchlist["symbols"] if item != symbol]
        return watchlist

    def list_user_portfolio_holdings(self, auth_user_id: str):
        return [item for item in self.holdings.values() if item["owner_auth_user_id"] == auth_user_id]

    def create_user_portfolio_holding(self, auth_user_id: str, symbol: str, quantity: float, average_cost: float | None, note: str | None):
        holding = {
            "holding_id": f"holding-{len(self.holdings) + 1}",
            "owner_auth_user_id": auth_user_id,
            "symbol": symbol,
            "quantity": quantity,
            "average_cost": average_cost,
            "note": note,
        }
        self.holdings[holding["holding_id"]] = holding
        return holding

    def update_user_portfolio_holding(self, auth_user_id: str, holding_id: str, quantity: float | None, average_cost: float | None, note: str | None):
        holding = self.holdings.get(holding_id)
        if not holding or holding["owner_auth_user_id"] != auth_user_id:
            return None
        if quantity is not None:
            holding["quantity"] = quantity
        if average_cost is not None:
            holding["average_cost"] = average_cost
        if note is not None:
            holding["note"] = note
        return holding

    def delete_user_portfolio_holding(self, auth_user_id: str, holding_id: str):
        holding = self.holdings.get(holding_id)
        if not holding or holding["owner_auth_user_id"] != auth_user_id:
            return False
        del self.holdings[holding_id]
        return True

    def fetch_latest_research_for_asset(self, symbol: str):
        return self.research.get(symbol)

    def generate_research_for_asset(self, auth_user_id: str, symbol: str):
        row = {
            "target_slug": symbol,
            "opinion": "중립",
            "thesis": f"Generated on-demand thesis for {symbol}",
            "bull": "Bull case",
            "base": "Base case",
            "bear": "Bear case",
            "sources": [{"kind": "db_price_indicator", "symbol": symbol}],
        }
        self.research[symbol] = row
        self.generated.append({"auth_user_id": auth_user_id, "symbol": symbol})
        return row

    def user_has_research_entitlement(self, auth_user_id: str, symbol: str):
        return auth_user_id == "user-a"

    def grant_ad_unlock(self, auth_user_id: str, symbol: str, ad_event_id: str):
        entitlement = {
            "auth_user_id": auth_user_id,
            "target_slug": symbol,
            "entitlement_state": "ad_unlocked",
            "expires_at": "2026-06-01T12:30:00+00:00",
        }
        self.entitlements[ad_event_id] = entitlement
        return entitlement

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


def test_unauthorized_watchlist_crud_returns_401(monkeypatch):
    client = client_with_db(monkeypatch, FakeAuthDB())

    response = client.post("/api/watchlists", json={"name": "AI Memory", "symbols": ["NVDA"]})

    assert response.status_code == 401


def test_invalid_token_returns_401(monkeypatch):
    client = client_with_db(monkeypatch, FakeAuthDB())

    response = client.get("/api/me", headers={"Authorization": "Bearer invalid"})

    assert response.status_code == 401


def test_create_watchlist_uses_token_subject_not_payload_profile_id(monkeypatch):
    fake_db = FakeAuthDB()
    client = client_with_db(monkeypatch, fake_db)
    token = create_test_token("user-a")

    response = client.post(
        "/api/watchlists",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "AI Memory", "symbols": ["NVDA", "005930.KS"], "profile_id": 999},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "AI Memory"
    assert response.json()["symbols"] == ["NVDA", "005930.KS"]
    assert fake_db.created[0]["owner_auth_user_id"] == "user-a"


def test_user_b_cannot_read_user_a_watchlist(monkeypatch):
    client = client_with_db(monkeypatch, FakeAuthDB())
    token = create_test_token("user-b")

    response = client.get("/api/watchlists/wl-a", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 404
    assert "NVDA" not in response.text


def test_watchlist_asset_add_remove_enforces_ownership(monkeypatch):
    client = client_with_db(monkeypatch, FakeAuthDB())
    token_a = create_test_token("user-a")
    token_b = create_test_token("user-b")

    add_response = client.post(
        "/api/watchlists/wl-a/assets",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"symbol": "000660.KS"},
    )
    denied_response = client.post(
        "/api/watchlists/wl-a/assets",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"symbol": "000660.KS"},
    )
    remove_response = client.delete(
        "/api/watchlists/wl-a/assets/000660.KS",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    assert add_response.status_code == 200
    assert "000660.KS" in add_response.json()["symbols"]
    assert denied_response.status_code == 404
    assert "NVDA" not in denied_response.text
    assert remove_response.status_code == 200
    assert "000660.KS" not in remove_response.json()["symbols"]


def test_portfolio_holding_crud_is_user_owned(monkeypatch):
    fake_db = FakeAuthDB()
    client = client_with_db(monkeypatch, fake_db)
    token_a = create_test_token("user-a")
    token_b = create_test_token("user-b")

    unauthenticated = client.post("/api/portfolio/holdings", json={"symbol": "NVDA", "quantity": 1})
    created = client.post(
        "/api/portfolio/holdings",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"symbol": "005930.KS", "quantity": 3, "average_cost": 70000},
    )
    denied = client.patch(
        "/api/portfolio/holdings/holding-a",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"quantity": 10},
    )
    updated = client.patch(
        "/api/portfolio/holdings/holding-a",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"quantity": 4},
    )
    deleted = client.delete("/api/portfolio/holdings/holding-a", headers={"Authorization": f"Bearer {token_a}"})

    assert unauthenticated.status_code == 401
    assert created.status_code == 201
    assert created.json()["owner_auth_user_id"] == "user-a"
    assert denied.status_code == 404
    assert "NVDA" not in denied.text
    assert updated.status_code == 200
    assert updated.json()["quantity"] == 4
    assert deleted.status_code == 204


def test_gated_research_redacts_without_entitlement(monkeypatch):
    client = client_with_db(monkeypatch, FakeAuthDB())
    token = create_test_token("user-free")

    response = client.get("/api/research/NVDA/latest", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["locked"] is True
    assert "thesis" not in body
    assert "Full source-cited thesis" not in response.text


def test_gated_research_full_with_entitlement(monkeypatch):
    client = client_with_db(monkeypatch, FakeAuthDB())
    token = create_test_token("user-a")

    response = client.get("/api/research/NVDA/latest", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["locked"] is False
    assert body["thesis"] == "Full source-cited thesis"


def test_generate_research_runs_only_for_authenticated_user_request(monkeypatch):
    fake_db = FakeAuthDB()
    client = client_with_db(monkeypatch, fake_db)
    token = create_test_token("user-a")

    unauthenticated = client.post("/api/research/NVDA/generate")
    generated = client.post("/api/research/NVDA/generate", headers={"Authorization": f"Bearer {token}"})

    assert unauthenticated.status_code == 401
    assert generated.status_code == 201
    assert generated.json()["locked"] is False
    assert generated.json()["thesis"] == "Generated on-demand thesis for NVDA"
    assert fake_db.generated == [{"auth_user_id": "user-a", "symbol": "NVDA"}]


def test_expired_ad_unlock_still_redacts_research(monkeypatch):
    fake_db = FakeAuthDB()
    fake_db.entitlements["expired"] = {
        "auth_user_id": "user-free",
        "target_slug": "NVDA",
        "entitlement_state": "ad_unlocked",
        "expires_at": "2026-06-01T11:59:59+00:00",
    }
    fake_db.user_has_research_entitlement = lambda auth_user_id, symbol: False
    client = client_with_db(monkeypatch, fake_db)
    token = create_test_token("user-free")

    response = client.get("/api/research/NVDA/latest", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["locked"] is True
    assert "thesis" not in body
    assert "Full source-cited thesis" not in response.text


def test_ad_unlock_endpoint_grants_access_state(monkeypatch):
    client = client_with_db(monkeypatch, FakeAuthDB())
    token = create_test_token("user-a")

    response = client.post(
        "/api/research/NVDA/ad-unlock",
        headers={"Authorization": f"Bearer {token}"},
        json={"ad_event_id": "test-ad-1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["target_slug"] == "NVDA"
    assert body["entitlement_state"] == "ad_unlocked"
