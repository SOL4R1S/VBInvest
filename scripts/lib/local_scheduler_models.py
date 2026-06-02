from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

DAILY_LOCK_NAME = "local-scheduler:daily-refresh"
WEEKLY_LOCK_NAME = "local-scheduler:weekly-precompute"
LOCK_TTL_SECONDS = 3600
DEFAULT_WATCHLIST = "semiconductor-core"


class LocalSchedulerStore(Protocol):
    def try_acquire_job_lock(self, lock_name: str, holder: str, ttl_seconds: int) -> bool:
        ...

    def release_job_lock(self, lock_name: str, holder: str) -> None:
        ...

    def fetch_setting(self, key: str) -> str | None:
        ...

    def upsert_setting(self, key: str, value: str) -> None:
        ...

    def fetch_latest_report_run(self, run_type: str, scope_slug: str | None) -> dict[str, Any] | None:
        ...


@dataclass(frozen=True, slots=True)
class SchedulerSettings:
    daily_refresh_enabled: bool
    weekly_precompute_enabled: bool
    watchlist: str
    include_news: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "daily_refresh_enabled": self.daily_refresh_enabled,
            "weekly_precompute_enabled": self.weekly_precompute_enabled,
            "watchlist": self.watchlist,
            "include_news": self.include_news,
        }


@dataclass(frozen=True, slots=True)
class SchedulerJobSummary:
    run_type: str
    status: str | None = None
    completed_at: str | None = None
    scope_slug: str | None = None
    news_items: int = 0
    disclosures: int = 0
    provider_disabled: list[dict[str, Any]] | None = None
    reason: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "run_type": self.run_type,
            "status": self.status,
            "completed_at": self.completed_at,
            "scope_slug": self.scope_slug,
            "reason": self.reason,
            "news_items": self.news_items,
            "disclosures": self.disclosures,
            "provider_disabled": self.provider_disabled or [],
        }
