from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from psycopg import OperationalError

from scripts import api


class FakeStartupRefreshDB:
    def __init__(self, *, locked: bool = False, last_success_at=None):
        self.locked = locked
        self.last_success_at = last_success_at
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

    def fetch_latest_successful_report_run(self, run_type: str, scope_slug: str):
        if run_type != "startup-market-refresh" or scope_slug != "semiconductor-core":
            return None
        if self.last_success_at is None:
            return None
        return {"run_id": "previous-success", "completed_at": self.last_success_at}


class UnavailableStartupRefreshDB(FakeStartupRefreshDB):
    def fetch_watchlist_assets(self, slug: str):
        raise OperationalError("forced unavailable test db")


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


def test_startup_refresh_dry_run_no_network_uses_fallback_when_db_unavailable(monkeypatch):
    client = client_with_db(monkeypatch, UnavailableStartupRefreshDB())

    response = client.post(
        "/api/startup/market-refresh?watchlist=semiconductor-core&dry_run=true&no_network=true&limit=1",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["watchlist"] == "semiconductor-core"
    assert body["report_run_id"] is None
    assert body["provider_disabled"][0]["provider"] == "yahoo-rss"
    assert body["provider_disabled"][0]["reason"] == "no-network"


def test_startup_refresh_defaults_to_source_collection(monkeypatch):
    fake_db = FakeStartupRefreshDB()
    client = client_with_db(monkeypatch, fake_db)

    response = client.post(
        "/api/startup/market-refresh?watchlist=semiconductor-core&dry_run=true&no_network=true&limit=1",
    )

    assert response.status_code == 200
    body = response.json()
    assert {
        "status",
        "watchlist",
        "dry_run",
        "locked",
        "stale",
        "price_rows",
        "indicator_rows",
        "news_items",
        "disclosures",
        "provider_disabled",
        "failures",
        "report_run_id",
        "last_success_at",
    } <= set(body)
    assert body["news_items"] == 0
    assert body["disclosures"] == 0
    assert body["provider_disabled"] == [
        {"symbol": "NVDA", "provider": "yahoo-rss", "reason": "no-network"},
        {"symbol": "NVDA", "provider": "disclosures", "reason": "no-network"},
    ]


def test_startup_refresh_skips_when_recent_success_exists_unless_forced(monkeypatch):
    recent = datetime.now(timezone.utc) - timedelta(minutes=5)
    fake_db = FakeStartupRefreshDB(last_success_at=recent)
    client = client_with_db(monkeypatch, fake_db)

    skipped = client.post(
        "/api/startup/market-refresh?watchlist=semiconductor-core&dry_run=true&no_network=true&limit=1",
    )
    forced = client.post(
        "/api/startup/market-refresh?watchlist=semiconductor-core&dry_run=true&no_network=true&limit=1&force=true",
    )

    assert skipped.status_code == 200
    assert skipped.json()["status"] == "skipped"
    assert skipped.json()["stale"] is True
    assert skipped.json()["price_rows"] == 0
    assert forced.status_code == 200
    assert forced.json()["status"] == "ok"
    assert forced.json()["stale"] is False
    assert forced.json()["price_rows"] > 0


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
