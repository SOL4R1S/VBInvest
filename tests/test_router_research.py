"""Tests for scripts.routers.research — research generation and jobs."""

from fastapi.testclient import TestClient

from scripts import api
from scripts.api import app
from scripts.lib.auth import create_test_token


class FakeResearchDB:
    def __init__(self):
        self.research_rows = {}
        self.report_runs = {}
        self._run_counter = 1

    def fetch_profile_by_auth_user(self, auth_user_id: str):
        return {"profile_id": 1, "auth_user_id": auth_user_id, "slug": auth_user_id}

    def fetch_latest_research_for_asset(self, symbol: str):
        return self.research_rows.get(symbol)

    def generate_research_for_asset(self, auth_user_id, symbol, obsidian_vault_path=None):
        row = {
            "run_id": f"run-{self._run_counter}",
            "symbol": symbol,
            "status": "completed",
            "title": f"Research: {symbol}",
            "summary": "AI-generated summary",
            "created_at": "2026-01-01T00:00:00Z",
        }
        self._run_counter += 1
        self.research_rows[symbol] = row
        return row

    def record_report_run(self, **kwargs):
        run_id = f"run-{self._run_counter}"
        self._run_counter += 1
        self.report_runs[run_id] = kwargs
        return run_id

    def cancel_report_run(self, run_id):
        if run_id not in self.report_runs:
            return None
        self.report_runs[run_id]["status"] = "canceled"
        return {"run_id": run_id, "status": "canceled", "error_message": "canceled by user"}


def _client_with_fake(monkeypatch, fake=None):
    fake = fake or FakeResearchDB()
    monkeypatch.setattr(api, "db", lambda: fake)
    monkeypatch.setattr(api, "auth_db", lambda: fake)
    return TestClient(app), fake


def _auth_headers(user="user-r"):
    token = create_test_token(user, email=f"{user}@example.com")
    return {"Authorization": f"Bearer {token}"}


def test_latest_research_not_found(monkeypatch):
    client, _ = _client_with_fake(monkeypatch)
    resp = client.get("/api/research/NVDA/latest", headers=_auth_headers())
    assert resp.status_code == 404


def test_generate_research(monkeypatch):
    client, _ = _client_with_fake(monkeypatch)
    resp = client.post("/api/research/NVDA/generate", headers=_auth_headers())
    assert resp.status_code == 201
    body = resp.json()
    assert body["symbol"] == "NVDA"
    assert body["status"] == "completed"


def test_latest_research_after_generate(monkeypatch):
    client, _ = _client_with_fake(monkeypatch)
    client.post("/api/research/AAPL/generate", headers=_auth_headers())
    resp = client.get("/api/research/AAPL/latest", headers=_auth_headers())
    assert resp.status_code == 200
    assert resp.json()["symbol"] == "AAPL"


def test_cancel_research_job_not_found(monkeypatch):
    client, _ = _client_with_fake(monkeypatch)
    resp = client.delete("/api/research-jobs/nonexistent", headers=_auth_headers())
    assert resp.status_code == 404


def test_cancel_research_generation(monkeypatch):
    client, _ = _client_with_fake(monkeypatch)
    resp = client.delete("/api/research/NVDA/generate", headers=_auth_headers())
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "canceled"


def test_ad_unlock_disabled(monkeypatch):
    client, _ = _client_with_fake(monkeypatch)
    resp = client.post("/api/research/NVDA/ad-unlock", headers=_auth_headers())
    assert resp.status_code == 501


def test_research_requires_auth(monkeypatch):
    client, _ = _client_with_fake(monkeypatch)
    resp = client.get("/api/research/NVDA/latest")
    assert resp.status_code == 401
