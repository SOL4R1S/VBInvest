import subprocess
import sys
from datetime import date, datetime, timezone

import pandas as pd

from scripts.startup_market_refresh import IngestOptions, ingest_assets
from scripts.lib.disclosures import DisclosureFetchResult
from scripts.lib.news import NewsFetchResult
from scripts.lib.prices import PriceFetchError, synthetic_history


def _market_frame(start: date, end: date) -> pd.DataFrame:
    rows = []
    current = start
    while current <= end:
        rows.append(
            {
                "date": current,
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
                "adj_close": 100.5,
                "volume": 1000,
                "currency": "USD",
                "provider": "test",
            }
        )
        current = date.fromordinal(current.toordinal() + 1)
    return pd.DataFrame(rows)


class CaptureDB:
    def __init__(self, latest_dates=None, price_date_ranges=None):
        self.latest_dates = latest_dates or {}
        self.price_date_ranges = price_date_ranges or {}
        self.price_rows = []
        self.indicator_rows = []

    def fetch_latest_price_dates(self, asset_ids):
        return {asset_id: self.latest_dates[asset_id] for asset_id in asset_ids if asset_id in self.latest_dates}

    def fetch_price_date_ranges(self, asset_ids):
        return {asset_id: self.price_date_ranges[asset_id] for asset_id in asset_ids if asset_id in self.price_date_ranges}

    def upsert_prices(self, rows):
        self.price_rows.extend(rows)
        return len(rows)

    def upsert_indicators(self, rows):
        self.indicator_rows.extend(rows)
        return len(rows)


def test_startup_market_refresh_dry_run_direct_script_execution():
    result = subprocess.run(
        [sys.executable, "scripts/startup_market_refresh.py", "--dry-run", "--no-network"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "VBinvest startup market refresh" in result.stdout
    assert "status=ok mode=dry-run network=disabled" in result.stdout
    assert "assets=17" in result.stdout
    assert "price_rows=4420" in result.stdout
    assert "trade_dates=" in result.stdout
    assert "failed=none" in result.stdout
    assert len(result.stdout) < 2000


def test_startup_market_refresh_rejects_malformed_at_kst_without_traceback():
    result = subprocess.run(
        [sys.executable, "scripts/startup_market_refresh.py", "--dry-run", "--at-kst", "not-a-date"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "invalid --at-kst" in result.stderr
    assert "Traceback" not in result.stderr


def test_startup_market_refresh_include_news_no_network_reports_disabled():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/startup_market_refresh.py",
            "--dry-run",
            "--no-network",
            "--include-news",
            "--limit",
            "1",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "news_items=0 disclosures=0" in result.stdout
    assert "provider_disabled=" in result.stdout
    assert "failed=none" in result.stdout


def test_provider_failure_records_partial_without_replacing_ticker():
    assets = [
        {"asset_id": 1, "symbol": "NVDA", "exchange": "NASDAQ"},
        {"asset_id": 2, "symbol": "AMD", "exchange": "NASDAQ"},
    ]

    def fetch_history(symbol: str):
        if symbol == "NVDA":
            raise PriceFetchError("forced provider failure")
        return synthetic_history(symbol, days=2)

    result = ingest_assets(
        assets,
        db=None,
        options=IngestOptions(no_network=False, synthetic=False),
        fetch_history=fetch_history,
    )

    assert result.status == "partial"
    assert result.failures == ["NVDA:PriceFetchError"]
    assert result.price_rows == 2
    assert result.indicator_rows == 2


def test_ingest_assets_retries_retryable_price_failure():
    assets = [{"asset_id": 1, "symbol": "NVDA", "exchange": "NASDAQ"}]
    calls = []

    def fetch_history(symbol: str):
        calls.append(symbol)
        if len(calls) == 1:
            raise PriceFetchError("429 rate limit")
        return synthetic_history(symbol, days=2)

    result = ingest_assets(
        assets,
        db=None,
        options=IngestOptions(no_network=False, synthetic=False, max_attempts=2),
        fetch_history=fetch_history,
    )

    assert result.status == "ok"
    assert calls == ["NVDA", "NVDA"]
    assert result.failures == []
    assert result.price_rows == 2


def test_ingest_assets_respects_job_lock_for_writes():
    class LockedDB:
        def __init__(self):
            self.lock_calls = []
            self.price_rows = 0

        def try_acquire_job_lock(self, lock_name: str, holder: str, ttl_seconds: int) -> bool:
            self.lock_calls.append((lock_name, holder, ttl_seconds))
            return False

        def upsert_prices(self, rows):
            self.price_rows += len(rows)

        def upsert_indicators(self, rows):
            return len(rows)

    db = LockedDB()
    result = ingest_assets(
        [{"asset_id": 1, "symbol": "NVDA", "exchange": "NASDAQ"}],
        db=db,
        options=IngestOptions(no_network=True, synthetic=False, job_name="startup-market-refresh:test", lock_holder="test"),
    )

    assert result.status == "locked"
    assert result.price_rows == 0
    assert result.indicator_rows == 0
    assert result.failures == ["job-lock:startup-market-refresh:test"]
    assert db.lock_calls == [("startup-market-refresh:test", "test", 3600)]
    assert db.price_rows == 0


def test_ingest_assets_counts_mocked_news_and_disclosures():
    assets = [{"asset_id": 1, "symbol": "NVDA", "exchange": "NASDAQ"}]

    def news_collector(asset, *, no_network):
        return NewsFetchResult(
            status="ok",
            items=[{"provider": "test-news", "title": "News", "source_id": "n1"}],
            provider_disabled=[],
        )

    def disclosure_collector(asset, *, no_network, dart_api_key):
        return DisclosureFetchResult(
            status="ok",
            items=[{"provider": "test-disclosure", "title": "Disclosure", "provider_disclosure_id": "d1"}],
            provider_disabled=[],
        )

    result = ingest_assets(
        assets,
        db=None,
        options=IngestOptions(no_network=False, synthetic=True, include_news=True),
        news_collector=news_collector,
        disclosure_collector=disclosure_collector,
    )

    assert result.status == "ok"
    assert result.news_items == 1
    assert result.disclosures == 1
    assert result.provider_disabled == []


def test_ingest_assets_skips_source_collection_when_include_news_false():
    assets = [{"asset_id": 1, "symbol": "NVDA", "exchange": "NASDAQ"}]
    calls = []

    def news_collector(asset, *, no_network):
        calls.append(("news", asset["symbol"], no_network))
        return NewsFetchResult(status="ok", items=[], provider_disabled=[])

    def disclosure_collector(asset, *, no_network, dart_api_key):
        calls.append(("disclosure", asset["symbol"], no_network, dart_api_key))
        return DisclosureFetchResult(status="ok", items=[], provider_disabled=[])

    result = ingest_assets(
        assets,
        db=None,
        options=IngestOptions(no_network=True, synthetic=True, include_news=False),
        news_collector=news_collector,
        disclosure_collector=disclosure_collector,
    )

    assert result.status == "ok"
    assert calls == []
    assert result.news_items == 0
    assert result.disclosures == 0
    assert result.provider_disabled == []


def test_ingest_assets_first_write_requests_historical_backfill_window():
    db = CaptureDB()
    calls = []

    def fetch_history(symbol: str, *, start_date: date | None = None, end_date: date | None = None):
        calls.append((symbol, start_date, end_date))
        assert start_date is not None
        assert end_date == date(2026, 6, 2)
        return _market_frame(start_date, end_date)

    result = ingest_assets(
        [{"asset_id": 1, "symbol": "NVDA", "exchange": "NASDAQ"}],
        db=db,
        options=IngestOptions(fetched_at=datetime(2026, 6, 2, 8, 0, tzinfo=timezone.utc)),
        fetch_history=fetch_history,
    )

    assert result.status == "ok"
    assert calls == [("NVDA", date(2021, 6, 3), date(2026, 6, 2))]
    assert len(db.price_rows) == 1826
    assert db.price_rows[0]["date"] == date(2021, 6, 3)
    assert db.price_rows[-1]["date"] == date(2026, 6, 2)


def test_ingest_assets_backfills_existing_short_history_before_incremental_skip():
    db = CaptureDB(
        latest_dates={1: date(2026, 6, 2)},
        price_date_ranges={1: {"earliest_date": date(2025, 9, 15), "latest_date": date(2026, 6, 2)}},
    )
    calls = []

    def fetch_history(symbol: str, *, start_date: date | None = None, end_date: date | None = None):
        calls.append((symbol, start_date, end_date))
        assert start_date is not None
        assert end_date is not None
        return _market_frame(start_date, end_date)

    result = ingest_assets(
        [{"asset_id": 1, "symbol": "NVDA", "exchange": "NASDAQ"}],
        db=db,
        options=IngestOptions(fetched_at=datetime(2026, 6, 2, 8, 0, tzinfo=timezone.utc)),
        fetch_history=fetch_history,
    )

    assert result.status == "ok"
    assert calls == [("NVDA", date(2021, 6, 3), date(2026, 6, 2))]
    assert db.price_rows[0]["date"] == date(2021, 6, 3)
    assert db.price_rows[-1]["date"] == date(2026, 6, 2)


def test_ingest_assets_incremental_write_persists_only_rows_after_latest_saved_date():
    db = CaptureDB(latest_dates={1: date(2026, 5, 30)})
    calls = []

    def fetch_history(symbol: str, *, start_date: date | None = None, end_date: date | None = None):
        calls.append((symbol, start_date, end_date))
        return _market_frame(date(2026, 5, 29), date(2026, 6, 2))

    result = ingest_assets(
        [{"asset_id": 1, "symbol": "NVDA", "exchange": "NASDAQ"}],
        db=db,
        options=IngestOptions(fetched_at=datetime(2026, 6, 2, 8, 0, tzinfo=timezone.utc)),
        fetch_history=fetch_history,
    )

    assert result.status == "ok"
    assert calls == [("NVDA", date(2025, 12, 2), date(2026, 6, 2))]
    assert [row["date"] for row in db.price_rows] == [
        date(2026, 5, 31),
        date(2026, 6, 1),
        date(2026, 6, 2),
    ]
    assert [row["date"] for row in db.indicator_rows] == [
        date(2026, 5, 31),
        date(2026, 6, 1),
        date(2026, 6, 2),
    ]


def test_ingest_assets_skips_price_fetch_when_latest_saved_date_reaches_run_date():
    db = CaptureDB(latest_dates={1: date(2026, 6, 2)})
    calls = []

    def fetch_history(symbol: str, *, start_date: date | None = None, end_date: date | None = None):
        calls.append((symbol, start_date, end_date))
        return _market_frame(date(2026, 6, 2), date(2026, 6, 2))

    result = ingest_assets(
        [{"asset_id": 1, "symbol": "NVDA", "exchange": "NASDAQ"}],
        db=db,
        options=IngestOptions(fetched_at=datetime(2026, 6, 2, 8, 0, tzinfo=timezone.utc)),
        fetch_history=fetch_history,
    )

    assert result.status == "ok"
    assert calls == []
    assert db.price_rows == []


def test_ingest_assets_no_network_write_uses_windowed_synthetic_history():
    db = CaptureDB()

    result = ingest_assets(
        [{"asset_id": 1, "symbol": "NVDA", "exchange": "NASDAQ"}],
        db=db,
        options=IngestOptions(no_network=True, fetched_at=datetime(2026, 6, 2, 8, 0, tzinfo=timezone.utc)),
    )

    assert result.status == "ok"
    assert len(db.price_rows) == 1826
    assert db.price_rows[0]["date"] == date(2021, 6, 3)
    assert db.price_rows[-1]["date"] == date(2026, 6, 2)
