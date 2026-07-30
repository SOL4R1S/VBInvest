"""Tests for PostgreSQL MarketDataMixin and ResearchMixin — mock cursor.

Uses mock cursor/connection since PostgreSQL is not available in CI.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

from scripts.lib.db_marketdata import MarketDataMixin
from scripts.lib.db_research import ResearchMixin


class FakePGMixin:
    """Base that provides a mock connect() returning (conn, cursor) context managers."""

    def __init__(self):
        self._mock_cursor = MagicMock()
        self._mock_conn = MagicMock()
        self._mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=self._mock_cursor)
        self._mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        self._mock_conn.__enter__ = MagicMock(return_value=self._mock_conn)
        self._mock_conn.__exit__ = MagicMock(return_value=False)

    def connect(self):
        return self._mock_conn


class FakeMarketDataDB(FakePGMixin, MarketDataMixin):
    pass


class FakeResearchDB(FakePGMixin, ResearchMixin):
    pass


class TestMarketDataMixin:
    def test_fetch_watchlist_assets(self):
        db = FakeMarketDataDB()
        db._mock_cursor.fetchall.return_value = [
            (1, "AAPL", "애플", "NASDAQ", "USD"),
            (2, "MSFT", "마이크로소프트", "NASDAQ", "USD"),
        ]
        result = db.fetch_watchlist_assets("default")
        assert len(result) == 2
        assert result[0]["symbol"] == "AAPL"
        assert result[1]["display_name_ko"] == "마이크로소프트"

    def test_ensure_assets_for_refresh_empty(self):
        db = FakeMarketDataDB()
        assert db.ensure_assets_for_refresh([]) == []

    def test_ensure_assets_for_refresh_skips_empty_symbol(self):
        db = FakeMarketDataDB()
        result = db.ensure_assets_for_refresh([{"symbol": ""}])
        assert result == []

    def test_ensure_assets_for_refresh(self):
        db = FakeMarketDataDB()
        db._mock_cursor.fetchone.return_value = (1, "AAPL", "애플", "NASDAQ", "USD")
        result = db.ensure_assets_for_refresh([{"symbol": "aapl", "display_name_ko": "애플"}])
        assert len(result) == 1
        assert result[0]["asset_id"] == 1
        assert result[0]["symbol"] == "AAPL"

    def test_upsert_prices_empty(self):
        db = FakeMarketDataDB()
        assert db.upsert_prices([]) == 0

    def test_upsert_prices(self):
        db = FakeMarketDataDB()
        rows = [{"asset_id": 1, "date": "2026-01-15", "close": 100}]
        assert db.upsert_prices(rows) == 1
        db._mock_cursor.executemany.assert_called_once()

    def test_upsert_indicators_empty(self):
        db = FakeMarketDataDB()
        assert db.upsert_indicators([]) == 0

    def test_upsert_indicators(self):
        db = FakeMarketDataDB()
        rows = [{"asset_id": 1, "date": "2026-01-15", "rsi14": 55.0}]
        assert db.upsert_indicators(rows) == 1
        db._mock_cursor.executemany.assert_called_once()

    def test_fetch_latest_price_dates_empty(self):
        db = FakeMarketDataDB()
        assert db.fetch_latest_price_dates([]) == {}

    def test_fetch_latest_price_dates(self):
        db = FakeMarketDataDB()
        db._mock_cursor.fetchall.return_value = [(1, date(2026, 1, 15))]
        result = db.fetch_latest_price_dates([1])
        assert result[1] == date(2026, 1, 15)

    def test_fetch_price_date_ranges_empty(self):
        db = FakeMarketDataDB()
        assert db.fetch_price_date_ranges([]) == {}

    def test_fetch_price_date_ranges(self):
        db = FakeMarketDataDB()
        db._mock_cursor.fetchall.return_value = [(1, date(2026, 1, 1), date(2026, 1, 15))]
        result = db.fetch_price_date_ranges([1])
        assert result[1]["earliest_date"] == date(2026, 1, 1)
        assert result[1]["latest_date"] == date(2026, 1, 15)


class TestResearchMixin:
    def test_upsert_research_views_empty(self):
        db = FakeResearchDB()
        assert db.upsert_research_views([]) == 0

    def test_upsert_research_views(self):
        db = FakeResearchDB()
        rows = [{"target_type": "asset", "target_slug": "AAPL", "report_date": "2026-01-15"}]
        assert db.upsert_research_views(rows) == 1
        db._mock_cursor.executemany.assert_called_once()

    def test_record_research_sources_empty(self):
        db = FakeResearchDB()
        assert db.record_research_sources([]) == 0

    def test_record_research_sources(self):
        db = FakeResearchDB()
        rows = [
            {
                "target_slug": "AAPL",
                "report_date": "2026-01-15",
                "source": {"kind": "news", "title": "Test", "url": "https://example.com"},
            }
        ]
        assert db.record_research_sources(rows) == 1
        db._mock_cursor.executemany.assert_called_once()

    def test_fetch_latest_research_views_empty(self):
        db = FakeResearchDB()
        db._mock_cursor.fetchall.return_value = []
        result = db.fetch_latest_research_views("default")
        assert result == {}

    def test_fetch_latest_research_for_asset_not_found(self):
        db = FakeResearchDB()
        db._mock_cursor.fetchone.return_value = None
        assert db.fetch_latest_research_for_asset("AAPL") is None

    def test_fetch_recent_news_for_asset(self):
        db = FakeResearchDB()
        # SQL: provider, source, COALESCE(canonical_url, url), title, published_at
        db._mock_cursor.fetchall.return_value = [
            ("reuters", "reuters", "https://example.com", "Title", "2026-01-15"),
        ]
        result = db.fetch_recent_news_for_asset(1, limit=5)
        assert len(result) == 1
        assert result[0]["provider"] == "reuters"
        assert result[0]["url"] == "https://example.com"

    def test_fetch_recent_disclosures_for_asset(self):
        db = FakeResearchDB()
        # SQL: provider, title, url, published_at, provider_disclosure_id
        db._mock_cursor.fetchall.return_value = [
            ("sec", "10-K", "https://sec.gov", "2026-01-15", "disc-1"),
        ]
        result = db.fetch_recent_disclosures_for_asset(1, limit=5)
        assert len(result) == 1
        assert result[0]["provider"] == "sec"
        assert result[0]["provider_disclosure_id"] == "disc-1"
