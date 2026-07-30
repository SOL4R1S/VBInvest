"""Tests for scripts.lib.dashboard_payload — serialization."""

import pandas as pd

from scripts.lib.dashboard_payload import serialize_dashboard_items


def test_serialize_basic():
    frame = pd.DataFrame(
        [
            {"date": "2026-01-01", "close": 100.0, "volume": 500},
            {"date": "2026-01-02", "close": 105.0, "volume": 600},
        ]
    )
    items = [{"asset": {"symbol": "NVDA"}, "history": frame}]
    result = serialize_dashboard_items(items)
    assert len(result) == 1
    assert result[0]["asset"]["symbol"] == "NVDA"
    assert result[0]["opinion"] == "중립"
    assert len(result[0]["history"]) == 2
    assert result[0]["latest"]["close"] == 105.0


def test_serialize_skips_synthetic():
    frame = pd.DataFrame(
        [
            {"date": "2026-01-01", "close": 100.0, "source": "synthetic"},
            {"date": "2026-01-02", "close": 105.0, "source": "yfinance"},
        ]
    )
    items = [{"asset": {"symbol": "AAPL"}, "history": frame}]
    result = serialize_dashboard_items(items)
    assert len(result[0]["history"]) == 1
    assert result[0]["history"][0]["close"] == 105.0


def test_serialize_skips_empty_history():
    frame = pd.DataFrame({"date": [], "close": []})
    items = [{"asset": {"symbol": "TSLA"}, "history": frame}]
    result = serialize_dashboard_items(items)
    assert len(result) == 0


def test_serialize_nan_to_none():
    frame = pd.DataFrame([{"date": "2026-01-01", "close": float("nan"), "volume": 100}])
    items = [{"asset": {"symbol": "MSFT"}, "history": frame}]
    result = serialize_dashboard_items(items)
    assert result[0]["history"][0]["close"] is None


def test_serialize_custom_opinion():
    frame = pd.DataFrame([{"date": "2026-01-01", "close": 50.0}])
    items = [{"asset": {"symbol": "GOOG"}, "history": frame, "opinion": "매수", "thesis": "AI growth"}]
    result = serialize_dashboard_items(items)
    assert result[0]["opinion"] == "매수"
    assert result[0]["thesis"] == "AI growth"
