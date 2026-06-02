import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from scripts import api
from scripts.lib import local_scheduler
from scripts.lib.auth import create_test_token
from scripts.lib.db_sqlite import SQLiteVBinvestDB
from scripts.lib.startup_market_refresh import run_startup_market_refresh


def create_scheduler_test_client(monkeypatch, fake_db):
    monkeypatch.setattr(api, "db", lambda: fake_db)
    monkeypatch.setattr(api, "auth_db", lambda: fake_db)
    return TestClient(api.app)


class FakeSchedulerDB:
    def __init__(self, *, locked: bool = False, latest_runs: dict[tuple[str, str | None], dict] | None = None):
        self.locked = locked
        self.settings: dict[str, str] = {}
        self.lock_calls: list[tuple[str, str, int]] = []
        self.release_calls: list[tuple[str, str]] = []
        self.latest_runs = latest_runs or {}

    def fetch_setting(self, key: str) -> str | None:
        return self.settings.get(key)

    def upsert_setting(self, key: str, value: str) -> None:
        self.settings[key] = value

    def try_acquire_job_lock(self, lock_name: str, holder: str, ttl_seconds: int) -> bool:
        self.lock_calls.append((lock_name, holder, ttl_seconds))
        return not self.locked

    def release_job_lock(self, lock_name: str, holder: str) -> None:
        self.release_calls.append((lock_name, holder))

    def fetch_latest_report_run(self, run_type: str, scope_slug: str | None):
        return self.latest_runs.get((run_type, scope_slug))

    def fetch_profile_by_auth_user(self, auth_user_id: str):
        return {
            "profile_id": 1,
            "auth_user_id": auth_user_id,
            "slug": "scheduler-owner",
            "email": "owner@example.com",
        }


def test_scheduler_settings_get_defaults(monkeypatch):
    client = create_scheduler_test_client(monkeypatch, FakeSchedulerDB())

    response = client.get("/api/scheduler/settings")

    assert response.status_code == 200
    assert response.json() == {
        "daily_refresh_enabled": True,
        "weekly_precompute_enabled": False,
        "watchlist": "semiconductor-core",
        "include_news": True,
    }


def test_scheduler_settings_patch_updates_store(monkeypatch):
    fake_db = FakeSchedulerDB()
    client = create_scheduler_test_client(monkeypatch, fake_db)
    token = create_test_token("user-a", email="user-a@example.com")

    response = client.patch(
        "/api/scheduler/settings",
        headers={"Authorization": f"Bearer {token}"},
        json={"daily_refresh_enabled": False, "watchlist": "dev-watchlist", "include_news": False},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["daily_refresh_enabled"] is False
    assert body["watchlist"] == "dev-watchlist"
    assert body["include_news"] is False
    assert body["weekly_precompute_enabled"] is False
    assert fake_db.settings["watchlist"] == "dev-watchlist"


def test_scheduler_settings_patch_rejects_invalid_bool_payload(monkeypatch):
    client = create_scheduler_test_client(monkeypatch, FakeSchedulerDB())
    token = create_test_token("user-a", email="user-a@example.com")

    response = client.patch(
        "/api/scheduler/settings",
        headers={"Authorization": f"Bearer {token}"},
        json={"daily_refresh_enabled": 1},
    )

    assert response.status_code == 422


def test_scheduler_tick_runs_startup_refresh_with_request_flags(monkeypatch):
    fake_db = FakeSchedulerDB()
    client = create_scheduler_test_client(monkeypatch, fake_db)
    token = create_test_token("user-a", email="user-a@example.com")

    captured: dict[str, object] = {}

    class Result:
        status = "ok"
        watchlist = "semiconductor-core"
        dry_run = True
        locked = False
        queued = 1
        running = 0
        succeeded = 1
        failed = 0
        price_rows = 10
        indicator_rows = 10
        news_items = 2
        disclosures = 0
        provider_disabled = []
        failures = []
        report_run_id = "startup-1"
        stale = False
        last_success_at = datetime(2026, 6, 2, 1, 0, tzinfo=timezone.utc)

    def fake_run_startup_refresh(_store, **kwargs):
        captured.update(kwargs)
        return Result

    monkeypatch.setattr(local_scheduler, "run_startup_market_refresh", fake_run_startup_refresh)

    response = client.post(
        "/api/scheduler/tick?dry_run=true&no_network=true&include_news=false&force=true",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["daily"] == {
        "run_type": "startup-market-refresh",
        "status": "ok",
        "watchlist": "semiconductor-core",
        "dry_run": True,
        "locked": False,
        "queued": 1,
        "running": 0,
        "succeeded": 1,
        "failed": 0,
        "price_rows": 10,
        "indicator_rows": 10,
        "news_items": 2,
        "disclosures": 0,
        "provider_disabled": [],
        "failures": [],
        "report_run_id": "startup-1",
        "stale": False,
        "last_success_at": "2026-06-02T01:00:00+00:00",
    }
    assert captured["watchlist"] == "semiconductor-core"
    assert captured["dry_run"] is True
    assert captured["no_network"] is True
    assert captured["include_news"] is False
    assert captured["force"] is True


def test_scheduler_tick_returns_locked_status_when_scheduler_lock_taken(monkeypatch):
    fake_db = FakeSchedulerDB(locked=True)
    client = create_scheduler_test_client(monkeypatch, fake_db)
    token = create_test_token("user-a", email="user-a@example.com")

    def fail_if_called(**_kwargs):
        raise AssertionError("startup refresh should not be executed when scheduler lock is held")

    monkeypatch.setattr(local_scheduler, "run_startup_market_refresh", fail_if_called)

    response = client.post(
        "/api/scheduler/tick?force=true",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["daily"]["status"] == "skipped"
    assert body["daily"]["locked"] is True
    assert body["daily"]["reason"] == "scheduler already running"
    assert fake_db.release_calls == []


def test_scheduler_tick_releases_lock_after_startup_failure(monkeypatch):
    fake_db = FakeSchedulerDB()
    client = create_scheduler_test_client(monkeypatch, fake_db)
    token = create_test_token("user-a", email="user-a@example.com")

    def fail_startup(*_args, **_kwargs):
        raise RuntimeError("forced failure")

    monkeypatch.setattr(local_scheduler, "run_startup_market_refresh", fail_startup)

    response = client.post(
        "/api/scheduler/tick?no_network=true&force=true",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert (local_scheduler.DAILY_LOCK_NAME, "api-scheduler") in fake_db.release_calls


def test_startup_refresh_bootstraps_fallback_assets_in_fresh_sqlite(tmp_path):
    repo = SQLiteVBinvestDB(tmp_path / "vbinvest.sqlite3")

    result = run_startup_market_refresh(
        repo,
        watchlist="semiconductor-core",
        dry_run=False,
        no_network=True,
        include_news=False,
        limit=1,
        force=True,
    )

    assert result.status == "ok"
    assert result.price_rows > 0
    assert result.indicator_rows > 0
    with repo.connect() as conn:
        price_count = conn.execute("SELECT COUNT(*) FROM daily_prices").fetchone()[0]
        indicator_count = conn.execute("SELECT COUNT(*) FROM daily_indicators").fetchone()[0]
    assert price_count > 0
    assert indicator_count > 0


def test_local_scheduler_tick_cli_runs_with_fresh_sqlite_config(tmp_path):
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        "\n".join(
            [
                "first_run_completed = true",
                'language = "ko"',
                "",
                "[database]",
                'mode = "sqlite"',
                f'sqlite_path = "{tmp_path / "vbinvest.sqlite3"}"',
                'postgres_url = ""',
                "",
                "[obsidian]",
                f'vault_path = "{vault_dir}"',
                'export_mode = "direct"',
                "",
                "[providers]",
                'opendart_api_key = ""',
                'ai_provider_name = ""',
                'ai_base_url = ""',
                'ai_model = ""',
                "ai_context_size = 8192",
                'ai_api_key = ""',
                "",
                "[scheduler]",
                "daily_refresh_enabled = true",
                "weekly_precompute_enabled = false",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, "scripts/local_scheduler_tick.py", "--no-network", "--limit", "1"],
        cwd=Path(__file__).resolve().parents[1],
        env={"VBINVEST_CONFIG_PATH": str(config_path), **os.environ},
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["daily"]["status"] == "ok"
    assert payload["weekly"] == {"run_type": "weekly-precompute", "status": "skipped", "reason": "disabled"}
