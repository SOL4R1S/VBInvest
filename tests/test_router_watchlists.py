"""Tests for scripts.routers.watchlists — watchlist CRUD and ticker endpoints."""

from fastapi.testclient import TestClient

from scripts import api
from scripts.api import app
from scripts.lib.auth import create_test_token


class FakeWatchlistDB:
    def __init__(self):
        self.watchlists = {}
        self._next_id = 1

    def fetch_profile_by_auth_user(self, auth_user_id: str):
        return {"profile_id": 1, "auth_user_id": auth_user_id, "slug": auth_user_id}

    def list_user_watchlists(self, auth_user_id: str):
        return list(self.watchlists.values())

    def create_user_watchlist(self, auth_user_id, name, symbols):
        wl_id = f"wl-{self._next_id}"
        self._next_id += 1
        row = {"watchlist_id": wl_id, "name": name, "symbols": symbols or []}
        self.watchlists[wl_id] = row
        return row

    def get_user_watchlist(self, auth_user_id, watchlist_id):
        return self.watchlists.get(watchlist_id)

    def add_user_watchlist_asset(self, auth_user_id, watchlist_id, symbol):
        wl = self.watchlists.get(watchlist_id)
        if wl is None:
            return None
        if symbol not in wl["symbols"]:
            wl["symbols"].append(symbol)
        return wl

    def remove_user_watchlist_asset(self, auth_user_id, watchlist_id, symbol):
        wl = self.watchlists.get(watchlist_id)
        if wl is None:
            return None
        wl["symbols"] = [s for s in wl["symbols"] if s != symbol]
        return wl

    def fetch_watchlist_assets(self, slug):
        return []


def _client_with_fake(monkeypatch, fake=None):
    fake = fake or FakeWatchlistDB()
    monkeypatch.setattr(api, "db", lambda: fake)
    monkeypatch.setattr(api, "auth_db", lambda: fake)
    monkeypatch.setattr(api, "validate_ticker_symbol", lambda s: {"valid": True, "symbol": s})
    monkeypatch.setattr(api, "search_ticker_suggestions", lambda q, limit=8: [{"symbol": "NVDA", "name": "NVIDIA"}])
    return TestClient(app), fake


def _auth_headers(user="user-w"):
    token = create_test_token(user, email=f"{user}@example.com")
    return {"Authorization": f"Bearer {token}"}


def test_list_watchlists_empty(monkeypatch):
    client, _ = _client_with_fake(monkeypatch)
    resp = client.get("/api/watchlists", headers=_auth_headers())
    assert resp.status_code == 200
    assert resp.json() == {"watchlists": []}


def test_create_watchlist(monkeypatch):
    client, _ = _client_with_fake(monkeypatch)
    resp = client.post(
        "/api/watchlists",
        json={"name": "Tech", "symbols": ["NVDA", "AAPL"]},
        headers=_auth_headers(),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Tech"
    assert body["symbols"] == ["NVDA", "AAPL"]


def test_get_watchlist(monkeypatch):
    client, fake = _client_with_fake(monkeypatch)
    created = fake.create_user_watchlist("u", "Core", ["TSLA"])
    resp = client.get(f"/api/watchlists/{created['watchlist_id']}", headers=_auth_headers())
    assert resp.status_code == 200
    assert resp.json()["name"] == "Core"


def test_get_watchlist_not_found(monkeypatch):
    client, _ = _client_with_fake(monkeypatch)
    resp = client.get("/api/watchlists/nope", headers=_auth_headers())
    assert resp.status_code == 404


def test_add_asset(monkeypatch):
    client, fake = _client_with_fake(monkeypatch)
    created = fake.create_user_watchlist("u", "Core", [])
    resp = client.post(
        f"/api/watchlists/{created['watchlist_id']}/assets",
        json={"symbol": "MSFT"},
        headers=_auth_headers(),
    )
    assert resp.status_code == 200
    assert "MSFT" in resp.json()["symbols"]


def test_remove_asset(monkeypatch):
    client, fake = _client_with_fake(monkeypatch)
    created = fake.create_user_watchlist("u", "Core", ["NVDA"])
    resp = client.delete(
        f"/api/watchlists/{created['watchlist_id']}/assets/NVDA",
        headers=_auth_headers(),
    )
    assert resp.status_code == 200
    assert "NVDA" not in resp.json()["symbols"]


def test_validate_ticker(monkeypatch):
    client, _ = _client_with_fake(monkeypatch)
    resp = client.get("/api/tickers/validate", params={"symbol": "NVDA"})
    assert resp.status_code == 200
    assert resp.json()["valid"] is True


def test_search_tickers(monkeypatch):
    client, _ = _client_with_fake(monkeypatch)
    resp = client.get("/api/tickers/search", params={"query": "nvidia"})
    assert resp.status_code == 200
    assert len(resp.json()["suggestions"]) > 0


def test_watchlists_require_auth(monkeypatch):
    client, _ = _client_with_fake(monkeypatch)
    resp = client.get("/api/watchlists")
    assert resp.status_code == 401
