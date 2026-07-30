"""Tests for scripts.routers.portfolio — holdings CRUD."""

from fastapi.testclient import TestClient

from scripts import api
from scripts.api import app
from scripts.lib.auth import create_test_token


class FakePortfolioDB:
    def __init__(self):
        self.holdings: dict[str, dict] = {}
        self._next_id = 1

    def fetch_profile_by_auth_user(self, auth_user_id: str):
        return {"profile_id": 1, "auth_user_id": auth_user_id, "slug": auth_user_id}

    def list_user_portfolio_holdings(self, auth_user_id: str):
        return list(self.holdings.values())

    def create_user_portfolio_holding(self, auth_user_id, symbol, quantity, average_cost, note):
        holding_id = f"h-{self._next_id}"
        self._next_id += 1
        row = {
            "holding_id": holding_id,
            "symbol": symbol,
            "quantity": quantity,
            "average_cost": average_cost,
            "note": note,
        }
        self.holdings[holding_id] = row
        return row

    def update_user_portfolio_holding(self, auth_user_id, holding_id, quantity, average_cost, note):
        if holding_id not in self.holdings:
            return None
        row = self.holdings[holding_id]
        if quantity is not None:
            row["quantity"] = quantity
        if average_cost is not None:
            row["average_cost"] = average_cost
        if note is not None:
            row["note"] = note
        return row

    def delete_user_portfolio_holding(self, auth_user_id, holding_id):
        return self.holdings.pop(holding_id, None) is not None


def _client_with_fake(monkeypatch, fake=None):
    fake = fake or FakePortfolioDB()
    monkeypatch.setattr(api, "db", lambda: fake)
    monkeypatch.setattr(api, "auth_db", lambda: fake)
    return TestClient(app), fake


def _auth_headers(user="user-p"):
    token = create_test_token(user, email=f"{user}@example.com")
    return {"Authorization": f"Bearer {token}"}


def test_list_holdings_empty(monkeypatch):
    client, _ = _client_with_fake(monkeypatch)
    resp = client.get("/api/portfolio/holdings", headers=_auth_headers())
    assert resp.status_code == 200
    assert resp.json() == {"holdings": []}


def test_create_holding(monkeypatch):
    client, _ = _client_with_fake(monkeypatch)
    resp = client.post(
        "/api/portfolio/holdings",
        json={"symbol": "NVDA", "quantity": 10, "average_cost": 120.5, "note": "core"},
        headers=_auth_headers(),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["symbol"] == "NVDA"
    assert body["quantity"] == 10
    assert body["holding_id"].startswith("h-")


def test_update_holding(monkeypatch):
    client, fake = _client_with_fake(monkeypatch)
    created = fake.create_user_portfolio_holding("u", "AAPL", 5, 180.0, None)
    resp = client.patch(
        f"/api/portfolio/holdings/{created['holding_id']}",
        json={"quantity": 20},
        headers=_auth_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["quantity"] == 20


def test_update_holding_not_found(monkeypatch):
    client, _ = _client_with_fake(monkeypatch)
    resp = client.patch(
        "/api/portfolio/holdings/nonexistent",
        json={"quantity": 1},
        headers=_auth_headers(),
    )
    assert resp.status_code == 404


def test_delete_holding(monkeypatch):
    client, fake = _client_with_fake(monkeypatch)
    created = fake.create_user_portfolio_holding("u", "TSLA", 3, 250.0, None)
    resp = client.delete(
        f"/api/portfolio/holdings/{created['holding_id']}",
        headers=_auth_headers(),
    )
    assert resp.status_code == 204


def test_delete_holding_not_found(monkeypatch):
    client, _ = _client_with_fake(monkeypatch)
    resp = client.delete("/api/portfolio/holdings/nope", headers=_auth_headers())
    assert resp.status_code == 404


def test_portfolio_requires_auth(monkeypatch):
    client, _ = _client_with_fake(monkeypatch)
    resp = client.get("/api/portfolio/holdings")
    assert resp.status_code == 401
