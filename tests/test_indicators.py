import math

import pandas as pd

from scripts.lib.indicators import add_indicators


def sample_prices(days=160):
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=days, freq="D"),
            "close": [100 + i + (i % 7) * 0.25 for i in range(days)],
            "volume": [1_000_000 + i for i in range(days)],
        }
    )


def test_add_indicators_adds_expected_columns():
    result = add_indicators(sample_prices())

    for column in [
        "return_1d",
        "return_1w",
        "return_1m",
        "return_3m",
        "return_6m",
        "return_ytd",
        "ma5",
        "ma20",
        "ma50",
        "ma120",
        "rsi14",
        "vol20",
        "drawdown_52w",
        "high_52w",
    ]:
        assert column in result.columns


def test_return_1d_uses_previous_close():
    result = add_indicators(sample_prices())

    expected = result.loc[10, "close"] / result.loc[9, "close"] - 1

    assert math.isclose(result.loc[10, "return_1d"], expected, rel_tol=1e-12)


def test_rsi14_is_bounded_after_warmup():
    result = add_indicators(sample_prices())
    rsi = result["rsi14"].dropna()

    assert not rsi.empty
    assert (rsi >= 0).all()
    assert (rsi <= 100).all()


def test_drawdown_52w_is_non_positive_and_uses_rolling_high():
    frame = sample_prices()
    frame.loc[159, "close"] = 120

    result = add_indicators(frame)

    assert result.loc[159, "high_52w"] == result.loc[:159, "close"].max()
    assert result.loc[159, "drawdown_52w"] <= 0
    assert math.isclose(
        result.loc[159, "drawdown_52w"],
        result.loc[159, "close"] / result.loc[159, "high_52w"] - 1,
        rel_tol=1e-12,
    )
