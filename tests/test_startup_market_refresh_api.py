from fastapi.testclient import TestClient
from pathlib import Path

from scripts import api


class FakeStartupRefreshDB:
    def __init__(self, *, locked: bool = False):
        self.locked = locked
        self.report_runs = []
        self.lock_calls = []
        self.release_calls = []

    def fetch_watchlist_assets(self, slug: str):
        if slug != "semiconductor-core":
            return []
        return [{"asset_id": 1, "symbol": "NVDA", "display_name_ko": "엔비디아", "exchange": "NASDAQ", "currency": "USD"}]

    def try_acquire_job_lock(self, lock_name: str, holder: str, ttl_seconds: int) -> bool:
        self.lock_calls.append((lock_name, holder, ttl_seconds))
        return not self.locked

    def release_job_lock(self, lock_name: str, holder: str) -> None:
        self.release_calls.append((lock_name, holder))

    def upsert_prices(self, rows):
        return len(rows)

    def upsert_indicators(self, rows):
        return len(rows)

    def record_report_run(self, **kwargs):
        self.report_runs.append(kwargs)
        return "run-startup-1"


def client_with_db(monkeypatch, fake_db: FakeStartupRefreshDB):
    monkeypatch.setattr(api, "db", lambda: fake_db)
    return TestClient(api.app)


def test_startup_market_refresh_rejects_unknown_watchlist(monkeypatch):
    client = client_with_db(monkeypatch, FakeStartupRefreshDB())

    response = client.post("/api/startup/market-refresh?watchlist=unknown&dry_run=true")

    assert response.status_code == 400
    assert "unknown watchlist" in response.text


def test_startup_market_refresh_dry_run_records_status(monkeypatch):
    fake_db = FakeStartupRefreshDB()
    client = client_with_db(monkeypatch, fake_db)

    response = client.post(
        "/api/startup/market-refresh?watchlist=semiconductor-core&dry_run=true&no_network=true&limit=1",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["watchlist"] == "semiconductor-core"
    assert body["dry_run"] is True
    assert body["price_rows"] > 0
    assert fake_db.report_runs[0]["run_type"] == "startup-market-refresh"
    assert fake_db.report_runs[0]["status"] == "ok"


def test_startup_market_refresh_concurrent_run_returns_skipped(monkeypatch):
    fake_db = FakeStartupRefreshDB(locked=True)
    client = client_with_db(monkeypatch, fake_db)

    response = client.post(
        "/api/startup/market-refresh?watchlist=semiconductor-core&no_network=true&limit=1",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "skipped"
    assert body["locked"] is True
    assert fake_db.lock_calls == [("startup-market-refresh:semiconductor-core", "api-startup", 3600)]
    assert fake_db.report_runs[0]["status"] == "skipped"


def test_startup_market_refresh_public_readme_keeps_local_first_positioning():
    readme = Path("README.md").read_text(encoding="utf-8")
    english_readme = Path("README.en.md").read_text(encoding="utf-8")

    assert "local-first" in readme
    assert "호스팅 SaaS가 아닙니다" in readme
    assert "로컬에서 실행" in readme
    assert "not a hosted SaaS" in english_readme
    assert "run it locally" in english_readme
