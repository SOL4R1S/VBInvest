from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.lib.config import ConfigError, load_opendart_api_key
from scripts.lib.config import serialize_report_run_summary
from scripts.lib.db import DatabaseConfig, VBinvestDB, build_indicator_rows, build_price_rows
from scripts.lib.disclosures import collect_disclosures_for_asset
from scripts.lib.indicators import add_indicators
from scripts.lib.market_calendar import summarize_trade_dates
from scripts.lib.news import collect_news_for_asset, dedupe_news_rows, prepare_news_rows
from scripts.lib.prices import PriceFetchError, fetch_price_history
from scripts.lib.watchlists import SEMICONDUCTOR_CORE, get_watchlist_symbols


KST = ZoneInfo("Asia/Seoul")


@dataclass(frozen=True)
class IngestOptions:
    no_network: bool = False
    synthetic: bool = False
    fetched_at: datetime | None = None
    max_attempts: int = 1
    retry_delay_seconds: float = 0.0
    job_name: str | None = None
    lock_holder: str = "vbinvest-ingest"
    lock_ttl_seconds: int = 3600
    include_news: bool = False
    dart_api_key: str | None = None


@dataclass(frozen=True)
class IngestResult:
    status: str
    failures: list[str]
    price_rows: int
    indicator_rows: int
    news_items: int = 0
    disclosures: int = 0
    provider_disabled: list[dict[str, str]] | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="VBinvest startup market refresh")
    parser.add_argument("--watchlist", default="semiconductor-core")
    parser.add_argument("--dry-run", action="store_true", help="do not write to the configured database")
    parser.add_argument("--no-network", action="store_true", help="skip live market data fetch")
    parser.add_argument("--synthetic", action="store_true", help="use deterministic sample prices")
    parser.add_argument("--limit", type=int, default=0, help="limit assets for smoke tests")
    parser.add_argument("--at-kst", help="override run time, e.g. 2026-06-01T17:00:00+09:00")
    parser.add_argument("--include-news", action="store_true", help="collect news and disclosure metadata")
    return parser.parse_args()


def fallback_assets(slug: str) -> list[dict]:
    if slug != "semiconductor-core":
        get_watchlist_symbols(slug)  # raises a clear ValueError
    return [dict(item, asset_id=i + 1) for i, item in enumerate(SEMICONDUCTOR_CORE)]


def load_assets(args: argparse.Namespace, db: VBinvestDB | None) -> list[dict]:
    if db is None:
        assets = fallback_assets(args.watchlist)
    else:
        assets = db.fetch_watchlist_assets(args.watchlist)
        if not assets:
            assets = fallback_assets(args.watchlist)
    return assets[: args.limit] if args.limit else assets


def parse_at_kst(value: str | None) -> datetime:
    if not value:
        return datetime.now(KST)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid --at-kst: {value}") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=KST)
    return parsed.astimezone(KST)


def ingest_assets(
    assets: list[dict],
    db: VBinvestDB | None,
    options: IngestOptions,
    *,
    fetch_history: Callable[[str], object] | None = None,
    news_collector=collect_news_for_asset,
    disclosure_collector=collect_disclosures_for_asset,
) -> IngestResult:
    failures: list[str] = []
    provider_disabled: list[dict[str, str]] = []
    price_rows = 0
    indicator_rows = 0
    news_items = 0
    disclosures = 0
    lock_acquired = False

    if db is not None and options.job_name:
        if not db.try_acquire_job_lock(options.job_name, options.lock_holder, options.lock_ttl_seconds):
            return IngestResult(
                status="locked",
                failures=[f"job-lock:{options.job_name}"],
                price_rows=0,
                indicator_rows=0,
                provider_disabled=[],
            )
        lock_acquired = True

    try:
        for asset in assets:
            symbol = asset["symbol"]
            try:
                prices = _fetch_for_asset(symbol, options, fetch_history)
                enriched = add_indicators(prices)
                built_prices = build_price_rows(asset["asset_id"], enriched, fetched_at=options.fetched_at)
                built_indicators = build_indicator_rows(asset["asset_id"], enriched)
                price_rows += len(built_prices)
                indicator_rows += len(built_indicators)
                if db is not None:
                    db.upsert_prices(built_prices)
                    db.upsert_indicators(built_indicators)
                if options.include_news:
                    news_result = news_collector(asset, no_network=options.no_network)
                    disclosure_result = disclosure_collector(
                        asset,
                        no_network=options.no_network,
                        dart_api_key=options.dart_api_key,
                    )
                    provider_disabled.extend(_provider_disabled(symbol, item) for item in news_result.provider_disabled)
                    provider_disabled.extend(_provider_disabled(symbol, item) for item in disclosure_result.provider_disabled)
                    if news_result.status == "failed":
                        failures.append(f"{symbol}:NewsFetchError")
                    if disclosure_result.status == "failed":
                        failures.append(f"{symbol}:DisclosureFetchError")
                    news_rows = dedupe_news_rows(prepare_news_rows(asset["asset_id"], news_result.items))
                    disclosure_rows = disclosure_result.items
                    news_items += len(news_rows)
                    disclosures += len(disclosure_rows)
                    if db is not None:
                        db.upsert_news_items(news_rows)
                        db.upsert_disclosures(disclosure_rows)
            except (PriceFetchError, RuntimeError, ValueError) as exc:
                failures.append(f"{symbol}:{type(exc).__name__}")
    finally:
        if lock_acquired and db is not None and options.job_name:
            db.release_job_lock(options.job_name, options.lock_holder)

    return IngestResult(
        status="partial" if failures else "ok",
        failures=failures,
        price_rows=price_rows,
        indicator_rows=indicator_rows,
        news_items=news_items,
        disclosures=disclosures,
        provider_disabled=provider_disabled,
    )


def _fetch_for_asset(symbol: str, options: IngestOptions, fetch_history: Callable[[str], object] | None):
    attempts = max(1, options.max_attempts)
    for attempt in range(1, attempts + 1):
        try:
            if fetch_history is None:
                return fetch_price_history(symbol, synthetic=options.synthetic, no_network=options.no_network)
            return fetch_history(symbol)
        except PriceFetchError as exc:
            if attempt >= attempts or not _is_retryable_price_error(exc):
                raise
            if options.retry_delay_seconds > 0:
                time.sleep(options.retry_delay_seconds * attempt)
    raise PriceFetchError(f"{symbol}: retry attempts exhausted")


def _is_retryable_price_error(exc: PriceFetchError) -> bool:
    message = str(exc).lower()
    return "429" in message or "rate limit" in message or "timeout" in message


def _provider_disabled(symbol: str, value: str) -> dict[str, str]:
    provider, separator, reason = value.partition(":")
    return {"symbol": symbol, "provider": provider, "reason": reason if separator else "disabled"}


def _format_provider_disabled(items: list[dict[str, str]] | None) -> str:
    if not items:
        return "none"
    return ",".join(f"{item['symbol']}:{item['provider']}:{item['reason']}" for item in items)


def main() -> int:
    args = parse_args()
    config = DatabaseConfig.from_env(os.environ)
    try:
        at_kst = parse_at_kst(args.at_kst)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    fetched_at = at_kst.astimezone(timezone.utc)
    now = fetched_at.isoformat(timespec="seconds")
    mode = "dry-run" if args.dry_run else "write"
    network = "disabled" if args.no_network else "enabled"

    db = None if args.dry_run else VBinvestDB(config)
    assets = load_assets(args, db)
    try:
        dart_api_key = load_opendart_api_key(environ=os.environ)
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    result = ingest_assets(
        assets,
        db,
        IngestOptions(
            no_network=args.no_network,
            synthetic=args.synthetic,
            fetched_at=fetched_at,
            max_attempts=2,
            retry_delay_seconds=0.5,
            job_name=None if args.dry_run else f"startup-market-refresh:{args.watchlist}",
            lock_holder=f"pid:{os.getpid()}",
            include_news=args.include_news,
            dart_api_key=dart_api_key,
        ),
    )

    summary = (
        f"assets={len(assets)} price_rows={result.price_rows} "
        f"indicator_rows={result.indicator_rows} failed={len(result.failures)}"
    )
    run_id = None
    if db is not None:
        run_id = db.record_report_run(
            run_type="startup-market-refresh",
            status=result.status,
            scope_slug=args.watchlist,
            failed_assets=result.failures,
            output_summary=serialize_report_run_summary(
                summary,
                {
                    "watchlist": args.watchlist,
                    "news_items": result.news_items,
                    "disclosures": result.disclosures,
                    "provider_disabled": result.provider_disabled or [],
                },
            ),
        )

    print("VBinvest startup market refresh")
    print(f"status={result.status} mode={mode} network={network} at={now}")
    print(
        f"watchlist={args.watchlist} assets={len(assets)} "
        f"price_rows={result.price_rows} indicator_rows={result.indicator_rows}"
    )
    print(f"trade_dates={summarize_trade_dates(assets, at_kst)}")
    print(
        f"news_items={result.news_items} disclosures={result.disclosures} "
        f"provider_disabled={_format_provider_disabled(result.provider_disabled)}"
    )
    print(f"db={config.safe_summary()}")
    print("failed=" + (",".join(result.failures) if result.failures else "none"))
    if run_id:
        print(f"report_run={run_id}")
    return 1 if result.failures and not args.dry_run else 0


if __name__ == "__main__":
    raise SystemExit(main())
