from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from scripts.startup_market_refresh import IngestOptions, fallback_assets, ingest_assets


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
    failures: list[str]
    report_run_id: str | None


def run_startup_market_refresh(
    store: StartupRefreshStore | None,
    *,
    watchlist: str,
    dry_run: bool,
    no_network: bool,
    include_news: bool,
    limit: int,
    lock_holder: str = "api-startup",
) -> StartupRefreshResult:
    assets = store.fetch_watchlist_assets(watchlist) if store is not None else fallback_assets(watchlist)
    if not assets:
        assets = fallback_assets(watchlist)
    if limit > 0:
        assets = assets[:limit]

    write_store = None if dry_run else store
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
    report_run_id = None
    if store is not None:
        report_run_id = store.record_report_run(
            run_type="startup-market-refresh",
            status=status,
            scope_slug=watchlist,
            failed_assets=result.failures,
            output_summary=(
                f"dry_run={dry_run} assets={len(assets)} price_rows={result.price_rows} "
                f"indicator_rows={result.indicator_rows} news_items={result.news_items} "
                f"disclosures={result.disclosures}"
            ),
        )
    return StartupRefreshResult(
        status=status,
        watchlist=watchlist,
        dry_run=dry_run,
        locked=locked,
        price_rows=result.price_rows,
        indicator_rows=result.indicator_rows,
        failures=result.failures,
        report_run_id=report_run_id,
    )
