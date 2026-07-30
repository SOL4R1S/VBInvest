"""Integration tests for SQLiteMarketMixin — prices, indicators, job locks, dashboard."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from scripts.lib.db_sqlite import SQLiteVBinvestDB


@pytest.fixture()
def db(tmp_path: Path) -> SQLiteVBinvestDB:
    return SQLiteVBinvestDB(tmp_path / "test.db")


@pytest.fixture()
def asset_id(db: SQLiteVBinvestDB) -> int:
    assets = db.ensure_assets_for_refresh([{"symbol": "AAPL", "display_name_ko": "애플"}])
    return assets[0]["asset_id"]


class TestUpsertPrices:
    def test_empty(self, db: SQLiteVBinvestDB):
        assert db.upsert_prices([]) == 0

    def test_insert_and_count(self, db: SQLiteVBinvestDB, asset_id: int):
        rows = [
            {
                "asset_id": asset_id,
                "date": "2026-01-15",
                "open": 100,
                "high": 110,
                "low": 95,
                "close": 105,
                "volume": 1000,
                "fetched_at": "2026-01-15T10:00:00Z",
            },
            {
                "asset_id": asset_id,
                "date": "2026-01-16",
                "open": 105,
                "high": 115,
                "low": 100,
                "close": 112,
                "volume": 1200,
                "fetched_at": "2026-01-16T10:00:00Z",
            },
        ]
        assert db.upsert_prices(rows) == 2

    def test_upsert_overwrites(self, db: SQLiteVBinvestDB, asset_id: int):
        row = {
            "asset_id": asset_id,
            "date": "2026-01-15",
            "open": 100,
            "high": 110,
            "low": 95,
            "close": 105,
            "volume": 1000,
            "fetched_at": "2026-01-15T10:00:00Z",
        }
        db.upsert_prices([row])
        updated = {**row, "close": 999}
        db.upsert_prices([updated])
        dates = db.fetch_latest_price_dates([asset_id])
        assert dates[asset_id] == date(2026, 1, 15)


class TestUpsertIndicators:
    def test_empty(self, db: SQLiteVBinvestDB):
        assert db.upsert_indicators([]) == 0

    def test_insert(self, db: SQLiteVBinvestDB, asset_id: int):
        rows = [
            {"asset_id": asset_id, "date": "2026-01-15", "ma5": 103.0, "ma20": 101.0, "rsi14": 55.0},
        ]
        assert db.upsert_indicators(rows) == 1


class TestJobLocks:
    def test_acquire_new(self, db: SQLiteVBinvestDB):
        assert db.try_acquire_job_lock("test-lock", "holder-a", 60) is True

    def test_acquire_same_holder(self, db: SQLiteVBinvestDB):
        db.try_acquire_job_lock("test-lock", "holder-a", 60)
        assert db.try_acquire_job_lock("test-lock", "holder-a", 60) is True

    def test_acquire_different_holder_blocked(self, db: SQLiteVBinvestDB):
        db.try_acquire_job_lock("test-lock", "holder-a", 3600)
        assert db.try_acquire_job_lock("test-lock", "holder-b", 3600) is False

    def test_release(self, db: SQLiteVBinvestDB):
        db.try_acquire_job_lock("test-lock", "holder-a", 60)
        db.release_job_lock("test-lock", "holder-a")
        assert db.try_acquire_job_lock("test-lock", "holder-b", 60) is True


class TestPriceDateQueries:
    def test_latest_price_dates_empty(self, db: SQLiteVBinvestDB):
        assert db.fetch_latest_price_dates([]) == {}

    def test_latest_price_dates(self, db: SQLiteVBinvestDB, asset_id: int):
        db.upsert_prices(
            [
                {"asset_id": asset_id, "date": "2026-01-10", "close": 100, "fetched_at": "2026-01-10T10:00:00Z"},
                {"asset_id": asset_id, "date": "2026-01-15", "close": 105, "fetched_at": "2026-01-15T10:00:00Z"},
            ]
        )
        result = db.fetch_latest_price_dates([asset_id])
        assert result[asset_id] == date(2026, 1, 15)

    def test_price_date_ranges_empty(self, db: SQLiteVBinvestDB):
        assert db.fetch_price_date_ranges([]) == {}

    def test_price_date_ranges(self, db: SQLiteVBinvestDB, asset_id: int):
        db.upsert_prices(
            [
                {"asset_id": asset_id, "date": "2026-01-10", "close": 100, "fetched_at": "2026-01-10T10:00:00Z"},
                {"asset_id": asset_id, "date": "2026-01-15", "close": 105, "fetched_at": "2026-01-15T10:00:00Z"},
            ]
        )
        result = db.fetch_price_date_ranges([asset_id])
        assert result[asset_id]["earliest_date"] == date(2026, 1, 10)
        assert result[asset_id]["latest_date"] == date(2026, 1, 15)


class TestCollectionStatus:
    def test_status_collected(self, db: SQLiteVBinvestDB):
        assert db._collection_status(100, False) == "collected"

    def test_status_partial(self, db: SQLiteVBinvestDB):
        assert db._collection_status(0, False) == "missing"

    def test_status_synthetic(self, db: SQLiteVBinvestDB):
        # price_rows > 0 AND has_synthetic → "synthetic"
        assert db._collection_status(5, True) == "synthetic"

    def test_status_missing_takes_priority(self, db: SQLiteVBinvestDB):
        # price_rows == 0 → "missing" regardless of has_synthetic
        assert db._collection_status(0, True) == "missing"
