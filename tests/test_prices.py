from datetime import date

import pandas as pd

from scripts.lib.prices import (
    PriceFetchError,
    fetch_price_history,
    fetch_stooq_history,
    normalize_yfinance_history,
    parse_yahoo_chart,
    search_ticker_suggestions,
    synthetic_history,
    validate_ticker_symbol,
)


def yahoo_payload():
    return {
        "chart": {
            "result": [
                {
                    "timestamp": [1704067200, 1704153600],
                    "meta": {"currency": "USD", "symbol": "NVDA"},
                    "indicators": {
                        "quote": [
                            {
                                "open": [10.0, 11.0],
                                "high": [12.0, 12.5],
                                "low": [9.5, 10.5],
                                "close": [11.0, 12.0],
                                "volume": [1000, 2000],
                            }
                        ],
                        "adjclose": [{"adjclose": [10.8, 11.9]}],
                    },
                }
            ]
        }
    }


def _price_row(current: date, *, provider: str = "test") -> dict:
    return {
        "date": current,
        "open": 100.0,
        "high": 101.0,
        "low": 99.0,
        "close": 100.5,
        "adj_close": 100.5,
        "volume": 1000,
        "currency": "USD",
        "provider": provider,
    }


def test_parse_yahoo_chart_normalizes_ohlcv():
    frame = parse_yahoo_chart("NVDA", yahoo_payload())

    assert list(frame.columns) == [
        "date",
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "volume",
        "currency",
        "provider",
    ]
    assert len(frame) == 2
    assert frame.loc[0, "close"] == 11.0
    assert frame.loc[1, "adj_close"] == 11.9
    assert frame.loc[0, "provider"] == "yahoo-chart"


def test_synthetic_history_is_deterministic_and_long_enough():
    first = synthetic_history("NVDA", days=260)
    second = synthetic_history("NVDA", days=260)

    pd.testing.assert_frame_equal(first, second)
    assert len(first) == 260
    assert {"open", "high", "low", "close", "volume"}.issubset(first.columns)


def test_fetch_price_history_uses_provider_fallback_order():
    calls = []

    def yahoo(symbol: str):
        calls.append(("yahoo", symbol))
        raise PriceFetchError("yahoo down")

    def yfinance_fetch(symbol: str):
        calls.append(("yfinance", symbol))
        return synthetic_history(symbol, days=2).assign(provider="yfinance")

    def stooq(symbol: str):
        calls.append(("stooq", symbol))
        return synthetic_history(symbol, days=2).assign(provider="stooq")

    frame = fetch_price_history("NVDA", yahoo_fetcher=yahoo, yfinance_fetcher=yfinance_fetch, stooq_fetcher=stooq)

    assert calls == [("yahoo", "NVDA"), ("yfinance", "NVDA")]
    assert frame.loc[0, "provider"] == "yfinance"


def test_fetch_price_history_passes_window_to_yfinance_and_filters_rows():
    calls = []

    def yahoo(symbol: str):
        calls.append(("yahoo", symbol))
        raise PriceFetchError("yahoo down")

    def yfinance_fetch(symbol: str, *, start_date: date | None = None, end_date: date | None = None):
        calls.append(("yfinance", symbol, start_date, end_date))
        return pd.DataFrame(
            [
                _price_row(date(2026, 5, 29), provider="yfinance"),
                _price_row(date(2026, 5, 31), provider="yfinance"),
                _price_row(date(2026, 6, 2), provider="yfinance"),
                _price_row(date(2026, 6, 3), provider="yfinance"),
            ]
        )

    def stooq(symbol: str):
        calls.append(("stooq", symbol))
        return synthetic_history(symbol, days=2).assign(provider="stooq")

    frame = fetch_price_history(
        "NVDA",
        start_date=date(2026, 5, 31),
        end_date=date(2026, 6, 2),
        yahoo_fetcher=yahoo,
        yfinance_fetcher=yfinance_fetch,
        stooq_fetcher=stooq,
    )

    assert calls == [
        ("yahoo", "NVDA"),
        ("yfinance", "NVDA", date(2026, 5, 31), date(2026, 6, 2)),
    ]
    assert list(frame["date"]) == [date(2026, 5, 31), date(2026, 6, 2)]
    assert frame.loc[0, "provider"] == "yfinance"


def test_fetch_price_history_falls_back_when_provider_has_no_rows_in_window():
    def yahoo(symbol: str):
        return pd.DataFrame([_price_row(date(2025, 1, 1), provider="yahoo-chart")])

    def yfinance_fetch(symbol: str, *, start_date: date | None = None, end_date: date | None = None):
        return pd.DataFrame([_price_row(date(2026, 6, 1), provider="yfinance")])

    frame = fetch_price_history(
        "NVDA",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 2),
        yahoo_fetcher=yahoo,
        yfinance_fetcher=yfinance_fetch,
    )

    assert list(frame["date"]) == [date(2026, 6, 1)]
    assert frame.loc[0, "provider"] == "yfinance"


def test_fetch_price_history_falls_back_when_provider_does_not_cover_requested_start():
    calls = []

    def yahoo(symbol: str):
        calls.append(("yahoo", symbol))
        return pd.DataFrame(
            [
                _price_row(date(2025, 9, 15), provider="yahoo-chart"),
                _price_row(date(2026, 6, 2), provider="yahoo-chart"),
            ]
        )

    def yfinance_fetch(symbol: str, *, start_date: date | None = None, end_date: date | None = None):
        calls.append(("yfinance", symbol, start_date, end_date))
        return pd.DataFrame(
            [
                _price_row(date(2021, 6, 3), provider="yfinance"),
                _price_row(date(2026, 6, 2), provider="yfinance"),
            ]
        )

    frame = fetch_price_history(
        "NVDA",
        start_date=date(2021, 6, 3),
        end_date=date(2026, 6, 2),
        yahoo_fetcher=yahoo,
        yfinance_fetcher=yfinance_fetch,
    )

    assert calls == [
        ("yahoo", "NVDA"),
        ("yfinance", "NVDA", date(2021, 6, 3), date(2026, 6, 2)),
    ]
    assert list(frame["date"]) == [date(2021, 6, 3), date(2026, 6, 2)]
    assert frame.loc[0, "provider"] == "yfinance"


def test_normalize_yfinance_history_maps_sdk_frame_to_db_columns():
    raw = pd.DataFrame(
        {
            "Date": ["2026-05-28", "2026-05-29"],
            "Open": [100.0, 102.0],
            "High": [104.0, 106.0],
            "Low": [99.0, 101.0],
            "Close": [103.0, 105.0],
            "Adj Close": [102.5, 104.5],
            "Volume": [1000, 1200],
        }
    )

    frame = normalize_yfinance_history("NVDA", raw, currency="USD")

    assert list(frame.columns) == [
        "date",
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "volume",
        "currency",
        "provider",
    ]
    assert frame.loc[0, "date"].isoformat() == "2026-05-28"
    assert frame.loc[1, "adj_close"] == 104.5
    assert frame.loc[0, "currency"] == "USD"
    assert frame.loc[0, "provider"] == "yfinance"


def test_fetch_price_history_raises_clear_error_when_all_providers_fail():
    def fail(name: str):
        def _inner(symbol: str):
            raise PriceFetchError(f"{name} failed for {symbol}")

        return _inner

    try:
        fetch_price_history(
            "NVDA",
            yahoo_fetcher=fail("yahoo"),
            yfinance_fetcher=fail("yfinance"),
            stooq_fetcher=fail("stooq"),
        )
    except PriceFetchError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected PriceFetchError")

    assert "NVDA: all price providers failed" in message
    assert "yahoo failed" in message
    assert "yfinance failed" in message
    assert "stooq failed" in message


def test_validate_ticker_symbol_accepts_provider_with_real_rows():
    def fetcher(symbol: str):
        assert symbol == "NVDA"
        return pd.DataFrame([_price_row(date(2026, 6, 1), provider="yahoo-chart")])

    result = validate_ticker_symbol(" nvda ", history_fetcher=fetcher)

    assert result == {"symbol": "NVDA", "valid": True, "provider": "yahoo-chart"}


def test_validate_ticker_symbol_rejects_missing_provider_rows():
    def fetcher(symbol: str):
        assert symbol == "NOTREAL"
        raise PriceFetchError("NOTREAL: all price providers failed")

    result = validate_ticker_symbol("notreal", history_fetcher=fetcher)

    assert result == {"symbol": "NOTREAL", "valid": False, "reason": "ticker_not_found"}


def test_validate_ticker_symbol_suggests_samsung_electronics_for_common_typo():
    def fetcher(symbol: str):
        assert symbol == "009530.KS"
        raise PriceFetchError("009530.KS: all price providers failed")

    result = validate_ticker_symbol("009530.KS", history_fetcher=fetcher, suggestion_searcher=lambda query, limit: [])

    assert result == {
        "symbol": "009530.KS",
        "valid": False,
        "reason": "ticker_not_found",
        "suggestion": "005930.KS",
        "suggestion_label": "삼성전자",
        "suggestions": [
            {
                "symbol": "005930.KS",
                "name": "삼성전자",
                "exchange": "KSC",
                "quote_type": "EQUITY",
            }
        ],
    }


def test_search_ticker_suggestions_uses_yfinance_quote_results():
    def searcher(query: str, limit: int):
        assert query == "Samsung Electronics"
        assert limit == 5
        return [
            {
                "symbol": "005930.KS",
                "shortname": "SamsungElec",
                "longname": "Samsung Electronics Co., Ltd.",
                "exchange": "KSC",
                "quoteType": "EQUITY",
            },
            {
                "symbol": "SSNLF",
                "shortname": "SAMSUNG ELECTRONICS CO",
                "longname": "Samsung Electronics Co., Ltd.",
                "exchange": "PNK",
                "quoteType": "EQUITY",
            },
        ]

    suggestions = search_ticker_suggestions("Samsung Electronics", searcher=searcher, limit=5)

    assert suggestions == [
        {
            "symbol": "005930.KS",
            "name": "Samsung Electronics Co., Ltd.",
            "exchange": "KSC",
            "quote_type": "EQUITY",
        },
        {
            "symbol": "SSNLF",
            "name": "SAMSUNG ELECTRONICS CO",
            "exchange": "PNK",
            "quote_type": "EQUITY",
        },
    ]


def test_validate_ticker_symbol_suggests_results_for_company_name_search():
    def fetcher(symbol: str):
        assert symbol == "SAMSUNG ELECTRONICS"
        raise PriceFetchError("SAMSUNG ELECTRONICS: all price providers failed")

    def searcher(query: str, limit: int):
        assert query == "Samsung Electronics"
        assert limit == 5
        return [
            {
                "symbol": "005930.KS",
                "shortname": "SamsungElec",
                "longname": "Samsung Electronics Co., Ltd.",
                "exchange": "KSC",
                "quoteType": "EQUITY",
            }
        ]

    result = validate_ticker_symbol("Samsung Electronics", history_fetcher=fetcher, suggestion_searcher=searcher)

    assert result == {
        "symbol": "SAMSUNG ELECTRONICS",
        "valid": False,
        "reason": "ticker_not_found",
        "suggestion": "005930.KS",
        "suggestion_label": "Samsung Electronics Co., Ltd.",
        "suggestions": [
            {
                "symbol": "005930.KS",
                "name": "Samsung Electronics Co., Ltd.",
                "exchange": "KSC",
                "quote_type": "EQUITY",
            }
        ],
    }


def test_validate_ticker_symbol_suggests_korean_alias_search():
    def fetcher(symbol: str):
        assert symbol == "삼성전자"
        raise PriceFetchError("삼성전자: all price providers failed")

    def searcher(query: str, limit: int):
        assert query == "Samsung Electronics"
        assert limit == 5
        return []

    result = validate_ticker_symbol("삼성전자", history_fetcher=fetcher, suggestion_searcher=searcher)

    assert result["suggestion"] == "005930.KS"
    assert result["suggestion_label"] == "삼성전자"
    assert result["suggestions"][:1] == [
        {
            "symbol": "005930.KS",
            "name": "삼성전자",
            "exchange": "KSC",
            "quote_type": "EQUITY",
        }
    ]


def test_fetch_stooq_history_wraps_malformed_provider_response(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return b"malformed provider response"

    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: Response())
    monkeypatch.setattr(pd, "read_csv", lambda value: (_ for _ in ()).throw(pd.errors.ParserError("bad csv")))

    try:
        fetch_stooq_history("NOTREALXYZ123")
    except PriceFetchError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected PriceFetchError")

    assert "NOTREALXYZ123: stooq returned malformed rows" in message
