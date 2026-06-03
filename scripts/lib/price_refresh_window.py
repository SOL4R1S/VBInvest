from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import pandas as pd

INITIAL_BACKFILL_DAYS = 365 * 5
INDICATOR_LOOKBACK_DAYS = 180


@dataclass(frozen=True)
class PriceRefreshWindow:
    fetch_start: date
    persist_start: date
    end: date


@dataclass(frozen=True)
class PriceDateRange:
    earliest_date: date
    latest_date: date


def run_date_from_fetched_at(fetched_at: datetime | None) -> date:
    instant = fetched_at if fetched_at is not None else datetime.now(timezone.utc)
    return instant.date()


def build_price_refresh_windows(assets: list[dict], db, run_date: date) -> dict[int, PriceRefreshWindow]:
    asset_ids = [int(asset["asset_id"]) for asset in assets]
    price_ranges = fetch_price_date_ranges(db, asset_ids)
    latest_dates = fetch_latest_price_dates(db, asset_ids)
    return {
        asset_id: price_refresh_window(
            price_ranges.get(asset_id).latest_date if asset_id in price_ranges else latest_dates.get(asset_id),
            run_date,
            earliest_date=price_ranges.get(asset_id).earliest_date if asset_id in price_ranges else None,
        )
        for asset_id in asset_ids
    }


def fetch_price_date_ranges(db, asset_ids: list[int]) -> dict[int, PriceDateRange]:
    if not asset_ids:
        return {}
    if hasattr(db, "fetch_price_date_ranges"):
        raw_ranges = db.fetch_price_date_ranges(asset_ids)
        ranges: dict[int, PriceDateRange] = {}
        for asset_id, value in raw_ranges.items():
            earliest = value.get("earliest_date") if isinstance(value, dict) else getattr(value, "earliest_date", None)
            latest = value.get("latest_date") if isinstance(value, dict) else getattr(value, "latest_date", None)
            if earliest is not None and latest is not None:
                ranges[int(asset_id)] = PriceDateRange(earliest_date=earliest, latest_date=latest)
        return ranges
    return {}


def fetch_latest_price_dates(db, asset_ids: list[int]) -> dict[int, date]:
    if not asset_ids:
        return {}
    if hasattr(db, "fetch_latest_price_dates"):
        latest_dates = db.fetch_latest_price_dates(asset_ids)
        return {int(asset_id): value for asset_id, value in latest_dates.items() if value is not None}
    if not hasattr(db, "connect"):
        return {}
    placeholders = ",".join(["%s"] * len(asset_ids))
    query = (
        "SELECT asset_id, max(date) AS latest_date "
        f"FROM daily_prices WHERE asset_id IN ({placeholders}) GROUP BY asset_id"
    )
    with db.connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, asset_ids)
            rows = cursor.fetchall()
    return {int(asset_id): latest_date for asset_id, latest_date in rows if latest_date is not None}


def price_refresh_window(latest_date: date | None, run_date: date, *, earliest_date: date | None = None) -> PriceRefreshWindow:
    backfill_start = run_date - timedelta(days=INITIAL_BACKFILL_DAYS)
    if latest_date is None:
        return PriceRefreshWindow(fetch_start=backfill_start, persist_start=backfill_start, end=run_date)
    if earliest_date is not None and earliest_date > backfill_start:
        return PriceRefreshWindow(fetch_start=backfill_start, persist_start=backfill_start, end=run_date)
    persist_start = latest_date + timedelta(days=1)
    fetch_start = persist_start - timedelta(days=INDICATOR_LOOKBACK_DAYS)
    return PriceRefreshWindow(fetch_start=fetch_start, persist_start=persist_start, end=run_date)


def filter_history_for_persistence(frame: pd.DataFrame, window: PriceRefreshWindow | None) -> pd.DataFrame:
    if window is None or frame.empty:
        return frame
    normalized = frame.copy()
    normalized["date"] = pd.to_datetime(normalized["date"]).dt.date
    mask = (normalized["date"] >= window.persist_start) & (normalized["date"] <= window.end)
    return normalized.loc[mask].reset_index(drop=True)
