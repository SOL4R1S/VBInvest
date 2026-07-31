"""Tests for pluggable price data source registry."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from scripts.lib.data_source import (
    PriceSourceRegistry,
    StooqSource,
    YahooChartSource,
    YFinanceSource,
    create_default_registry,
)
from scripts.lib.prices import PriceFetchError


def _make_frame(days: int = 5) -> pd.DataFrame:
    dates = pd.date_range(end=date.today(), periods=days, freq="B")
    return pd.DataFrame(
        {
            "Date": dates,
            "Open": [100.0] * days,
            "High": [105.0] * days,
            "Low": [95.0] * days,
            "Close": [102.0] * days,
            "Volume": [1000] * days,
        }
    )


class FakeSource:
    def __init__(self, slug: str, priority: int, *, fail: bool = False, symbols: set[str] | None = None) -> None:
        self.provider_slug = slug
        self.priority = priority
        self._fail = fail
        self._symbols = symbols
        self.called = False

    def supports_symbol(self, symbol: str) -> bool:
        if self._symbols is None:
            return True
        return symbol in self._symbols

    def fetch_history(
        self, symbol: str, *, start_date: date | None = None, end_date: date | None = None
    ) -> pd.DataFrame:
        self.called = True
        if self._fail:
            raise PriceFetchError(f"{self.provider_slug} down")
        return _make_frame()


class TestPriceSourceRegistry:
    def test_priority_ordering(self) -> None:
        registry = PriceSourceRegistry()
        low = FakeSource("low", 30)
        high = FakeSource("high", 10)
        registry.register(low)
        registry.register(high)
        assert [s.provider_slug for s in registry.sources] == ["high", "low"]

    def test_fallback_on_failure(self) -> None:
        registry = PriceSourceRegistry()
        failing = FakeSource("fail", 10, fail=True)
        working = FakeSource("ok", 20)
        registry.register(failing)
        registry.register(working)
        result = registry.fetch("AAPL")
        assert not result.empty
        assert failing.called
        assert working.called

    def test_all_fail_raises(self) -> None:
        registry = PriceSourceRegistry()
        registry.register(FakeSource("a", 10, fail=True))
        registry.register(FakeSource("b", 20, fail=True))
        with pytest.raises(PriceFetchError, match="all price providers failed"):
            registry.fetch("AAPL")

    def test_symbol_filter_skips_unsupported(self) -> None:
        registry = PriceSourceRegistry()
        korean_only = FakeSource("kr", 10, symbols={"005930.KS"})
        registry.register(korean_only)
        with pytest.raises(PriceFetchError, match="all price providers failed"):
            registry.fetch("AAPL")
        assert not korean_only.called

    def test_empty_registry_raises(self) -> None:
        registry = PriceSourceRegistry()
        with pytest.raises(PriceFetchError):
            registry.fetch("AAPL")


class TestBuiltinSources:
    def test_yahoo_supports_all(self) -> None:
        assert YahooChartSource().supports_symbol("AAPL")
        assert YahooChartSource().supports_symbol("005930.KS")

    def test_yfinance_supports_all(self) -> None:
        assert YFinanceSource().supports_symbol("MSFT")

    def test_stooq_korean_only(self) -> None:
        src = StooqSource()
        assert src.supports_symbol("005930.KS")
        assert src.supports_symbol("035420.KQ")
        assert not src.supports_symbol("AAPL")

    def test_priorities(self) -> None:
        assert YahooChartSource().priority < YFinanceSource().priority < StooqSource().priority


class TestDefaultRegistry:
    def test_has_three_sources(self) -> None:
        registry = create_default_registry()
        assert len(registry.sources) == 3

    def test_source_order(self) -> None:
        registry = create_default_registry()
        slugs = [s.provider_slug for s in registry.sources]
        assert slugs == ["yahoo-chart", "yfinance", "stooq"]
