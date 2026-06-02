from __future__ import annotations

from datetime import datetime
from typing import Any

from scripts.lib.config import parse_report_run_summary
from scripts.lib.local_scheduler_models import (
    DAILY_LOCK_NAME,
    DEFAULT_WATCHLIST,
    LOCK_TTL_SECONDS,
    LocalSchedulerStore,
    SchedulerJobSummary,
    SchedulerSettings,
)
from scripts.lib.startup_market_refresh import run_startup_market_refresh


class LocalScheduler:
    def __init__(self, store: LocalSchedulerStore):
        self._store = store
        self._running = False
        self._last_tick_status: str | None = None

    def status(self) -> dict[str, Any]:
        settings = self._load_settings()
        daily = self._fetch_latest_run("startup-market-refresh", settings.watchlist)
        weekly = self._fetch_latest_run("weekly-precompute", settings.watchlist)
        return {
            "running": self._running,
            "last_tick_status": self._last_tick_status,
            **settings.as_dict(),
            "daily": daily.as_dict() if daily else {"run_type": "startup-market-refresh"},
            "weekly": weekly.as_dict() if weekly else {"run_type": "weekly-precompute"},
        }

    def get_settings(self) -> SchedulerSettings:
        return self._load_settings()

    def patch_settings(
        self,
        *,
        daily_refresh_enabled: bool | None = None,
        weekly_precompute_enabled: bool | None = None,
        watchlist: str | None = None,
        include_news: bool | None = None,
    ) -> SchedulerSettings:
        self._ensure_defaults()

        if daily_refresh_enabled is not None:
            self._store.upsert_setting("daily_refresh_enabled", _bool_value(daily_refresh_enabled))
        if weekly_precompute_enabled is not None:
            self._store.upsert_setting("weekly_precompute_enabled", _bool_value(weekly_precompute_enabled))
        if watchlist is not None:
            trimmed = watchlist.strip()
            self._store.upsert_setting("watchlist", trimmed if trimmed else DEFAULT_WATCHLIST)
        if include_news is not None:
            self._store.upsert_setting("include_news", _bool_value(include_news))

        self._ensure_defaults()
        return self._load_settings()

    def tick(
        self,
        *,
        dry_run: bool = False,
        no_network: bool = False,
        include_news: bool = True,
        limit: int = 0,
        force: bool = False,
        lock_holder: str = "api-scheduler",
        dart_api_key: str | None = None,
    ) -> dict[str, Any]:
        self._ensure_defaults()
        settings = self._load_settings()
        if not self._running:
            self._running = True
        try:
            self._last_tick_status = "running"
            daily = self._tick_daily(
                settings=settings,
                dry_run=dry_run,
                no_network=no_network,
                include_news=include_news,
                limit=limit,
                force=force,
                lock_holder=lock_holder,
                dart_api_key=dart_api_key,
            )
            weekly = self._tick_weekly(settings)
            self._last_tick_status = (daily.get("status") or "ok")
            return {
                "running": False,
                "last_tick_status": self._last_tick_status,
                "daily": daily,
                "weekly": weekly,
            }
        finally:
            self._running = False

    def _tick_daily(
        self,
        *,
        settings: SchedulerSettings,
        dry_run: bool,
        no_network: bool,
        include_news: bool,
        limit: int,
        force: bool,
        lock_holder: str,
        dart_api_key: str | None,
    ) -> dict[str, Any]:
        if not settings.daily_refresh_enabled:
            return {"run_type": "startup-market-refresh", "status": "skipped", "reason": "daily refresh disabled"}
        if not self._store.try_acquire_job_lock(DAILY_LOCK_NAME, lock_holder, LOCK_TTL_SECONDS):
            return {"run_type": "startup-market-refresh", "status": "skipped", "locked": True, "reason": "scheduler already running"}
        try:
            result = run_startup_market_refresh(
                self._store,
                watchlist=settings.watchlist,
                dry_run=dry_run,
                no_network=no_network,
                include_news=include_news,
                limit=limit,
                force=force,
                lock_holder=lock_holder,
                dart_api_key=dart_api_key,
            )
            return {
                "run_type": "startup-market-refresh",
                "status": result.status,
                "watchlist": result.watchlist,
                "dry_run": result.dry_run,
                "locked": result.locked,
                "queued": result.queued,
                "running": result.running,
                "succeeded": result.succeeded,
                "failed": result.failed,
                "price_rows": result.price_rows,
                "indicator_rows": result.indicator_rows,
                "news_items": result.news_items,
                "disclosures": result.disclosures,
                "provider_disabled": result.provider_disabled,
                "failures": result.failures,
                "report_run_id": result.report_run_id,
                "stale": result.stale,
                "last_success_at": _coerce_last_success_at(result.last_success_at),
            }
        finally:
            self._store.release_job_lock(DAILY_LOCK_NAME, lock_holder)

    def _tick_weekly(self, settings: SchedulerSettings) -> dict[str, Any]:
        if not settings.weekly_precompute_enabled:
            return {"run_type": "weekly-precompute", "status": "skipped", "reason": "disabled"}
        return {"run_type": "weekly-precompute", "status": "skipped", "reason": "not implemented"}

    def _load_settings(self) -> SchedulerSettings:
        self._ensure_defaults()
        return SchedulerSettings(
            daily_refresh_enabled=_coerce_bool(
                self._store.fetch_setting("daily_refresh_enabled"),
                True,
            ),
            weekly_precompute_enabled=_coerce_bool(
                self._store.fetch_setting("weekly_precompute_enabled"),
                False,
            ),
            watchlist=_coerce_watchlist(
                self._store.fetch_setting("watchlist"),
            ),
            include_news=_coerce_bool(
                self._store.fetch_setting("include_news"),
                True,
            ),
        )

    def _fetch_latest_run(self, run_type: str, scope_slug: str | None) -> SchedulerJobSummary | None:
        row = self._store.fetch_latest_report_run(run_type, scope_slug)
        if row is None:
            return None
        completed_at = row.get("completed_at") if isinstance(row, dict) else None
        if isinstance(completed_at, datetime):
            completed_at = completed_at.isoformat()
        output_summary = row.get("output_summary") if isinstance(row, dict) and isinstance(row.get("output_summary"), str) else ""
        summary = parse_report_run_summary(output_summary)
        return SchedulerJobSummary(
            run_type=run_type,
            status=row.get("status", "") if isinstance(row.get("status"), str) else None,
            completed_at=completed_at if isinstance(completed_at, str) else None,
            scope_slug=row.get("scope_slug") if isinstance(row.get("scope_slug"), str) else scope_slug,
            news_items=_coerce_int(summary.get("news_items"), 0),
            disclosures=_coerce_int(summary.get("disclosures"), 0),
            provider_disabled=summary.get("provider_disabled") if isinstance(summary.get("provider_disabled"), list) else None,
            reason=row.get("error_message") if isinstance(row.get("error_message"), str) else None,
        )

    def _ensure_defaults(self) -> None:
        defaults = {
            "daily_refresh_enabled": "true",
            "weekly_precompute_enabled": "false",
            "watchlist": DEFAULT_WATCHLIST,
            "include_news": "true",
        }
        for key, value in defaults.items():
            if self._store.fetch_setting(key) is None:
                self._store.upsert_setting(key, value)


def _coerce_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    normalized = str(value).strip().lower()
    return normalized in {"1", "true", "yes", "on"}


def _coerce_int(value: object, default: int) -> int:
    if isinstance(value, int):
        return value
    return default


def _coerce_watchlist(value: str | None) -> str:
    if not value:
        return DEFAULT_WATCHLIST
    trimmed = value.strip()
    return trimmed or DEFAULT_WATCHLIST


def _coerce_last_success_at(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _bool_value(value: bool) -> str:
    return "true" if value else "false"
