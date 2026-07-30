"""Tests for scripts.lib.local_scheduler_models — dataclass models."""

from scripts.lib.local_scheduler_models import (
    DAILY_LOCK_NAME,
    DEFAULT_WATCHLIST,
    LOCK_TTL_SECONDS,
    WEEKLY_LOCK_NAME,
    SchedulerJobSummary,
    SchedulerSettings,
)


def test_constants():
    assert DAILY_LOCK_NAME == "local-scheduler:daily-refresh"
    assert WEEKLY_LOCK_NAME == "local-scheduler:weekly-precompute"
    assert LOCK_TTL_SECONDS == 3600
    assert DEFAULT_WATCHLIST == "semiconductor-core"


def test_scheduler_settings_as_dict():
    settings = SchedulerSettings(
        daily_refresh_enabled=True,
        weekly_precompute_enabled=False,
        watchlist="semiconductor-core",
        include_news=True,
    )
    d = settings.as_dict()
    assert d["daily_refresh_enabled"] is True
    assert d["weekly_precompute_enabled"] is False
    assert d["watchlist"] == "semiconductor-core"
    assert d["include_news"] is True


def test_scheduler_settings_frozen():
    settings = SchedulerSettings(
        daily_refresh_enabled=True,
        weekly_precompute_enabled=True,
        watchlist="test",
        include_news=False,
    )
    try:
        settings.daily_refresh_enabled = False  # type: ignore[misc]
        assert False, "Should have raised"
    except AttributeError:
        pass


def test_scheduler_job_summary_as_dict():
    summary = SchedulerJobSummary(
        run_type="daily-refresh",
        status="completed",
        completed_at="2026-01-01T00:00:00Z",
        scope_slug="semiconductor-core",
        news_items=5,
        disclosures=2,
    )
    d = summary.as_dict()
    assert d["run_type"] == "daily-refresh"
    assert d["status"] == "completed"
    assert d["news_items"] == 5
    assert d["disclosures"] == 2
    assert d["provider_disabled"] == []


def test_scheduler_job_summary_defaults():
    summary = SchedulerJobSummary(run_type="weekly-precompute")
    d = summary.as_dict()
    assert d["status"] is None
    assert d["completed_at"] is None
    assert d["news_items"] == 0
    assert d["provider_disabled"] == []
