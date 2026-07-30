"""Tests for scripts.lib.db_base — shared helpers."""

import json
from datetime import UTC, datetime

import pandas as pd

from scripts.lib.db_base import (
    _collection_status,
    _profile_slug,
    _research_source_type,
    build_indicator_rows,
    build_price_rows,
    hashlib_sha,
    json_dumps,
    none_if_na,
)

# ---------------------------------------------------------------------------
# none_if_na
# ---------------------------------------------------------------------------


def test_none_if_na_nan():
    assert none_if_na(float("nan")) is None


def test_none_if_na_normal():
    assert none_if_na(42) == 42
    assert none_if_na("hello") == "hello"
    assert none_if_na(None) is None


# ---------------------------------------------------------------------------
# json_dumps
# ---------------------------------------------------------------------------


def test_json_dumps_none():
    assert json_dumps(None) == "{}"


def test_json_dumps_dict():
    result = json.loads(json_dumps({"a": 1, "b": "한글"}))
    assert result == {"a": 1, "b": "한글"}


def test_json_dumps_datetime():
    dt = datetime(2026, 1, 1, tzinfo=UTC)
    result = json_dumps({"ts": dt})
    assert "2026" in result


# ---------------------------------------------------------------------------
# _research_source_type
# ---------------------------------------------------------------------------


def test_research_source_type():
    assert _research_source_type("news") == "news"
    assert _research_source_type("disclosure") == "disclosure"
    assert _research_source_type("db_price_indicator") == "indicator"
    assert _research_source_type(None) == "manual"
    assert _research_source_type("unknown") == "manual"


# ---------------------------------------------------------------------------
# _collection_status
# ---------------------------------------------------------------------------


def test_collection_status():
    assert _collection_status(0, False) == "missing"
    assert _collection_status(10, True) == "synthetic"
    assert _collection_status(10, False) == "collected"


# ---------------------------------------------------------------------------
# _profile_slug
# ---------------------------------------------------------------------------


def test_profile_slug_normal():
    assert _profile_slug("user-123") == "user-123"


def test_profile_slug_special_chars():
    assert _profile_slug("user@example.com") == "user-example-com"


def test_profile_slug_empty():
    slug = _profile_slug("!!!")
    assert slug.startswith("profile-")


# ---------------------------------------------------------------------------
# build_price_rows
# ---------------------------------------------------------------------------


def test_build_price_rows():
    frame = pd.DataFrame(
        [
            {
                "date": "2026-01-01",
                "open": 100.0,
                "high": 110.0,
                "low": 95.0,
                "close": 105.0,
                "adj_close": 105.0,
                "volume": 1000,
                "source": "yfinance",
                "currency": "KRW",
            }
        ]
    )
    rows = build_price_rows(1, frame)
    assert len(rows) == 1
    row = rows[0]
    assert row["asset_id"] == 1
    assert row["close"] == 105.0
    assert row["adj_close"] == 105.0
    assert row["source"] == "yfinance"
    assert row["provider"] == "yfinance"
    assert row["currency"] == "KRW"
    assert isinstance(row["fetched_at"], datetime)


def test_build_price_rows_nan_handling():
    frame = pd.DataFrame([{"date": "2026-01-01", "open": float("nan"), "close": 50.0}])
    rows = build_price_rows(2, frame)
    assert rows[0]["open"] is None
    assert rows[0]["close"] == 50.0


# ---------------------------------------------------------------------------
# build_indicator_rows
# ---------------------------------------------------------------------------


def test_build_indicator_rows():
    frame = pd.DataFrame(
        [{"date": "2026-01-01", "return_1d": 0.02, "ma5": 100.0, "rsi14": 55.0, "vol20": 0.3}]
    )
    rows = build_indicator_rows(1, frame)
    assert len(rows) == 1
    row = rows[0]
    assert row["asset_id"] == 1
    assert row["return_1d"] == 0.02
    assert row["ma5"] == 100.0
    assert row["rsi14"] == 55.0
    assert row["return_1w"] is None  # not in frame


# ---------------------------------------------------------------------------
# hashlib_sha
# ---------------------------------------------------------------------------


def test_hashlib_sha():
    result = hashlib_sha("test")
    assert len(result) == 64
    assert result == hashlib_sha("test")
    assert result != hashlib_sha("other")
