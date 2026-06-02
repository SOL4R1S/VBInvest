from __future__ import annotations

from dataclasses import dataclass

import pytest

from scripts.lib import local_scheduler
from scripts.lib.local_scheduler import DAILY_LOCK_NAME, LocalScheduler


@dataclass
class FakeRefreshResult:
    status: str
    watchlist: str = "semiconductor-core"
    dry_run: bool = False
    locked: bool = False
    queued: int = 0
    running: int = 0
    succeeded: int = 1
    failed: int = 0
    stale: bool = False
    price_rows: int = 2
    indicator_rows: int = 2
    news_items: int = 0
    disclosures: int = 0
    provider_disabled: list[dict[str, str]] | None = None
    failures: list[str] | None = None
    report_run_id: str | None = "run-1"
    last_success_at: str | None = None


class FakeSchedulerStore:
    def __init__(self, *, locked: bool = False) -> None:
        self.locked = locked
        self.settings: dict[str, str] = {}
        self.lock_calls: list[tuple[str, str, int]] = []
        self.release_calls: list[tuple[str, str]] = []
        self.latest_runs: dict[tuple[str, str | None], dict[str, object]] = {}

    def try_acquire_job_lock(self, lock_name: str, holder: str, ttl_seconds: int) -> bool:
        self.lock_calls.append((lock_name, holder, ttl_seconds))
        return not self.locked

    def release_job_lock(self, lock_name: str, holder: str) -> None:
        self.release_calls.append((lock_name, holder))

    def fetch_setting(self, key: str) -> str | None:
        return self.settings.get(key)

    def upsert_setting(self, key: str, value: str) -> None:
        self.settings[key] = value

    def fetch_latest_report_run(self, run_type: str, scope_slug: str | None) -> dict[str, object] | None:
        return self.latest_runs.get((run_type, scope_slug))


def test_scheduler_skips_weekly_precompute_when_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    store = FakeSchedulerStore()

    def fake_refresh(*args: object, **kwargs: object) -> FakeRefreshResult:
        return FakeRefreshResult(status="ok")

    monkeypatch.setattr(local_scheduler, "run_startup_market_refresh", fake_refresh)

    result = LocalScheduler(store).tick(no_network=True, include_news=False)

    assert result["daily"]["status"] == "ok"
    assert result["running"] is False
    assert result["weekly"] == {"run_type": "weekly-precompute", "status": "skipped", "reason": "disabled"}
    assert store.lock_calls == [(DAILY_LOCK_NAME, "api-scheduler", 3600)]


def test_scheduler_does_not_overlap_duplicate_daily_job(monkeypatch: pytest.MonkeyPatch) -> None:
    store = FakeSchedulerStore(locked=True)

    def fake_refresh(*args: object, **kwargs: object) -> FakeRefreshResult:
        raise AssertionError("daily refresh must not start while scheduler lock is held")

    monkeypatch.setattr(local_scheduler, "run_startup_market_refresh", fake_refresh)

    result = LocalScheduler(store).tick(no_network=True, include_news=False)

    assert result["daily"]["status"] == "skipped"
    assert result["daily"]["locked"] is True
    assert store.release_calls == []


def test_scheduler_releases_lock_after_failed_job_and_allows_next_tick(monkeypatch: pytest.MonkeyPatch) -> None:
    store = FakeSchedulerStore()
    calls: list[str] = []

    def fake_refresh(*args: object, **kwargs: object) -> FakeRefreshResult:
        calls.append("refresh")
        if len(calls) == 1:
            raise ValueError("forced refresh failure")
        return FakeRefreshResult(status="ok")

    monkeypatch.setattr(local_scheduler, "run_startup_market_refresh", fake_refresh)
    scheduler = LocalScheduler(store)

    with pytest.raises(ValueError, match="forced refresh failure"):
        scheduler.tick(no_network=True, include_news=False)

    result = scheduler.tick(no_network=True, include_news=False)

    assert result["daily"]["status"] == "ok"
    assert calls == ["refresh", "refresh"]
    assert store.release_calls == [
        (DAILY_LOCK_NAME, "api-scheduler"),
        (DAILY_LOCK_NAME, "api-scheduler"),
    ]


def test_scheduler_patch_settings_persists_weekly_precompute_enabled() -> None:
    store = FakeSchedulerStore()
    scheduler = LocalScheduler(store)

    updated = scheduler.patch_settings(weekly_precompute_enabled=True)

    assert updated.weekly_precompute_enabled is True
    assert store.settings["weekly_precompute_enabled"] == "true"
