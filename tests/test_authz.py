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
        self.report_runs = []

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

    def generate_research_for_asset(self, auth_user_id: str, symbol: str, *, obsidian_vault_path=None):
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

    def cancel_report_run(self, run_id: str):
        return {"run_id": run_id, "status": "canceled", "error_message": "canceled by user"}

    def record_report_run(self, **kwargs):
        self.report_runs.append(kwargs)
        return f"run-{len(self.report_runs)}"

    def user_has_research_entitlement(self, auth_user_id: str, symbol: str):
        raise AssertionError("local research access must not call entitlement gate")

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


def test_ticker_validation_endpoint_reports_invalid_symbol(monkeypatch):
    client = client_with_db(monkeypatch, FakeAuthDB())

    monkeypatch.setattr(
        api,
        "validate_ticker_symbol",
        lambda symbol: {"symbol": symbol.strip().upper(), "valid": False, "reason": "ticker_not_found"},
    )
    response = client.get("/api/tickers/validate", params={"symbol": "notreal"})

    assert response.status_code == 404
    assert response.json()["detail"] == {"symbol": "NOTREAL", "valid": False, "reason": "ticker_not_found"}


def test_ticker_validation_endpoint_returns_suggestion_for_common_typo(monkeypatch):
    client = client_with_db(monkeypatch, FakeAuthDB())

    monkeypatch.setattr(
        api,
        "validate_ticker_symbol",
        lambda symbol: {
            "symbol": symbol.strip().upper(),
            "valid": False,
            "reason": "ticker_not_found",
            "suggestion": "005930.KS",
            "suggestion_label": "삼성전자",
            "suggestions": [
                {
                    "symbol": "005930.KS",
                    "name": "삼성전자",
                    "exchange": "KSC",
                    "quote_type": "EQUITY",
                }
            ],
        },
    )
    response = client.get("/api/tickers/validate", params={"symbol": "009530.KS"})

    assert response.status_code == 404
    assert response.json()["detail"]["suggestion"] == "005930.KS"
    assert response.json()["detail"]["suggestions"][0]["name"] == "삼성전자"


def test_ticker_validation_endpoint_returns_name_search_suggestions(monkeypatch):
    client = client_with_db(monkeypatch, FakeAuthDB())

    monkeypatch.setattr(
        api,
        "validate_ticker_symbol",
        lambda symbol: {
            "symbol": symbol.strip().upper(),
            "valid": False,
            "reason": "ticker_not_found",
            "suggestion": "005930.KS",
            "suggestion_label": "SamsungElec",
            "suggestions": [
                {
                    "symbol": "005930.KS",
                    "name": "SamsungElec",
                    "exchange": "KSC",
                    "quote_type": "EQUITY",
                },
                {
                    "symbol": "SSNLF",
                    "name": "SAMSUNG ELECTRONICS CO",
                    "exchange": "PNK",
                    "quote_type": "EQUITY",
                },
            ],
        },
    )
    response = client.get("/api/tickers/validate", params={"symbol": "Samsung Electronics"})

    assert response.status_code == 404
    assert response.json()["detail"]["suggestions"][1]["symbol"] == "SSNLF"


def test_ticker_validation_endpoint_returns_provider_for_valid_symbol(monkeypatch):
    client = client_with_db(monkeypatch, FakeAuthDB())

    monkeypatch.setattr(
        api,
        "validate_ticker_symbol",
        lambda symbol: {"symbol": symbol.strip().upper(), "valid": True, "provider": "yfinance"},
    )
    response = client.get("/api/tickers/validate", params={"symbol": "nvda"})

    assert response.status_code == 200
    assert response.json() == {"symbol": "NVDA", "valid": True, "provider": "yfinance"}


def test_ticker_search_endpoint_returns_autocomplete_suggestions(monkeypatch):
    client = client_with_db(monkeypatch, FakeAuthDB())

    monkeypatch.setattr(
        api,
        "search_ticker_suggestions",
        lambda query, limit: [
            {"symbol": "005930.KS", "name": "삼성전자", "exchange": "KSC", "quote_type": "EQUITY"},
            {"symbol": "009150.KS", "name": "삼성전기", "exchange": "KSC", "quote_type": "EQUITY"},
        ],
    )
    response = client.get("/api/tickers/search", params={"query": "삼", "limit": 5})

    assert response.status_code == 200
    assert response.json() == {
        "query": "삼",
        "suggestions": [
            {"symbol": "005930.KS", "name": "삼성전자", "exchange": "KSC", "quote_type": "EQUITY"},
            {"symbol": "009150.KS", "name": "삼성전기", "exchange": "KSC", "quote_type": "EQUITY"},
        ],
    }


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


def test_local_research_returns_full_report_without_entitlement_gate(monkeypatch):
    client = client_with_db(monkeypatch, FakeAuthDB())
    token = create_test_token("user-free")

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


def test_cancel_research_job_requires_auth_and_returns_status(monkeypatch):
    client = client_with_db(monkeypatch, FakeAuthDB())
    token = create_test_token("user-a")

    unauthenticated = client.delete("/api/research-jobs/run-1")
    canceled = client.delete("/api/research-jobs/run-1", headers={"Authorization": f"Bearer {token}"})

    assert unauthenticated.status_code == 401
    assert canceled.status_code == 200
    assert canceled.json() == {"run_id": "run-1", "status": "canceled", "error_message": "canceled by user"}


def test_cancel_current_symbol_generation_records_canceled_run(monkeypatch):
    fake_db = FakeAuthDB()
    client = client_with_db(monkeypatch, fake_db)
    token = create_test_token("user-a")

    response = client.delete("/api/research/NVDA/generate", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {"run_id": "run-1", "status": "canceled", "error_message": "canceled by user"}
    assert fake_db.report_runs[0]["status"] == "canceled"
    assert fake_db.report_runs[0]["scope_slug"] == "NVDA"


def test_ad_unlock_endpoint_is_disabled_in_local_mode(monkeypatch):
    client = client_with_db(monkeypatch, FakeAuthDB())
    token = create_test_token("user-a")

    response = client.post(
        "/api/research/NVDA/ad-unlock",
        headers={"Authorization": f"Bearer {token}"},
        json={"ad_event_id": "test-ad-1"},
    )

    assert response.status_code == 410
    assert response.json()["detail"] == "hosted monetization is disabled in local mode"


def test_local_session_token_authenticates_without_jwt(monkeypatch):
    fake_db = FakeAuthDB()
    client = client_with_db(monkeypatch, fake_db)
    monkeypatch.setenv("VBINVEST_LOCAL_SESSION_TOKEN", "qa-token")

    response = client.get("/api/me", headers={"Authorization": "Bearer qa-token"})

    assert response.status_code == 200
    assert response.json()["auth_user_id"] == "local-owner"
    assert response.json()["provider"] == "local"


def test_frontend_index_injects_local_session_token(monkeypatch, tmp_path):
    out_dir = tmp_path / "frontend-out"
    out_dir.mkdir()
    (out_dir / "index.html").write_text("<html><head></head><body>VBinvest</body></html>", encoding="utf-8")
    monkeypatch.setenv("VBINVEST_FRONTEND_OUT_DIR", str(out_dir))
    monkeypatch.setenv("VBINVEST_LOCAL_SESSION_TOKEN", "qa-token")
    client = client_with_db(monkeypatch, FakeAuthDB())

    response = client.get("/")

    assert response.status_code == 200
    assert 'window.__VBINVEST_LOCAL_SESSION_TOKEN__="qa-token"' in response.text


def test_frontend_index_omits_local_session_script_when_token_missing(monkeypatch, tmp_path):
    out_dir = tmp_path / "frontend-out"
    out_dir.mkdir()
    (out_dir / "index.html").write_text("<html><head></head><body>VBinvest</body></html>", encoding="utf-8")
    monkeypatch.setenv("VBINVEST_FRONTEND_OUT_DIR", str(out_dir))
    monkeypatch.delenv("VBINVEST_LOCAL_SESSION_TOKEN", raising=False)
    client = client_with_db(monkeypatch, FakeAuthDB())

    response = client.get("/")

    assert response.status_code == 200
    assert "__VBINVEST_LOCAL_SESSION_TOKEN__" not in response.text


def test_shutdown_requires_local_session_token(monkeypatch):
    client = client_with_db(monkeypatch, FakeAuthDB())
    monkeypatch.setenv("VBINVEST_LOCAL_SESSION_TOKEN", "qa-token")

    response = client.post("/api/system/shutdown")

    assert response.status_code == 401


def test_shutdown_is_disabled_without_launcher_callback(monkeypatch):
    client = client_with_db(monkeypatch, FakeAuthDB())
    monkeypatch.setenv("VBINVEST_LOCAL_SESSION_TOKEN", "qa-token")

    response = client.post("/api/system/shutdown", headers={"Authorization": "Bearer qa-token"})

    assert response.status_code == 503
    assert response.json()["detail"] == "local launcher shutdown is not available"


def test_shutdown_invokes_local_callback_when_enabled(monkeypatch):
    client = client_with_db(monkeypatch, FakeAuthDB())
    monkeypatch.setenv("VBINVEST_LOCAL_SESSION_TOKEN", "qa-token")
    monkeypatch.setenv("VBINVEST_LOCAL_SHUTDOWN_ENABLED", "1")

    called = {"count": 0}

    def fake_shutdown() -> None:
        called["count"] += 1

    monkeypatch.setattr(api, "LOCAL_SHUTDOWN_CALLBACK", fake_shutdown)

    response = client.post("/api/system/shutdown", headers={"Authorization": "Bearer qa-token"})

    assert response.status_code == 200
    assert response.json() == {"status": "shutting_down"}
    assert called["count"] == 1


def test_shutdown_beacon_accepts_local_session_token_body(monkeypatch):
    client = client_with_db(monkeypatch, FakeAuthDB())
    monkeypatch.setenv("VBINVEST_LOCAL_SESSION_TOKEN", "qa-token")
    monkeypatch.setenv("VBINVEST_LOCAL_SHUTDOWN_ENABLED", "1")

    called = {"count": 0}

    def fake_shutdown() -> None:
        called["count"] += 1

    monkeypatch.setattr(api, "LOCAL_SHUTDOWN_CALLBACK", fake_shutdown)

    response = client.post("/api/system/shutdown-beacon", json={"token": "qa-token"})

    assert response.status_code == 200
    assert response.json() == {"status": "shutting_down"}
    assert called["count"] == 1


def test_shutdown_beacon_rejects_wrong_token(monkeypatch):
    client = client_with_db(monkeypatch, FakeAuthDB())
    monkeypatch.setenv("VBINVEST_LOCAL_SESSION_TOKEN", "qa-token")
    monkeypatch.setenv("VBINVEST_LOCAL_SHUTDOWN_ENABLED", "1")
    monkeypatch.setattr(api, "LOCAL_SHUTDOWN_CALLBACK", lambda: None)

    response = client.post("/api/system/shutdown-beacon", json={"token": "wrong"})

    assert response.status_code == 401
