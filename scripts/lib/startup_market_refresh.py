from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

from scripts.startup_market_refresh import IngestOptions, fallback_assets, ingest_assets

try:
    from psycopg import OperationalError as PostgresOperationalError
except ImportError:
    PostgresOperationalError = RuntimeError

STALE_REFRESH_WINDOW = timedelta(minutes=30)


class StartupRefreshStore(Protocol):
    def fetch_watchlist_assets(self, slug: str) -> list[dict]:
        ...

    def record_report_run(self, **kwargs: object) -> str:
        ...


@dataclass(frozen=True)
class StartupRefreshResult:
    status: str
    watchlist: str
    dry_run: bool
    locked: bool
    price_rows: int
    indicator_rows: int
    news_items: int
    disclosures: int
    provider_disabled: list[dict[str, str]]
    failures: list[str]
    report_run_id: str | None
    stale: bool
    last_success_at: datetime | None


def run_startup_market_refresh(
    store: StartupRefreshStore | None,
    *,
    watchlist: str,
    dry_run: bool,
    no_network: bool,
    include_news: bool,
    limit: int,
    force: bool = False,
    lock_holder: str = "api-startup",
) -> StartupRefreshResult:
    effective_store = store
    try:
        assets = store.fetch_watchlist_assets(watchlist) if store is not None else fallback_assets(watchlist)
    except PostgresOperationalError:
        if not dry_run:
            raise
        effective_store = None
        assets = fallback_assets(watchlist)
    if not assets:
        assets = fallback_assets(watchlist)
    if limit > 0:
        assets = assets[:limit]

    last_success_at = _latest_success_at(effective_store, watchlist)
    if not force and _is_recent_success(last_success_at):
        report_run_id = _record_report_run(
            effective_store,
            status="skipped",
            watchlist=watchlist,
            assets=len(assets),
            dry_run=dry_run,
            price_rows=0,
            indicator_rows=0,
            news_items=0,
            disclosures=0,
            failures=[],
            stale=True,
        )
        return StartupRefreshResult(
            status="skipped",
            watchlist=watchlist,
            dry_run=dry_run,
            locked=False,
            stale=True,
            price_rows=0,
            indicator_rows=0,
            news_items=0,
            disclosures=0,
            provider_disabled=[],
            failures=[],
            report_run_id=report_run_id,
            last_success_at=last_success_at,
        )

    write_store = None if dry_run else effective_store
    result = ingest_assets(
        assets,
        write_store,
        IngestOptions(
            no_network=no_network,
            synthetic=no_network,
            fetched_at=datetime.now(timezone.utc),
            max_attempts=2,
            retry_delay_seconds=0.0,
            job_name=None if dry_run else f"startup-market-refresh:{watchlist}",
            lock_holder=lock_holder,
            include_news=include_news,
        ),
    )
    locked = result.status == "locked"
    status = "skipped" if locked else result.status
    report_run_id = _record_report_run(
        effective_store,
        status=status,
        watchlist=watchlist,
        assets=len(assets),
        dry_run=dry_run,
        price_rows=result.price_rows,
        indicator_rows=result.indicator_rows,
        news_items=result.news_items,
        disclosures=result.disclosures,
        failures=result.failures,
        stale=False,
    )
    return StartupRefreshResult(
        status=status,
        watchlist=watchlist,
        dry_run=dry_run,
        locked=locked,
        price_rows=result.price_rows,
        indicator_rows=result.indicator_rows,
        news_items=result.news_items,
        disclosures=result.disclosures,
        provider_disabled=result.provider_disabled or [],
        failures=result.failures,
        report_run_id=report_run_id,
        stale=False,
        last_success_at=last_success_at,
    )


def _latest_success_at(store: StartupRefreshStore | None, watchlist: str) -> datetime | None:
    if store is None:
        return None
    row = _fetch_latest_success_row(store, watchlist)
    if row is None:
        return None
    if isinstance(row, dict):
        return _coerce_datetime(row.get("completed_at"))
    if isinstance(row, tuple) and row:
        return _coerce_datetime(row[0])
    return None


def _fetch_latest_success_row(store: StartupRefreshStore, watchlist: str) -> Any | None:
    fetcher = getattr(store, "fetch_latest_successful_report_run", None)
    if callable(fetcher):
        return fetcher("startup-market-refresh", watchlist)
    connector = getattr(store, "connect", None)
    if not callable(connector):
        return None
    sql = """
    SELECT completed_at
    FROM report_runs
    WHERE run_type = %s AND scope_slug = %s AND status = 'ok' AND completed_at IS NOT NULL
    ORDER BY completed_at DESC
    LIMIT 1
    """
    with connector() as conn, conn.cursor() as cur:
        cur.execute(sql, ("startup-market-refresh", watchlist))
        return cur.fetchone()


def _coerce_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        return _coerce_datetime(parsed)
    return None


def _is_recent_success(last_success_at: datetime | None) -> bool:
    if last_success_at is None:
        return False
    return datetime.now(timezone.utc) - last_success_at <= STALE_REFRESH_WINDOW


def _record_report_run(
    store: StartupRefreshStore | None,
    *,
    status: str,
    watchlist: str,
    assets: int,
    dry_run: bool,
    price_rows: int,
    indicator_rows: int,
    news_items: int,
    disclosures: int,
    failures: list[str],
    stale: bool,
) -> str | None:
    if store is None:
        return None
    return store.record_report_run(
        run_type="startup-market-refresh",
        status=status,
        scope_slug=watchlist,
        failed_assets=failures,
        output_summary=(
            f"dry_run={dry_run} stale={stale} assets={assets} price_rows={price_rows} "
            f"indicator_rows={indicator_rows} news_items={news_items} disclosures={disclosures}"
        ),
    )
