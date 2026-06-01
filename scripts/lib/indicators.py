from __future__ import annotations

import pandas as pd


def _require_columns(frame: pd.DataFrame, required: set[str]) -> None:
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"missing required columns: {', '.join(sorted(missing))}")


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period, min_periods=period).mean()
    avg_loss = loss.rolling(period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(100).where(avg_gain.notna())


def add_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of *frame* with VBinvest daily indicator columns.

    Required input columns: ``date`` and ``close``. The function preserves all
    existing columns, sorts by date, and computes the default semiconductor
    dashboard indicators: returns, MA 5/20/50/120, RSI14, 20-day volatility,
    52-week high, and drawdown from that high.
    """

    _require_columns(frame, {"date", "close"})
    result = frame.copy()
    result["date"] = pd.to_datetime(result["date"])
    result = result.sort_values("date").reset_index(drop=True)
    close = pd.to_numeric(result["close"], errors="coerce")
    result["close"] = close

    result["return_1d"] = close.pct_change(1)
    result["return_1w"] = close.pct_change(5)
    result["return_1m"] = close.pct_change(21)
    result["return_3m"] = close.pct_change(63)
    result["return_6m"] = close.pct_change(126)

    year_start = result["date"].dt.year
    first_close_by_year = close.groupby(year_start).transform("first")
    result["return_ytd"] = close / first_close_by_year - 1

    for period in (5, 20, 50, 120):
        result[f"ma{period}"] = close.rolling(period, min_periods=period).mean()

    result["rsi14"] = _rsi(close, 14)
    result["vol20"] = result["return_1d"].rolling(20, min_periods=20).std()
    result["high_52w"] = close.rolling(252, min_periods=1).max()
    result["drawdown_52w"] = close / result["high_52w"] - 1

    return result
