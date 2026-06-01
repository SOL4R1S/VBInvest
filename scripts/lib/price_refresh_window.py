from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import pandas as pd

INITIAL_BACKFILL_DAYS = 260
INDICATOR_LOOKBACK_DAYS = 180


@dataclass(frozen=True)
class PriceRefreshWindow:
    fetch_start: date
    persist_start: date
    end: date


def run_date_from_fetched_at(fetched_at: datetime | None) -> date:
    instant = fetched_at if fetched_at is not None else datetime.now(timezone.utc)
    return instant.date()


def build_price_refresh_windows(assets: list[dict], db, run_date: date) -> dict[int, PriceRefreshWindow]:
    asset_ids = [int(asset["asset_id"]) for asset in assets]
    latest_dates = fetch_latest_price_dates(db, asset_ids)
    return {
        asset_id: price_refresh_window(latest_dates.get(asset_id), run_date)
        for asset_id in asset_ids
    }


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


def price_refresh_window(latest_date: date | None, run_date: date) -> PriceRefreshWindow:
    if latest_date is None:
        start = run_date - timedelta(days=INITIAL_BACKFILL_DAYS)
        return PriceRefreshWindow(fetch_start=start, persist_start=start, end=run_date)
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
