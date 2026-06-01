import subprocess
import sys

from scripts.startup_market_refresh import IngestOptions, ingest_assets
from scripts.lib.disclosures import DisclosureFetchResult
from scripts.lib.news import NewsFetchResult
from scripts.lib.prices import PriceFetchError, synthetic_history


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
