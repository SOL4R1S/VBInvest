from __future__ import annotations

import json
import math
import random
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from io import StringIO
from typing import Any

import pandas as pd

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={range}&interval={interval}"


class PriceFetchError(RuntimeError):
    pass


def parse_yahoo_chart(symbol: str, payload: dict[str, Any]) -> pd.DataFrame:
    chart = payload.get("chart") or {}
    error = chart.get("error")
    if error:
        raise PriceFetchError(f"{symbol}: yahoo error: {error}")
    results = chart.get("result") or []
    if not results:
        raise PriceFetchError(f"{symbol}: yahoo returned no result")

    result = results[0]
    timestamps = result.get("timestamp") or []
    quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
    adjclose_items = (result.get("indicators") or {}).get("adjclose") or [{}]
    adjclose = adjclose_items[0].get("adjclose") or [None] * len(timestamps)
    currency = (result.get("meta") or {}).get("currency")

    rows = []
    for i, ts in enumerate(timestamps):
        close = _at(quote.get("close"), i)
        if close is None or (isinstance(close, float) and math.isnan(close)):
            continue
        rows.append(
            {
                "date": datetime.fromtimestamp(ts, tz=timezone.utc).date(),
                "open": _at(quote.get("open"), i),
                "high": _at(quote.get("high"), i),
                "low": _at(quote.get("low"), i),
                "close": close,
                "adj_close": _at(adjclose, i),
                "volume": _at(quote.get("volume"), i),
                "currency": currency,
                "provider": "yahoo-chart",
            }
        )

    frame = pd.DataFrame(rows)
    if frame.empty:
        raise PriceFetchError(f"{symbol}: no valid close prices")
    return frame.sort_values("date").reset_index(drop=True)


def _at(values: list[Any] | None, index: int) -> Any:
    if not values or index >= len(values):
        return None
    return values[index]


def fetch_yahoo_chart(symbol: str, *, range_: str = "1y", interval: str = "1d", timeout: int = 20) -> pd.DataFrame:
    url = YAHOO_CHART_URL.format(symbol=urllib.parse.quote(symbol), range=range_, interval=interval)
    request = urllib.request.Request(url, headers={"User-Agent": "VBinvest/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise PriceFetchError(f"{symbol}: yahoo fetch failed: {exc}") from exc
    return parse_yahoo_chart(symbol, payload)


def fetch_yfinance_history(
    symbol: str,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError as exc:
        raise PriceFetchError(f"{symbol}: yfinance unavailable: {exc}") from exc
    try:
        ticker = yf.Ticker(symbol)
        if start_date is None and end_date is None:
            frame = ticker.history(period="1y", interval="1d", auto_adjust=False)
        else:
            history_kwargs = {"interval": "1d", "auto_adjust": False}
            if start_date is not None:
                history_kwargs["start"] = start_date.isoformat()
            if end_date is not None:
                history_kwargs["end"] = (end_date + timedelta(days=1)).isoformat()
            frame = ticker.history(**history_kwargs)
        info = ticker.fast_info
    except (AttributeError, KeyError, RuntimeError, TypeError, ValueError) as exc:
        raise PriceFetchError(f"{symbol}: yfinance fetch failed: {exc}") from exc
    if frame.empty:
        raise PriceFetchError(f"{symbol}: yfinance returned no rows")

    return normalize_yfinance_history(symbol, frame, currency=_fast_info_currency(info))


def normalize_yfinance_history(symbol: str, frame: pd.DataFrame, *, currency: str | None) -> pd.DataFrame:
    if frame.empty:
        raise PriceFetchError(f"{symbol}: yfinance returned no rows")
    result = frame.reset_index()
    date_column = "Date" if "Date" in result.columns else result.columns[0]
    return pd.DataFrame(
        {
            "date": pd.to_datetime(result[date_column]).dt.date,
            "open": pd.to_numeric(result.get("Open"), errors="coerce"),
            "high": pd.to_numeric(result.get("High"), errors="coerce"),
            "low": pd.to_numeric(result.get("Low"), errors="coerce"),
            "close": pd.to_numeric(result.get("Close"), errors="coerce"),
            "adj_close": pd.to_numeric(result.get("Adj Close", result.get("Close")), errors="coerce"),
            "volume": pd.to_numeric(result.get("Volume"), errors="coerce"),
            "currency": currency,
            "provider": "yfinance",
        }
    ).dropna(subset=["close"]).sort_values("date").reset_index(drop=True)


def _fast_info_currency(info) -> str | None:
    currency = getattr(info, "currency", None)
    if currency is not None:
        return str(currency)
    try:
        value = info["currency"]
    except (KeyError, TypeError):
        return None
    return str(value) if value is not None else None


def fetch_stooq_history(symbol: str) -> pd.DataFrame:
    stooq_symbol = symbol.lower().replace(".ks", ".kr").replace(".kq", ".kr")
    url = f"https://stooq.com/q/d/l/?s={urllib.parse.quote(stooq_symbol)}&i=d"
    request = urllib.request.Request(url, headers={"User-Agent": "VBinvest/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            csv_text = response.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError, UnicodeDecodeError) as exc:
        raise PriceFetchError(f"{symbol}: stooq fetch failed: {exc}") from exc

    frame = pd.read_csv(StringIO(csv_text))
    required = {"Date", "Open", "High", "Low", "Close", "Volume"}
    if frame.empty or not required.issubset(frame.columns):
        raise PriceFetchError(f"{symbol}: stooq returned no valid rows")
    return pd.DataFrame(
        {
            "date": pd.to_datetime(frame["Date"]).dt.date,
            "open": pd.to_numeric(frame["Open"], errors="coerce"),
            "high": pd.to_numeric(frame["High"], errors="coerce"),
            "low": pd.to_numeric(frame["Low"], errors="coerce"),
            "close": pd.to_numeric(frame["Close"], errors="coerce"),
            "adj_close": pd.to_numeric(frame["Close"], errors="coerce"),
            "volume": pd.to_numeric(frame["Volume"], errors="coerce"),
            "currency": None,
            "provider": "stooq",
        }
    ).dropna(subset=["close"]).sort_values("date").reset_index(drop=True)


def fetch_price_history(
    symbol: str,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    synthetic: bool = False,
    no_network: bool = False,
    yahoo_fetcher=fetch_yahoo_chart,
    yfinance_fetcher=fetch_yfinance_history,
    stooq_fetcher=fetch_stooq_history,
) -> pd.DataFrame:
    if synthetic or no_network:
        if start_date is not None and end_date is not None:
            days = max(0, (end_date - start_date).days + 1)
            return synthetic_history(symbol, days=days, start_date=start_date)
        return filter_price_history_window(synthetic_history(symbol), start_date=start_date, end_date=end_date)

    failures: list[str] = []
    for provider, fetcher in (
        ("yahoo", yahoo_fetcher),
        ("yfinance", yfinance_fetcher),
        ("stooq", stooq_fetcher),
    ):
        try:
            if provider == "yfinance" and (start_date is not None or end_date is not None):
                frame = fetcher(symbol, start_date=start_date, end_date=end_date)
            else:
                frame = fetcher(symbol)
        except PriceFetchError as exc:
            failures.append(f"{provider} failed: {exc}")
            continue
        filtered = filter_price_history_window(frame, start_date=start_date, end_date=end_date)
        if filtered.empty:
            failures.append(f"{provider} failed: empty frame")
            continue
        return filtered
    raise PriceFetchError(f"{symbol}: all price providers failed: {'; '.join(failures)}")


def filter_price_history_window(
    frame: pd.DataFrame,
    *,
    start_date: date | None,
    end_date: date | None,
) -> pd.DataFrame:
    if frame.empty:
        return frame
    result = frame.copy()
    result["date"] = pd.to_datetime(result["date"]).dt.date
    if start_date is not None:
        result = result[result["date"] >= start_date]
    if end_date is not None:
        result = result[result["date"] <= end_date]
    return result.sort_values("date").reset_index(drop=True)


def synthetic_history(symbol: str, *, days: int = 260, start_date: date | None = None) -> pd.DataFrame:
    """Deterministic non-market sample data for tests and offline demos."""
    rng = random.Random(symbol)
    start = start_date or date(2025, 1, 1)
    price = 80.0 + rng.random() * 50
    rows = []
    for offset in range(days):
        current = start + timedelta(days=offset)
        drift = 0.03 + math.sin(offset / 12) * 0.15 + rng.uniform(-0.8, 0.8)
        open_ = price
        close = max(1.0, price + drift)
        high = max(open_, close) + rng.uniform(0, 1.5)
        low = min(open_, close) - rng.uniform(0, 1.5)
        volume = int(1_000_000 + rng.random() * 500_000 + offset * 100)
        rows.append(
            {
                "date": current,
                "open": round(open_, 4),
                "high": round(high, 4),
                "low": round(low, 4),
                "close": round(close, 4),
                "adj_close": round(close, 4),
                "volume": volume,
                "currency": "USD",
                "provider": "synthetic",
            }
        )
        price = close
    return pd.DataFrame(rows)
