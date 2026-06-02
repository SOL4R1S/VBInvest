from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Protocol

from scripts.startup_market_refresh import (
    IngestOptions,
    fallback_assets,
    ingest_assets,
)
from scripts.lib.config import serialize_report_run_summary
from scripts.lib.price_refresh_window import fetch_latest_price_dates
from scripts.lib.market_calendar import KST, completed_trade_date

try:
    from psycopg import OperationalError as PostgresOperationalError
except ImportError:
    PostgresOperationalError = RuntimeError

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
    queued: int
    running: int
    succeeded: int
    failed: int
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
    dart_api_key: str | None = None,
) -> StartupRefreshResult:
    effective_store = store
    try:
        watchlist_assets = (
            store.fetch_watchlist_assets(watchlist) if store is not None else fallback_assets(watchlist)
        )
    except PostgresOperationalError:
        if not dry_run:
            raise
        effective_store = None
        watchlist_assets = fallback_assets(watchlist)
    assets = _combine_assets(
        watchlist_assets if watchlist_assets else fallback_assets(watchlist),
        _portfolio_holdings_assets(effective_store),
    )
    if not assets:
        assets = fallback_assets(watchlist)
    assets = _ensure_assets_for_store(effective_store, assets)
    if limit > 0:
        assets = assets[:limit]
    asset_count = len(assets)
    queued = running = 0

    def compute_counts(
        status: str,
        failures: list[str],
        provider_disabled: list[dict[str, str]],
    ) -> tuple[int, int, int, int]:
        if status in {"locked", "skipped"}:
            return (0, 0, 0, 0)
        if status == "partial":
            failed = len(failures) + len(provider_disabled)
            succeeded = max(asset_count - failed, 0)
            return (0, 0, succeeded, failed)
        return (0, 0, asset_count, 0)

    last_success_at = _latest_success_at(effective_store, watchlist)
    if not force and _are_all_assets_fresh(effective_store, assets):
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
            stale=False,
            provider_disabled=[],
        )
        return StartupRefreshResult(
            status="skipped",
            watchlist=watchlist,
            dry_run=dry_run,
            locked=False,
            queued=queued,
            running=running,
            succeeded=0,
            failed=0,
            stale=False,
            price_rows=0,
            indicator_rows=0,
            news_items=0,
            disclosures=0,
            provider_disabled=[],
            failures=[],
            report_run_id=report_run_id,
            last_success_at=last_success_at,
        )
    if not force and _is_recent_success(last_success_at, assets):
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
            provider_disabled=[],
        )
        return StartupRefreshResult(
            status="skipped",
            watchlist=watchlist,
            dry_run=dry_run,
            locked=False,
            queued=queued,
            running=running,
            succeeded=0,
            failed=0,
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
            dart_api_key=dart_api_key,
        ),
    )
    locked = result.status == "locked"
    status = "skipped" if locked else result.status
    queued, running, succeeded, failed = compute_counts(
        status=status,
        failures=result.failures,
        provider_disabled=result.provider_disabled or [],
    )
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
        provider_disabled=result.provider_disabled or [],
    )
    return StartupRefreshResult(
        status=status,
        watchlist=watchlist,
        dry_run=dry_run,
        locked=locked,
        queued=queued,
        running=running,
        succeeded=succeeded,
        failed=failed,
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


def _ensure_assets_for_store(store: StartupRefreshStore | None, assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if store is None:
        return assets
    ensureer = getattr(store, "ensure_assets_for_refresh", None)
    if not callable(ensureer):
        return assets
    return ensureer(assets)


def _are_all_assets_fresh(store: StartupRefreshStore | None, assets: list[dict]) -> bool:
    if store is None:
        return False
    assets_with_id = [_parse_asset_with_asset_id(asset) for asset in assets]
    if any(asset is None for asset in assets_with_id):
        return False
    assets_with_id = [asset for asset in assets_with_id if asset is not None]
    if not assets_with_id:
        return False
    latest_dates = fetch_latest_price_dates(store, [int(asset["asset_id"]) for asset in assets_with_id])
    if not latest_dates:
        return False
    now = datetime.now(timezone.utc)
    return all(
        latest_dates.get(int(asset["asset_id"])) is not None
        and latest_dates[int(asset["asset_id"])] >= _trade_date_for_asset(asset, now)
        for asset in assets_with_id
    )


def _is_recent_success(last_success_at: datetime | None, assets: list[dict], now: datetime | None = None) -> bool:
    if last_success_at is None:
        return False
    if not assets:
        return False
    last_run_at = _coerce_datetime(last_success_at)
    if last_run_at is None:
        return False
    if now is None:
        now = datetime.now(timezone.utc)
    latest_trade_date = _latest_trade_date(assets, now)
    if latest_trade_date is None:
        return False
    return last_run_at.astimezone(KST).date() >= latest_trade_date


def _latest_trade_date(assets: list[dict], now: datetime) -> date | None:
    family_dates = {_trade_date_for_asset(asset, now) for asset in assets}
    return None if not family_dates else max(family_dates)


def _trade_date_for_asset(asset: dict, now: datetime):
    if now.tzinfo is None:
        now_kst = now.replace(tzinfo=KST)
    else:
        now_kst = now.astimezone(KST)
    return completed_trade_date(asset.get("exchange"), now_kst)


def _combine_assets(watchlist_assets: list[dict], portfolio_assets: list[dict]) -> list[dict]:
    merged: list[dict] = []
    seen = set()
    for asset in watchlist_assets + portfolio_assets:
        key = _asset_identity(asset)
        if key is None:
            continue
        if key in seen:
            continue
        seen.add(key)
        merged.append(asset)
    return merged


def _portfolio_holdings_assets(store: StartupRefreshStore | None) -> list[dict]:
    if store is None:
        return []
    for method_name in ("list_portfolio_holdings", "list_all_portfolio_holdings", "list_user_portfolio_holdings"):
        method = getattr(store, method_name, None)
        if callable(method):
            try:
                return list(method())
            except TypeError:
                continue
            except (AttributeError, ValueError):
                continue
    return []


def _asset_identity(asset: dict) -> tuple[str, int | str] | None:
    try:
        asset_id = int(asset["asset_id"])
        return ("asset_id", asset_id)
    except (TypeError, KeyError, ValueError):
        symbol = asset.get("symbol")
        if not isinstance(symbol, str):
            return None
        return ("symbol", symbol.upper())


def _parse_asset_with_asset_id(asset: dict) -> dict | None:
    if not isinstance(asset, dict):
        return None
    try:
        asset_id = int(asset["asset_id"])
    except (KeyError, TypeError, ValueError):
        return None
    return {
        "asset_id": asset_id,
        "symbol": asset.get("symbol"),
        "display_name_ko": asset.get("display_name_ko"),
        "exchange": asset.get("exchange"),
        "currency": asset.get("currency"),
    }


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
    provider_disabled: list[dict[str, str]],
) -> str | None:
    if store is None:
        return None
    return store.record_report_run(
        run_type="startup-market-refresh",
        status=status,
        scope_slug=watchlist,
        failed_assets=failures,
        output_summary=serialize_report_run_summary(
            (
                f"dry_run={dry_run} stale={stale} assets={assets} price_rows={price_rows} "
                f"indicator_rows={indicator_rows} news_items={news_items} disclosures={disclosures}"
            ),
            {
                "watchlist": watchlist,
                "news_items": news_items,
                "disclosures": disclosures,
                "provider_disabled": provider_disabled,
            },
        ),
    )
