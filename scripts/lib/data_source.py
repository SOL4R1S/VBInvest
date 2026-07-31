"""Pluggable price data source architecture.

Provides a Protocol-based registry so new price sources can be added
without modifying the fallback chain in prices.py.
"""

from __future__ import annotations

from datetime import date
from typing import Protocol, runtime_checkable

import pandas as pd

from scripts.lib.prices import (
    PriceFetchError,
    covers_requested_start,
    fetch_stooq_history,
    fetch_yahoo_chart,
    fetch_yfinance_history,
    filter_price_history_window,
)


@runtime_checkable
class PriceDataSource(Protocol):
    """Price data source plugin interface."""

    @property
    def provider_slug(self) -> str: ...

    @property
    def priority(self) -> int: ...

    def supports_symbol(self, symbol: str) -> bool: ...

    def fetch_history(
        self,
        symbol: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> pd.DataFrame: ...


class YahooChartSource:
    """Yahoo Finance chart API (HTTP, no library dependency)."""

    provider_slug: str = "yahoo-chart"
    priority: int = 10

    def supports_symbol(self, symbol: str) -> bool:
        return True

    def fetch_history(
        self,
        symbol: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> pd.DataFrame:
        return fetch_yahoo_chart(symbol)


class YFinanceSource:
    """yfinance library — supports date-range queries."""

    provider_slug: str = "yfinance"
    priority: int = 20

    def supports_symbol(self, symbol: str) -> bool:
        return True

    def fetch_history(
        self,
        symbol: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> pd.DataFrame:
        if start_date is not None or end_date is not None:
            return fetch_yfinance_history(symbol, start_date=start_date, end_date=end_date)
        return fetch_yfinance_history(symbol)


class StooqSource:
    """Stooq CSV — primarily Korean market symbols."""

    provider_slug: str = "stooq"
    priority: int = 30

    def supports_symbol(self, symbol: str) -> bool:
        return symbol.endswith((".KS", ".KQ", ".KR"))

    def fetch_history(
        self,
        symbol: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> pd.DataFrame:
        return fetch_stooq_history(symbol)


class PriceSourceRegistry:
    """Ordered registry of price data sources with priority-based fallback."""

    def __init__(self) -> None:
        self._sources: list[PriceDataSource] = []

    def register(self, source: PriceDataSource) -> None:
        self._sources.append(source)
        self._sources.sort(key=lambda s: s.priority)

    @property
    def sources(self) -> list[PriceDataSource]:
        return list(self._sources)

    def fetch(
        self,
        symbol: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> pd.DataFrame:
        """Try sources in priority order; raise PriceFetchError if all fail."""
        failures: list[str] = []
        for source in self._sources:
            if not source.supports_symbol(symbol):
                continue
            try:
                frame = source.fetch_history(symbol, start_date=start_date, end_date=end_date)
            except PriceFetchError as exc:
                failures.append(f"{source.provider_slug} failed: {exc}")
                continue
            filtered = filter_price_history_window(frame, start_date=start_date, end_date=end_date)
            if filtered.empty:
                failures.append(f"{source.provider_slug} failed: empty frame")
                continue
            if not covers_requested_start(filtered, start_date=start_date):
                failures.append(f"{source.provider_slug} failed: missing requested start")
                continue
            return filtered
        raise PriceFetchError(f"{symbol}: all price providers failed: {'; '.join(failures)}")


def create_default_registry() -> PriceSourceRegistry:
    """Build the default registry with all built-in sources."""
    registry = PriceSourceRegistry()
    registry.register(YahooChartSource())
    registry.register(YFinanceSource())
    registry.register(StooqSource())
    return registry


# Global default registry — import and use directly
default_registry = create_default_registry()
