from scripts.lib.db import build_indicator_rows, build_price_rows
from scripts.lib.indicators import add_indicators
from scripts.lib.prices import synthetic_history


def test_build_price_rows_contains_asset_id_and_ohlcv():
    frame = synthetic_history("NVDA", days=2)

    rows = build_price_rows(42, frame)

    assert rows[0]["asset_id"] == 42
    assert rows[0]["date"] == frame.loc[0, "date"]
    assert rows[0]["close"] == frame.loc[0, "close"]
    assert rows[0]["source"] == "synthetic"
    assert rows[0]["provider"] == "synthetic"
    assert rows[0]["currency"] == "USD"
    assert rows[0]["adj_close"] == frame.loc[0, "adj_close"]
    assert rows[0]["fetched_at"] is not None


def test_build_indicator_rows_contains_latest_indicator_fields():
    frame = add_indicators(synthetic_history("NVDA", days=140))

    rows = build_indicator_rows(42, frame)

    assert rows[-1]["asset_id"] == 42
    assert "ma120" in rows[-1]
    assert "rsi14" in rows[-1]
    assert "drawdown_52w" in rows[-1]
