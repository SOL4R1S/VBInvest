"""Shared helpers for VBinvestDB mixins — extracted from db.py."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any

import pandas as pd


def none_if_na(value: Any) -> Any:
    return None if pd.isna(value) else value


def json_dumps(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False, default=str)


def _research_source_type(kind: str | None) -> str:
    if kind == "news":
        return "news"
    if kind == "disclosure":
        return "disclosure"
    if kind == "db_price_indicator":
        return "indicator"
    return "manual"


def _collection_status(price_rows: int, has_synthetic: bool) -> str:
    if price_rows == 0:
        return "missing"
    if has_synthetic:
        return "synthetic"
    return "collected"


def _profile_slug(auth_user_id: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_-]+", "-", auth_user_id).strip("-").lower()
    return value or f"profile-{uuid.uuid4()}"


def build_price_rows(asset_id: int, frame: pd.DataFrame, fetched_at: datetime | None = None) -> list[dict[str, Any]]:
    fetched = fetched_at or datetime.now(UTC)
    rows: list[dict[str, Any]] = []
    for record in frame.to_dict("records"):
        provider = record.get("provider") or record.get("source")
        rows.append(
            {
                "asset_id": asset_id,
                "date": record["date"],
                "open": none_if_na(record.get("open")),
                "high": none_if_na(record.get("high")),
                "low": none_if_na(record.get("low")),
                "close": none_if_na(record.get("close")),
                "adj_close": none_if_na(record.get("adj_close")),
                "volume": none_if_na(record.get("volume")),
                "source": provider,
                "provider": provider,
                "currency": none_if_na(record.get("currency")),
                "fetched_at": fetched,
            }
        )
    return rows


def build_indicator_rows(asset_id: int, frame: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    indicator_columns = [
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
    ]
    for record in frame.to_dict("records"):
        row: dict[str, Any] = {"asset_id": asset_id, "date": record["date"]}
        for col in indicator_columns:
            row[col] = none_if_na(record.get(col))
        rows.append(row)
    return rows


def hashlib_sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
